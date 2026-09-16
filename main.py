import os
import asyncio
import logging
import html
import traceback
from aiohttp import web
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ChatMemberHandler,
    filters,
    ContextTypes,
)

from config import BOT_TOKEN, OWNER_ID
from database import init_db, register_chat, unregister_chat
from handlers import (
    cmd_start,
    cmd_help,
    cmd_profile,
    cmd_leaderboard,
    cmd_game,
    cmd_cancel,
    on_restart_callback,
    on_mode_select_callback,
    handle_message_answer,
)
from multiplayer_handlers import (
    cmd_create_room,
    cmd_cancelroom,
    cmd_leaveroom,
    handle_room_callback,
    handle_mp_message_answer,
)
from admin_handlers import (
    cmd_owner,
    cmd_addadmin,
    cmd_removeadmin,
    cmd_admins,
    cmd_botstats,
    cmd_maintenance,
    cmd_broadcast,
    cmd_setxp,
    cmd_addxp,
    cmd_playerinfo,
    cmd_resetstats,
    cmd_setstats,
    cmd_activematches,
    cmd_stopmatch,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Render health check ping
async def handle_ping(request):
    return web.Response(text="Abacus Bot is Running!")

# Unified message router for answers & auto chat tracking
async def unified_message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat:
        await register_chat(chat.id, chat.type)

    if not update.message or not update.message.text:
        return
    handled = await handle_mp_message_answer(update, context)
    if not handled:
        await handle_message_answer(update, context)

# --- OWNER NOTIFICATIONS & LISTENERS ---

async def track_chat_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Group add ya remove hone par owner ko DM bhejta hai aur database update karta hai."""
    result = update.my_chat_member
    if not result:
        return

    chat = result.chat
    new_status = result.new_chat_member.status
    old_status = result.old_chat_member.status

    if new_status in ["member", "administrator"] and old_status not in ["member", "administrator"]:
        await register_chat(chat.id, chat.type)
        try:
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=f"➕ *Added to Group!*\n• *Title:* `{chat.title}`\n• *Chat ID:* `{chat.id}`\n• *Type:* `{chat.type}`",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Could not send join alert: {e}")

    elif new_status in ["left", "kicked"]:
        await unregister_chat(chat.id)
        try:
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=f"➖ *Removed from Group!*\n• *Title:* `{chat.title}`\n• *Chat ID:* `{chat.id}`",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Could not send leave alert: {e}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Unhandled bot crashes direct owner ke DM me aayenge."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    err_preview = html.escape(tb_string[-3000:])
    try:
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=f"🚨 <b>SYSTEM CRASH ALERT</b>\n\n<pre>{err_preview}</pre>",
            parse_mode="HTML"
        )
    except Exception:
        pass

async def main() -> None:
    await init_db()
    logger.info("Database initialized successfully.")

    # Render port binding
    port = int(os.environ.get("PORT", 10000))
    server = web.Application()
    server.router.add_get("/", handle_ping)
    server.router.add_get("/healthz", handle_ping)
    runner = web.AppRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Health check web server running on port {port}")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Automatic listeners & Error handlers
    app.add_handler(ChatMemberHandler(track_chat_status, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_error_handler(error_handler)

    # Core User Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(CommandHandler("leaderboard", cmd_leaderboard))
    app.add_handler(CommandHandler("game", cmd_game))
    app.add_handler(CommandHandler("cancel", cmd_cancel))

    # Room Direct Commands
    app.add_handler(CommandHandler("room", cmd_create_room))
    app.add_handler(CommandHandler("cancelroom", cmd_cancelroom))
    app.add_handler(CommandHandler("leaveroom", cmd_leaveroom))

    # Owner & Admin Commands (admin_handlers.py se)
    app.add_handler(CommandHandler("owner", cmd_owner))
    app.add_handler(CommandHandler("addadmin", cmd_addadmin))
    app.add_handler(CommandHandler("removeadmin", cmd_removeadmin))
    app.add_handler(CommandHandler("admins", cmd_admins))
    app.add_handler(CommandHandler("botstats", cmd_botstats))
    app.add_handler(CommandHandler("maintenance", cmd_maintenance))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))

    app.add_handler(CommandHandler("setxp", cmd_setxp))
    app.add_handler(CommandHandler("addxp", cmd_addxp))
    app.add_handler(CommandHandler("playerinfo", cmd_playerinfo))
    app.add_handler(CommandHandler("resetstats", cmd_resetstats))
    app.add_handler(CommandHandler("setstats", cmd_setstats))
    app.add_handler(CommandHandler("activematches", cmd_activematches))
    app.add_handler(CommandHandler("stopmatch", cmd_stopmatch))

    # Button Callbacks
    app.add_handler(CallbackQueryHandler(on_mode_select_callback, pattern="^mode_"))
    app.add_handler(CallbackQueryHandler(on_restart_callback, pattern="^start_game$"))
    app.add_handler(CallbackQueryHandler(handle_room_callback, pattern="^mp_"))

    # Unified Message Listener
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, unified_message_router)
    )

    async with app:
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        logger.info("Abacus Bot polling started successfully!")

        # Bot start hone par owner ko DM alert bhejo
        try:
            await app.bot.send_message(
                chat_id=OWNER_ID,
                text="🟢 *Abacus Bot Online!*\nDatabase connected & system ready.",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Could not send startup alert: {e}")

        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")