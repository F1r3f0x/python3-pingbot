# python3-pingbot

Quick and dirty telegram bot to just get a health ping from your host, good enough to start working on telegram bots and try stuff.
---

## Features

- **User Authorization**: Silently ignores and drops requests from unauthorized Telegram user IDs.
- **Latency Ping (`/ping`)**: Quick alive check that measures and reports interactive message round-trip latency.
- **Host Status Report (`/status`)**:
  - **OS & Kernel**: Distribution details and running kernel version.
  - **Uptimes**: Host system uptime and bot process uptime.
  - **Hardware Metrics**: Real-time CPU load, RAM usage (MB and percentage), and root disk space (GB and percentage).
  - **Network Inspection**: Primary local IP and external public IP (with a 60-second in-memory cache to prevent rate-limiting).
  - **Network Latency**: Concurrent latency measurements for both Telegram API and outbound HTTP.
- **Asynchronous & Concurrent**: Uses `asyncio.gather()` to measure network targets concurrently.

---

## Preview

### `/status`
```markdown
🖥️ Host Status Report

• OS: CachyOS (7.2.7-1-cachyos)
• System Uptime: 8:25:12
• Bot Uptime: 0:13:00
• CPU Load: 6.8%
• RAM Usage: 38.9% (12450MB / 32006MB)
• Disk Usage: 43.6% (197GB / 463GB)
• Local IP: `192.168.1.99`
• Public IP: `190.20.118.164`
• Requests Latency: 148 ms (Telegram) | 49 ms (HTTP)
```

### `/ping`
```markdown
🏓 Pong! Latency: 142 ms
```

---

## Quick Start

### 1. Requirements

- Python `3.10+` (tested on `3.14`)
- [uv](https://github.com/astral-sh/uv) (recommended) or standard `pip`

### 2. Configuration

Create a `.env` file in the project directory:

```env
# Bot token obtained from @BotFather on Telegram
BOT_TOKEN="1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ"

# Your personal numerical Telegram User ID (obtain from @userinfobot)
ALLOWED_USER_ID="123456789"
```

> [!IMPORTANT]
> The bot will refuse to start if either `BOT_TOKEN` or `ALLOWED_USER_ID` is missing or invalid. Any messages from unauthorized users are silently ignored.

### 3. Run the Bot

With `uv`:
```bash
# Sync dependencies and run
uv run python3-pingbot

# Or via Python module execution
uv run python -m python3_pingbot
```

With standard `pip`:
```bash
pip install -r requirements.txt
pip install -e .
python3 -m python3_pingbot
```

---



## Project Structure

```
python3-pingbot/
├── pyproject.toml             # Project metadata, dependencies, and script entrypoint
├── requirements.txt           # Standard pip dependency mirror
├── python3-pingbot.service    # systemd user service unit template
├── README.md                  # Documentation
└── src/
    └── python3_pingbot/
        ├── __init__.py        # Package version metadata
        ├── __main__.py        # Module entrypoint ("python -m python3_pingbot")
        └── bot.py             # Bot handlers, system probes, and CLI runner
```

---

## License
@F1r3f0x (plabin@outlook.cl)
GPLv3
