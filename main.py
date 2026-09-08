import logging
from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from config import BOT_TOKEN
from database import init_db
from handlers import (
    cmd_start,
    cmd_help,
    cmd_game,
    cmd_cancel,
    cmd_profile,
    cmd_leaderboard,
    handle_message_answer,
    on_restart_callback
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

async def post_init(application) -> None:
    await init_db()
    
    # Telegram menu button me commands register karna
    commands = [
        BotCommand("game", "Start multiplayer math game"),
        BotCommand("profile", "View your Level, Badge and XP"),
        BotCommand("leaderboard", "Global top players ranking"),
        BotCommand("cancel", "Stop current active game"),
        BotCommand("help", "How to play and rules"),
    ]
    await application.bot.set_my_commands(commands)
    
    logging.info("Abacus game database initialized & commands registered successfully.")

def main() -> None:
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("game", cmd_game))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(CommandHandler("leaderboard", cmd_leaderboard))

    # Callback & Messages
    app.add_handler(CallbackQueryHandler(on_restart_callback, pattern="^start_game$"))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message_answer))

    print("Abacus Multiplayer Bot started.")
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()