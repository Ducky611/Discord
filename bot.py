import discord
from discord.ext import commands, tasks
import json
import os
import time

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "data.json"

# ------------------------
# Data Handling
# ------------------------

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

def ensure_user(guild_id, user_id):
    if guild_id not in data:
        data[guild_id] = {}

    if user_id not in data[guild_id]:
        data[guild_id][user_id] = {
            "total_seconds": 0,
            "clocked_in": False,
            "clock_in_time": None,
            "brownie_points": 0,
            "progress_counter": 0
        }

    return data[guild_id][user_id]

# ------------------------
# Utility Functions
# ------------------------

def format_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{int(hours)}h {int(minutes)}m"

def messages_required(points):
    return 10 + (points * 2)

# ------------------------
# Clock Buttons
# ------------------------

class ClockView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Clock In", style=discord.ButtonStyle.green, custom_id="clock_in")
    async def clock_in(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = str(interaction.guild.id)
        user_id = str(interaction.user.id)

        user = ensure_user(guild_id, user_id)

        if user["clocked_in"]:
            await interaction.response.send_message("❗ You're already clocked in.", ephemeral=True)
            return

        user["clocked_in"] = True
        user["clock_in_time"] = time.time()
        save_data(data)

        await interaction.response.send_message("✅ You clocked in!", ephemeral=True)

    @discord.ui.button(label="Clock Out", style=discord.ButtonStyle.red, custom_id="clock_out")
    async def clock_out(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = str(interaction.guild.id)
        user_id = str(interaction.user.id)

        user = ensure_user(guild_id, user_id)

        if not user["clocked_in"]:
            await interaction.response.send_message("❗ You're not clocked in.", ephemeral=True)
            return

        worked = time.time() - user["clock_in_time"]
        user["total_seconds"] += worked
        user["clocked_in"] = False
        user["clock_in_time"] = None
        user["progress_counter"] += 1

        required = messages_required(user["brownie_points"])

        if user["progress_counter"] >= required:
            user["brownie_points"] += 1
            user["progress_counter"] = 0

        save_data(data)

        await interaction.response.send_message(
            f"🕒 Clocked out!\nYou worked {format_time(worked)}",
            ephemeral=True
        )

# ------------------------
# Commands
# ------------------------

@bot.command()
@commands.has_permissions(administrator=True)
async def clockpanel(ctx):
    embed = discord.Embed(
        title="🕒 Staff Clock Panel",
        description="Use the buttons below to clock in or clock out.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed, view=ClockView())

@bot.command()
async def stat(ctx, member: discord.Member = None):
    member = member or ctx.author

    guild_id = str(ctx.guild.id)
    user_id = str(member.id)

    user = ensure_user(guild_id, user_id)
    required = messages_required(user["brownie_points"])

    embed = discord.Embed(
        title=f"📊 {member.display_name}'s Stats",
        color=discord.Color.purple()
    )

    embed.add_field(
        name="Brownie Points",
        value=f"{user['brownie_points']}",
        inline=False
    )

    embed.add_field(
        name="Progress",
        value=f"{user['progress_counter']} / {required}",
        inline=False
    )

    embed.add_field(
        name="Hours Worked",
        value=format_time(user["total_seconds"]),
        inline=False
    )

    await ctx.send(embed=embed)

@bot.command()
async def leaderboard(ctx):
    guild_id = str(ctx.guild.id)

    if guild_id not in data:
        await ctx.send("No data yet.")
        return

    users = data[guild_id]

    sorted_users = sorted(
        users.items(),
        key=lambda x: x[1]["total_seconds"],
        reverse=True
    )

    embed = discord.Embed(
        title="🏆 Leaderboard",
        color=discord.Color.gold()
    )

    for i, (user_id, stats) in enumerate(sorted_users[:10], start=1):
        member = ctx.guild.get_member(int(user_id))
        if member:
            embed.add_field(
                name=f"{i}. {member.display_name}",
                value=format_time(stats["total_seconds"]),
                inline=False
            )

    await ctx.send(embed=embed)

# ------------------------
# Ready Event
# ------------------------

@bot.event
async def on_ready():
    bot.add_view(ClockView())  # persistent buttons
    print(f"✅ Logged in as {bot.user}")

# ------------------------
# Run
# ------------------------

if TOKEN is None:
    print("❌ TOKEN environment variable not set.")
else:
    bot.run(TOKEN)
