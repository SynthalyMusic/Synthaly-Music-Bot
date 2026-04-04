import discord
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
bot = commands.Bot(command_prefix=">", intents=intents)

# ---------------- EMOJIS ----------------
SynthalyBG = "<:SMBG:1475991847552942130>"
Spotify = "<:spotify:1475992203674521765>"
AppleMusic = "<:AppleMusic:1476328276753649899>"

# ---------------- STATE ----------------
guild_queues = {}
guild_loops = {}
favorites = {}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn"
}

# ---------------- API ----------------
def get_detailed_release(json_data, search_input):
    releases = json_data.get("releases", [])
    match = next(
        (r for r in releases if search_input.lower() in r["title"].lower()),
        None
    )

    if match:
        r = requests.get(f"https://music.synthaly.com/api/v1/releases/{match['id']}")
        return r.json()

    return None


# ---------------- SAFE DISCONNECT ----------------
async def auto_disconnect(vc, guild_id):
    await asyncio.sleep(120)

    if not vc or not vc.channel:
        return

    if len(vc.channel.members) == 1:
        await vc.disconnect()
        guild_queues[guild_id] = []
        guild_loops[guild_id] = False


# ---------------- QUEUE ENGINE ----------------
def play_next(vc, guild_id):
    if not vc:
        return

    if guild_loops.get(guild_id) and vc.source:
        vc.play(vc.source, after=lambda e: play_next(vc, guild_id))
        return

    queue = guild_queues.get(guild_id, [])

    if not queue:
        bot.loop.create_task(auto_disconnect(vc, guild_id))
        return

    song = queue.pop(0)

    def after(e):
        if guild_queues.get(guild_id):
            play_next(vc, guild_id)
        else:
            bot.loop.create_task(auto_disconnect(vc, guild_id))

    vc.play(
        discord.FFmpegPCMAudio(song["url"], **FFMPEG_OPTIONS),
        after=after
    )


# ---------------- CONFIRMATION VIEW ----------------
class PlayView(View):
    def __init__(self, audio_url, title, artist):
        super().__init__(timeout=120)
        self.audio_url = audio_url
        self.title = title
        self.artist = artist

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not interaction.user.voice:
            return await interaction.response.send_message(
                "Please join a voice channel first!",
                ephemeral=True
            )

        await interaction.response.defer()

        gid = interaction.guild.id
        channel = interaction.user.voice.channel
        vc = interaction.guild.voice_client

        guild_queues.setdefault(gid, [])
        guild_loops.setdefault(gid, False)

        if vc:
            if vc.channel != channel:
                await vc.move_to(channel)
        else:
            vc = await channel.connect()

        song = {
            "url": self.audio_url,
            "title": self.title,
            "artist": self.artist
        }

        # queue if already playing
        if vc.is_playing() or vc.is_paused():
            guild_queues[gid].append(song)
            await interaction.followup.send(f"Queued: **{self.title}**")
            self.stop()
            return

        # play immediately
        guild_queues[gid].insert(0, song)

        def after(e):
            if guild_queues.get(gid):
                play_next(vc, gid)
            else:
                bot.loop.create_task(auto_disconnect(vc, gid))

        vc.play(
            discord.FFmpegPCMAudio(self.audio_url, **FFMPEG_OPTIONS),
            after=after
        )

        embed = discord.Embed(
            title="Now Playing",
            description=f"**{self.title} by {self.artist}**",
            color=0x000000
        )

        await interaction.followup.send(embed=embed)
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Playback cancelled.",
            ephemeral=True
        )
        self.stop()


# ---------------- EVENTS ----------------
@bot.event
async def on_ready():
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name="Synthaly Music"
        )
    )
    print(f"Logged in as {bot.user}")
    await bot.tree.sync()


@bot.event
async def on_voice_state_update(member, before, after):
    vc = member.guild.voice_client

    if vc and len(vc.channel.members) == 1:
        await asyncio.sleep(60)

        if vc and len(vc.channel.members) == 1:
            await vc.disconnect()
            guild_queues[member.guild.id] = []


# ---------------- COMMANDS ----------------
@bot.tree.command(name="play", description="Play music")
async def play(interaction: discord.Interaction, search: str):

    if len(search) < 2:
        return await interaction.response.send_message(
            "Search too short.",
            ephemeral=True
        )

    r = requests.get("https://music.synthaly.com/api/v1/releases")
    data = get_detailed_release(r.json(), search)

    if not data or "release" not in data:
        return await interaction.response.send_message(
            "Not found.",
            ephemeral=True
        )

    rel = data["release"]

    embed = discord.Embed(
        title=f"{SynthalyBG} {rel['title']} by {rel['artist_name']}",
        description=(
            "Are you sure you want to **play** this song?\n\n"
            f"{Spotify} [Spotify]({rel['streaming_links']['spotify']})\n"
            f"{AppleMusic} [Apple Music]({rel['streaming_links']['apple_music']})"
        ),
        color=0x000000
    )

    embed.set_thumbnail(url=rel["cover_url"])

    view = PlayView(rel["audio_url"], rel["title"], rel["artist_name"])
    await interaction.response.send_message(embed=embed, view=view)


@bot.tree.command(name="skip", description="Skip song")
async def skip(interaction: discord.Interaction):
    vc = interaction.guild.voice_client

    if not vc or not vc.is_playing():
        return await interaction.response.send_message(
            "Nothing playing.",
            ephemeral=True
        )

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
        return await interaction.response.send_message(
            "Queue empty.",
            ephemeral=True
        )

    desc = "\n".join(
        f"{i+1}. {s['title']} - {s['artist']}"
        for i, s in enumerate(q)
    )

    embed = discord.Embed(title="Queue", description=desc, color=0x000000)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="loop", description="Toggle loop")
async def loop(interaction: discord.Interaction):
    gid = interaction.guild.id
    guild_loops[gid] = not guild_loops.get(gid, False)

    await interaction.response.send_message(
        f"Loop {'enabled' if guild_loops[gid] else 'disabled'}."
    )


@bot.tree.command(name="favorite", description="Save current song")
async def favorite(interaction: discord.Interaction):
    vc = interaction.guild.voice_client

    if not vc:
        return await interaction.response.send_message(
            "Nothing playing.",
            ephemeral=True
        )

    favorites.setdefault(interaction.user.id, []).append("Last Played Song")
    await interaction.response.send_message("Saved to favorites.")


@bot.tree.command(name="favorites", description="View favorites")
async def view_favorites(interaction: discord.Interaction):
    favs = favorites.get(interaction.user.id, [])

    if not favs:
        return await interaction.response.send_message(
            "No favorites.",
            ephemeral=True
        )

    await interaction.response.send_message("\n".join(favs))


# ---------------- RUN ----------------
bot.run(token)
