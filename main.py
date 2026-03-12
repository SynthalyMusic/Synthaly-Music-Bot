import discord
import os
import requests
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("TOKEN")

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
    print(f"Logged in as {bot.user.name}! Active")
    await bot.tree.sync()

@bot.tree.command(name="play", description="Play music from Synthaly")
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
        title = f"{SynthalyBG} {title} by {rel['artist_name']}",
        color = 0x000000,
        description = f"Are you sure you want to **play** this song?\n\n{Spotify} [Spotify]({rel['streaming_links']['spotify']})\n{AppleMusic} [Apple Music]({rel['streaming_links']['apple_music']})"
    )
    embed.set_thumbnail(url=rel['cover_url'])

    view = PlayView(audio_url, title)
    await interaction.response.send_message(embed=embed, view=view)

bot.run(token)
