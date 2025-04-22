import discord
import time
from discord.ext import commands, tasks
import random, json, os
with open("master-pokemon-data.json", "r") as f:
    WILD_POKEMON = json.load(f)
battle_selection = {}
duels = {}  # duel_id -> {challenger, opponent, turn, pokemon1, pokemon2}
# ----- Setup -----
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="b!", intents=intents)

wild_pokemon = None
caught_by = None
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

async def gain_xp(pokemon, amount, ctx):
    old_level = pokemon["level"]  # Store level BEFORE adding XP
    pokemon["xp"] += amount

    leveledUp = False
    pokemon["xp"] += amount
    while pokemon["xp"] >= pokemon["level"] * 10:
        pokemon["xp"] -= pokemon["level"] * 10
        pokemon["level"] += 1 + random.randint(0, 5)
        pokemon["hp"] = 30 + random.randint(0, 10) + pokemon["level"] * 5
        pokemon["damage"] = 5 + random.randint(0, 3) + pokemon["level"] * 2
        leveledUp = True
    # Notify if level increased
    if leveledUp:
        await ctx.send(f"{ctx.author.mention} **{pokemon['name']}** leveled up to level {pokemon['level']}! 🎉")
        embed = discord.Embed(
            title=f"🎉 {pokemon['name']} leveled up!",
            description=f"**Level {old_level} ➔ Level {pokemon['level']}**",
            color=0x3498db
        )
        await ctx.send(embed=embed)


# ----- Bot Events -----
@bot.event
async def on_ready():
    print(f"Bot is ready: {bot.user}")
    spawn_pokemon.start()

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
        wild_pokemon = None
    else:
        await ctx.send(f"Too late {ctx.author.mention}, someone already caught it!")

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
        await ctx.send(f"🏆 {attacker['name']} wins the duel! {ctx.author.mention} is victorious!")
        del duels[duel_id]
        await gain_xp(attacker, 10, ctx)
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
        "Good luck and have fun!\n"
        "Remember to checkout my website :) https://boltbert.netlify.app/"
    )

bot.run("BOT_TOKEN")
