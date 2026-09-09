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
    handle_message_answer,
    restore_xp_command,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def handle_ping(request):
    return web.Response(text="Abacus Bot is Running!")


async def main() -> None:
    # 1. Database initialize
    await init_db()
    logger.info("Database initialized successfully.")

    # 2. Render port binding (Health Check Server)
    port = int(os.environ.get("PORT", 10000))
    server = web.Application()
    server.router.add_get("/", handle_ping)
    server.router.add_get("/healthz", handle_ping)
    runner = web.AppRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Health check web server running on port {port}")

    # 3. Telegram Application setup
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Core Command Handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(CommandHandler("leaderboard", cmd_leaderboard))
    app.add_handler(CommandHandler("game", cmd_game))
    app.add_handler(CommandHandler("cancel", cmd_cancel))

    # Admin Restore Command
    app.add_handler(CommandHandler("setxp", restore_xp_command))

    # Callback & Answers
    app.add_handler(CallbackQueryHandler(on_restart_callback, pattern="^start_game$"))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_answer)
    )

    # 4. Start polling asynchronously
    async with app:
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        logger.info("Abacus Bot polling started successfully!")
        
        # Keep running
        while True:
            await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")