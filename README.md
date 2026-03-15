<div align="center">

[![GitHub stars](https://img.shields.io/github/stars/SynthalyMusic/Synthaly-Music-Bot?style=for-the-badge)](https://github.com/SynthalyMusic/Synthaly-Music-Bot/stargazers)
[![Issues](https://img.shields.io/github/issues/SynthalyMusic/Synthaly-Music-Bot?style=for-the-badge)](https://github.com/SynthalyMusic/Synthaly-Music-Bot/issues)
[![Contributors](https://img.shields.io/github/contributors/SynthalyMusic/Synthaly-Music-Bot?style=for-the-badge)](https://github.com/SynthalyMusic/Synthaly-Music-Bot/graphs/contributors)
[![Discord](https://img.shields.io/discord/1115420307507925012?label=Discord&color=5865F2&style=for-the-badge)](https://discord.gg/YZVAVDY6YQ)


<br>

<img src="https://cloud.synthaly.com/images/sm-logo.png" width="200">

# Synthaly Music Discord Bot
[![Better Stack Badge](https://uptime.betterstack.com/status-badges/v1/monitor/2fy6j.svg)](https://status.music.synthaly.com/)

Play licensed Synthaly Music tracks directly inside Discord via the official Synthaly Music API.

<br>

<a href="https://www.producthunt.com/posts/synthaly-music" target="_blank">
<img src="https://api.producthunt.com/widgets/embed-image/v1/featured.svg?post_id=1098106&theme=light" width="250" height="54" />
</a>

<br>

</div>

---

## 📖 Contents

- Overview
- Features
- Commands
- Getting Started
- Architecture
- Contributing
- Support
- License

---

## 🎵 Overview

The **Synthaly Music Discord Bot** allows Discord communities to stream official Synthaly Music catalog releases directly into voice channels.

Unlike traditional music bots, this bot is built around a **licensed distribution ecosystem**, ensuring artists are supported while providing communities with high-quality playback.

Designed for:

- Synthaly partner communities  
- Roblox music ecosystem servers  
- Artist fan communities  
- Developers integrating Synthaly audio systems  

---

## ✨ Features

- 🎧 Stream official Synthaly Music catalog
- 🔎 Search tracks and artists via API
- ⚡ High-performance queue system
- 🤖 Modern slash command support
- 📀 High-quality audio streaming
- 🔐 Licensed music playback infrastructure
- 📊 Playback analytics integration ready
- 🌐 Scalable architecture for large servers
- 🧠 Smart discovery & recommendation foundation
- 🛠️ Developer-friendly modular codebase

---

## 🎶 Commands

```

/play <query>

````

---

## ⚡ Getting Started

### Requirements

- Python **3.10+**
- FFmpeg installed and available in system PATH
- Discord Bot Token
- Synthaly API access (public catalog endpoint)

---

### Install Dependencies

Clone the repository:

```bash
git clone https://github.com/SynthalyMusic/Synthaly-Music-Bot
cd Synthaly-Music-Bot
````

Install Python packages:

```bash
pip install -r requirements.txt
```

---

### Environment Setup

Create a `.env` file in the project root:

```
TOKEN=your_discord_bot_token_here
```

---

### Run the Bot

```bash
python main.py
```

---

### FFmpeg Installation

This bot requires FFmpeg for audio playback.

#### Windows

Download:
[https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/)

Add the `bin` folder to your **System PATH**.

#### Linux

```bash
sudo apt install ffmpeg
```

#### macOS

```bash
brew install ffmpeg
```

---

### First Run Notes

On first startup:

* Slash commands will auto-sync
* Bot must have **Voice permissions**
* Bot must have **Use Application Commands**
* Bot must have **Connect + Speak**

If playback fails, verify:

* FFmpeg installed correctly
* Bot has voice permissions
* Voice region is stable

---

## 🧩 Architecture

The bot connects to:

* Synthaly Music API
* Audio streaming pipeline
* Discord Voice Gateway
* Playback orchestration layer

This ensures:

* Stable streaming
* Low latency playback
* Licensed music enforcement
* Platform-wide consistency

---

## 🤝 Contributing

We welcome contributions including:

* Feature improvements
* Performance optimizations
* Bug fixes
* Documentation updates
* API integration expansions

Please open an issue or submit a pull request.

---

## 😕 Support

[![Discord](https://discordapp.com/api/guilds/1115420307507925012/widget.png?style=banner4)](https://discord.gg/YZVAVDY6YQ)

Join the Synthaly community for support, updates, and development discussions.

---

## 📜 License

Synthaly Music Bot by Synthaly LLC is licensed under the [GPLv3 license](https://github.com/SynthalyMusic/Synthaly-Music-Bot/blob/main/LICENSE).

© 2026 Synthaly LLC
All rights reserved.
