"""
Telegram bot – python-telegram-bot 21.x
Polling mode, Render-compatible (no webhook / event-loop conflicts).
"""

import logging
import asyncio
from typing import Optional

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
)
from telegram.constants import ChatMemberStatus, ParseMode
from telegram.error import TelegramError, Forbidden, BadRequest
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

import config
import database as db

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Conversation states ───────────────────────────────────────────
(
    ADMIN_MENU,
    BROADCAST_TEXT_WAIT,
    BROADCAST_PHOTO_WAIT,
    BROADCAST_PHOTO_CAPTION_WAIT,
    CHANGE_WELCOME_TEXT_WAIT,
    CHANGE_WELCOME_IMAGE_WAIT,
) = range(6)

# ── Keyboards ─────────────────────────────────────────────────────

def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["🎁 Join Free Giftcode Channel", "💎 VIP Prediction Group"],
            ["🎮 Premium Panel APK", "🎉 Sign-Up Bonus"],
        ],
        resize_keyboard=True,
    )


def verify_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("✅ Verify Join", callback_data="verify_join")]]
    )


def admin_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["📢 Broadcast Text", "🖼 Broadcast Photo"],
            ["📊 Statistics", "✏️ Change Welcome Text"],
            ["🖼 Change Welcome Image", "🔙 Back to Main"],
        ],
        resize_keyboard=True,
    )


# ── Force-join helper ─────────────────────────────────────────────

async def is_member(bot, user_id: int) -> bool:
    """Return True if user is a member of the force-join channel."""
    try:
        member = await bot.get_chat_member(config.FORCE_JOIN_CHANNEL, user_id)
        return member.status in (
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        )
    except TelegramError:
        # If we can't check (private channel invite link used), allow through
        return True


async def send_force_join(update: Update) -> None:
    """Send the 'please join' message with inline verify button."""
    text = (
        "⚠️ *Access Restricted*\n\n"
        "You must join our official channel before using this bot.\n\n"
        f"👉 [Join Channel]({config.CHANNEL_LINK})\n\n"
        "After joining, tap *Verify Join* below."
    )
    await update.effective_message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=verify_keyboard(),
        disable_web_page_preview=True,
    )


# ── Welcome sender ────────────────────────────────────────────────

async def send_welcome(update: Update) -> None:
    welcome_text  = db.get_setting("welcome_text")
    welcome_image = db.get_setting("welcome_image")

    if welcome_image:
        try:
            await update.effective_message.reply_photo(
                photo=welcome_image,
                caption=welcome_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=main_keyboard(),
            )
            return
        except (TelegramError, BadRequest):
            pass  # fall through to text-only

    await update.effective_message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_keyboard(),
    )


# ── /start ────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    db.upsert_user(user.id, user.username, user.first_name, user.last_name)

    if not await is_member(context.bot, user.id):
        await send_force_join(update)
        return

    await send_welcome(update)


# ── Verify Join callback ──────────────────────────────────────────

async def verify_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if await is_member(context.bot, user.id):
        await query.message.delete()
        db.upsert_user(user.id, user.username, user.first_name, user.last_name)
        await send_welcome(update)
    else:
        await query.answer(
            "❌ You haven't joined yet! Please join first.", show_alert=True
        )


# ── Menu buttons ──────────────────────────────────────────────────

BUTTON_RESPONSES = {
    "🎁 Join Free Giftcode Channel": (
        "🎁 *Free Giftcode Channel*\n\nJoin now to get daily free gift codes!",
        config.CHANNEL_LINK,
        "🔗 Join Channel",
    ),
    "💎 VIP Prediction Group": (
        "💎 *VIP Prediction Group*\n\nGet exclusive VIP predictions and tips!",
        config.VIP_LINK,
        "🔗 Join VIP Group",
    ),
    "🎮 Premium Panel APK": (
        "🎮 *Premium Panel APK*\n\nDownload our premium panel application!",
        config.APK_LINK,
        "📥 Download APK",
    ),
    "🎉 Sign-Up Bonus": (
        "🎉 *Sign-Up Bonus*\n\nClaim your exclusive sign-up bonus now!",
        config.BONUS_LINK,
        "🌐 Claim Bonus",
    ),
}


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    if text not in BUTTON_RESPONSES:
        return

    user = update.effective_user
    if not await is_member(context.bot, user.id):
        await send_force_join(update)
        return

    caption, link, btn_label = BUTTON_RESPONSES[text]
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(btn_label, url=link)]]
    )
    await update.message.reply_text(
        caption,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
    )


# ── Admin guard ───────────────────────────────────────────────────

def is_admin(update: Update) -> bool:
    user = update.effective_user
    return (user.username or "").lower() == config.ADMIN_USERNAME.lower()


# ══════════════════════════════════════════════════════════════════
# ADMIN CONVERSATION
# ══════════════════════════════════════════════════════════════════

async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_admin(update):
        await update.message.reply_text("⛔ Access denied.")
        return ConversationHandler.END

    total   = db.get_user_count()
    active  = db.get_active_count()
    await update.message.reply_text(
        f"👑 *Admin Panel*\n\n👥 Total users: *{total}*\n✅ Active: *{active}*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_keyboard(),
    )
    return ADMIN_MENU


async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text

    if text == "📢 Broadcast Text":
        await update.message.reply_text(
            "✏️ Send the text message you want to broadcast to all users.\n\n"
            "Type /cancel to abort."
        )
        return BROADCAST_TEXT_WAIT

    if text == "🖼 Broadcast Photo":
        await update.message.reply_text(
            "🖼 Send the photo you want to broadcast (with optional caption).\n\n"
            "Type /cancel to abort."
        )
        return BROADCAST_PHOTO_WAIT

    if text == "📊 Statistics":
        total  = db.get_user_count()
        active = db.get_active_count()
        await update.message.reply_text(
            f"📊 *Bot Statistics*\n\n"
            f"👥 Total users  : *{total}*\n"
            f"✅ Active users : *{active}*\n"
            f"🚫 Blocked/left : *{total - active}*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_keyboard(),
        )
        return ADMIN_MENU

    if text == "✏️ Change Welcome Text":
        current = db.get_setting("welcome_text")
        await update.message.reply_text(
            f"Current welcome text:\n\n{current}\n\n"
            "Send the new welcome text (Markdown supported).\n\nType /cancel to abort."
        )
        return CHANGE_WELCOME_TEXT_WAIT

    if text == "🖼 Change Welcome Image":
        await update.message.reply_text(
            "Send a photo to use as the new welcome image, "
            "or send /remove_image to remove it.\n\nType /cancel to abort."
        )
        return CHANGE_WELCOME_IMAGE_WAIT

    if text == "🔙 Back to Main":
        await update.message.reply_text(
            "Returned to main menu.", reply_markup=main_keyboard()
        )
        return ConversationHandler.END

    return ADMIN_MENU


# ── Broadcast text ────────────────────────────────────────────────

async def broadcast_text_receive(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    msg_text = update.message.text_markdown_v2 or update.message.text
    users = db.get_all_users()
    sent = blocked = failed = 0

    status_msg = await update.message.reply_text(
        f"📤 Broadcasting to {len(users)} users…"
    )

    for row in users:
        uid = row["user_id"]
        try:
            await context.bot.send_message(
                uid, msg_text, parse_mode=ParseMode.MARKDOWN
            )
            sent += 1
        except Forbidden:
            db.mark_blocked(uid)
            blocked += 1
        except TelegramError:
            failed += 1
        await asyncio.sleep(0.05)   # stay under flood limit

    await status_msg.edit_text(
        f"✅ Broadcast complete!\n\n"
        f"📨 Sent    : {sent}\n"
        f"🚫 Blocked : {blocked}\n"
        f"❌ Failed  : {failed}",
    )
    await update.message.reply_text("Back to admin panel.", reply_markup=admin_keyboard())
    return ADMIN_MENU


# ── Broadcast photo ───────────────────────────────────────────────

async def broadcast_photo_receive(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if not update.message.photo:
        await update.message.reply_text("⚠️ Please send a photo.")
        return BROADCAST_PHOTO_WAIT

    context.user_data["bc_photo_id"]      = update.message.photo[-1].file_id
    context.user_data["bc_photo_caption"] = update.message.caption or ""

    users = db.get_all_users()
    sent = blocked = failed = 0

    status_msg = await update.message.reply_text(
        f"📤 Broadcasting photo to {len(users)} users…"
    )

    for row in users:
        uid = row["user_id"]
        try:
            await context.bot.send_photo(
                uid,
                photo=context.user_data["bc_photo_id"],
                caption=context.user_data["bc_photo_caption"],
                parse_mode=ParseMode.MARKDOWN,
            )
            sent += 1
        except Forbidden:
            db.mark_blocked(uid)
            blocked += 1
        except TelegramError:
            failed += 1
        await asyncio.sleep(0.05)

    await status_msg.edit_text(
        f"✅ Photo broadcast complete!\n\n"
        f"📨 Sent    : {sent}\n"
        f"🚫 Blocked : {blocked}\n"
        f"❌ Failed  : {failed}",
    )
    await update.message.reply_text("Back to admin panel.", reply_markup=admin_keyboard())
    return ADMIN_MENU


# ── Change welcome text ───────────────────────────────────────────

async def change_welcome_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    new_text = update.message.text
    db.set_setting("welcome_text", new_text)
    await update.message.reply_text(
        "✅ Welcome text updated!", reply_markup=admin_keyboard()
    )
    return ADMIN_MENU


# ── Change welcome image ──────────────────────────────────────────

async def change_welcome_image(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if update.message.text and update.message.text.strip() == "/remove_image":
        db.set_setting("welcome_image", "")
        await update.message.reply_text(
            "✅ Welcome image removed.", reply_markup=admin_keyboard()
        )
        return ADMIN_MENU

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        db.set_setting("welcome_image", file_id)
        await update.message.reply_text(
            "✅ Welcome image updated!", reply_markup=admin_keyboard()
        )
        return ADMIN_MENU

    await update.message.reply_text("⚠️ Please send a photo or type /remove_image.")
    return CHANGE_WELCOME_IMAGE_WAIT


# ── Cancel ────────────────────────────────────────────────────────

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "❌ Cancelled.", reply_markup=admin_keyboard()
    )
    return ADMIN_MENU


# ══════════════════════════════════════════════════════════════════
# APP SETUP
# ══════════════════════════════════════════════════════════════════

def build_app() -> Application:
    db.init_db()

    app = Application.builder().token(config.BOT_TOKEN).build()

    # ── Admin conversation ────────────────────────────────────────
    admin_conv = ConversationHandler(
        entry_points=[CommandHandler("admin", admin_start)],
        states={
            ADMIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_menu)
            ],
            BROADCAST_TEXT_WAIT: [
                CommandHandler("cancel", cancel),
                MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_text_receive),
            ],
            BROADCAST_PHOTO_WAIT: [
                CommandHandler("cancel", cancel),
                MessageHandler(filters.PHOTO, broadcast_photo_receive),
                MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_photo_receive),
            ],
            CHANGE_WELCOME_TEXT_WAIT: [
                CommandHandler("cancel", cancel),
                MessageHandler(filters.TEXT & ~filters.COMMAND, change_welcome_text),
            ],
            CHANGE_WELCOME_IMAGE_WAIT: [
                CommandHandler("remove_image", change_welcome_image),
                CommandHandler("cancel", cancel),
                MessageHandler(filters.PHOTO | filters.TEXT, change_welcome_image),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(admin_conv)
    app.add_handler(CallbackQueryHandler(verify_join, pattern="^verify_join$"))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler)
    )

    return app


from flask import Flask
from threading import Thread

flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Bot Running", 200


def run_web():
    flask_app.run(host="0.0.0.0", port=10000)


def main() -> None:
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = build_app()

    logger.info("Bot is running (polling)…")

    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    Thread(target=run_web).start()
    main()
