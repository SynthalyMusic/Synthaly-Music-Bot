import discord
import os
import requests
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("TOKEN")import discord
import os
import requests
import asyncio
from discord import app_commands
from discord.ext import commands
from discord.ui import View
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='>', intents=intents)

## EMOJIS
SynthalyBG = "<:SMBG:1475991847552942130>"
Spotify = "<:spotify:1475992203674521765>"
AppleMusic = "<:AppleMusic:1476328276753649899>"

## STATE
guild_queues = {}
guild_loops = {}
favorites = {}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

# ---------------- API ----------------
def get_detailed_release(json_data, search_input):
    releases = json_data.get('releases', [])
    match = next((r for r in releases if search_input.lower() in r['title'].lower()), None)
    if match:
        response = requests.get(f"https://music.synthaly.com/api/v1/releases/{match['id']}")
        return response.json()
    return None

# ---------------- PLAYBACK ----------------
async def auto_disconnect(vc, guild_id):
    await asyncio.sleep(180)
    if vc and len(vc.channel.members) == 1:
        await vc.disconnect()
        guild_queues[guild_id] = []
        
def play_next(vc, guild_id):
    if guild_loops.get(guild_id):
        vc.play(vc.source, after=lambda e: play_next(vc, guild_id))
        return

    if guild_queues[guild_id]:
        song = guild_queues[guild_id].pop(0)

        def after(e):
            if guild_queues[guild_id]:
                play_next(vc, guild_id)
            else:
                bot.loop.create_task(auto_disconnect(vc, guild_id))

        vc.play(discord.FFmpegPCMAudio(song["url"], **FFMPEG_OPTIONS), after=after)

# ---------------- VIEW ----------------
class PlayView(View):
    def __init__(self, audio_url, title):
        super().__init__(timeout=120)
        self.audio_url = audio_url
        self.title = title

    @discord.ui.button(label="Play", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.voice:
            return await interaction.response.send_message("Join a VC first.", ephemeral=True)

        await interaction.response.defer()

        channel = interaction.user.voice.channel
        vc = interaction.guild.voice_client
        gid = interaction.guild.id

        if gid not in guild_queues:
            guild_queues[gid] = []
            guild_loops[gid] = False

        if vc:
            if vc.channel.id != channel.id:
                await vc.move_to(channel)
        else:
            vc = await channel.connect()

        song = {"url": self.audio_url, "title": self.title}

        if vc.is_playing():
            guild_queues[gid].append(song)
            return await interaction.followup.send(f"Added to queue: **{self.title}**")

        def after(e):
            if guild_queues[gid]:
                play_next(vc, gid)
            else:
                bot.loop.create_task(auto_disconnect(vc, gid))

        vc.play(discord.FFmpegPCMAudio(self.audio_url, **FFMPEG_OPTIONS), after=after)

        embed = discord.Embed(
            title="Now Playing",
            description=f"**{self.title}**",
            color=0x000000
        )
        await interaction.followup.send(embed=embed)

# ---------------- EVENTS ----------------
@bot.event
async def on_ready():
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(type=discord.ActivityType.listening, name="Synthaly Music")
    )
    print(f"Logged in as {bot.user}")
    await bot.tree.sync()

@bot.event
async def on_voice_state_update(member, before, after):
    vc = member.guild.voice_client
    if vc and len(vc.channel.members) == 1:
        await asyncio.sleep(60)
        if len(vc.channel.members) == 1:
            await vc.disconnect()
            guild_queues[member.guild.id] = []

# ---------------- COMMANDS ----------------
@bot.tree.command(name="play", description="Play music")
async def play(interaction: discord.Interaction, search: str):
    if len(search) < 2:
        return await interaction.response.send_message("Search too short.", ephemeral=True)

    r = requests.get("https://music.synthaly.com/api/v1/releases")
    data = get_detailed_release(r.json(), search)

    if not data or 'release' not in data:
        return await interaction.response.send_message("Not found.", ephemeral=True)

    rel = data['release']

    embed = discord.Embed(
        title=f"{SynthalyBG} {rel['title']} - {rel['artist_name']}",
        description=(
            f"{Spotify} [Spotify]({rel['streaming_links']['spotify']})\n"
            f"{AppleMusic} [Apple Music]({rel['streaming_links']['apple_music']})"
        ),
        color=0x000000
    )
    embed.set_thumbnail(url=rel['cover_url'])

    view = PlayView(rel['audio_url'], rel['title'])
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="skip", description="Skip song")
async def skip(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if not vc or not vc.is_playing():
        return await interaction.response.send_message("Nothing playing.", ephemeral=True)

    vc.stop()
    await interaction.response.send_message("Skipped.")

@bot.tree.command(name="stop", description="Stop and leave")
async def stop(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc:
        guild_queues[interaction.guild.id] = []
        await vc.disconnect()
        await interaction.response.send_message("Disconnected.")
    else:
        await interaction.response.send_message("Not connected.", ephemeral=True)

@bot.tree.command(name="queue", description="Show queue")
async def queue(interaction: discord.Interaction):
    q = guild_queues.get(interaction.guild.id, [])
    if not q:
        return await interaction.response.send_message("Queue empty.", ephemeral=True)

    desc = "\n".join([f"{i+1}. {s['title']}" for i, s in enumerate(q)])
    embed = discord.Embed(title="Queue", description=desc, color=0x000000)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="loop", description="Toggle loop")
async def loop(interaction: discord.Interaction):
    gid = interaction.guild.id
    guild_loops[gid] = not guild_loops.get(gid, False)
    await interaction.response.send_message(f"Loop {'enabled' if guild_loops[gid] else 'disabled'}.")

@bot.tree.command(name="favorite", description="Save current song")
async def favorite(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if not vc or not vc.source:
        return await interaction.response.send_message("Nothing playing.", ephemeral=True)

    favorites.setdefault(interaction.user.id, []).append("Unknown Track")
    await interaction.response.send_message("Saved to favorites.")

@bot.tree.command(name="favorites", description="View favorites")
async def view_favorites(interaction: discord.Interaction):
    favs = favorites.get(interaction.user.id, [])
    if not favs:
        return await interaction.response.send_message("No favorites.", ephemeral=True)

    await interaction.response.send_message("\n".join(favs))

bot.run(token)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='>', intents=intents)

## EMOJIS
SynthalyBG = "<:SMBG:1475991847552942130>"
SynthalyTBG = "<:SMTR:1475991785305149646>"
Spotify = "<:spotify:1475992203674521765>"
AppleMusic = "<:AppleMusic:1476328276753649899>"

def get_detailed_release(json_data, search_input):
    releases = json_data.get('releases', [])
    match = next((r for r in releases if search_input.lower() in r['title'].lower()), None)
    if match:
        response = requests.get(f"https://music.synthaly.com/api/v1/releases/{match['id']}")
        return response.json()
    return None

class PlayView(discord.ui.View):
    def __init__(self, audio_url, title):
        super().__init__(timeout=120)
        self.audio_url = audio_url
        self.title = title

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.voice:
            return await interaction.response.send_message("Please join a voice channel first!", ephemeral=True)

        await interaction.response.defer()

        channel = interaction.user.voice.channel
        vc = interaction.guild.voice_client

        if vc:
            if vc.channel.id != channel.id:
                await vc.move_to(channel)
        else:
            vc = await channel.connect()

        FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }

        if vc.is_playing():
            vc.stop()

        vc.play(discord.FFmpegPCMAudio(self.audio_url, **FFMPEG_OPTIONS))
        await interaction.followup.send(f"Now playing: **{self.title}**")

    @discord.ui.button(label="No", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Playback cancelled.", ephemeral=True)
        self.stop()

@bot.event
async def on_ready():
    activity = discord.Activity(
        type=discord.ActivityType.listening,
        name="Synthaly Music"
    )
    await bot.change_presence(status=discord.Status.online, activity=activity)

    print(f"Logged in as {bot.user.name}! Active")
    await bot.tree.sync()

@bot.tree.command(name="play", description="Play music from Synthaly")
@app_commands.describe(search="Search for a song title")
async def play(interaction: discord.Interaction, search: str):
    if len(search) < 2:
        return await interaction.response.send_message("Search query too short!", ephemeral=True)

    r = requests.get("https://music.synthaly.com/api/v1/releases")
    releaseJson = get_detailed_release(r.json(), search)

    if not releaseJson or 'release' not in releaseJson:
        return await interaction.response.send_message("Song not found.", ephemeral=True)

    rel = releaseJson['release']

    audio_url = rel.get('audio_url')
    title = rel.get('title')

    embed = discord.Embed(
        title=f"{SynthalyBG} {title} by {rel['artist_name']}",
        color=0x000000,
        description=(
            f"Are you sure you want to **play** this song?\n\n"
            f"{Spotify} [Spotify]({rel['streaming_links']['spotify']})\n"
            f"{AppleMusic} [Apple Music]({rel['streaming_links']['apple_music']})"
        )
    )
    embed.set_thumbnail(url=rel['cover_url'])

    view = PlayView(audio_url, title)
    await interaction.response.send_message(embed=embed, view=view)

bot.run(token)
