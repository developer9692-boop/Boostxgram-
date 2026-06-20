#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════╗
# ║         BOOSTXGRAM — PAID SMM PANEL BOT             ║
# ║         Credit-based · UPI Payments · Admin Panel   ║
# ║         Install : pip install pyTelegramBotAPI       ║
# ║         Run     : python3 boostxgram.py             ║
# ╚══════════════════════════════════════════════════════╝

import telebot
import sqlite3
import math
import time
import re
import os
import sys
import requests
import logging
import shutil
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ─────────────────────────────────────────────────────
#                   LOGGING SETUP
# ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.WARNING,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════
#                      CONFIG
# ═══════════════════════════════════════════════════
BOT_TOKEN      = os.environ.get('BOT_TOKEN',        '8669859381:AAHikP0guXq5JXXViVT5G28eAYEhveIx5qg')
OWNER_ID       = int(os.environ.get('OWNER_ID',     '7493660827'))
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD',   'Rimjhim')

# Force Join Config
CHANNEL_USERNAME = os.environ.get('CHANNEL_USERNAME', "@ERRORARMY1")
CHANNEL_URL      = os.environ.get('CHANNEL_URL',      "https://t.me/ERRORARMY1")
GROUP_USERNAME   = os.environ.get('GROUP_USERNAME',   "ERRORARMY1")
GROUP_URL        = os.environ.get('GROUP_URL',        "https://t.me/+ymUEGuWGnYExMmZl")
CHANNEL_ID       = os.environ.get('CHANNEL_ID',       "@ERRORARMY1")

# Payment Config
INR_TO_CREDITS   = 3          # 1 INR = 3 Credits
QR_IMAGE_URL     = "https://raw.githubusercontent.com/developer9692-boop/Instgram-Services/main/qr.png"
MIN_PAYMENT_INR  = 10         # Minimum payment in INR

# ═══════════════════════════════════════════════════
#                     SERVICES
# ═══════════════════════════════════════════════════
services = {
    "Followers": {"name": "👤 Followers", "base": 100,  "cost": 10, "icon": "👤"},
    "Likes":     {"name": "❤️ Likes",     "base": 100,  "cost": 5,  "icon": "❤️"},
    "Views":     {"name": "👁 Views",      "base": 1000, "cost": 2,  "icon": "👁"},
    "Shares":    {"name": "🔁 Shares",    "base": 1000, "cost": 5,  "icon": "🔁"},
    "Comments":  {"name": "💬 Comments",  "base": 100,  "cost": 3,  "icon": "💬"},
}

# ═══════════════════════════════════════════════════
#                    BOT INIT
# ═══════════════════════════════════════════════════
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

# ═══════════════════════════════════════════════════
#                DESIGN ELEMENTS
# ═══════════════════════════════════════════════════
DIV  = "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰"
DIV2 = "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
DIV3 = "━━━━━━━━━━━━━━━━━━━━"

# ═══════════════════════════════════════════════════
#                    DATABASE
# ═══════════════════════════════════════════════════
def db():
    conn = sqlite3.connect('bot.db', check_same_thread=False, timeout=20)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=15000")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT    DEFAULT '',
            first_name  TEXT    DEFAULT '',
            credits     INTEGER DEFAULT 0,
            referral_id INTEGER,
            step        TEXT    DEFAULT '',
            is_verified INTEGER DEFAULT 0,
            is_banned   INTEGER DEFAULT 0,
            joined_at   INTEGER DEFAULT 0
        )
    """)

    # Orders table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER,
            service_name TEXT,
            quantity     INTEGER,
            link         TEXT,
            cost         INTEGER,
            status       TEXT
        )
    """)

    # Redeem codes
    cur.execute("""
        CREATE TABLE IF NOT EXISTS redeem_codes (
            code         TEXT PRIMARY KEY,
            reward_value INTEGER,
            max_uses     INTEGER,
            current_uses INTEGER DEFAULT 0
        )
    """)

    # Redeem history
    cur.execute("""
        CREATE TABLE IF NOT EXISTS redeem_history (
            user_id  INTEGER,
            code     TEXT,
            PRIMARY KEY (user_id, code)
        )
    """)

    # Payments table (NEW)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            payment_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        INTEGER,
            amount_inr     INTEGER,
            credits        INTEGER,
            transaction_id TEXT,
            status         TEXT    DEFAULT 'Pending',
            created_time   INTEGER DEFAULT 0
        )
    """)

    # Migration: add missing columns gracefully
    migrations = [
        "ALTER TABLE users ADD COLUMN username TEXT DEFAULT ''",
        "ALTER TABLE users ADD COLUMN first_name TEXT DEFAULT ''",
        "ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN joined_at INTEGER DEFAULT 0",
    ]
    for sql in migrations:
        try:
            cur.execute(sql)
            conn.commit()
        except Exception:
            pass

    conn.commit()
    return conn


# ═══════════════════════════════════════════════════
#                  USER HELPERS
# ═══════════════════════════════════════════════════
def getUser(user_id):
    try:
        conn = db()
        cur  = conn.cursor()
        cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        u = cur.fetchone()
        if not u:
            cur.execute(
                "INSERT INTO users (user_id, joined_at) VALUES (?,?)",
                (user_id, int(time.time()))
            )
            conn.commit()
            conn.close()
            return getUser(user_id)
        result = dict(u)
        conn.close()
        return result
    except Exception as e:
        logger.error(f"getUser error: {e}")
        return {
            'user_id': user_id, 'username': '', 'first_name': '',
            'credits': 0, 'step': '', 'is_verified': 0,
            'is_banned': 0, 'joined_at': 0
        }


def updateUserInfo(user_id, username, first_name):
    try:
        conn = db()
        conn.execute(
            "UPDATE users SET username=?, first_name=? WHERE user_id=?",
            (username or '', first_name or '', user_id)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"updateUserInfo error: {e}")


def setStep(user_id, step):
    try:
        conn = db()
        conn.execute("UPDATE users SET step=? WHERE user_id=?", (step, user_id))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"setStep error: {e}")


# ═══════════════════════════════════════════════════
#              BACKUP / RESTORE FUNCTIONS
# ═══════════════════════════════════════════════════
DB_PATH    = 'bot.db'
BACKUP_PATH = 'bot_backup.db'

def send_db_backup(chat_id, label="Manual Backup"):
    """Send the bot.db file to a Telegram chat (owner/admin)."""
    try:
        if not os.path.exists(DB_PATH):
            bot.send_message(chat_id, "❌ Database file not found!")
            return
        # Make a safe copy to avoid locking issues
        shutil.copy2(DB_PATH, BACKUP_PATH)
        size_kb = os.path.getsize(BACKUP_PATH) / 1024
        ts = time.strftime('%Y-%m-%d %H:%M:%S')
        caption = (
            f"🗄 <b>DATABASE BACKUP</b>\n"
            f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n\n"
            f"📅 <b>Time   :</b> {ts}\n"
            f"📝 <b>Label  :</b> {label}\n"
            f"💾 <b>Size   :</b> {size_kb:.1f} KB\n\n"
            f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
            f"⬆️ Send this file back with /restore to recover data on a new server."
        )
        with open(BACKUP_PATH, 'rb') as f:
            bot.send_document(
                chat_id,
                f,
                caption=caption,
                parse_mode="HTML",
                visible_file_name=f"boostxgram_backup_{time.strftime('%Y%m%d_%H%M%S')}.db"
            )
        logger.info(f"Backup sent to {chat_id} ({label})")
    except Exception as e:
        logger.error(f"send_db_backup error: {e}")
        try:
            bot.send_message(chat_id, f"❌ Backup failed: {e}")
        except Exception:
            pass


def auto_backup_loop():
    """Background thread: sends backup to owner every 24 hours."""
    INTERVAL = 24 * 60 * 60  # 24 hours
    while True:
        time.sleep(INTERVAL)
        try:
            send_db_backup(OWNER_ID, label="Auto Backup (24h)")
            logger.info("Auto-backup sent to owner.")
        except Exception as e:
            logger.error(f"auto_backup_loop error: {e}")


# ─── /backup command ───────────────────────────────
@bot.message_handler(commands=['backup'])
def cmd_backup(message):
    uid = message.from_user.id
    if uid != OWNER_ID:
        bot.send_message(message.chat.id, "❌ Owner only command.")
        return
    bot.send_message(message.chat.id, "⏳ Preparing database backup...")
    send_db_backup(message.chat.id, label="Manual /backup")


# ─── /restore command ──────────────────────────────
@bot.message_handler(commands=['restore'])
def cmd_restore(message):
    uid = message.from_user.id
    if uid != OWNER_ID:
        bot.send_message(message.chat.id, "❌ Owner only command.")
        return
    bot.send_message(
        message.chat.id,
        "📤 <b>RESTORE MODE</b>\n"
        "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n\n"
        "Send your backed-up <code>.db</code> file now as a document.\n"
        "⚠️ This will <b>overwrite</b> the current database!\n\n"
        "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(message, handle_restore_upload)


def handle_restore_upload(message):
    uid = message.from_user.id
    if uid != OWNER_ID:
        return
    try:
        if not message.document:
            bot.send_message(message.chat.id, "❌ No file received. Send the .db file as a document.")
            return
        fname = message.document.file_name or ""
        if not fname.endswith('.db'):
            bot.send_message(message.chat.id, "❌ Invalid file. Must be a .db file.")
            return
        # Download the file
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        # Backup existing db before overwriting
        if os.path.exists(DB_PATH):
            shutil.copy2(DB_PATH, DB_PATH + '.pre_restore')
        # Write restored db
        with open(DB_PATH, 'wb') as f:
            f.write(downloaded)
        # Verify it's a valid SQLite file
        try:
            test_conn = sqlite3.connect(DB_PATH)
            test_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            test_conn.close()
        except Exception:
            # Rollback
            if os.path.exists(DB_PATH + '.pre_restore'):
                shutil.copy2(DB_PATH + '.pre_restore', DB_PATH)
            bot.send_message(message.chat.id, "❌ File is not a valid SQLite database. Restore cancelled.")
            return
        bot.send_message(
            message.chat.id,
            "✅ <b>DATABASE RESTORED!</b>\n"
            "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n\n"
            "All users and data have been restored.\n"
            "🔄 Restart the bot if needed for changes to take full effect.\n\n"
            "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰",
            parse_mode="HTML"
        )
        logger.info(f"Database restored from file by owner {uid}")
    except Exception as e:
        logger.error(f"handle_restore_upload error: {e}")
        bot.send_message(message.chat.id, f"❌ Restore failed: {e}")


# ═══════════════════════════════════════════════════
#               CHANNEL CHECK (FORCE JOIN)
# ═══════════════════════════════════════════════════
def isJoined(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status in ('left', 'kicked'):
            return False
    except Exception:
        return False
    return True


# ═══════════════════════════════════════════════════
#                  URL VALIDATOR
# ═══════════════════════════════════════════════════
URL_RE = re.compile(
    r'^(https?|ftp)://'
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
    r'localhost|\d{1,3}(?:\.\d{1,3}){3})'
    r'(?::\d+)?(?:/?|[/?]\S+)$', re.IGNORECASE
)


# ═══════════════════════════════════════════════════
#              UI BUILDERS
# ═══════════════════════════════════════════════════

def send_join_screen(chat_id, first_name=""):
    name_str = f" <b>{first_name}</b>" if first_name else ""
    text = (
        f"🌌 <b>WELCOME{name_str}!</b>\n"
        f"{DIV}\n\n"
        "🔐 <b>Access Restricted</b>\n\n"
        "To unlock <b>BoostXGram SMM Panel</b>\n"
        "you must join our community first!\n\n"
        f"{DIV2}\n\n"
        "📢 <b>Step 1 —</b> Join our Channel\n"
        f"  ➤ <code>{CHANNEL_USERNAME}</code>\n\n"
        "👥 <b>Step 2 —</b> Join our Group\n"
        f"  ➤ <code>{GROUP_USERNAME}</code>\n\n"
        f"{DIV2}\n\n"
        "✅ After joining both, tap <b>\"Verify Me\"</b> below\n\n"
        f"{DIV}"
    )
    mk = InlineKeyboardMarkup()
    mk.row(
        InlineKeyboardButton("📢 Join Channel", url=CHANNEL_URL),
        InlineKeyboardButton("👥 Join Group",   url=GROUP_URL)
    )
    mk.row(InlineKeyboardButton("✅ Verify Me — I've Joined!", callback_data="verify"))
    try:
        bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=mk)
    except Exception as e:
        logger.error(f"send_join_screen error: {e}")


def send_main_menu(chat_id, user):
    credits = user['credits']
    uid     = user['user_id']
    name    = user.get('first_name', '') or 'User'
    text = (
        f"⚡ <b>BOOSTXGRAM SMM PANEL</b> ⚡\n"
        f"{DIV}\n\n"
        f"👋 Hello, <b>{name}</b>!\n\n"
        f"┌ 🆔 <b>Your ID   :</b> <code>{uid}</code>\n"
        f"└ 💎 <b>Credits   :</b> <b>{credits}</b> credits\n\n"
        f"{DIV2}\n"
        f"🚀 <b>What would you like to do?</b>\n"
        f"{DIV2}\n\n"
        "  🛒  Order social media services\n"
        "  💳  Add funds via UPI payment\n"
        "  🎁  Redeem codes for free credits\n"
        "  📦  Track your orders\n"
        "  📬  Message the owner directly\n\n"
        f"{DIV}\n"
        "🌐 <b>BoostXGram — Pro SMM Services</b>"
    )
    mk = InlineKeyboardMarkup()
    mk.row(
        InlineKeyboardButton("🛒 Order Services", callback_data="menu_order"),
        InlineKeyboardButton("💳 Add Funds",       callback_data="menu_addfunds")
    )
    mk.row(
        InlineKeyboardButton("💎 My Wallet",      callback_data="menu_balance"),
        InlineKeyboardButton("📦 My Orders",      callback_data="menu_myorders")
    )
    mk.row(
        InlineKeyboardButton("🎁 Redeem Code",    callback_data="menu_redeem"),
        InlineKeyboardButton("📋 How to Use",     callback_data="menu_howto")
    )
    mk.row(
        InlineKeyboardButton("📖 FAQ",            callback_data="menu_faq"),
        InlineKeyboardButton("📬 Contact Owner",  callback_data="menu_contact")
    )
    try:
        bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=mk)
    except Exception as e:
        logger.error(f"send_main_menu error: {e}")


def send_service_menu(chat_id):
    text = (
        f"🛒 <b>SELECT A SERVICE</b>\n"
        f"{DIV}\n\n"
        "Choose the boost you want to order:\n\n"
        f"  👤 <b>Followers</b>  ·  10 credits / 100\n"
        f"  ❤️ <b>Likes</b>      ·  5 credits  / 100\n"
        f"  👁 <b>Views</b>      ·  2 credits  / 1,000\n"
        f"  🔁 <b>Shares</b>     ·  5 credits  / 1,000\n"
        f"  💬 <b>Comments</b>   ·  3 credits  / 100\n\n"
        f"{DIV2}\n"
        f"💡 <i>Minimum order: 100 units per service</i>\n"
        f"{DIV}"
    )
    mk = InlineKeyboardMarkup()
    mk.row(
        InlineKeyboardButton("👤 Followers", callback_data="svc_Followers"),
        InlineKeyboardButton("❤️ Likes",     callback_data="svc_Likes")
    )
    mk.row(
        InlineKeyboardButton("👁 Views",     callback_data="svc_Views"),
        InlineKeyboardButton("🔁 Shares",   callback_data="svc_Shares")
    )
    mk.row(InlineKeyboardButton("💬 Comments", callback_data="svc_Comments"))
    mk.row(InlineKeyboardButton("🏠 Back to Home", callback_data="back_home"))
    try:
        bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=mk)
    except Exception as e:
        logger.error(f"send_service_menu error: {e}")


def send_order_summary(chat_id, service, qty, cost):
    s = services[service]
    text = (
        f"📊 <b>ORDER SUMMARY</b>\n"
        f"{DIV}\n\n"
        f"┌ 📦 <b>Service  :</b>  {s['name']}\n"
        f"├ 🔢 <b>Quantity :</b>  {qty:,} units\n"
        f"└ 💰 <b>Cost     :</b>  {cost} credits\n\n"
        f"{DIV2}\n"
        "✅ Confirm to deduct credits & proceed\n"
        "   You'll send your link in the next step.\n"
        f"{DIV}"
    )
    mk = InlineKeyboardMarkup()
    mk.row(InlineKeyboardButton(f"✅ Confirm & Pay {cost} Credits", callback_data=f"confirm_{service}_{qty}_{cost}"))
    mk.row(InlineKeyboardButton("✏️ Change Quantity", callback_data=f"svc_{service}"))
    mk.row(InlineKeyboardButton("🏠 Back to Home",    callback_data="back_home"))
    try:
        bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=mk)
    except Exception as e:
        logger.error(f"send_order_summary error: {e}")


def send_faq(chat_id):
    text = (
        f"📖 <b>FREQUENTLY ASKED QUESTIONS</b>\n"
        f"{DIV}\n\n"

        "❓ <b>What is BoostXGram?</b>\n"
        "   A paid Telegram SMM panel bot for\n"
        "   ordering Instagram & social media\n"
        "   services using credits.\n\n"

        "❓ <b>How do I get credits?</b>\n"
        f"   • Add funds via UPI: <b>1 INR = {INR_TO_CREDITS} Credits</b>\n"
        "   • Redeem promo codes\n"
        "   • Watch channels for giveaways\n\n"

        "❓ <b>How fast are orders delivered?</b>\n"
        "   Most orders complete within <b>1–24 hours</b>.\n\n"

        "❓ <b>What link should I send?</b>\n"
        "   A direct URL to your post/profile\n"
        "   starting with <code>https://</code>\n\n"

        "❓ <b>Minimum order size?</b>\n"
        "   Minimum <b>100 units</b> per order.\n\n"

        "❓ <b>Order delayed or issue?</b>\n"
        "   Use <b>📬 Contact Owner</b> button.\n\n"

        "❓ <b>Minimum top-up?</b>\n"
        f"   Minimum top-up is <b>₹{MIN_PAYMENT_INR}</b>.\n\n"

        f"{DIV}"
    )
    mk = InlineKeyboardMarkup()
    mk.row(
        InlineKeyboardButton("💳 Add Funds",    callback_data="menu_addfunds"),
        InlineKeyboardButton("🛒 Order Now",    callback_data="menu_order")
    )
    mk.row(InlineKeyboardButton("🏠 Back to Home", callback_data="back_home"))
    try:
        bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=mk)
    except Exception as e:
        logger.error(f"send_faq error: {e}")


def send_howto(chat_id):
    text = (
        f"📋 <b>HOW TO USE BOOSTXGRAM</b>\n"
        f"{DIV}\n\n"

        "① <b>Join Both Channels</b>\n"
        "   Join our channel & group to unlock\n"
        "   all bot features.\n\n"

        "② <b>Add Funds</b>\n"
        f"   💳 Add Funds → Enter amount (₹)\n"
        f"   → Pay via UPI → Send UTR ID\n"
        f"   → Admin approves → Credits added!\n\n"

        "③ <b>Place an Order</b>\n"
        "   🛒 Order Services → Pick service\n"
        "   → Enter quantity (min 100)\n"
        "   → Confirm → Send your link\n\n"

        "④ <b>Wait for Delivery</b>\n"
        "   You'll get a notification when\n"
        "   your order is completed ✅\n\n"

        f"{DIV2}\n"
        f"💰 <b>PRICING TABLE</b>\n"
        f"{DIV2}\n\n"
        "  👤 Followers — 10 cr / 100\n"
        "  ❤️ Likes     —  5 cr / 100\n"
        "  👁 Views     —  2 cr / 1,000\n"
        "  🔁 Shares    —  5 cr / 1,000\n"
        "  💬 Comments  —  3 cr / 100\n\n"
        f"{DIV2}\n"
        f"💳 <b>TOP-UP RATE</b>\n"
        f"{DIV2}\n\n"
        f"  1 INR = {INR_TO_CREDITS} Credits\n"
        f"  Minimum top-up: ₹{MIN_PAYMENT_INR}\n\n"
        f"{DIV}\n"
        "💡 <i>cr = credits</i>"
    )
    mk = InlineKeyboardMarkup()
    mk.row(
        InlineKeyboardButton("💳 Add Funds", callback_data="menu_addfunds"),
        InlineKeyboardButton("🛒 Order Now", callback_data="menu_order")
    )
    mk.row(InlineKeyboardButton("🏠 Back to Home", callback_data="back_home"))
    try:
        bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=mk)
    except Exception as e:
        logger.error(f"send_howto error: {e}")


def send_balance(chat_id, user):
    try:
        conn = db()
        cur  = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM orders WHERE user_id=?", (user['user_id'],))
        total_orders = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM orders WHERE user_id=? AND status='Completed'", (user['user_id'],))
        done_orders = cur.fetchone()[0]
        cur.execute(
            "SELECT COUNT(*), COALESCE(SUM(amount_inr),0) FROM payments WHERE user_id=? AND status='Approved'",
            (user['user_id'],)
        )
        pay_row = cur.fetchone()
        total_payments = pay_row[0]
        total_spent    = pay_row[1]
        cur.execute(
            "SELECT amount_inr, credits, status, created_time FROM payments WHERE user_id=? ORDER BY payment_id DESC LIMIT 3",
            (user['user_id'],)
        )
        recent_payments = [dict(r) for r in cur.fetchall()]
        conn.close()
    except Exception as e:
        logger.error(f"send_balance db error: {e}")
        total_orders    = 0
        done_orders     = 0
        total_payments  = 0
        total_spent     = 0
        recent_payments = []

    joined = time.strftime("%d %b %Y", time.localtime(user.get('joined_at') or 0))
    text = (
        f"💎 <b>MY WALLET</b>\n"
        f"{DIV}\n\n"
        f"┌ 👤 <b>Name      :</b> {user.get('first_name','') or 'User'}\n"
        f"├ 🆔 <b>User ID   :</b> <code>{user['user_id']}</code>\n"
        f"└ 📅 <b>Joined    :</b> {joined}\n\n"
        f"{DIV2}\n"
        f"💰 <b>BALANCE</b>\n"
        f"{DIV2}\n\n"
        f"  💎 Credits Available : <b>{user['credits']}</b>\n\n"
        f"{DIV2}\n"
        f"📦 <b>ORDERS</b>\n"
        f"{DIV2}\n\n"
        f"  📦 Total Orders    : {total_orders}\n"
        f"  ✅ Completed       : {done_orders}\n"
        f"  ⏳ Pending         : {total_orders - done_orders}\n\n"
        f"{DIV2}\n"
        f"💳 <b>PAYMENTS</b>\n"
        f"{DIV2}\n\n"
        f"  💸 Total Paid      : ₹{total_spent}\n"
        f"  🔄 Transactions    : {total_payments}\n"
    )

    if recent_payments:
        text += f"\n{DIV2}\n📋 <b>RECENT PAYMENTS</b>\n{DIV2}\n\n"
        for p in recent_payments:
            status_icon = "✅" if p['status'] == "Approved" else ("❌" if p['status'] == "Declined" else "⏳")
            dt = time.strftime("%d %b", time.localtime(p['created_time']))
            text += (
                f"  {status_icon} ₹{p['amount_inr']} → {p['credits']} cr  [{dt}]\n"
            )

    text += f"\n{DIV}"
    mk = InlineKeyboardMarkup()
    mk.row(
        InlineKeyboardButton("💳 Add Funds",   callback_data="menu_addfunds"),
        InlineKeyboardButton("🛒 Order Now",   callback_data="menu_order")
    )
    mk.row(
        InlineKeyboardButton("🎁 Redeem Code", callback_data="menu_redeem"),
        InlineKeyboardButton("🏠 Home",        callback_data="back_home")
    )
    try:
        bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=mk)
    except Exception as e:
        logger.error(f"send_balance send error: {e}")


def send_my_orders(chat_id, user_id):
    try:
        conn = db()
        cur  = conn.cursor()
        cur.execute(
            "SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 5",
            (user_id,)
        )
        rows = cur.fetchall()
        conn.close()
    except Exception as e:
        logger.error(f"send_my_orders error: {e}")
        rows = []

    if not rows:
        text = (
            f"📦 <b>MY ORDERS</b>\n"
            f"{DIV}\n\n"
            "😕 You haven't placed any orders yet.\n\n"
            "Tap 🛒 <b>Order Services</b> to get started!\n\n"
            f"{DIV}"
        )
    else:
        text = (
            f"📦 <b>MY RECENT ORDERS</b>\n"
            f"{DIV}\n\n"
        )
        for o in rows:
            o = dict(o)
            status_icon = "✅" if o['status'] == "Completed" else "⏳"
            text += (
                f"┌ 🆔 <b>Order #{o['id']}</b>\n"
                f"├ 📦 {o['service_name']}  ·  {o['quantity']:,} units\n"
                f"├ 💰 {o['cost']} credits\n"
                f"└ {status_icon} <b>{o['status']}</b>\n\n"
            )
        text += f"{DIV}\n📋 Showing last 5 orders"

    mk = InlineKeyboardMarkup()
    mk.row(InlineKeyboardButton("🛒 New Order",    callback_data="menu_order"))
    mk.row(InlineKeyboardButton("🏠 Back to Home", callback_data="back_home"))
    try:
        bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=mk)
    except Exception as e:
        logger.error(f"send_my_orders send error: {e}")


# ═══════════════════════════════════════════════════
#          PAYMENT UI & FLOW BUILDERS
# ═══════════════════════════════════════════════════

def send_add_funds_prompt(chat_id, user_id):
    setStep(user_id, "payment_amount")
    mk = InlineKeyboardMarkup()
    mk.row(InlineKeyboardButton("🔙 Cancel", callback_data="back_home"))
    bot.send_message(
        chat_id,
        f"💳 <b>ADD FUNDS TO WALLET</b>\n"
        f"{DIV}\n\n"
        f"💡 <b>Exchange Rate:</b> 1 INR = {INR_TO_CREDITS} Credits\n"
        f"📏 <b>Minimum Top-up:</b> ₹{MIN_PAYMENT_INR}\n\n"
        f"{DIV2}\n"
        "💰 <b>How many rupees do you want to add?</b>\n\n"
        "<i>Send a number (e.g. 50, 100, 500)</i>\n\n"
        f"{DIV}",
        parse_mode="HTML",
        reply_markup=mk
    )


def send_payment_confirmation(chat_id, user_id, amount_inr, credits):
    mk = InlineKeyboardMarkup()
    mk.row(InlineKeyboardButton("✅ Confirm Payment", callback_data=f"pay_confirm_{amount_inr}_{credits}"))
    mk.row(InlineKeyboardButton("✏️ Change Amount",   callback_data="menu_addfunds"))
    mk.row(InlineKeyboardButton("🔙 Cancel",          callback_data="back_home"))
    bot.send_message(
        chat_id,
        f"💳 <b>PAYMENT CONFIRMATION</b>\n"
        f"{DIV}\n\n"
        f"┌ 💸 <b>Amount     :</b> ₹{amount_inr}\n"
        f"├ 💎 <b>Credits    :</b> +{credits} credits\n"
        f"└ 💱 <b>Rate       :</b> 1 INR = {INR_TO_CREDITS} Credits\n\n"
        f"{DIV2}\n"
        "✅ Click <b>Confirm Payment</b> to proceed\n"
        "You'll receive a UPI QR code to scan.\n\n"
        f"{DIV}",
        parse_mode="HTML",
        reply_markup=mk
    )


def send_qr_and_ask_utr(chat_id, user_id, amount_inr, credits):
    setStep(user_id, f"payment_utr:{amount_inr}:{credits}")
    try:
        # Download QR from GitHub
        resp = requests.get(QR_IMAGE_URL, timeout=10)
        if resp.status_code == 200:
            bot.send_photo(
                chat_id,
                resp.content,
                caption=(
                    f"📷 <b>UPI PAYMENT QR CODE</b>\n"
                    f"{DIV}\n\n"
                    f"┌ 💸 <b>Pay Amount :</b> ₹{amount_inr}\n"
                    f"└ 💎 <b>You'll Get  :</b> {credits} Credits\n\n"
                    f"{DIV2}\n"
                    "📌 <b>Steps:</b>\n"
                    "  1. Open any UPI app\n"
                    "  2. Scan the QR code above\n"
                    f"  3. Pay exactly <b>₹{amount_inr}</b>\n"
                    "  4. Copy the <b>Transaction/UTR ID</b>\n\n"
                    f"{DIV}\n"
                    "⬇️ <b>Send your Transaction ID / UTR Number below:</b>"
                ),
                parse_mode="HTML"
            )
        else:
            raise Exception("QR fetch failed")
    except Exception as e:
        logger.error(f"QR fetch error: {e}")
        # Fallback text if QR can't be fetched
        bot.send_message(
            chat_id,
            f"💳 <b>UPI PAYMENT</b>\n"
            f"{DIV}\n\n"
            f"┌ 💸 <b>Pay Amount :</b> ₹{amount_inr}\n"
            f"└ 💎 <b>You'll Get  :</b> {credits} Credits\n\n"
            f"{DIV2}\n"
            "⚠️ QR image temporarily unavailable.\n"
            "Contact admin for UPI details.\n\n"
            f"{DIV2}\n"
            "📌 After payment, send your\n"
            "<b>Transaction ID / UTR Number</b> below:\n\n"
            f"{DIV}",
            parse_mode="HTML"
        )

    mk = InlineKeyboardMarkup()
    mk.row(InlineKeyboardButton("🔙 Cancel", callback_data="back_home"))
    bot.send_message(
        chat_id,
        "✏️ <b>Enter your Transaction ID / UTR Number:</b>",
        parse_mode="HTML",
        reply_markup=mk
    )


def forward_payment_to_admin(user_id, username, first_name, amount_inr, credits, utr, payment_id):
    uname = f"@{username}" if username else "—"
    mk = InlineKeyboardMarkup()
    mk.row(
        InlineKeyboardButton("✅ Approve", callback_data=f"pay_approve_{payment_id}"),
        InlineKeyboardButton("❌ Decline", callback_data=f"pay_decline_{payment_id}")
    )
    try:
        bot.send_message(
            OWNER_ID,
            f"💳 <b>NEW PAYMENT REQUEST</b>\n"
            f"{DIV}\n\n"
            f"┌ 👤 <b>User ID   :</b> <code>{user_id}</code>\n"
            f"├ 📛 <b>Name      :</b> {first_name or '—'}\n"
            f"├ 🔗 <b>Username  :</b> {uname}\n"
            f"├ 💸 <b>Amount    :</b> ₹{amount_inr}\n"
            f"├ 💎 <b>Credits   :</b> {credits}\n"
            f"├ 🔖 <b>UTR/TxnID :</b> <code>{utr}</code>\n"
            f"└ 🆔 <b>Pay ID    :</b> #{payment_id}\n\n"
            f"{DIV}\n"
            "⬆️ Tap to <b>Approve</b> or <b>Decline</b> this payment:",
            parse_mode="HTML",
            reply_markup=mk
        )
    except Exception as e:
        logger.error(f"forward_payment_to_admin error: {e}")


# ═══════════════════════════════════════════════════
#              ADMIN PANEL (ENHANCED)
# ═══════════════════════════════════════════════════

def send_admin_panel(chat_id):
    mk = InlineKeyboardMarkup()
    mk.row(
        InlineKeyboardButton("📊 Statistics",     callback_data="adm_stats"),
        InlineKeyboardButton("👥 Manage Users",   callback_data="adm_users")
    )
    mk.row(
        InlineKeyboardButton("📦 View Orders",    callback_data="adm_orders"),
        InlineKeyboardButton("🎟 Create Code",    callback_data="adm_createcode")
    )
    mk.row(
        InlineKeyboardButton("💳 Payments",       callback_data="adm_payments"),
        InlineKeyboardButton("⏳ Pending Pays",   callback_data="adm_pending_pays")
    )
    mk.row(
        InlineKeyboardButton("📢 Broadcast",      callback_data="adm_broadcast"),
        InlineKeyboardButton("🔍 Find User",      callback_data="adm_finduser")
    )
    try:
        bot.send_message(
            chat_id,
            f"👑 <b>ADMIN CONTROL PANEL</b>\n"
            f"{DIV}\n\n"
            "Welcome back, <b>Admin</b>! 🔑\n\n"
            "Select an action from the menu below:\n\n"
            f"{DIV}",
            parse_mode="HTML",
            reply_markup=mk
        )
    except Exception as e:
        logger.error(f"send_admin_panel error: {e}")


def send_admin_user_profile(chat_id, target_id):
    try:
        conn = db()
        cur  = conn.cursor()
        cur.execute("SELECT * FROM users WHERE user_id=?", (target_id,))
        u = cur.fetchone()
        if not u:
            conn.close()
            mk = InlineKeyboardMarkup()
            mk.row(InlineKeyboardButton("🔙 Back", callback_data="adm_users"))
            bot.send_message(
                chat_id,
                f"❌ <b>User not found.</b>\n\nNo user with ID <code>{target_id}</code> exists.",
                parse_mode="HTML", reply_markup=mk
            )
            return
        u = dict(u)
        cur.execute("SELECT COUNT(*) FROM orders WHERE user_id=?", (target_id,))
        total_orders = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM orders WHERE user_id=? AND status='Completed'", (target_id,))
        done_orders = cur.fetchone()[0]
        cur.execute(
            "SELECT COUNT(*), COALESCE(SUM(amount_inr),0) FROM payments WHERE user_id=? AND status='Approved'",
            (target_id,)
        )
        pay_row = cur.fetchone()
        conn.close()
    except Exception as e:
        logger.error(f"send_admin_user_profile error: {e}")
        return

    ban_status = "🚫 BANNED" if u.get('is_banned') else "✅ Active"
    joined = time.strftime("%d %b %Y", time.localtime(u.get('joined_at') or 0))
    uname  = f"@{u['username']}" if u.get('username') else "—"

    text = (
        f"👤 <b>USER PROFILE</b>\n"
        f"{DIV}\n\n"
        f"┌ 🆔 <b>User ID   :</b> <code>{u['user_id']}</code>\n"
        f"├ 📛 <b>Name      :</b> {u.get('first_name','') or '—'}\n"
        f"├ 🔗 <b>Username  :</b> {uname}\n"
        f"├ 📅 <b>Joined    :</b> {joined}\n"
        f"├ 💎 <b>Credits   :</b> {u['credits']}\n"
        f"└ 🔒 <b>Status    :</b> {ban_status}\n\n"
        f"{DIV2}\n"
        f"📦 Orders  : {total_orders} total  ·  {done_orders} completed\n"
        f"💸 Spent   : ₹{pay_row[1]}  ·  {pay_row[0]} transactions\n"
        f"{DIV}"
    )

    ban_btn = "✅ Unban User" if u.get('is_banned') else "🚫 Ban User"
    ban_cb  = f"adm_unban_{target_id}" if u.get('is_banned') else f"adm_ban_{target_id}"

    mk = InlineKeyboardMarkup()
    mk.row(
        InlineKeyboardButton("➕ Add Credits",    callback_data=f"adm_addfunds_{target_id}"),
        InlineKeyboardButton("➖ Remove Credits", callback_data=f"adm_removefunds_{target_id}")
    )
    mk.row(
        InlineKeyboardButton(ban_btn,             callback_data=ban_cb),
        InlineKeyboardButton("📨 Send Message",   callback_data=f"adm_msg_{target_id}")
    )
    mk.row(InlineKeyboardButton("🔙 Back to Users", callback_data="adm_users"))
    try:
        bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=mk)
    except Exception as e:
        logger.error(f"send_admin_user_profile send error: {e}")


# ═══════════════════════════════════════════════════
#               CALLBACK HANDLER
# ═══════════════════════════════════════════════════
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    try:
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        data    = call.data

        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass

        user = getUser(user_id)

        # ── BANNED CHECK ──────────────────────────────
        if user.get('is_banned') and user_id != OWNER_ID:
            try:
                bot.answer_callback_query(call.id, "🚫 You are banned from using this bot.", show_alert=True)
            except Exception:
                pass
            return

        # ── VERIFY ────────────────────────────────────
        if data == "verify":
            if isJoined(user_id):
                try:
                    conn = db()
                    conn.execute("UPDATE users SET is_verified=1 WHERE user_id=?", (user_id,))
                    conn.commit()
                    conn.close()
                except Exception as e:
                    logger.error(f"verify db error: {e}")
                bot.send_message(
                    chat_id,
                    f"🎉 <b>Verification Successful!</b>\n\n"
                    f"Welcome to <b>BoostXGram SMM Panel</b>!\n"
                    f"Add funds to start ordering services 🚀\n\n"
                    f"💳 Tap <b>Add Funds</b> to top up your wallet.",
                    parse_mode="HTML"
                )
                user = getUser(user_id)
                send_main_menu(chat_id, user)
            else:
                try:
                    bot.answer_callback_query(
                        call.id,
                        "❌ You haven't joined both yet!\nPlease join the channel & group first.",
                        show_alert=True
                    )
                except Exception:
                    pass
            return

        # ── BACK HOME ─────────────────────────────────
        if data == "back_home":
            setStep(user_id, "")
            user = getUser(user_id)
            send_main_menu(chat_id, user)
            return

        # ── MAIN MENU BUTTONS ─────────────────────────
        if data == "menu_order":
            setStep(user_id, "service")
            send_service_menu(chat_id)
            return

        if data == "menu_addfunds":
            send_add_funds_prompt(chat_id, user_id)
            return

        if data == "menu_redeem":
            setStep(user_id, "redeem")
            mk = InlineKeyboardMarkup()
            mk.row(InlineKeyboardButton("🔙 Cancel", callback_data="back_home"))
            bot.send_message(
                chat_id,
                f"🎁 <b>REDEEM A CODE</b>\n"
                f"{DIV}\n\n"
                "Type and send your <b>promo code</b> below 👇\n\n"
                "💡 <i>Codes are shared in our channels\n"
                "or given out by the owner during events.</i>\n\n"
                f"{DIV}",
                parse_mode="HTML",
                reply_markup=mk
            )
            return

        if data == "menu_faq":
            send_faq(chat_id)
            return

        if data == "menu_howto":
            send_howto(chat_id)
            return

        if data == "menu_balance":
            user = getUser(user_id)
            send_balance(chat_id, user)
            return

        if data == "menu_myorders":
            send_my_orders(chat_id, user_id)
            return

        if data == "menu_contact":
            setStep(user_id, "contact")
            mk = InlineKeyboardMarkup()
            mk.row(InlineKeyboardButton("🔙 Cancel", callback_data="back_home"))
            bot.send_message(
                chat_id,
                f"📬 <b>CONTACT THE OWNER</b>\n"
                f"{DIV}\n\n"
                "✏️ Type your message and send it.\n"
                "The owner will reply as soon as possible.\n\n"
                "💡 <i>Include your Order ID if it's\n"
                "related to a specific order.</i>\n\n"
                f"{DIV}",
                parse_mode="HTML",
                reply_markup=mk
            )
            return

        # ── SERVICE SELECT ────────────────────────────
        if data.startswith("svc_"):
            service = data[4:]
            if service not in services:
                return
            s = services[service]
            setStep(user_id, f"qty:{service}")
            mk = InlineKeyboardMarkup()
            mk.row(InlineKeyboardButton("🔙 Back to Services", callback_data="menu_order"))
            bot.send_message(
                chat_id,
                f"{s['icon']} <b>SERVICE SELECTED: {service.upper()}</b>\n"
                f"{DIV}\n\n"
                f"┌ 💰 <b>Rate    :</b> {s['cost']} credits per {s['base']:,}\n"
                f"└ 📏 <b>Minimum :</b> 100 units\n\n"
                f"{DIV2}\n"
                f"📝 <b>Enter the quantity you want:</b>\n"
                f"<i>(numbers only — e.g. 500, 1000, 5000)</i>\n\n"
                f"{DIV}",
                parse_mode="HTML",
                reply_markup=mk
            )
            return

        # ── CONFIRM ORDER ─────────────────────────────
        if data.startswith("confirm_"):
            parts   = data.split("_", 3)
            service = parts[1]
            qty     = int(parts[2])
            cost    = int(parts[3])
            user    = getUser(user_id)

            if user['credits'] < cost:
                mk = InlineKeyboardMarkup()
                mk.row(
                    InlineKeyboardButton("💳 Add Funds",   callback_data="menu_addfunds"),
                    InlineKeyboardButton("🎁 Redeem Code", callback_data="menu_redeem")
                )
                mk.row(InlineKeyboardButton("🏠 Home", callback_data="back_home"))
                bot.send_message(
                    chat_id,
                    f"❌ <b>NOT ENOUGH CREDITS</b>\n"
                    f"{DIV}\n\n"
                    f"  💰 You need   : <b>{cost}</b> credits\n"
                    f"  💎 You have   : <b>{user['credits']}</b> credits\n\n"
                    f"{DIV2}\n"
                    "💳 Add funds via UPI to top up!\n\n"
                    f"{DIV}",
                    parse_mode="HTML",
                    reply_markup=mk
                )
                return

            try:
                conn = db()
                conn.execute("UPDATE users SET credits=credits-? WHERE user_id=?", (cost, user_id))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"confirm order deduct error: {e}")

            setStep(user_id, f"link:{service}:{qty}:{cost}")
            mk = InlineKeyboardMarkup()
            mk.row(InlineKeyboardButton("🔙 Cancel Order", callback_data="back_home"))
            bot.send_message(
                chat_id,
                f"🔗 <b>SEND YOUR LINK</b>\n"
                f"{DIV}\n\n"
                f"✅ <b>{cost} credits</b> have been deducted.\n\n"
                "Now send the <b>direct URL</b> to your\n"
                "profile or post below 👇\n\n"
                "📌 <b>Example:</b>\n"
                "<code>https://instagram.com/yourprofile</code>\n\n"
                f"{DIV}\n"
                "⚠️ <i>Must start with https://</i>",
                parse_mode="HTML",
                reply_markup=mk
            )
            return

        # ── PAYMENT CONFIRM → SEND QR ─────────────────
        if data.startswith("pay_confirm_"):
            parts      = data.split("_")
            amount_inr = int(parts[2])
            credits    = int(parts[3])
            send_qr_and_ask_utr(chat_id, user_id, amount_inr, credits)
            return

        # ═══════════════════════════════════════════════
        #              ADMIN PAYMENT CALLBACKS
        # ═══════════════════════════════════════════════

        # ── ADMIN: APPROVE PAYMENT ────────────────────
        if data.startswith("pay_approve_") and user_id == OWNER_ID:
            payment_id = int(data.split("_")[2])
            try:
                conn = db()
                cur  = conn.cursor()
                cur.execute("SELECT * FROM payments WHERE payment_id=?", (payment_id,))
                pay = cur.fetchone()
                if not pay:
                    conn.close()
                    bot.answer_callback_query(call.id, "❌ Payment not found!", show_alert=True)
                    return
                pay = dict(pay)
                if pay['status'] != 'Pending':
                    conn.close()
                    bot.answer_callback_query(call.id, f"⚠️ Already {pay['status']}!", show_alert=True)
                    return
                conn.execute(
                    "UPDATE payments SET status='Approved' WHERE payment_id=?",
                    (payment_id,)
                )
                conn.execute(
                    "UPDATE users SET credits=credits+? WHERE user_id=?",
                    (pay['credits'], pay['user_id'])
                )
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"pay_approve error: {e}")
                bot.answer_callback_query(call.id, "❌ Error approving payment.", show_alert=True)
                return

            try:
                bot.answer_callback_query(call.id, f"✅ Payment #{payment_id} approved!", show_alert=True)
            except Exception:
                pass

            # Edit admin message
            try:
                bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
                bot.send_message(
                    chat_id,
                    f"✅ <b>Payment #{payment_id} APPROVED</b>\n"
                    f"User <code>{pay['user_id']}</code> received <b>{pay['credits']} credits</b>.",
                    parse_mode="HTML"
                )
            except Exception:
                pass

            # Notify user
            try:
                mk = InlineKeyboardMarkup()
                mk.row(
                    InlineKeyboardButton("🛒 Order Now", callback_data="menu_order"),
                    InlineKeyboardButton("💎 My Wallet", callback_data="menu_balance")
                )
                bot.send_message(
                    pay['user_id'],
                    f"🎉 <b>PAYMENT APPROVED!</b>\n"
                    f"{DIV}\n\n"
                    f"┌ 💸 <b>Amount Paid :</b> ₹{pay['amount_inr']}\n"
                    f"├ 💎 <b>Credits Added:</b> +{pay['credits']} credits\n"
                    f"└ 🆔 <b>Payment ID  :</b> #{payment_id}\n\n"
                    f"{DIV2}\n"
                    "✅ Credits have been added to your wallet!\n"
                    "You can now place orders. 🚀\n\n"
                    f"{DIV}",
                    parse_mode="HTML",
                    reply_markup=mk
                )
            except Exception:
                pass
            return

        # ── ADMIN: DECLINE PAYMENT ────────────────────
        if data.startswith("pay_decline_") and user_id == OWNER_ID:
            payment_id = int(data.split("_")[2])
            try:
                conn = db()
                cur  = conn.cursor()
                cur.execute("SELECT * FROM payments WHERE payment_id=?", (payment_id,))
                pay = cur.fetchone()
                if not pay:
                    conn.close()
                    bot.answer_callback_query(call.id, "❌ Payment not found!", show_alert=True)
                    return
                pay = dict(pay)
                if pay['status'] != 'Pending':
                    conn.close()
                    bot.answer_callback_query(call.id, f"⚠️ Already {pay['status']}!", show_alert=True)
                    return
                conn.execute(
                    "UPDATE payments SET status='Declined' WHERE payment_id=?",
                    (payment_id,)
                )
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"pay_decline error: {e}")
                return

            try:
                bot.answer_callback_query(call.id, f"❌ Payment #{payment_id} declined.", show_alert=True)
            except Exception:
                pass

            try:
                bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
                bot.send_message(
                    chat_id,
                    f"❌ <b>Payment #{payment_id} DECLINED</b>\n"
                    f"User <code>{pay['user_id']}</code> has been notified.",
                    parse_mode="HTML"
                )
            except Exception:
                pass

            # Notify user
            try:
                mk = InlineKeyboardMarkup()
                mk.row(
                    InlineKeyboardButton("💳 Try Again",    callback_data="menu_addfunds"),
                    InlineKeyboardButton("📬 Contact Admin", callback_data="menu_contact")
                )
                bot.send_message(
                    pay['user_id'],
                    f"❌ <b>PAYMENT DECLINED</b>\n"
                    f"{DIV}\n\n"
                    f"┌ 💸 <b>Amount :</b> ₹{pay['amount_inr']}\n"
                    f"└ 🆔 <b>Pay ID :</b> #{payment_id}\n\n"
                    f"{DIV2}\n"
                    "Your payment could not be verified.\n"
                    "No credits were added.\n\n"
                    "If you believe this is a mistake,\n"
                    "contact the admin with your UTR ID.\n\n"
                    f"{DIV}",
                    parse_mode="HTML",
                    reply_markup=mk
                )
            except Exception:
                pass
            return

        # ══════════════════════════════════════════════
        #              ADMIN CALLBACKS
        # ══════════════════════════════════════════════
        if user_id != OWNER_ID:
            return

        if data == "back_admin":
            setStep(user_id, "admin")
            send_admin_panel(chat_id)
            return

        # ── STATS ─────────────────────────────────────
        if data == "adm_stats":
            try:
                conn = db()
                cur  = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM users")
                u_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM users WHERE is_banned=1")
                banned_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM orders")
                o_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM orders WHERE status='Completed'")
                done = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM redeem_codes")
                codes = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*), COALESCE(SUM(amount_inr),0) FROM payments WHERE status='Approved'")
                pr = cur.fetchone()
                cur.execute("SELECT COUNT(*) FROM payments WHERE status='Pending'")
                pending_pays = cur.fetchone()[0]
                conn.close()
            except Exception as e:
                logger.error(f"adm_stats error: {e}")
                return
            mk = InlineKeyboardMarkup()
            mk.row(InlineKeyboardButton("🔙 Admin Panel", callback_data="back_admin"))
            bot.send_message(
                chat_id,
                f"📊 <b>BOT STATISTICS</b>\n"
                f"{DIV}\n\n"
                f"👥 <b>USERS</b>\n"
                f"  ├ Total      : {u_count}\n"
                f"  └ Banned     : {banned_count}\n\n"
                f"📦 <b>ORDERS</b>\n"
                f"  ├ Total      : {o_count}\n"
                f"  ├ Completed  : {done}\n"
                f"  └ Pending    : {o_count - done}\n\n"
                f"💳 <b>PAYMENTS</b>\n"
                f"  ├ Approved   : {pr[0]}\n"
                f"  ├ Revenue    : ₹{pr[1]}\n"
                f"  └ Pending    : {pending_pays}\n\n"
                f"🎟 <b>Promo Codes :</b> {codes}\n\n"
                f"{DIV}",
                parse_mode="HTML",
                reply_markup=mk
            )
            return

        # ── USERS LIST ────────────────────────────────
        if data == "adm_users":
            try:
                conn = db()
                cur  = conn.cursor()
                cur.execute("SELECT user_id, first_name, credits, is_banned FROM users ORDER BY user_id DESC LIMIT 20")
                rows = cur.fetchall()
                conn.close()
            except Exception as e:
                logger.error(f"adm_users error: {e}")
                return

            msg_text = f"👥 <b>USERS LIST</b> (last 20)\n{DIV}\n\n"
            for r in rows:
                ban_icon = "🚫" if r[3] else "✅"
                name     = r[1] or "—"
                msg_text += f"{ban_icon} <code>{r[0]}</code>  ·  {name}  ·  💎{r[2]}\n"

            msg_text += f"\n{DIV}\n💡 Use <b>🔍 Find User</b> to manage a specific user."

            mk = InlineKeyboardMarkup()
            mk.row(InlineKeyboardButton("🔍 Find User by ID", callback_data="adm_finduser"))
            mk.row(InlineKeyboardButton("🔙 Admin Panel",     callback_data="back_admin"))
            bot.send_message(chat_id, msg_text, parse_mode="HTML", reply_markup=mk)
            return

        # ── FIND USER ─────────────────────────────────
        if data == "adm_finduser":
            setStep(user_id, "adm_search_user")
            mk = InlineKeyboardMarkup()
            mk.row(InlineKeyboardButton("🔙 Cancel", callback_data="back_admin"))
            bot.send_message(
                chat_id,
                f"🔍 <b>FIND USER</b>\n"
                f"{DIV}\n\n"
                "Enter the <b>User ID</b> to look up:\n"
                "<i>(Telegram numeric user ID)</i>\n\n"
                f"{DIV}",
                parse_mode="HTML",
                reply_markup=mk
            )
            return

        # ── VIEW ALL PAYMENTS ─────────────────────────
        if data == "adm_payments":
            try:
                conn = db()
                cur  = conn.cursor()
                cur.execute(
                    "SELECT * FROM payments ORDER BY payment_id DESC LIMIT 10"
                )
                rows = [dict(r) for r in cur.fetchall()]
                conn.close()
            except Exception as e:
                logger.error(f"adm_payments error: {e}")
                rows = []

            msg = f"💳 <b>PAYMENT HISTORY</b> (last 10)\n{DIV}\n\n"
            if not rows:
                msg += "No payments yet.\n"
            for p in rows:
                icon = "✅" if p['status'] == "Approved" else ("❌" if p['status'] == "Declined" else "⏳")
                dt   = time.strftime("%d %b %H:%M", time.localtime(p['created_time']))
                msg += (
                    f"{icon} <b>#{p['payment_id']}</b>  ·  <code>{p['user_id']}</code>\n"
                    f"   ₹{p['amount_inr']} → {p['credits']} cr  ·  {p['status']}  ·  {dt}\n\n"
                )
            msg += f"{DIV}"
            mk = InlineKeyboardMarkup()
            mk.row(InlineKeyboardButton("🔙 Admin Panel", callback_data="back_admin"))
            bot.send_message(chat_id, msg, parse_mode="HTML", reply_markup=mk)
            return

        # ── PENDING PAYMENTS ──────────────────────────
        if data == "adm_pending_pays":
            try:
                conn = db()
                cur  = conn.cursor()
                cur.execute(
                    "SELECT * FROM payments WHERE status='Pending' ORDER BY payment_id DESC"
                )
                rows = [dict(r) for r in cur.fetchall()]
                conn.close()
            except Exception as e:
                logger.error(f"adm_pending_pays error: {e}")
                rows = []

            if not rows:
                mk = InlineKeyboardMarkup()
                mk.row(InlineKeyboardButton("🔙 Admin Panel", callback_data="back_admin"))
                bot.send_message(
                    chat_id,
                    f"⏳ <b>PENDING PAYMENTS</b>\n{DIV}\n\n"
                    "✅ No pending payments!\n\n"
                    f"{DIV}",
                    parse_mode="HTML", reply_markup=mk
                )
                return

            for p in rows:
                mk = InlineKeyboardMarkup()
                mk.row(
                    InlineKeyboardButton("✅ Approve", callback_data=f"pay_approve_{p['payment_id']}"),
                    InlineKeyboardButton("❌ Decline", callback_data=f"pay_decline_{p['payment_id']}")
                )
                dt = time.strftime("%d %b %H:%M", time.localtime(p['created_time']))
                bot.send_message(
                    chat_id,
                    f"⏳ <b>PENDING PAYMENT #{p['payment_id']}</b>\n"
                    f"{DIV2}\n\n"
                    f"👤 User  : <code>{p['user_id']}</code>\n"
                    f"💸 Amount: ₹{p['amount_inr']}\n"
                    f"💎 Credits: {p['credits']}\n"
                    f"🔖 UTR   : <code>{p['transaction_id']}</code>\n"
                    f"🕒 Time  : {dt}\n",
                    parse_mode="HTML",
                    reply_markup=mk
                )
            return

        # ── ADD CREDITS ───────────────────────────────
        if data.startswith("adm_addfunds_"):
            target_id = int(data.split("_")[2])
            setStep(user_id, f"adm_adding_funds:{target_id}")
            mk = InlineKeyboardMarkup()
            mk.row(InlineKeyboardButton("🔙 Cancel", callback_data=f"adm_viewuser_{target_id}"))
            bot.send_message(
                chat_id,
                f"➕ <b>ADD CREDITS</b>\n"
                f"{DIV}\n\n"
                f"Adding credits to user: <code>{target_id}</code>\n\n"
                "Enter the <b>amount of credits</b> to add:\n"
                "<i>(e.g. 50, 100, 500)</i>\n\n"
                f"{DIV}",
                parse_mode="HTML",
                reply_markup=mk
            )
            return

        # ── REMOVE CREDITS ────────────────────────────
        if data.startswith("adm_removefunds_"):
            target_id = int(data.split("_")[2])
            setStep(user_id, f"adm_removing_funds:{target_id}")
            mk = InlineKeyboardMarkup()
            mk.row(InlineKeyboardButton("🔙 Cancel", callback_data=f"adm_viewuser_{target_id}"))
            bot.send_message(
                chat_id,
                f"➖ <b>REMOVE CREDITS</b>\n"
                f"{DIV}\n\n"
                f"Removing credits from user: <code>{target_id}</code>\n\n"
                "Enter the <b>amount of credits</b> to remove:\n"
                "<i>(e.g. 50, 100, 500)</i>\n\n"
                f"{DIV}",
                parse_mode="HTML",
                reply_markup=mk
            )
            return

        # ── BAN USER ──────────────────────────────────
        if data.startswith("adm_ban_"):
            target_id = int(data.split("_")[2])
            try:
                conn = db()
                conn.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (target_id,))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"adm_ban error: {e}")
            try:
                bot.send_message(
                    target_id,
                    f"🚫 <b>Account Banned</b>\n\n"
                    "Your account has been banned from using this bot.\n"
                    "Contact the owner if you believe this is a mistake.",
                    parse_mode="HTML"
                )
            except Exception:
                pass
            try:
                bot.answer_callback_query(call.id, f"✅ User {target_id} banned.", show_alert=True)
            except Exception:
                pass
            send_admin_user_profile(chat_id, target_id)
            return

        # ── UNBAN USER ────────────────────────────────
        if data.startswith("adm_unban_"):
            target_id = int(data.split("_")[2])
            try:
                conn = db()
                conn.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (target_id,))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"adm_unban error: {e}")
            try:
                bot.send_message(
                    target_id,
                    f"✅ <b>Account Unbanned</b>\n\n"
                    "Your account has been unbanned.\n"
                    "You can now use the bot again! 🎉",
                    parse_mode="HTML"
                )
            except Exception:
                pass
            try:
                bot.answer_callback_query(call.id, f"✅ User {target_id} unbanned.", show_alert=True)
            except Exception:
                pass
            send_admin_user_profile(chat_id, target_id)
            return

        # ── VIEW USER (from inline) ───────────────────
        if data.startswith("adm_viewuser_"):
            target_id = int(data.split("_")[2])
            send_admin_user_profile(chat_id, target_id)
            return

        # ── SEND MESSAGE TO USER ──────────────────────
        if data.startswith("adm_msg_"):
            target_id = int(data.split("_")[2])
            setStep(user_id, f"adm_sending_msg:{target_id}")
            mk = InlineKeyboardMarkup()
            mk.row(InlineKeyboardButton("🔙 Cancel", callback_data=f"adm_viewuser_{target_id}"))
            bot.send_message(
                chat_id,
                f"📨 <b>SEND MESSAGE TO USER</b>\n"
                f"{DIV}\n\n"
                f"Recipient: <code>{target_id}</code>\n\n"
                "Type the message to send:\n\n"
                f"{DIV}",
                parse_mode="HTML",
                reply_markup=mk
            )
            return

        # ── ORDERS LIST ───────────────────────────────
        if data == "adm_orders":
            try:
                conn = db()
                cur  = conn.cursor()
                cur.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 10")
                rows = cur.fetchall()
                conn.close()
            except Exception as e:
                logger.error(f"adm_orders error: {e}")
                return

            msg_text = f"📦 <b>RECENT ORDERS</b> (last 10)\n{DIV}\n\n"
            for o in rows:
                o = dict(o)
                icon = "✅" if o['status'] == "Completed" else "⏳"
                msg_text += (
                    f"┌ 🆔 <b>Order #{o['id']}</b>  ·  👤 <code>{o['user_id']}</code>\n"
                    f"├ 📦 {o['service_name']}  ·  {o['quantity']:,} units\n"
                    f"└ {icon} {o['status']}\n\n"
                )
            msg_text += f"{DIV}"
            mk = InlineKeyboardMarkup()
            mk.row(InlineKeyboardButton("🔙 Admin Panel", callback_data="back_admin"))
            bot.send_message(chat_id, msg_text, parse_mode="HTML", reply_markup=mk)
            return

        # ── CREATE CODE ───────────────────────────────
        if data == "adm_createcode":
            setStep(user_id, "code_name")
            mk = InlineKeyboardMarkup()
            mk.row(InlineKeyboardButton("🔙 Cancel", callback_data="back_admin"))
            bot.send_message(
                chat_id,
                f"🎟 <b>CREATE PROMO CODE</b>\n"
                f"{DIV}\n\n"
                "Step <b>1 of 3</b> — Enter the <b>code name:</b>\n"
                "<i>e.g. BOOST100, SMM2025</i>\n\n"
                f"{DIV}",
                parse_mode="HTML",
                reply_markup=mk
            )
            return

        # ── BROADCAST ─────────────────────────────────
        if data == "adm_broadcast":
            setStep(user_id, "broadcast")
            mk = InlineKeyboardMarkup()
            mk.row(InlineKeyboardButton("🔙 Cancel", callback_data="back_admin"))
            bot.send_message(
                chat_id,
                f"📢 <b>BROADCAST MESSAGE</b>\n"
                f"{DIV}\n\n"
                "✏️ Type the message to send to\n"
                "<b>ALL users</b> and send it:\n\n"
                "⚠️ <i>This will message every registered user.</i>\n\n"
                f"{DIV}",
                parse_mode="HTML",
                reply_markup=mk
            )
            return

    except Exception as e:
        logger.error(f"callback_handler unhandled error: {e}")


# ═══════════════════════════════════════════════════
#               MESSAGE HANDLER
# ═══════════════════════════════════════════════════
@bot.message_handler(func=lambda m: True, content_types=['text'])
def message_handler(message):
    try:
        text    = message.text or ''
        chat_id = message.chat.id
        user_id = message.from_user.id
        msg_id  = message.message_id

        user = getUser(user_id)
        updateUserInfo(user_id, message.from_user.username, message.from_user.first_name)

        # ── BANNED ────────────────────────────────────
        if user.get('is_banned') and user_id != OWNER_ID:
            bot.send_message(
                chat_id,
                "🚫 <b>You are banned from using this bot.</b>",
                parse_mode="HTML"
            )
            return

        # ── NOT VERIFIED: force join ──────────────────
        if not user['is_verified']:
            send_join_screen(chat_id, message.from_user.first_name or "")
            return

        # ── /start ────────────────────────────────────
        if text.startswith("/start"):
            setStep(user_id, "")
            user = getUser(user_id)
            send_main_menu(chat_id, user)
            return

        # ── /admin ────────────────────────────────────
        if text == "/admin" and user_id == OWNER_ID:
            setStep(user_id, "admin_pass")
            bot.send_message(
                chat_id,
                f"🔐 <b>ADMIN LOGIN</b>\n"
                f"{DIV}\n\n"
                "Enter the admin password:",
                parse_mode="HTML"
            )
            return

        # ── /done <id> (Owner only) ───────────────────
        if text.startswith("/done") and user_id == OWNER_ID:
            parts    = text.split()
            order_id = parts[1] if len(parts) > 1 else None
            if not order_id:
                bot.send_message(chat_id, "❌ Usage: <code>/done order_id</code>", parse_mode="HTML")
                return
            try:
                conn = db()
                cur  = conn.cursor()
                cur.execute("SELECT * FROM orders WHERE id=?", (order_id,))
                o = cur.fetchone()
                if o:
                    o = dict(o)
                    conn.execute("UPDATE orders SET status='Completed' WHERE id=?", (order_id,))
                    conn.commit()
                    conn.close()
                    mk = InlineKeyboardMarkup()
                    mk.row(InlineKeyboardButton("🏠 Home", callback_data="back_home"))
                    try:
                        bot.send_message(
                            o['user_id'],
                            f"🎉 <b>ORDER COMPLETED!</b>\n"
                            f"{DIV}\n\n"
                            f"┌ 🆔 <b>Order ID :</b> <code>{order_id}</code>\n"
                            f"├ 📦 <b>Service  :</b> {o['service_name']}\n"
                            f"├ 🔢 <b>Quantity :</b> {o['quantity']:,}\n"
                            f"└ 🔗 <b>Link     :</b>\n<code>{o['link']}</code>\n\n"
                            f"✅ <b>Status: Completed</b>\n\n"
                            f"{DIV}\n"
                            "💎 Thank you for using BoostXGram!",
                            parse_mode="HTML",
                            reply_markup=mk
                        )
                    except Exception:
                        pass
                    bot.send_message(chat_id, f"✅ Order <b>#{order_id}</b> marked as Completed.", parse_mode="HTML")
                else:
                    conn.close()
                    bot.send_message(chat_id, "❌ Order not found.")
            except Exception as e:
                logger.error(f"/done error: {e}")
            return

        # ── /balance (quick check) ────────────────────
        if text == "/balance":
            user = getUser(user_id)
            bot.send_message(
                chat_id,
                f"💎 <b>Your Balance:</b> <b>{user['credits']} credits</b>\n\n"
                f"💳 Top up via <b>Add Funds</b> button.",
                parse_mode="HTML"
            )
            return

        # ══════════════════════════════════════════════
        #              STEP-BASED FLOW
        # ══════════════════════════════════════════════
        step = user['step'] or ''

        # ── ADMIN PASSWORD ────────────────────────────
        if step == "admin_pass":
            if text == ADMIN_PASSWORD:
                setStep(user_id, "admin")
                send_admin_panel(chat_id)
            else:
                bot.send_message(chat_id, "❌ Wrong password. Try again.")
            return

        # ── ADMIN: SEARCH USER ────────────────────────
        if step == "adm_search_user":
            if not text.strip().isdigit():
                bot.send_message(chat_id, "❌ Please send a valid numeric <b>User ID</b>.", parse_mode="HTML")
                return
            target_id = int(text.strip())
            setStep(user_id, "admin")
            send_admin_user_profile(chat_id, target_id)
            return

        # ── ADMIN: ADD CREDITS ────────────────────────
        if step.startswith("adm_adding_funds:"):
            target_id = int(step.split(":")[1])
            if not text.strip().isdigit():
                bot.send_message(chat_id, "❌ Please enter a valid number.")
                return
            amount = int(text.strip())
            try:
                conn = db()
                conn.execute("UPDATE users SET credits=credits+? WHERE user_id=?", (amount, target_id))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"adm_adding_funds error: {e}")
            setStep(user_id, "admin")
            try:
                bot.send_message(
                    target_id,
                    f"💎 <b>Credits Added!</b>\n\n"
                    f"<b>+{amount} credits</b> have been added to your\n"
                    f"account by the admin.\n\n"
                    f"Use /start to check your balance!",
                    parse_mode="HTML"
                )
            except Exception:
                pass
            mk = InlineKeyboardMarkup()
            mk.row(InlineKeyboardButton("👤 View User",  callback_data=f"adm_viewuser_{target_id}"))
            mk.row(InlineKeyboardButton("🔙 Admin Panel", callback_data="back_admin"))
            bot.send_message(
                chat_id,
                f"✅ <b>Credits Added!</b>\n\n"
                f"Added <b>{amount} credits</b> to user <code>{target_id}</code>.",
                parse_mode="HTML",
                reply_markup=mk
            )
            return

        # ── ADMIN: REMOVE CREDITS ─────────────────────
        if step.startswith("adm_removing_funds:"):
            target_id = int(step.split(":")[1])
            if not text.strip().isdigit():
                bot.send_message(chat_id, "❌ Please enter a valid number.")
                return
            amount = int(text.strip())
            try:
                conn = db()
                cur = conn.cursor()
                cur.execute("SELECT credits FROM users WHERE user_id=?", (target_id,))
                row = cur.fetchone()
                current = row[0] if row else 0
                new_credits = max(0, current - amount)
                conn.execute("UPDATE users SET credits=? WHERE user_id=?", (new_credits, target_id))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"adm_removing_funds error: {e}")
                new_credits = 0
            setStep(user_id, "admin")
            mk = InlineKeyboardMarkup()
            mk.row(InlineKeyboardButton("👤 View User",  callback_data=f"adm_viewuser_{target_id}"))
            mk.row(InlineKeyboardButton("🔙 Admin Panel", callback_data="back_admin"))
            bot.send_message(
                chat_id,
                f"✅ <b>Credits Removed!</b>\n\n"
                f"Removed <b>{amount} credits</b> from user <code>{target_id}</code>.\n"
                f"New balance: <b>{new_credits} credits</b>",
                parse_mode="HTML",
                reply_markup=mk
            )
            return

        # ── ADMIN: SEND MESSAGE TO USER ───────────────
        if step.startswith("adm_sending_msg:"):
            target_id = int(step.split(":")[1])
            setStep(user_id, "admin")
            try:
                mk_user = InlineKeyboardMarkup()
                mk_user.row(InlineKeyboardButton("🏠 Home", callback_data="back_home"))
                bot.send_message(
                    target_id,
                    f"📨 <b>Message from Admin</b>\n"
                    f"{DIV}\n\n"
                    f"{text}\n\n"
                    f"{DIV}",
                    parse_mode="HTML",
                    reply_markup=mk_user
                )
                mk = InlineKeyboardMarkup()
                mk.row(InlineKeyboardButton("👤 View User",  callback_data=f"adm_viewuser_{target_id}"))
                mk.row(InlineKeyboardButton("🔙 Admin Panel", callback_data="back_admin"))
                bot.send_message(chat_id, f"✅ Message sent to <code>{target_id}</code>.", parse_mode="HTML", reply_markup=mk)
            except Exception as e:
                bot.send_message(chat_id, f"❌ Could not send message: {e}")
            return

        # ── BROADCAST ─────────────────────────────────
        if step == "broadcast":
            setStep(user_id, "admin")
            try:
                conn = db()
                cur  = conn.cursor()
                cur.execute("SELECT user_id FROM users")
                rows = cur.fetchall()
                conn.close()
            except Exception as e:
                logger.error(f"broadcast db error: {e}")
                rows = []
            sent = 0
            for row in rows:
                try:
                    bot.send_message(row[0], text)
                    sent += 1
                except Exception:
                    pass
                time.sleep(0.05)
            bot.send_message(chat_id, f"✅ Broadcast sent to <b>{sent}</b> users.", parse_mode="HTML")
            return

        # ── CREATE CODE step 1 ────────────────────────
        if step == "code_name":
            setStep(user_id, f"code_value:{text}")
            mk = InlineKeyboardMarkup()
            mk.row(InlineKeyboardButton("🔙 Cancel", callback_data="back_admin"))
            bot.send_message(
                chat_id,
                f"✅ Code: <b>{text}</b>\n\n"
                "Step <b>2 of 3</b> — Enter <b>credit value:</b>\n"
                "<i>(how many credits this code grants)</i>",
                parse_mode="HTML",
                reply_markup=mk
            )
            return

        # ── CREATE CODE step 2 ────────────────────────
        if step.startswith("code_value:"):
            code = step.split(":", 1)[1]
            if not text.isdigit():
                bot.send_message(chat_id, "❌ Enter a valid number.")
                return
            setStep(user_id, f"code_limit:{code}:{text}")
            mk = InlineKeyboardMarkup()
            mk.row(InlineKeyboardButton("🔙 Cancel", callback_data="back_admin"))
            bot.send_message(
                chat_id,
                f"✅ Value: <b>{text} credits</b>\n\n"
                "Step <b>3 of 3</b> — Enter <b>max uses:</b>\n"
                "<i>(how many times this code can be used)</i>",
                parse_mode="HTML",
                reply_markup=mk
            )
            return

        # ── CREATE CODE step 3 ────────────────────────
        if step.startswith("code_limit:"):
            parts = step.split(":")
            code  = parts[1]
            value = parts[2]
            if not text.isdigit():
                bot.send_message(chat_id, "❌ Enter a valid number.")
                return
            try:
                conn = db()
                conn.execute(
                    "INSERT OR REPLACE INTO redeem_codes (code, reward_value, max_uses) VALUES (?,?,?)",
                    (code, int(value), int(text))
                )
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"code_limit insert error: {e}")
            setStep(user_id, "admin")
            mk = InlineKeyboardMarkup()
            mk.row(InlineKeyboardButton("🔙 Admin Panel", callback_data="back_admin"))
            bot.send_message(
                chat_id,
                f"✅ <b>PROMO CODE CREATED!</b>\n"
                f"{DIV}\n\n"
                f"┌ 🎟 <b>Code    :</b> <code>{code}</code>\n"
                f"├ 💰 <b>Value   :</b> {value} credits\n"
                f"└ 🔢 <b>Max Use :</b> {text} times\n\n"
                f"{DIV}",
                parse_mode="HTML",
                reply_markup=mk
            )
            return

        # ── PAYMENT: AMOUNT INPUT ─────────────────────
        if step == "payment_amount":
            if not text.strip().isdigit():
                bot.send_message(
                    chat_id,
                    "❌ <b>Invalid amount!</b>\n\n"
                    "Please enter a number (e.g. <code>50</code>)",
                    parse_mode="HTML"
                )
                return
            amount_inr = int(text.strip())
            if amount_inr < MIN_PAYMENT_INR:
                bot.send_message(
                    chat_id,
                    f"❌ <b>Minimum top-up is ₹{MIN_PAYMENT_INR}</b>\n\n"
                    f"Please enter ₹{MIN_PAYMENT_INR} or more.",
                    parse_mode="HTML"
                )
                return
            credits = amount_inr * INR_TO_CREDITS
            setStep(user_id, "")
            send_payment_confirmation(chat_id, user_id, amount_inr, credits)
            return

        # ── PAYMENT: UTR INPUT ────────────────────────
        if step.startswith("payment_utr:"):
            parts      = step.split(":")
            amount_inr = int(parts[1])
            credits    = int(parts[2])
            utr        = text.strip()

            if len(utr) < 6:
                bot.send_message(
                    chat_id,
                    "❌ <b>Invalid Transaction ID.</b>\n\n"
                    "Please send a valid UTR / Transaction ID.",
                    parse_mode="HTML"
                )
                return

            # Save to DB
            try:
                conn = db()
                cur  = conn.cursor()
                cur.execute(
                    "INSERT INTO payments (user_id, amount_inr, credits, transaction_id, status, created_time) VALUES (?,?,?,?,?,?)",
                    (user_id, amount_inr, credits, utr, 'Pending', int(time.time()))
                )
                conn.commit()
                payment_id = cur.lastrowid
                conn.close()
            except Exception as e:
                logger.error(f"payment_utr insert error: {e}")
                bot.send_message(chat_id, "❌ Failed to submit payment. Please try again.")
                return

            setStep(user_id, "")

            # Confirm to user
            mk = InlineKeyboardMarkup()
            mk.row(
                InlineKeyboardButton("💎 My Wallet",    callback_data="menu_balance"),
                InlineKeyboardButton("🏠 Home",          callback_data="back_home")
            )
            bot.send_message(
                chat_id,
                f"✅ <b>PAYMENT SUBMITTED!</b>\n"
                f"{DIV}\n\n"
                f"┌ 💸 <b>Amount     :</b> ₹{amount_inr}\n"
                f"├ 💎 <b>Credits    :</b> {credits}\n"
                f"├ 🔖 <b>UTR / TxnID:</b> <code>{utr}</code>\n"
                f"└ 🆔 <b>Payment ID :</b> #{payment_id}\n\n"
                f"{DIV2}\n"
                "⏳ Your payment is <b>under review</b>.\n"
                "Admin will verify and add credits shortly!\n\n"
                f"{DIV}",
                parse_mode="HTML",
                reply_markup=mk
            )

            # Forward to admin
            u = getUser(user_id)
            forward_payment_to_admin(
                user_id,
                u.get('username', ''),
                u.get('first_name', ''),
                amount_inr,
                credits,
                utr,
                payment_id
            )
            return

        # ── QUANTITY INPUT ────────────────────────────
        if step.startswith("qty:"):
            service = step.split(":", 1)[1]
            if service not in services:
                return
            if not text.isdigit():
                bot.send_message(chat_id, "❌ Please send a <b>number only</b>.", parse_mode="HTML")
                return
            qty = int(text)
            if qty < 100:
                bot.send_message(chat_id, "❌ Minimum quantity is <b>100 units</b>.", parse_mode="HTML")
                return
            s     = services[service]
            units = math.ceil(qty / s['base'])
            cost  = units * s['cost']
            setStep(user_id, f"confirm_pending:{service}:{qty}:{cost}")
            send_order_summary(chat_id, service, qty, cost)
            return

        # ── LINK INPUT ────────────────────────────────
        if step.startswith("link:"):
            parts   = step.split(":")
            service = parts[1]
            qty     = int(parts[2])
            cost    = int(parts[3])

            if not URL_RE.match(text):
                bot.send_message(
                    chat_id,
                    "❌ <b>Invalid link!</b>\n\n"
                    "Please send a valid URL starting with\n"
                    "<code>https://</code>",
                    parse_mode="HTML"
                )
                return

            try:
                conn = db()
                cur  = conn.cursor()
                cur.execute(
                    "INSERT INTO orders (user_id, service_name, quantity, link, cost, status) VALUES (?,?,?,?,?,?)",
                    (user_id, service, qty, text, cost, 'Pending')
                )
                conn.commit()
                oid = cur.lastrowid
                conn.close()
            except Exception as e:
                logger.error(f"link insert order error: {e}")
                bot.send_message(chat_id, "❌ Failed to place order. Please try again.")
                return

            # Owner notification
            try:
                bot.send_message(
                    OWNER_ID,
                    f"🚨 <b>NEW ORDER RECEIVED!</b>\n"
                    f"{DIV}\n\n"
                    f"┌ 🆔 <b>Order ID :</b> <code>{oid}</code>\n"
                    f"├ 👤 <b>User ID  :</b> <code>{user_id}</code>\n"
                    f"├ 📦 <b>Service  :</b> {service}\n"
                    f"├ 🔢 <b>Quantity :</b> {qty:,}\n"
                    f"├ 💰 <b>Cost     :</b> {cost} credits\n"
                    f"└ 🔗 <b>Link     :</b>\n<code>{text}</code>\n\n"
                    f"{DIV}\n"
                    f"⚡ Complete: <code>/done {oid}</code>",
                    parse_mode="HTML"
                )
            except Exception:
                pass

            mk = InlineKeyboardMarkup()
            mk.row(
                InlineKeyboardButton("📦 My Orders", callback_data="menu_myorders"),
                InlineKeyboardButton("🏠 Home",      callback_data="back_home")
            )
            bot.send_message(
                chat_id,
                f"✅ <b>ORDER PLACED SUCCESSFULLY!</b>\n"
                f"{DIV}\n\n"
                f"┌ 🆔 <b>Order ID :</b> <code>{oid}</code>\n"
                f"├ 📦 <b>Service  :</b> {service}\n"
                f"├ 🔢 <b>Quantity :</b> {qty:,} units\n"
                f"└ 💰 <b>Cost     :</b> {cost} credits\n\n"
                f"{DIV2}\n"
                "⏳ Status: <b>Pending</b>\n"
                "🔔 You'll be notified when it's done!\n\n"
                f"{DIV}",
                parse_mode="HTML",
                reply_markup=mk
            )
            setStep(user_id, "")
            return

        # ── REDEEM CODE ───────────────────────────────
        if step == "redeem":
            code = text.strip().upper()
            try:
                conn = db()
                cur  = conn.cursor()
                cur.execute("SELECT * FROM redeem_codes WHERE UPPER(code)=?", (code,))
                c = cur.fetchone()

                if c:
                    c = dict(c)
                    cur.execute("SELECT 1 FROM redeem_history WHERE user_id=? AND code=?", (user_id, code))
                    already_used = cur.fetchone()

                    if already_used:
                        mk = InlineKeyboardMarkup()
                        mk.row(InlineKeyboardButton("🏠 Home", callback_data="back_home"))
                        bot.send_message(
                            chat_id,
                            f"❌ <b>ALREADY REDEEMED</b>\n"
                            f"{DIV}\n\n"
                            "You have already used this code.\n"
                            "Each code can only be redeemed <b>once per user</b>.\n\n"
                            "🔔 Watch our channels for new codes!\n\n"
                            f"{DIV}",
                            parse_mode="HTML",
                            reply_markup=mk
                        )
                    elif c['current_uses'] >= c['max_uses']:
                        mk = InlineKeyboardMarkup()
                        mk.row(InlineKeyboardButton("🏠 Home", callback_data="back_home"))
                        bot.send_message(
                            chat_id,
                            f"❌ <b>CODE EXPIRED</b>\n"
                            f"{DIV}\n\n"
                            "This code has reached its max uses.\n\n"
                            "🔔 Watch our channels for new codes!",
                            parse_mode="HTML",
                            reply_markup=mk
                        )
                    else:
                        conn.execute(
                            "UPDATE users SET credits=credits+? WHERE user_id=?",
                            (c['reward_value'], user_id)
                        )
                        conn.execute(
                            "UPDATE redeem_codes SET current_uses=current_uses+1 WHERE UPPER(code)=?",
                            (code,)
                        )
                        conn.execute(
                            "INSERT OR IGNORE INTO redeem_history (user_id, code) VALUES (?,?)",
                            (user_id, code)
                        )
                        conn.commit()
                        mk = InlineKeyboardMarkup()
                        mk.row(
                            InlineKeyboardButton("🛒 Order Now", callback_data="menu_order"),
                            InlineKeyboardButton("🏠 Home",      callback_data="back_home")
                        )
                        bot.send_message(
                            chat_id,
                            f"🎉 <b>CODE REDEEMED!</b>\n"
                            f"{DIV}\n\n"
                            f"💎 <b>+{c['reward_value']} credits</b> added to your wallet!\n\n"
                            "Use /start to see your updated balance.\n\n"
                            f"{DIV}",
                            parse_mode="HTML",
                            reply_markup=mk
                        )
                else:
                    mk = InlineKeyboardMarkup()
                    mk.row(InlineKeyboardButton("🏠 Home", callback_data="back_home"))
                    bot.send_message(
                        chat_id,
                        f"❌ <b>INVALID CODE</b>\n"
                        f"{DIV}\n\n"
                        "That code doesn't exist.\n"
                        "Check for typos and try again.\n\n"
                        f"{DIV}",
                        parse_mode="HTML",
                        reply_markup=mk
                    )

                conn.close()
            except Exception as e:
                logger.error(f"redeem error: {e}")
            setStep(user_id, "")
            return

        # ── CONTACT OWNER ─────────────────────────────
        if step == "contact":
            setStep(user_id, "")
            try:
                bot.forward_message(OWNER_ID, chat_id, msg_id)
                bot.send_message(
                    OWNER_ID,
                    f"📬 <b>User Message</b>\n"
                    f"From: <code>{user_id}</code>  (@{message.from_user.username or '—'})",
                    parse_mode="HTML"
                )
            except Exception:
                pass
            mk = InlineKeyboardMarkup()
            mk.row(InlineKeyboardButton("🏠 Home", callback_data="back_home"))
            bot.send_message(
                chat_id,
                f"✅ <b>MESSAGE SENT!</b>\n"
                f"{DIV}\n\n"
                "Your message was forwarded to the owner.\n"
                "Please wait for a reply 📬\n\n"
                f"{DIV}",
                parse_mode="HTML",
                reply_markup=mk
            )
            return

        # ── DEFAULT FALLBACK ──────────────────────────
        setStep(user_id, "")
        send_main_menu(chat_id, user)

    except Exception as e:
        logger.error(f"message_handler unhandled error: {e}")


# ═══════════════════════════════════════════════════
#                      MAIN
# ═══════════════════════════════════════════════════
if __name__ == '__main__':
    try:
        _conn = db()
        _conn.close()
    except Exception as e:
        print(f"  [ERROR] Database init failed: {e}")
        sys.exit(1)

    # ── Start auto-backup thread (every 24 hours) ──
    backup_thread = threading.Thread(target=auto_backup_loop, daemon=True)
    backup_thread.start()
    print("  Auto-Backup: Enabled (every 24h → Owner DM)")

    print("╔══════════════════════════════════════════╗")
    print("║   ⚡  BOOSTXGRAM SMM PANEL — RUNNING  ⚡  ║")
    print("╚══════════════════════════════════════════╝")
    print(f"  Owner ID   : {OWNER_ID}")
    print(f"  Channel    : {CHANNEL_USERNAME}")
    print(f"  Rate       : 1 INR = {INR_TO_CREDITS} Credits")
    print(f"  Min Top-up : ₹{MIN_PAYMENT_INR}")
    print(f"  Database   : bot.db (SQLite WAL)")
    print("  Status     : Polling...\n")

    while True:
        try:
            bot.infinity_polling(
                timeout=60,
                long_polling_timeout=60,
                allowed_updates=["message", "callback_query"],
                skip_pending=True
            )
        except Exception as e:
            logger.error(f"Polling crashed: {e}")
            print(f"  [WARN] Polling error — reconnecting in 5s... ({e})")
            time.sleep(5)
            continue
