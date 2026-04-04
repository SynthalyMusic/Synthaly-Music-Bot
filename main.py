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
guild_locks = {}
current_song = {}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin",
    "options": "-vn"
}

# ---------------- SAFE HTTP (NON-BLOCKING WRAPPER) ----------------
async def safe_get_json(url):
    loop = asyncio.get_event_loop()
    def _req():
        return requests.get(url, timeout=10).json()
    return await loop.run_in_executor(None, _req)


def get_detailed_release(json_data, search_input):
    releases = json_data.get("releases", [])
    match = next(
        (r for r in releases if search_input.lower() in r["title"].lower()),
        None
    )

    if match:
        r = requests.get(
            f"https://music.synthaly.com/api/v1/releases/{match['id']}",
            timeout=10
        )
        return r.json()

    return None


# ---------------- SAFE DISCONNECT ----------------
async def auto_disconnect(vc, guild_id):
    try:
        await asyncio.sleep(120)

        if not vc or not vc.channel:
            return

        if vc.is_connected() and len(vc.channel.members) == 1:
            await vc.disconnect()

        guild_queues[guild_id] = []
        guild_loops[guild_id] = False
        guild_locks[guild_id] = False

    except Exception:
        guild_locks[guild_id] = False


# ---------------- QUEUE ENGINE ----------------
def play_next(vc, guild_id):
    if not vc:
        return

    if guild_locks.get(guild_id):
        return

    guild_locks[guild_id] = True

    try:
        queue = guild_queues.get(guild_id, [])

        if guild_loops.get(guild_id) and queue:
            queue.append(queue[0])

        if not queue:
            bot.loop.create_task(auto_disconnect(vc, guild_id))
            guild_locks[guild_id] = False
            return

        song = queue.pop(0)
        current_song[guild_id] = song

        def after(err):
            async def runner():
                try:
                    guild_locks[guild_id] = False
                    if err:
                        pass

                    vc2 = vc.guild.voice_client if vc.guild else None

                    if vc2 and guild_queues.get(guild_id):
                        play_next(vc2, guild_id)
                    else:
                        await auto_disconnect(vc2, guild_id)

                except Exception:
                    guild_locks[guild_id] = False

            bot.loop.create_task(runner())

        vc.play(
            discord.FFmpegPCMAudio(song["url"], **FFMPEG_OPTIONS),
            after=after
        )

    except Exception:
        guild_locks[guild_id] = False


# ---------------- VIEW ----------------
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
        guild_locks.setdefault(gid, False)

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

        if vc.is_playing() or vc.is_paused():
            guild_queues[gid].append(song)
            await interaction.followup.send(f"Queued: **{self.title}**")
            self.stop()
            return

        guild_queues[gid].append(song)
        current_song[gid] = song

        play_next(vc, gid)

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

    if vc and vc.channel and len(vc.channel.members) == 1:
        await asyncio.sleep(60)

        if vc and vc.is_connected() and len(vc.channel.members) == 1:
            await vc.disconnect()
            guild_queues[member.guild.id] = []
            guild_locks[member.guild.id] = False


# ---------------- COMMANDS ----------------
@bot.tree.command(name="play", description="Search for a song and play it in your voice channel")
async def play(interaction: discord.Interaction, search: str):

    if len(search) < 2:
        return await interaction.response.send_message("Search too short.", ephemeral=True)

    data = await safe_get_json("https://music.synthaly.com/api/v1/releases")

    data = get_detailed_release(data, search)

    if not data or "release" not in data:
        return await interaction.response.send_message("Not found.", ephemeral=True)

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


@bot.tree.command(name="skip", description="Skip the currently playing song")
async def skip(interaction: discord.Interaction):
    vc = interaction.guild.voice_client

    if not vc or not vc.is_playing():
        return await interaction.response.send_message("Nothing playing.", ephemeral=True)

    vc.stop()
    await interaction.response.send_message("Skipped.")


@bot.tree.command(name="stop", description="Stop playback and disconnect the bot")
async def stop(interaction: discord.Interaction):
    vc = interaction.guild.voice_client

    if vc:
        guild_queues[interaction.guild.id] = []
        guild_locks[interaction.guild.id] = False
        await vc.disconnect()
        await interaction.response.send_message("Disconnected.")
    else:
        await interaction.response.send_message("Not connected.", ephemeral=True)


@bot.tree.command(name="queue", description="View the current music queue")
async def queue(interaction: discord.Interaction):
    q = guild_queues.get(interaction.guild.id, [])

    if not q:
        return await interaction.response.send_message("Queue empty.", ephemeral=True)

    desc = "\n".join(f"{i+1}. {s['title']} - {s['artist']}" for i, s in enumerate(q))

    await interaction.response.send_message(embed=discord.Embed(title="Queue", description=desc))


@bot.tree.command(name="loop", description="Toggle looping of the current queue")
async def loop(interaction: discord.Interaction):
    gid = interaction.guild.id
    guild_loops[gid] = not guild_loops.get(gid, False)
    await interaction.response.send_message(f"Loop {'enabled' if guild_loops[gid] else 'disabled'}.")


@bot.tree.command(name="favorite", description="Save the currently playing song to your favorites")
async def favorite(interaction: discord.Interaction):
    gid = interaction.guild.id
    song = current_song.get(gid)

    if not song:
        return await interaction.response.send_message("No song detected.", ephemeral=True)

    favorites.setdefault(interaction.user.id, []).append(song["title"])
    await interaction.response.send_message("Saved to favorites.")


@bot.tree.command(name="favorites", description="View your saved favorite songs")
async def view_favorites(interaction: discord.Interaction):
    favs = favorites.get(interaction.user.id, [])

    if not favs:
        return await interaction.response.send_message("No favorites.", ephemeral=True)

    await interaction.response.send_message("\n".join(favs))


bot.run(token)
