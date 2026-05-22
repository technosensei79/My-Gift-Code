import os

# ── Bot credentials ──────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# ── Admin ────────────────────────────────────────────────────────
ADMIN_USERNAME = "techno"          # without @
ADMIN_IDS: list[int] = []          # filled at runtime from DB / env

# ── Force-join channel ───────────────────────────────────────────
# Use the public username OR the numeric id (e.g. -1001234567890)
FORCE_JOIN_CHANNEL = os.getenv("FORCE_JOIN_CHANNEL", "@techno")   # change to your channel username or id

# ── Default welcome content ──────────────────────────────────────
DEFAULT_WELCOME_TEXT = (
    "👋 *Welcome to the Official Bot!*\n\n"
    "Use the menu below to explore our services. "
    "Join our channel to unlock all features. 🚀"
)
DEFAULT_WELCOME_IMAGE = ""          # URL or file_id; leave empty to send text only

# ── Button links ─────────────────────────────────────────────────
CHANNEL_LINK  = "https://t.me/+JDL_5OZNjMlhODA1"
VIP_LINK      = "https://t.me/+n0NvxGrNOrllZDQ1"
APK_LINK      = "https://technosensei.shop/app.apk"
BONUS_LINK    = "https://technosensei.shop"

# ── Database ─────────────────────────────────────────────────────
DB_PATH = os.getenv("DB_PATH", "bot.db")
