import os
import asyncio
import logging
from aiohttp import web
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from config import BOT_TOKEN
from database import init_db
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
    restore_xp_command,
)
from multiplayer_handlers import (
    cmd_create_room,
    cmd_cancelroom,
    cmd_leaveroom,
    handle_room_callback,
    handle_mp_message_answer,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

async def handle_ping(request):
    return web.Response(text="Abacus Bot is Running!")

async def unified_message_router(update, context):
    if not update.message or not update.message.text:
        return
    # Pehle check karo agar multiplayer chal raha hai
    handled = await handle_mp_message_answer(update, context)
    if not handled:
        # Nahi toh normal classic game ko pass karo
        await handle_message_answer(update, context)

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

    # Core Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(CommandHandler("leaderboard", cmd_leaderboard))
    app.add_handler(CommandHandler("game", cmd_game))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(CommandHandler("setxp", restore_xp_command))

    # Room Direct Commands
    app.add_handler(CommandHandler("room", cmd_create_room))
    app.add_handler(CommandHandler("cancelroom", cmd_cancelroom))
    app.add_handler(CommandHandler("leaveroom", cmd_leaveroom))

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
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")