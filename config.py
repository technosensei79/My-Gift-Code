import os

# ── Bot credentials ──────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "8477103947:AAF7iKw_YJoojMLW9Xpv5lRM4jOSEOG2w2g")

# ── Admin ────────────────────────────────────────────────────────
ADMIN_USERNAME = "technosupportt"          # without @
ADMIN_IDS: list[int] = []          # filled at runtime from DB / env

# ── Force-join channel ───────────────────────────────────────────
# Use the public username OR the numeric id (e.g. -1001234567890)
FORCE_JOIN_CHANNEL = os.getenv("FORCE_JOIN_CHANNEL", "https://t.me/+9KXhPzm8hqs3NmVl")   # change to your channel username or id

# ── Default welcome content ──────────────────────────────────────
DEFAULT_WELCOME_TEXT = (
    "👋 *Welcome to the Official Bot!*\n\n"
    "Use the menu below to explore our services. "
    "Join our channel to unlock all features. 🚀"
)
DEFAULT_WELCOME_IMAGE = ""          # URL or file_id; leave empty to send text only

# ── Button links ─────────────────────────────────────────────────
CHANNEL_LINK  = "https://t.me/+9KXhPzm8hqs3NmVl"
VIP_LINK      = "https://t.me/+9KXhPzm8hqs3NmVl"
APK_LINK      = "https://technosensei.shop/app.apk"
BONUS_LINK    = "https://technosensei.shop"

# ── Database ─────────────────────────────────────────────────────
DB_PATH = os.getenv("DB_PATH", "bot.db")
