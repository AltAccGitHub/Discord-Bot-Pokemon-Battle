import discord
import time
from discord.ext import commands, tasks
import random, json, os
with open("master-pokemon-data.json", "r") as f:
    WILD_POKEMON = json.load(f)

with open("master-raid-data.json","r") as f:
    RAID_POKEMON = json.load(f)

battle_selection = {}
duels = {}  # duel_id -> {challenger, opponent, turn, pokemon1, pokemon2}

raid_data = {
    "name" : None,
    "hp" : 0,
    "current_hp" : 0,
    "level" : 0,
    "damage" : 0,
}
# ----- Setup -----
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="b!", intents=intents)

wild_pokemon = None
caught_by = None
caught_bys = None
data_file = "data.json"

# ----- Data Handling -----
def load_data():
    if os.path.exists(data_file):
        with open(data_file, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(data_file, "w") as f:
        json.dump(data, f, indent=4)

def create_pokemon(name):
    base_hp = 30
    base_damage = 10
    base_level = 1
    return {
        "name": name,
        "level": base_level + random.randint(0 , 5),
        "hp": base_hp + random.randint(0 , 15),
        "damage": base_damage + random.randint(0 , 5),
        "xp": 0
    }
def create_raid_pokemon(name):
    base_hp = 100
    base_damage = 50
    base_level = 1
    return{
        "active": False,
        "catch_allow": False,
        'name': name,
        'level': base_level + random.randint(0 , 10),
        'hp': base_hp + random.randint(0 , 15),
        'damage': base_damage + random.randint(0 , 5),
        'xp': 0
    }

async def gain_xp(pokemon, amount, ctx):
    user_id = str(ctx.author.id)
    data = load_data()

    if user_id not in data or not data[user_id]:
        await ctx.send("You have no Pokémon.")
        return

    # Find the matching Pokémon
    for i, p in enumerate(data[user_id]):
        if p["name"] == pokemon["name"] and p["level"] == pokemon["level"]:
            p["xp"] += amount
            leveledUp = False
            old_level = p["level"]

            while p["xp"] >= p["level"] * 10:
                p["xp"] -= p["level"] * 10
                p["level"] += 1
                p["hp"] = 30 + random.randint(0, 10) + p["level"] * 5
                p["damage"] = 5 + random.randint(0, 3) + p["level"] * 2
                leveledUp = True

            data[user_id][i] = p  # Update the Pokémon in the list
            save_data(data)

            await ctx.send(f"{ctx.author.mention} {p['name']} gained {amount} XP!")

            if leveledUp:
                await ctx.send(f"🎉 {p['name']} leveled up to level {p['level']}!")
            return

    await ctx.send("Could not find the matching Pokémon to update XP.")

# ----- Bot Events -----
@bot.event
async def on_ready():
    print(f"Bot is ready: {bot.user}")
    spawn_pokemon.start()
    spawn_raid.start()

# ----- Spawn Pokémon -----
@tasks.loop(minutes=5)
async def spawn_pokemon():
    global wild_pokemon, caught_by
    channel = discord.utils.get(bot.get_all_channels(), name="general")  # Change channel name
    wild_pokemon = random.choice(WILD_POKEMON)
    caught_by = None

    file = discord.File(f"images/{wild_pokemon.lower()}.png", filename="image.png")
    embed = discord.Embed(
        title="A wild Pokémon appeared!", 
        description=f"It's a **{wild_pokemon}**!\nType `b!catch` to catch it!\nIcon made by Roundicon Freebies from www.flaticon.com",
        color=0x00ff0
        )
    embed.set_thumbnail(url="attachment://image.png")
    await channel.send(file=file , embed=embed)

@tasks.loop(hours=1)
async def spawn_raid():
    global raid_pokemon
    channel = discord.utils.get(bot.get_all_channels(), name="raid-boss")
    raid_pokemon = random.choice(RAID_POKEMON)
    raid_data["name"] = raid_pokemon
    raid_data["active"] = True,
    raid_data["catch_allow"] = False,
    hp = 100 + random.randint(0 , 100)
    raid_data["hp"] = hp
    raid_data["max_hp"] = hp

    file = discord.File(f"images/{raid_pokemon.lower()}.png" , filename="image.png")
    embed = discord.Embed(
        title="🔥A wild RAID appeared",
        description=f"It's a **{raid_pokemon}**!\n Type `b!raid` to raid it!\nHP : {raid_data['hp']}\nIcon made by HEKTakun",
        color=0x00ff0,
    )
    print(f'Raid Pokemon {raid_pokemon}')
    embed.set_thumbnail(url='attachment://image.png')
    await channel.send(file=file , embed=embed)

async def spawn_raid_pokemon():
    global caught_by
    if raid_data["catch_allow"]:
        channel = discord.utils.get(bot.get_all_channels(), name="raid-boss")  # Change channel name
        caught_by = None

        file = discord.File(f"images/{raid_pokemon.lower()}.png", filename="image.png")
        embed = discord.Embed(
            title="A RAID Pokémon appeared!", 
            description=f"It's a **{raid_pokemon}**!\nType `b!raidcatch` to catch it!\nIcon made by HEKTakun",
            color=0x00ff0
            )
        embed.set_thumbnail(url="attachment://image.png")
        await channel.send(file=file , embed=embed)

# ----- Catch Command -----
@bot.command()
async def catch(ctx):
    global wild_pokemon, caught_by
    if not wild_pokemon:
        await ctx.send("There's no Pokémon to catch right now.")
        return

    if caught_by is None:
        caught_by = ctx.author.id
        user_id = str(ctx.author.id)
        data = load_data()
        if user_id not in data:
            data[user_id] = []

        pokemon = create_pokemon(wild_pokemon)
        await gain_xp(pokemon, 5, ctx)  # Gain XP on catch
        data[user_id].append(pokemon)
        save_data(data)

        await ctx.send(f"{ctx.author.mention} caught **{wild_pokemon}**! 🎉")
        print (f"Caught Pokemon : {pokemon['name']} , {pokemon['level']} , {pokemon['xp']}")
        wild_pokemon = None
    else:
        await ctx.send(f"Too late {ctx.author.mention}, someone already caught it!")

@bot.command()
async def raidcatch(ctx):
    global raid_pokemon, caught_bys
    if caught_bys is None and raid_data['catch_allow']:
        if raid_data['catch_allow']:
            caught_bys = ctx.author.id
            user_id = str(ctx.author.id)
            data = load_data()
            if user_id not in data:
                data[user_id] = []

            raid = create_raid_pokemon(raid_pokemon)
            await gain_xp(raid, 5, ctx)  # Gain XP on catch
            data[user_id].append(raid)
            save_data(data)

            await ctx.send(f"{ctx.author.mention} caught **{raid_pokemon}**! 🎉")
            raid_data["catch_allow"] = False
            raid_pokemon = None
        else:
            await ctx.send(f"There is no RAID!! or someone already caught it {ctx.author.mention}!")

# ----- My Pokémon Command -----
@bot.command()
async def mypokemon(ctx):
    user_id = str(ctx.author.id)
    data = load_data()
    if user_id not in data or len(data[user_id]) == 0:
        await ctx.send("You haven't caught any Pokémon yet!")
        return

    desc = ""
    for idx, poke in enumerate(data[user_id], 1):
        desc += f"{idx}. {poke['name']} - Lv{poke['level']} (HP: {poke['hp']}, DMG: {poke['damage']}, XP: {poke['xp']})\n"

    embed = discord.Embed(title=f"{ctx.author.name}'s Pokémon", description=desc, color=0x3498db)
    await ctx.send(embed=embed)

# ----- Fight Command -----
@bot.command()
async def fight(ctx, index: int):
    user_id = str(ctx.author.id)
    data = load_data()

    if user_id not in data or not data[user_id]:
        await ctx.send("You don't have any Pokémon to fight with!")
        return

    if index < 1 or index > len(data[user_id]):
        await ctx.send("Invalid Pokémon number! Use the one from `b!mypokemon`.")
        return

    selected_pokemon = data[user_id][index - 1]
    selected_pokemon["current_hp"] = selected_pokemon["hp"]  # Set current HP for the fight
    if selected_pokemon == data[user_id][index - 1]:
        print(f"Selected Pokémon: {selected_pokemon['name']} Lv. {selected_pokemon['level']} HP : {selected_pokemon['current_hp']}")

    # Save selection to a global battle tracker (we'll make a dict)
    battle_selection[user_id] = selected_pokemon

    await ctx.send(f"{ctx.author.mention} selected **{selected_pokemon['name']}** (Lv. {selected_pokemon['level']}) for battle! 🥊")

@bot.command()
async def duel(ctx, opponent: discord.Member):
    challenger_id = str(ctx.author.id)
    opponent_id = str(opponent.id)

    # Prevent self-dueling
    if challenger_id == opponent_id:
        await ctx.send("You can't duel yourself!")
        return

    # Check if both players have selected Pokémon
    if challenger_id not in battle_selection:
        await ctx.send("You must select your Pokémon using `b!fight <number>` first!")
        return

    if opponent_id not in battle_selection:
        await ctx.send(f"{opponent.mention} hasn't selected their Pokémon yet!")
        return

    # Create a duel ID
    duel_id = f"{challenger_id}_{opponent_id}"
    duels[duel_id] = {
        "challenger": ctx.author,
        "opponent": opponent,
        "turn": challenger_id,
        "pokemon1": battle_selection[challenger_id].copy(),
        "pokemon2": battle_selection[opponent_id].copy(),
        "last_move": time.time()
    }

    await ctx.send(f"{ctx.author.mention} has challenged {opponent.mention} to a Pokémon duel! 🥊\nUse `b!attack` to start!")

@bot.command()
async def attack(ctx):
    user_id = str(ctx.author.id)
    selected_pokemon = battle_selection[user_id]

    # Find the duel the user is in
    duel = None
    duel_id = None
    for did, d in duels.items():
        if d["challenger"].id == ctx.author.id or d["opponent"].id == ctx.author.id:
            duel = d
            duel_id = did
            break

    if not duel:
        await ctx.send("You're not currently in a duel!")
        return

    if duel["turn"] != user_id:
        await ctx.send("It's not your turn!")
        return

    attacker = duel["pokemon1"] if duel["challenger"].id == ctx.author.id else duel["pokemon2"]
    defender = duel["pokemon2"] if duel["challenger"].id == ctx.author.id else duel["pokemon1"]

    damage = attacker["damage"]
    defender["current_hp"] -= damage

    # Send attack result
    await ctx.send(
        f"💥 {attacker['name']} attacks {defender['name']} for {damage} damage!\n"
        f"{defender['name']} HP: {max(0, defender['current_hp'])}/{defender['hp']}"
    )

    # Check for winner
    if defender["current_hp"] <= 0:
        data = load_data()
        await ctx.send(f"🏆 {attacker['name']} wins the duel! {ctx.author.mention} is victorious!")
        del duels[duel_id]
        await gain_xp(selected_pokemon , 10 , ctx)
        await ctx.send(
            f"{attacker['name']} gained 10 XP!\n"
        )
        return

    # Switch turns
    duel["turn"] = str(duel["opponent"].id if duel["turn"] == str(duel['challenger'].id) else duel["challenger"].id)

    if time.time() - duel["last_move"] > 60:  # 60 seconds timeout
        await ctx.send("⏱️ Duel timed out due to inactivity!")
        del duels[duel_id]
        return
    
@bot.command()
async def raid(ctx):
    data = load_data()
    user_id = str(ctx.author.id)

    ## Check first
    if user_id not in data or not data[user_id]:
        await ctx.send("❌ You don't have any Pokémon to fight with!")
        return

    # Ensure the user has selected a Pokémon
    if user_id not in battle_selection:
        await ctx.send("⚔️ Please select a Pokémon first using `b!fight <number>`.")
        return
    
    selected_pokemon = battle_selection[user_id]

    if not raid_data["active"]:
        await ctx.send("❌ There's no active raid right now!")
        return
    
    if user_id not in data:
        await ctx.send("❌ You don't have any Pokémon to fight with!")
        return
    
    # Ensure 'current_hp' exists in selected_pokemon, if not initialize it
    if "current_hp" not in selected_pokemon:
        selected_pokemon["current_hp"] = selected_pokemon["hp"]  # Initialize current_hp to max hp

    # Check if selected Pokémon is still alive
    if selected_pokemon["current_hp"] <= 0:
        await ctx.send(f"💀 {selected_pokemon['name']} has fainted! Please choose another using `b!fight <number>`.")
        return

    # Damage from selected Pokémon
    damage = selected_pokemon["damage"]
    raid_data["hp"] -= damage

    await ctx.send(
        f"💥 {ctx.author.mention}'s **{selected_pokemon['name']}** dealt **{damage}** damage!\n"
        f"🩸 Raid Boss HP: {max(0, raid_data['hp'])}/{raid_data['max_hp']}"
    )

    # Optional: Raid boss counterattack (you can randomize the damage)
    raid_damage = random.randint(5, 30)
    selected_pokemon["current_hp"] -= raid_damage
    await ctx.send(
        f"🔁 The raid boss attacked **{selected_pokemon['name']}** for **{raid_damage}** damage!\n"
        f"❤️ HP: {max(0, selected_pokemon['current_hp'])}/{selected_pokemon['hp']}"
    )

    # If Pokémon fainted
    if selected_pokemon["current_hp"] <= 0:
        await ctx.send(f"💀 **{selected_pokemon['name']}** has fainted and will be removed from your team!")
        for p in data[user_id]:
            if p["name"] == selected_pokemon["name"] and p["level"] == selected_pokemon["level"]:
                data[user_id].remove(p)
                break
        save_data(data)
        del battle_selection[user_id]

        if data[user_id]:
            await ctx.send(f"{ctx.author.mention}, choose another Pokémon using `b!fight <number>`.")
        else:
            await ctx.send(f"{ctx.author.mention}, you have no Pokémon left!")

    # If raid defeated
    if raid_data["hp"] <= 0:
        await ctx.send(f"🎉 **{raid_data['name']}** has been defeated!")
        await gain_xp(selected_pokemon , random.randint(10 , 50) , ctx)
        print 
        raid_data["active"] = False
        raid_data["catch_allow"] = True
        await spawn_raid_pokemon()
# Bot Guides
@bot.command()
async def guide(ctx):
    await ctx.send(
        "Welcome to the Pokémon Battle Bot! Here are some commands you can use:\n"
        "`b!catch` - Catch a wild Pokémon!\n"
        "`b!mypokemon` - View your caught Pokémon!\n"
        "`b!fight <number>` - Select a Pokémon to fight with!\n"
        "`b!duel @user` - Challenge another user to a duel!\n"
        "`b!attack` - Attack in the duel!\n"
        "`b!raid` - Join the Raid!\n"
        "`b!raidcatch` - Catch a RAID Pokemon!\n"
        "Good luck and have fun!\n"
        "Remember to checkout my website :) https://boltbert.netlify.app/"
    )

bot.run("BOT_TOKEN")
