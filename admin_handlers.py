import asyncio
from typing import Optional, Tuple
from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatType

from config import OWNER_ID
from database import (
    get_player_by_target,
    get_player_rank,
    get_or_create_player,
    set_player_xp,
    reset_player_full_stats,
    set_player_full_stats,
    add_bot_admin,
    remove_bot_admin,
    get_all_admins,
    get_all_broadcast_chats,
    get_db_pool
)
from player_system import get_level_progress, get_level_badge, calculate_player_level
from game_manager import game_manager

# In-memory maintenance flag
MAINTENANCE_MODE = False

# --- PERMISSION HELPERS & DECORATORS ---

async def is_admin_or_owner(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    admins = await get_all_admins()
    return any(a["user_id"] == user_id for a in admins)

def owner_only_dm(func):
    """Sirf Super Owner aur sirf Bot DM me chalegi."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        chat = update.effective_chat
        
        if not user or user.id != OWNER_ID:
            await update.effective_message.reply_text("⛔ *Access Denied:* Sirf Super Owner ye command use kar sakta hai.", parse_mode="Markdown")
            return
            
        if chat.type != ChatType.PRIVATE:
            await update.effective_message.reply_text("⚠️ Ye command sirf *Bot DM* me chalegi.", parse_mode="Markdown")
            return
            
        return await func(update, context, *args, **kwargs)
    return wrapper

def admin_only(dm_only: bool = False):
    """Owner aur Sub-Admins dono use kar sakte hain."""
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user = update.effective_user
            chat = update.effective_chat
            
            if not user or not await is_admin_or_owner(user.id):
                await update.effective_message.reply_text("⛔ *Access Denied:* Admin permission required.", parse_mode="Markdown")
                return
                
            if dm_only and chat.type != ChatType.PRIVATE:
                await update.effective_message.reply_text("⚠️ Ye command sirf *Bot DM* me chalegi.", parse_mode="Markdown")
                return
                
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator

async def resolve_target(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Tuple[Optional[int], Optional[str], Optional[str]]:
    """Reply > Mention/ID > None"""
    msg = update.effective_message
    if msg.reply_to_message and msg.reply_to_message.from_user:
        replied = msg.reply_to_message.from_user
        return replied.id, replied.username, replied.first_name

    if context.args:
        raw_target = context.args[0]
        data = await get_player_by_target(raw_target)
        if data:
            return data["user_id"], data.get("username"), data.get("username") or f"User_{data['user_id']}"
        clean = raw_target.replace("@", "").strip()
        if clean.isdigit():
            return int(clean), None, f"User_{clean}"
        return None, clean, clean

    return None, None, None

# --- SUPER OWNER DM-ONLY COMMANDS ---

@owner_only_dm
async def cmd_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👑 *ABACUS BOT OWNER PANEL*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔒 *Owner Commands (DM Only):*\n"
        "• `/owner` — Ye manual guide\n"
        "• `/addadmin <user>` — Naya admin add karein\n"
        "• `/removeadmin <user>` — Admin access revoke karein\n\n"
        "🛠️ *System Controls (DM Only):*\n"
        "• `/admins` — Active admin list dekhein\n"
        "• `/botstats` — Bot & DB metrics check karein\n"
        "• `/maintenance` — Game maintenance toggle karein\n"
        "• `/broadcast` — (Reply to banner or write text) saare users/groups ko bhejein\n\n"
        "🎮 *Player & Game Controls (DM + Group):*\n"
        "• `/setxp <user> <amount>` — XP direct set karein\n"
        "• `/addxp <user> <amount>` — XP add/deduct karein\n"
        "• `/playerinfo <user>` — Full styled dashboard\n"
        "• `/resetstats <user>` — Full stats wipeout\n"
        "• `/setstats <user> <xp> <solves> <played> <wins>` — Recovery tool\n"
        "• `/activematches` — Current active games list\n"
        "• `/stopmatch` — Current group ka game force stop karein"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

@owner_only_dm
async def cmd_addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_id, target_user, _ = await resolve_target(update, context)
    if not target_id:
        await update.message.reply_text("Usage: `/addadmin <numeric_user_id>` ya user ke message par reply karke likho.", parse_mode="Markdown")
        return

    ok = await add_bot_admin(target_id, target_user, update.effective_user.id)
    if ok:
        await update.message.reply_text(f"✅ User `{target_id}` ko sub-admin privileges de di gayi hain.", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ User pehle se hi admin hai ya add nahi ho saka.")

@owner_only_dm
async def cmd_removeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_id, _, _ = await resolve_target(update, context)
    if not target_id:
        await update.message.reply_text("Usage: `/removeadmin <numeric_user_id>` ya reply karein.", parse_mode="Markdown")
        return

    ok = await remove_bot_admin(target_id)
    if ok:
        await update.message.reply_text(f"✅ Admin privileges `{target_id}` se revoke kar di gayi hain.", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Ye user admin list me nahi mila.")

# --- ADMIN DM-ONLY COMMANDS ---

@admin_only(dm_only=True)
async def cmd_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admins = await get_all_admins()
    text = f"👑 *SUPER OWNER:*\n• `{OWNER_ID}`\n\n🛡️ *SUB-ADMINS ({len(admins)}):*\n"
    if not admins:
        text += "_Koi sub-admin configured nahi hai._"
    else:
        for a in admins:
            uname = f"@{a['username']}" if a.get("username") else "No username"
            text += f"• `{a['user_id']}` ({uname})\n"
    await update.message.reply_text(text, parse_mode="Markdown")

@admin_only(dm_only=True)
async def cmd_botstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        total_players = await conn.fetchval("SELECT COUNT(*) FROM abacus_players")
        total_solves = await conn.fetchval("SELECT COALESCE(SUM(correct_answers), 0) FROM abacus_players")
        total_chats = await conn.fetchval("SELECT COUNT(*) FROM bot_chats")
        total_mp = await conn.fetchval("SELECT COALESCE(SUM(mp_played), 0) FROM abacus_players")

    text = (
        "📊 *ABACUS SYSTEM METRICS*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"• *Database:* `Neon PostgreSQL (Connected)`\n"
        f"• *Registered Players:* `{total_players:,}`\n"
        f"• *Total Solves:* `{total_solves:,}`\n"
        f"• *Multiplayer Matches:* `{total_mp:,}`\n"
        f"• *Known Chats/Groups:* `{total_chats:,}`\n"
        f"• *Maintenance Status:* `{'🚨 ACTIVE' if MAINTENANCE_MODE else '🟢 LIVE'}`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

@admin_only(dm_only=True)
async def cmd_maintenance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global MAINTENANCE_MODE
    MAINTENANCE_MODE = not MAINTENANCE_MODE
    status = "🚨 *MAINTENANCE MODE ACTIVATED*\nAb normal players games start nahi kar sakte." if MAINTENANCE_MODE else "🟢 *MAINTENANCE MODE DEACTIVATED*\nBot normal gameplay ke liye ready hai."
    await update.message.reply_text(status, parse_mode="Markdown")

@admin_only(dm_only=True)
async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chats = await get_all_broadcast_chats()
    
    if not chats:
        await msg.reply_text("❌ Database me koi saved chats/groups nahi mile broadcast ke liye.")
        return

    is_reply = bool(msg.reply_to_message)
    broadcast_text = " ".join(context.args) if context.args else None

    if not is_reply and not broadcast_text:
        await msg.reply_text("Usage:\n1. Kisi banner/post ke reply me `/broadcast` likho\n2. Ya direct `/broadcast <message>` likho.")
        return

    status_msg = await msg.reply_text(f"🚀 Broadcasting message to {len(chats)} chats...")
    sent, failed = 0, 0

    for cid in chats:
        try:
            if is_reply:
                await context.bot.copy_message(
                    chat_id=cid,
                    from_chat_id=msg.chat_id,
                    message_id=msg.reply_to_message.message_id
                )
            else:
                await context.bot.send_message(chat_id=cid, text=broadcast_text, parse_mode="Markdown")
            sent += 1
            await asyncio.sleep(0.05)  # Telegram flood prevention
        except Exception:
            failed += 1

    await status_msg.edit_text(f"📢 *Broadcast Finished!*\n\n✅ Delivered: `{sent}`\n❌ Failed/Blocked: `{failed}`", parse_mode="Markdown")

# --- DM + GROUP COMMANDS ---

@admin_only(dm_only=False)
async def cmd_setxp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    target_id, target_user, _ = await resolve_target(update, context)
    
    # Value dhoondna (args ke hisab se)
    val_str = None
    if msg.reply_to_message and context.args:
        val_str = context.args[0]
    elif len(context.args) >= 2:
        val_str = context.args[1]

    if not val_str or not val_str.lstrip("-").isdigit():
        await msg.reply_text("Usage: `/setxp <user> <amount>` ya user ke message par reply karke `/setxp <amount>`", parse_mode="Markdown")
        return

    amount = int(val_str)
    
    # Agar target_user nahi mila but numeric target_id hai
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        if target_id:
            res = await conn.execute("UPDATE abacus_players SET total_xp = $1 WHERE user_id = $2", amount, target_id)
        else:
            res = await conn.execute("UPDATE abacus_players SET total_xp = $1 WHERE LOWER(username) = LOWER($2)", amount, target_user.replace("@", ""))
            
    if res != "UPDATE 0":
        await msg.reply_text(f"✅ XP successfully `{amount}` set kar diya gaya.")
    else:
        await msg.reply_text("❌ Player database me nahi mila.")

@admin_only(dm_only=False)
async def cmd_addxp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    target_id, target_user, _ = await resolve_target(update, context)

    val_str = None
    if msg.reply_to_message and context.args:
        val_str = context.args[0]
    elif len(context.args) >= 2:
        val_str = context.args[1]

    if not val_str or not val_str.lstrip("-").isdigit():
        await msg.reply_text("Usage: `/addxp <user> <amount>` ya reply karke `/addxp <amount>`", parse_mode="Markdown")
        return

    delta = int(val_str)
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        if target_id:
            res = await conn.execute("UPDATE abacus_players SET total_xp = GREATEST(0, total_xp + $1) WHERE user_id = $2", delta, target_id)
        else:
            res = await conn.execute("UPDATE abacus_players SET total_xp = GREATEST(0, total_xp + $1) WHERE LOWER(username) = LOWER($2)", delta, target_user.replace("@", ""))

    if res != "UPDATE 0":
        await msg.reply_text(f"✅ XP updated by `{delta:+}`.")
    else:
        await msg.reply_text("❌ Player database me nahi mila.")

@admin_only(dm_only=False)
async def cmd_playerinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    target_id, target_user, display_name = await resolve_target(update, context)

    if not target_id and not target_user:
        await msg.reply_text("Usage: `/playerinfo <user>` ya user ke message par reply karein.", parse_mode="Markdown")
        return

    target = str(target_id) if target_id else target_user
    player = await get_player_by_target(target)

    if not player:
        await msg.reply_text("❌ Player database me nahi mila.")
        return

    p_id = player["user_id"]
    p_name = player.get("username") or display_name or "Unknown"
    p_xp = player.get("total_xp", 0)
    p_solves = player.get("correct_answers", 0)
    p_played = player.get("mp_played", 0)
    p_wins = player.get("mp_wins", 0)

    level, badge, _, xp_needed = get_level_progress(p_xp)
    win_rate = f"{(p_wins / p_played * 100):.2f}%" if p_played > 0 else "0.00%"

    text = (
        "👤 *PLAYER INFO*\n\n"
        f"• *Name:* {display_name or p_name}\n"
        f"• *Username:* @{player.get('username') if player.get('username') else 'None'}\n"
        f"• *User ID:* `{p_id}`\n\n"
        "🏆 *PROGRESS*\n"
        f"• *Level:* {level}\n"
        f"• *XP:* {p_xp:,}\n"
        f"• *XP to Next Level:* {xp_needed:,}\n"
        f"• *Rank:* {badge}\n\n"
        "🎮 *STATS*\n"
        f"• *Matches Played:* {p_played}\n"
        f"• *Wins:* {p_wins}\n"
        f"• *Win Rate:* {win_rate}\n"
        f"• *Correct Solves:* {p_solves:,}"
    )
    await msg.reply_text(text, parse_mode="Markdown")

@admin_only(dm_only=False)
async def cmd_resetstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    target_id, target_user, _ = await resolve_target(update, context)

    if not target_id and not target_user:
        await msg.reply_text("Usage: `/resetstats <user>` ya reply karein.", parse_mode="Markdown")
        return

    target = str(target_id) if target_id else target_user
    player = await get_player_by_target(target)
    if not player:
        await msg.reply_text("❌ User database me nahi mila.")
        return

    await reset_player_full_stats(player["user_id"])
    await msg.reply_text(f"🗑️ Player `{player['user_id']}` ka saara stats clean reset (0) kar diya gaya.")

@admin_only(dm_only=False)
async def cmd_setstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Format: /setstats <user> <xp> <solves> <played> <wins>"""
    msg = update.effective_message
    is_reply = bool(msg.reply_to_message)
    args = context.args

    if is_reply and len(args) == 4:
        target_id = msg.reply_to_message.from_user.id
        xp, solves, played, wins = map(int, args)
    elif not is_reply and len(args) == 5:
        target = args[0]
        player = await get_player_by_target(target)
        if not player:
            await msg.reply_text("❌ User nahi mila.")
            return
        target_id = player["user_id"]
        xp, solves, played, wins = map(int, args[1:])
    else:
        await msg.reply_text("Format:\n• `/setstats <user> <xp> <solves> <played> <wins>`\n• Reply me: `/setstats <xp> <solves> <played> <wins>`")
        return

    await set_player_full_stats(target_id, xp, solves, played, wins)
    await msg.reply_text(f"✅ Player `{target_id}` full career restored:\nXP: {xp:,} | Solves: {solves} | Played: {played} | Wins: {wins}")

@admin_only(dm_only=False)
async def cmd_activematches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    active_classic = [cid for cid, s in game_manager.sessions.items() if s.active_round and not s.active_round.is_resolved]
    text = (
        "⚔️ *ACTIVE MATCHES*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"• *Active Classic Games:* `{len(active_classic)}`\n"
    )
    if active_classic:
        for cid in active_classic:
            text += f"  └ Chat ID: `{cid}`\n"
    await update.effective_message.reply_text(text, parse_mode="Markdown")

@admin_only(dm_only=False)
async def cmd_stopmatch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = game_manager.get_session(chat_id)
    
    async with session.lock:
        if not session.active_round or session.active_round.is_resolved:
            await update.effective_message.reply_text("⚠️ Is chat me koi active round nahi chal raha.")
            return
        session.active_round.is_resolved = True
        if session.active_round.task:
            session.active_round.task.cancel()

    await game_manager.end_session(chat_id)
    await update.effective_message.reply_text("🛑 Match ko Admin dwara force-stop kar diya gaya.")