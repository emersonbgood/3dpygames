from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import random
import os
import math
import sys

# Start engine
app = Ursina()
window.fps_counter.enabled = False

# Global Game States
health = 100
gold = 10
inventory = []
game_paused = False
dragon_slain = False
village_spawned = False  # Will be spawned at startup
has_house = False
is_night = False
chest_opened = False

# Screen Information Labels (No emojis to ensure no terminal warnings)
hp_text = Text(text=f'HP: {health}', position=(-0.8, 0.45), scale=2, color=color.pink)
gold_text = Text(text=f'GOLD: {gold}g', position=(-0.8, 0.38), scale=2, color=color.yellow)
story_text = Text(
    text='[QUEST] Follow the red dot cursor to the GOLD block to grab your Key!',
    position=(-0.6, -0.25), scale=1.3, background=True
)

# Render Hotbar Elements
hotbar_slots = []
slot_texts = []
for i in range(9):
    slot = Entity(
        parent=camera.ui, model='quad', color=color.gray,
        scale=(0.08, 0.08), position=(-0.36 + (i * 0.09), -0.42)
    )
    hotbar_slots.append(slot)
    stext = Text(text='', parent=slot, scale=1.2, position=(-0.2, 0), color=color.white)
    slot_texts.append(stext)

def update_ui():
    global health, gold
    hp_text.text = f'HP: {health}'
    gold_text.text = f'GOLD: {gold}g'
    for i in range(9):
        if i < len(inventory):
            hotbar_slots[i].color = color.dark_gray
            slot_texts[i].text = inventory[i][:3].upper()
        else:
            hotbar_slots[i].color = color.gray
            slot_texts[i].text = ''

# --- 360-Degree Mountain Bowl Map Mesh Generation ---
terrain_size = 100  # Expanded from 80
vertices, triangles, uvs, colors = [], [], [], []

def get_height(x, z):
    center_x, center_z = terrain_size / 2, terrain_size / 2
    dist_from_center = math.sqrt((x - center_x)**2 + (z - center_z)**2)
    base_hills = (math.sin(x * 0.2) + math.cos(z * 0.2)) * 1.0
    
    if dist_from_center > 42:  # Expanded from 32
        mountain_lift = (dist_from_center - 42) * 4.0
        if 47 < x < 53 and z > 78:
            return base_hills
        return base_hills + mountain_lift
    return base_hills

for z in range(terrain_size):
    for x in range(terrain_size):
        y = get_height(x, z)
        vertices.append((x, y, z))
        uvs.append((x / terrain_size, z / terrain_size))
        
        center_x, center_z = terrain_size / 2, terrain_size / 2
        dist = math.sqrt((x - center_x)**2 + (z - center_z)**2)
        if dist > 46:  # Expanded from 36
            colors.append(color.white)
        elif dist > 42:  # Expanded from 32
            colors.append(color.gray)
        else:
            colors.append(color.green)

for z in range(terrain_size - 1):
    for x in range(terrain_size - 1):
        root = x + (z * terrain_size)
        triangles.append((root, root + 1, root + terrain_size))
        triangles.append((root + 1, root + terrain_size + 1, root + terrain_size))

terrain_mesh = Mesh(vertices=vertices, triangles=triangles, uvs=uvs, colors=colors)
terrain = Entity(model=terrain_mesh, texture='white_cube', collider='mesh')

# --- Spawn Coordinate Targets ---
spawn_x, spawn_z = 40, 35
spawn_y = get_height(spawn_x, spawn_z)

shaft_x, shaft_y, shaft_z = 40, get_height(40, 70), 70
shop_x, shop_z = 34, 34
shop_y = get_height(shop_x, shop_z)

# Shop Counter
Entity(model='cube', color=color.brown, scale=(3, 0.2, 2), position=(shop_x, shop_y + 0.1, shop_z), collider='box')
for offset_x in [-1.4, 1.4]:
    for offset_z in [-0.9, 0.9]:
        Entity(model='cube', color=color.brown, scale=(0.1, 2, 0.1), position=(shop_x + offset_x, shop_y + 1, shop_z + offset_z), collider='box')
Entity(model='cube', color=color.red, scale=(3.2, 0.1, 2.2), position=(shop_x, shop_y + 2, shop_z))

# Cave Framework
for offset_y in [0.5, 1.5, 2.5]:
    Entity(model='cube', color=color.orange, scale=(0.2, 1, 0.2), position=(shaft_x - 1.5, shaft_y + offset_y, shaft_z - 1), collider='box')
    Entity(model='cube', color=color.orange, scale=(0.2, 1, 0.2), position=(shaft_x + 1.5, shaft_y + offset_y, shaft_z - 1), collider='box')
Entity(model='cube', color=color.orange, scale=(3.2, 0.2, 0.4), position=(shaft_x, shaft_y + 3.0, shaft_z - 1), collider='box')

# Quest World Map Elements
key_obj = Entity(model='cube', color=color.gold, texture='gold_block.png', scale=0.6, position=(30, get_height(30, 30) + 0.5, 30), collider='box')
merchant_obj = Entity(model='cube', color=color.azure, texture='white_cube', scale=(0.8, 1.6, 0.8), position=(shop_x, shop_y + 0.9, shop_z), collider='box')
lock_rock_obj = Entity(model='cube', color=color.dark_gray, texture='white_cube', scale=(3.0, 3.5, 0.8), position=(shaft_x, shaft_y + 1.6, shaft_z - 1), collider='box')
dragon_obj = Entity(model='cube', color=color.black, texture='white_cube', scale=2.5, position=(shaft_x, shaft_y + 1.5, shaft_z + 4.0), collider='box')
cave_roof = Entity(model='cube', color=color.dark_gray, texture='white_cube', scale=(5.5, 0.4, 10.0), position=(shaft_x, shaft_y + 4.8, shaft_z + 2.0), collider='box')

# --- Hidden Treasure Chest ---
chest_master = Entity(position=(spawn_x, spawn_y - 4.0, spawn_z))
chest_base = Entity(parent=chest_master, model='cube', color=color.rgb(110, 60, 30), scale=(1.2, 0.5, 0.8), position=(0, 0.25, 0), collider='box', texture='oak_planks.png')
chest_lid = Entity(parent=chest_master, model='cube', color=color.rgb(139, 69, 19), scale=(1.22, 0.25, 0.82), position=(0, 0.5, 0.4), origin=(0, 0, -0.4), texture='oak_planks.png')
mc_gold_block = Entity(parent=chest_master, model='cube', texture='gold_block.png', color=color.gold, scale=(0.25, 0.25, 0.25), position=(-0.2, 0.25, 0), enabled=False)
mc_diamond_item = Entity(parent=chest_master, model='quad', texture='diamond.png', color=color.cyan, scale=(0.25, 0.25), position=(0.2, 0.25, 0), enabled=False)
glow_ring = Entity(model='cube', color=color.Color(60, 1, 1, 0.2), scale=(2.5, 12, 2.5), position=(spawn_x, spawn_y + 4, spawn_z), enabled=False)

villagers_list = []
village_structures = []

# Player Initialization Elements
player = FirstPersonController(position=(spawn_x, spawn_y + 2.0, spawn_z))
player.cursor.color = color.red
sky_box = Sky(color=color.cyan)
sun_light = DirectionalLight(y=5, z=-5, rotation=(45, 45, 45))

def distance_to(entity):
    """Calculates the exact math distance between the player and an entity."""
    return math.sqrt((player.x - entity.x)**2 + (player.y - entity.y)**2 + (player.z - entity.z)**2)

def update():
    global is_night, has_house
    
    # 1. WORLD BORDER LOCK - Expanded
    center_x, center_z = terrain_size / 2, terrain_size / 2
    current_dist = math.sqrt((player.x - center_x)**2 + (player.z - center_z)**2)
    if current_dist > 43.5:  # Expanded from 33.5
        angle = math.atan2(player.z - center_z, player.x - center_x)
        player.x = center_x + math.cos(angle) * 43.4
        player.z = center_z + math.sin(angle) * 43.4
        story_text.text = "[WORLD BORDER] The mountain peaks are too snowy to scale!"

    # 2. HOUSE DETECTOR NIGHT TRIGGER
    if has_house and not is_night:
        if 48 < player.x < 52 and 36 < player.z < 40:
            is_night = True
            sky_box.color = color.black
            sun_light.color = color.Color(240, 0.2, 0.1)
            story_text.text = "[NIGHT TIME] It became dark! Go sleep in your blue bed block."

def input(key):
    global health, gold, inventory, dragon_slain, village_spawned, has_house, chest_opened
    
    # CRITICAL EXIT FIX: Shift + Q completely closes the game window safely
    if key == 'shift+q':
        application.quit()
        quit()

    if key == 'left mouse down':
        # 1. Interaction: Golden Key Block
        if key_obj and key_obj.enabled and distance_to(key_obj) < 4.0:
            if 'Key' not in inventory:
                inventory.append('Key')
                key_obj.disable()
                destroy(key_obj)
                story_text.text = "[KEY OBTAINED] Go walk right up to the dark gray rock door to unlock it!"
                update_ui()
                return

        # 2. Interaction: Merchant NPC Shop Block (SEPARATE from villagers)
        if merchant_obj and distance_to(merchant_obj) < 4.0:
            if 'Sword' in inventory and gold < 200:
                inventory.remove('Sword')
                gold += 50
                update_ui()
                story_text.text = "Merchant: Here's 50g for that blade! Good luck defeating the dragon!"
            elif gold >= 10 and 'Sword' not in inventory:
                gold -= 10
                inventory.append('Sword')
                story_text.text = "[SWORD PURCHASED] Blade acquired! Go slay the dragon in the mountain cave!"
                update_ui()
            elif 'Sword' in inventory and gold >= 200:
                story_text.text = "Merchant: You look rich enough! Go get that dragon yourself!"
            else:
                story_text.text = "Merchant: Swords cost 10 gold!"
            return

        # 3. Interaction: Locked Charcoal Rock Door
        if lock_rock_obj and lock_rock_obj.enabled and distance_to(lock_rock_obj) < 5.0:
            if 'Key' in inventory:
                inventory.remove('Key')
                lock_rock_obj.disable()
                destroy(lock_rock_obj)
                story_text.text = "[UNLOCKED] The rock door crumbles! Enter the cave tunnel and hit the dragon!"
                update_ui()
            else:
                story_text.text = "[LOCKED] Walk right up to the drawing. You need an Iron Key!"
            return

        # 4. Interaction: Black Dragon Boss
        if dragon_obj and dragon_obj.enabled and distance_to(dragon_obj) < 6.0:
            if 'Sword' in inventory:
                dragon_pos = dragon_obj.position
                dragon_obj.disable()
                destroy(dragon_obj)
                dragon_slain = True
                story_text.text = "[BOOM!] Dragon defeated! Run back to the center spawn area to get your reward!"
                
                exp = Entity(model='quad', color=color.orange, scale=4.5, position=dragon_pos)
                exp.look_at(player)
                invoke(destroy, exp, delay=1.5)
                invoke(raise_chest_from_ground, delay=1.5)
            else:
                damage = random.randint(20, 35)
                health -= damage
                update_ui()
                if health <= 0:
                    story_text.text = "[GAME OVER] Slain by dragon! Hold Shift + Q to exit."
                    player.disable()
                else:
                    story_text.text = f"[HURT] The dragon hit you for {damage} damage! Go buy a sword from the merchant!"
            return

        # 5. Interaction: Surfaced Loot Chest (FIXED - Check chest_opened and use parent entity)
        if chest_master and dragon_slain and distance_to(chest_master) < 5.0 and not chest_opened:
            chest_lid.rotation_x = -65
            mc_gold_block.enabled = True
            mc_diamond_item.enabled = True
            gold += 100
            chest_opened = True
            update_ui()
            story_text.text = "[CHEST OPENED] You looted gold and diamonds! (+100g) Trade with the villagers!"
            return

        # 6. Interaction: Village NPCs and Trades
        for villager in villagers_list:
            if distance_to(villager) < 4.0:
                handle_villager_trade(villager)
                return

        # 7. Interaction: Village Well
        for well in village_structures:
            if well.name == "well" and distance_to(well) < 3.0:
                story_text.text = "You rest by the well. The cool water refreshes you. (+20 HP)"
                health = min(100, health + 20)
                update_ui()
                return

        # 8. Interaction: Blue Bed Block inside bought House
        if has_house and is_night:
            for struct in village_structures:
                if struct.name == "bed_block" and distance_to(struct) < 3.5:
                    story_text.text = "ZZZ... You fall asleep peacefully. GAME COMPLETED! Hold Shift + Q to exit."
                    player.disable()
                    return


def handle_villager_trade(villager):
    """Handle all NPC trades based on inventory and gold."""
    global health, gold, inventory, has_house
    
    # Blacksmith: Buy sword for 50g, sell items
    if villager.color == color.black:  # Blacksmith
        if 'Sword' in inventory and gold < 200:
            inventory.remove('Sword')
            gold += 50
            update_ui()
            story_text.text = "Blacksmith: Fine blade! I'll give you 50g for it."
        elif 'Armor' not in inventory and gold >= 80:
            response = story_text.text
            story_text.text = "Blacksmith: I have armor for 80g. Click again to buy."
            if response == "Blacksmith: I have armor for 80g. Click again to buy.":
                gold -= 80
                inventory.append('Armor')
                update_ui()
                story_text.text = "Blacksmith: Good choice! You're well-protected now."
        else:
            story_text.text = "Blacksmith: Need anything forged or repaired?"
    
    # Healer: Sell potions
    elif villager.color == color.green:  # Healer
        if gold >= 30 and 'Potion' not in inventory:
            gold -= 30
            inventory.append('Potion')
            update_ui()
            story_text.text = "[Apothocary]: Here's a healing potion! Use it when you need it."
        elif 'Potion' in inventory:
            inventory.remove('Potion')
            health = min(100, health + 50)
            update_ui()
            story_text.text = "[Apothocary]: I hope that potion helps! (+50 HP)"
        else:
            story_text.text = "[Apothocary]: Potions cost 30g. Stay healthy, friend!"
    
    # House Seller: Main village trader
    elif villager.color == color.azure:  # Village Trader/House Seller
        if gold >= 200 and not has_house:
            gold -= 200
            has_house = True
            update_ui()
            story_text.text = "Village Elder: You bought the house! Walk inside the brick walls."
            for structure in village_structures:
                if structure.name in ["house_wall", "house_roof", "bed_block"]:
                    structure.collision = 'none'  # Allow walking through the house structures
        elif has_house:
            story_text.text = "Village Elder: Welcome home! The whole village respects you now."
        else:
            story_text.text = "Village Elder: I have a fine house for 200g!"

def raise_chest_from_ground():
    """Raise the treasure chest from underground when dragon is defeated."""
    chest_master.y = spawn_y + 0.5  # Raise to ground level
    story_text.text = "[CHEST RISING] The buried treasure rises from the ground! Click it to open!"


def spawn_village():
    """Spawn the village with multiple traders and structures."""
    global village_spawned, villagers_list, village_structures
    
    village_spawned = True
    glow_ring.enabled = True
    chest_master.y = spawn_y
    story_text.text = "[VILLAGE] A peaceful village surrounds you! Explore and trade with NPCs."
    
    # Village center coordinates (expanded area)
    village_center_x, village_center_z = spawn_x + 8, spawn_z + 8
    vy = get_height(village_center_x, village_center_z)
    
    # 1. VILLAGE WELL (Center attraction)
    well_post1 = Entity(model='cube', color=color.brown, scale=(0.15, 2.5, 0.15), position=(village_center_x - 1.0, vy + 1.25, village_center_z), collider='box')
    well_post2 = Entity(model='cube', color=color.brown, scale=(0.15, 2.5, 0.15), position=(village_center_x + 1.0, vy + 1.25, village_center_z), collider='box')
    well_roof = Entity(model='cube', color=color.brown, scale=(2.5, 0.3, 0.4), position=(village_center_x, vy + 2.7, village_center_z), collider='box')
    well_bucket = Entity(name="well", model='cube', color=color.gray, scale=(0.5, 0.5, 0.5), position=(village_center_x, vy + 1.2, village_center_z), collider='box')
    village_structures.extend([well_post1, well_post2, well_roof, well_bucket])
    
    # 2. MAIN HOUSE (Buyable, blue bed inside)
    hx, hz = village_center_x - 5, village_center_z - 5
    hy = get_height(hx, hz)
    house_wall = Entity(name="house_wall", model='cube', color=color.white, scale=(4, 3, 4), position=(hx, hy + 1.5, hz), collider='box', texture='bricks.png')
    house_roof = Entity(name="house_roof", model='cube', color=color.white, scale=(4.5, 0.6, 4.5), position=(hx, hy + 3.2, hz), collider='box', texture='black_concrete.png')
    house_doorway_cut = Entity(model='cube', color=color.green, scale=(1.2, 2.2, 4.2), position=(hx, hy + 1.1, hz), collider='box')
    destroy(house_doorway_cut)
    bed = Entity(name="bed_block", model='cube', color=color.blue, scale=(1.2, 0.4, 2.0), position=(hx + 1, hy + 0.2, hz + 0.8), collider='box', texture='blue_wool.png')
    village_structures.extend([house_wall, house_roof, bed])
    
    # 3. BLACKSMITH SHOP (Dark gray, sells armor)
    bx, bz = village_center_x + 5, village_center_z - 5
    by = get_height(bx, bz)
    blacksmith_wall = Entity(model='cube', color=color.white, scale=(3, 2.5, 3), position=(bx, by + 1.25, bz), texture='bricks.png')
    blacksmith_roof = Entity(model='cube', color=color.white, scale=(3.3, 0.4, 3.3), position=(bx, by + 2.8, bz), collider='box', texture='black_concrete.png')
    blacksmith_anvil = Entity(model='cube', color=color.gray, scale=(0.8, 0.3, 0.8), position=(bx + 0.5, by + 0.3, bz + 0.5), collider='box', texture='iron_block.png')
    blacksmith_npc = Entity(model='cube', color=color.black, scale=(0.6, 1.6, 0.6), position=(bx, by + 0.8, bz), collider='box')
    villagers_list.append(blacksmith_npc)
    village_structures.extend([blacksmith_wall, blacksmith_roof, blacksmith_anvil])
    
    # 4. HEALER'S HUT (Green, sells potions)
    hx2, hz2 = village_center_x - 5, village_center_z + 5
    hy2 = get_height(hx2, hz2)
    healer_wall = Entity(model='cube', color=color.white, scale=(3, 2.5, 3), position=(hx2, hy2 + 1.25, hz2), texture='bricks.png')
    healer_roof = Entity(model='cube', color=color.white, scale=(3.3, 0.4, 3.3), position=(hx2, hy2 + 2.8, hz2), collider='box', texture='black_concrete.png')
    healer_shelf = Entity(model='cube', color=color.brown, scale=(0.5, 1.2, 2.5), position=(hx2 - 1.2, hy2 + 1.0, hz2), collider='box', texture='oak_planks.png')
    healer_npc = Entity(model='cube', color=color.green, scale=(0.6, 1.6, 0.6), position=(hx2, hy2 + 0.8, hz2), collider='box')
    villagers_list.append(healer_npc)
    village_structures.extend([healer_wall, healer_roof, healer_shelf])
    
    # 5. VILLAGE ELDER'S HALL (Azure, house trader)
    ex, ez = village_center_x + 5, village_center_z + 5
    ey = get_height(ex, ez)
    elder_hall = Entity(model='cube', color=color.white, scale=(4, 3, 4), position=(ex, ey + 1.5, ez), texture='bricks.png')
    elder_roof = Entity(model='cube', color=color.white, scale=(4.5, 0.5, 4.5), position=(ex, ey + 3.2, ez), collider='box', texture='black_concrete.png')
    elder_npc = Entity(model='cube', color=color.azure, scale=(0.7, 1.7, 0.7), position=(ex, ey + 0.85, ez), collider='box')
    villagers_list.append(elder_npc)
    village_structures.extend([elder_hall, elder_roof])


def trigger_victory_spawn():
    """Called after dragon is slain."""
    pass  # Village already spawned at startup now

# Spawn the village immediately at game start
spawn_village()

app.run()
