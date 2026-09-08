import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ChatType

from config import LEVEL_SPECS
from math_engine import generate_question
from database import get_or_create_player, record_correct_answer, get_leaderboard
from player_system import get_level_progress, calculate_player_level, get_level_badge
from game_manager import game_manager, ActiveRound

def get_start_again_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔄 START AGAIN", callback_data="start_game")]])

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type == ChatType.PRIVATE:
        await update.message.reply_text(
            "👋 Welcome to Abacus!\n\n"
            "Add me to any group and run /game to play!"
        )
    else:
        await update.message.reply_text("🧮 Abacus Bot ready! Type /game to start.")

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "📖 *ABACUS RULES*\n"
        "• Fastest correct answer wins XP.\n"
        "• Next round starts immediately.\n"
        "• If timer expires, game ends.\n\n"
        "*Commands:*\n"
        "/game - Start session\n"
        "/cancel - Stop game\n"
        "/profile - View your Level & XP\n"
        "/leaderboard - Global leaderboard"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    username = user.username or user.first_name
    player = await get_or_create_player(user.id, username)
    level, badge, next_level_xp, xp_needed = get_level_progress(player["total_xp"])

    text = (
        f"👤 @{player['username']}\n"
        f"🎖️ {badge} (Lvl {level})\n"
        f"⭐ {player['total_xp']:,} XP  •  ✅ {player['correct_answers']} Solved\n"
        f"📈 Next: {next_level_xp:,} XP (🔥 {xp_needed:,} left)"
    )
    await update.message.reply_text(text)

async def cmd_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rows = await get_leaderboard(10)
    if not rows:
        await update.message.reply_text("🏆 No players on the leaderboard yet!")
        return

    rank_icons = {1: "🥇", 2: "🥈", 3: "🥉"}

    text = "🏆 ABACUS LEADERBOARD\n\n"
    for i, row in enumerate(rows, 1):
        lvl = calculate_player_level(row["total_xp"])
        badge = get_level_badge(lvl)
        icon = rank_icons.get(i, f"#{i}")

        display_name = f"@{row['username']}" if row['username'] else f"User {row['user_id']}"
        xp_formatted = f"{row['total_xp']:,}"

        text += (
            f"{icon} {display_name}\n"
            f"   {badge} • Lv. {lvl}\n"
            f"   {xp_formatted} XP\n\n"
        )

    await update.message.reply_text(text.strip())

async def start_new_round(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = game_manager.get_session(chat_id)
    async with session.lock:
        level = session.current_level
        spec = LEVEL_SPECS.get(level, LEVEL_SPECS[15])
        question_text, answer = generate_question(level)

        msg_text = (
            f"🧮 ABACUS\n"
            f"━━━━━━━━━━━━\n\n"
            f"🎯 Level {level}\n\n"
            f"{question_text}\n\n"
            f"⏱️ {spec.time_limit} seconds"
        )
        msg = await context.bot.send_message(chat_id=chat_id, text=msg_text)

        round_id = msg.message_id
        active = ActiveRound(
            round_id=round_id,
            question_level=level,
            question=question_text,
            correct_answer=int(answer),
            message_id=msg.message_id
        )
        session.active_round = active

        active.task = asyncio.create_task(
            game_manager.start_timer(chat_id, round_id, spec.time_limit, handle_timeout_wrapper(context))
        )

def handle_timeout_wrapper(context: ContextTypes.DEFAULT_TYPE):
    async def _on_timeout(chat_id: int, round_id: int):
        await handle_round_timeout(chat_id, round_id, context)
    return _on_timeout

async def handle_round_timeout(chat_id: int, round_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = game_manager.get_session(chat_id)
    correct_ans = None

    async with session.lock:
        active = session.active_round
        if not active or active.round_id != round_id or active.is_resolved:
            return
        active.is_resolved = True
        correct_ans = active.correct_answer

    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⏰ TIME'S UP!\n\n✅ Correct Answer: {correct_ans}",
            reply_markup=get_start_again_markup()
        )
    except Exception as e:
        print(f"Error sending timeout: {e}")

    await game_manager.end_session(chat_id)

async def cmd_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if chat.type == ChatType.PRIVATE:
        await update.message.reply_text("This command must be run inside a group!")
        return

    session = game_manager.get_session(chat.id)
    async with session.lock:
        if session.active_round and not session.active_round.is_resolved:
            await update.message.reply_text("A game is already in progress!")
            return
        session.current_level = 1

    await start_new_round(chat.id, context)

async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    session = game_manager.get_session(chat_id)

    async with session.lock:
        if not session.active_round or session.active_round.is_resolved:
            await update.message.reply_text("No game active to cancel.")
            return

    await game_manager.end_session(chat_id)
    await update.message.reply_text("🛑 Game cancelled.", reply_markup=get_start_again_markup())

async def on_restart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id

    session = game_manager.get_session(chat_id)
    async with session.lock:
        if session.active_round and not session.active_round.is_resolved:
            return
        session.current_level = 1

    await query.edit_message_reply_markup(reply_markup=None)
    await start_new_round(chat_id, context)

async def handle_message_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message or not message.text:
        return

    chat = update.effective_chat
    user = update.effective_user
    print(f"[{chat.title or 'Private'}] {user.first_name}: {message.text}")

    clean_text = (
        message.text.strip()
        .replace("−", "-")
        .replace("—", "-")
        .replace("–", "-")
    )

    try:
        user_answer = int(clean_text)
    except ValueError:
        return

    session = game_manager.get_session(chat.id)
    if not session.active_round or session.active_round.is_resolved:
        return

    is_session_complete = False

    async with session.lock:
        active = session.active_round
        if not active or active.is_resolved:
            return

        if user_answer != int(active.correct_answer):
            return

        active.is_resolved = True
        if active.task:
            active.task.cancel()

        level_spec = LEVEL_SPECS.get(active.question_level, LEVEL_SPECS[15])
        xp_gain = level_spec.base_xp

        username_val = user.username or user.first_name
        current_data = await get_or_create_player(user.id, username_val)
        old_level = calculate_player_level(current_data["total_xp"])

        updated_player = await record_correct_answer(user.id, username_val, xp_gain)
        new_level = calculate_player_level(updated_player["total_xp"])

        username_display = f"@{user.username}" if user.username else user.first_name

        if session.current_level >= 15:
            is_session_complete = True
            win_text = (
                f"🏆 {username_display}\n\n"
                f"✅ Correct Answer!\n\n"
                f"⭐ +{xp_gain} XP\n"
                f"✅ Total Correct: {updated_player['correct_answers']}\n\n"
                f"👑 ALL 15 LEVELS COMPLETED! VICTORY!"
            )
        else:
            win_text = (
                f"🏆 {username_display}\n\n"
                f"✅ Correct Answer!\n\n"
                f"⭐ +{xp_gain} XP\n"
                f"✅ Total Correct: {updated_player['correct_answers']}\n\n"
                f"➡️ Next round..."
            )

        await message.reply_text(win_text)

        if new_level > old_level:
            await context.bot.send_message(
                chat_id=chat.id,
                text=f"🎉 LEVEL UP!\n{username_display} reached Level {new_level}!"
            )

        if is_session_complete:
            await game_manager.end_session(chat.id)
            await context.bot.send_message(
                chat_id=chat.id,
                text="🎉 Game Finished! You cleared the entire Abacus gauntlet!",
                reply_markup=get_start_again_markup()
            )
            return

        session.current_level += 1

    await start_new_round(chat.id, context)