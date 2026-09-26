# Author: @F1r3f0x (plabin@outlook.cl)
# License: GPLv3

import asyncio
import os
import platform
import socket
import sys
import time
from datetime import timedelta

import httpx
import psutil
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


def load_env_file() -> None:
    """Load key-value pairs from local .env or .env.dev into os.environ if present."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    search_paths = [
        ".env",
        ".env.dev",
        os.path.join(base_dir, ".env"),
        os.path.join(base_dir, ".env.dev"),
    ]
    for path in search_paths:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, val = line.split("=", 1)
                            key, val = key.strip(), val.strip().strip("'\"")
                            if key not in os.environ:
                                os.environ[key] = val
                break
            except Exception:
                pass


# Startup timestamp to track bot process uptime
START_TIME = time.time()
_cached_public_ip: tuple[str, float] = ("", 0.0)


def get_os_info() -> str:
    """Return operating system and kernel information."""
    try:
        info = platform.freedesktop_os_release()
        pretty_name = info.get("PRETTY_NAME") or info.get("NAME")
        if pretty_name:
            return f"{pretty_name} ({platform.release()})"
    except Exception:
        pass
    return f"{platform.system()} {platform.release()}".strip() or "Unknown"


def get_local_ip() -> str:
    """Return local network IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.254.254.254", 1))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


async def get_public_ip() -> str:
    """Fetch public IP address with 60-second caching."""
    global _cached_public_ip
    ip, cache_time = _cached_public_ip
    if ip and (time.time() - cache_time < 60):
        return ip

    endpoints = ["https://api.ipify.org", "https://icanhazip.com"]
    async with httpx.AsyncClient(timeout=3.0) as client:
        for url in endpoints:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    ip = resp.text.strip()
                    _cached_public_ip = (ip, time.time())
                    return ip
            except Exception:
                continue
    return ip if ip else "Unavailable"


async def measure_http_latency() -> float | None:
    """Measure outbound HTTP round-trip latency via a lightweight HEAD request."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            start = time.perf_counter()
            await client.head("https://1.1.1.1")
            return (time.perf_counter() - start) * 1000
    except Exception:
        return None


async def measure_telegram_latency(bot) -> float | None:
    """Measure Telegram API round-trip latency."""
    try:
        start = time.perf_counter()
        await bot.get_me()
        return (time.perf_counter() - start) * 1000
    except Exception:
        return None


def restricted(func):
    """Decorator to silently ignore requests from unauthorized users."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            allowed_id = int(os.getenv("ALLOWED_USER_ID", "0"))
        except ValueError:
            allowed_id = 0

        user_id = update.effective_user.id if update.effective_user else None
        if user_id != allowed_id:
            # Drop the packet silently without replying
            return
        return await func(update, context)
    return wrapper


@restricted
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Quick latency / alive check."""
    start = time.perf_counter()
    msg = await update.message.reply_text("🏓 Pong...")
    latency = (time.perf_counter() - start) * 1000
    try:
        await msg.edit_text(f"🏓 **Pong!** Latency: `{latency:.0f} ms`", parse_mode="Markdown")
    except Exception:
        pass


@restricted
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Detailed host resource summary."""
    # Gather async network info concurrently
    public_ip, tg_lat, http_lat = await asyncio.gather(
        get_public_ip(),
        measure_telegram_latency(context.bot),
        measure_http_latency(),
    )

    # System uptime
    boot_time = psutil.boot_time()
    system_uptime = timedelta(seconds=int(time.time() - boot_time))
    bot_uptime = timedelta(seconds=int(time.time() - START_TIME))

    # CPU & RAM
    cpu_usage = psutil.cpu_percent(interval=0.5)
    memory = psutil.virtual_memory()

    # Disk usage on host root partition
    disk = psutil.disk_usage("/")

    # Host info & IPs
    os_info = get_os_info()
    local_ip = get_local_ip()
    local_ip_str = f"`{local_ip}`" if local_ip != "Unavailable" else "Unavailable"
    public_ip_str = f"`{public_ip}`" if public_ip != "Unavailable" else "Unavailable"

    # Latencies
    lat_parts = []
    if tg_lat is not None:
        lat_parts.append(f"{tg_lat:.0f} ms (Telegram)")
    if http_lat is not None:
        lat_parts.append(f"{http_lat:.0f} ms (HTTP)")
    latency_str = " | ".join(lat_parts) if lat_parts else "N/A"

    response = (
        f"🖥️ **Host Status Report**\n\n"
        f"• **OS:** {os_info}\n"
        f"• **System Uptime:** {system_uptime}\n"
        f"• **Bot Uptime:** {bot_uptime}\n"
        f"• **CPU Load:** {cpu_usage}%\n"
        f"• **RAM Usage:** {memory.percent}% ({memory.used // (1024**2)}MB / {memory.total // (1024**2)}MB)\n"
        f"• **Disk Usage:** {disk.percent}% ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)\n"
        f"• **Local IP:** {local_ip_str}\n"
        f"• **Public IP:** {public_ip_str}\n"
        f"• **Requests Latency:** {latency_str}\n"
    )
    await update.message.reply_text(response, parse_mode="Markdown")


def main(argv: list[str] | None = None) -> int:
    """Main CLI entrypoint for python3-pingbot."""
    load_env_file()

    bot_token = os.getenv("BOT_TOKEN")
    try:
        allowed_user_id = int(os.getenv("ALLOWED_USER_ID", "0"))
    except ValueError:
        allowed_user_id = 0

    if not bot_token or allowed_user_id == 0:
        print(
            "Error: BOT_TOKEN and a valid ALLOWED_USER_ID must be provided.\n"
            "Set them in your environment or in a .env file.\n\n"
            "Example:\n"
            "  BOT_TOKEN=\"123456:ABC-DEF...\"\n"
            "  ALLOWED_USER_ID=\"123456789\"",
            file=sys.stderr,
        )
        return 1

    app = Application.builder().token(bot_token).build()

    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("status", status))

    print(f"Bot listening for User ID: {allowed_user_id}...")
    try:
        app.run_polling()
    except (KeyboardInterrupt, SystemExit):
        print("\nBot stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())