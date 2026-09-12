import time
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ChatType

from config import LEVEL_SPECS
from math_engine import generate_question
from database import add_xp, get_player
from multiplayer_mgr import multiplayer_manager, RoomTurn, RoomPlayer

def get_room_lobby_markup(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Join Room", callback_data=f"mp_join_{chat_id}")],
        [InlineKeyboardButton("🚪 Leave Room", callback_data=f"mp_leave_{chat_id}")],
        [InlineKeyboardButton("🚀 Start Game (Host)", callback_data=f"mp_start_{chat_id}")],
        [InlineKeyboardButton("🛑 Cancel Room", callback_data=f"mp_cancel_{chat_id}")]
    ])

def get_mp_restart_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 START AGAIN", callback_data="mp_rehost")]
    ])

async def cmd_create_room(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == ChatType.PRIVATE:
        await update.message.reply_text("Room mode group chats ke liye hai! Mujhe kisi group me add karke `/game` try karo.")
        return

    if multiplayer_manager.get_room(chat.id):
        await update.message.reply_text("⚠️ Is group me already ek room chal raha hai! Use cancel karne ke liye host `/cancelroom` use kare.")
        return

    if user.id in multiplayer_manager.user_to_room:
        await update.message.reply_text("⚠️ Aap pehle se kisi active room me joined hain!")
        return

    room = multiplayer_manager.create_room(chat.id, user.id, user.first_name)
    if not room:
        await update.message.reply_text("❌ Room create nahi ho saka.")
        return

    await update.message.reply_text(
        f"👑 *BATTLE ROYALE ROOM LOBBY*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 *Host:* {user.first_name}\n"
        f"🎯 *Mode:* Elimination (Last Player Standing)\n\n"
        f"👥 *Players Joined (1):*\n"
        f"1. {user.first_name}\n\n"
        f"Dusre log *Join Room* daba kar shamil hon!",
        parse_mode="Markdown",
        reply_markup=get_room_lobby_markup(chat.id)
    )

async def handle_room_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data
    user = update.effective_user

    if data == "mp_rehost":
        await query.answer()
        await cmd_create_room(update, context)
        return

    parts = data.split("_")
    action = parts[1]
    room_chat_id = int(parts[2])

    room = multiplayer_manager.get_room(room_chat_id)
    if not room:
        await query.answer("Yeh room exist nahi karta ya band ho chuka hai.", show_alert=True)
        return

    if action == "join":
        if room.is_started:
            await query.answer("Match already start ho chuka hai!", show_alert=True)
            return
        if user.id in multiplayer_manager.user_to_room:
            await query.answer("Aap already is room ya kisi aur room me hain!", show_alert=True)
            return

        room.add_player(user.id, user.username or user.first_name, user.first_name)
        multiplayer_manager.user_to_room[user.id] = room_chat_id
        await query.answer("Lobby join kar li! 🎉")

        player_list = "\n".join([f"{i+1}. {p.first_name}" for i, p in enumerate(room.players.values())])
        await query.edit_message_text(
            f"👑 *BATTLE ROYALE ROOM LOBBY*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👑 *Host:* {room.players[room.host_id].first_name}\n"
            f"🎯 *Mode:* Elimination (Last Player Standing)\n\n"
            f"👥 *Players Joined ({len(room.players)}):*\n"
            f"{player_list}\n\n"
            f"Host ke start karne ka wait karein...",
            parse_mode="Markdown",
            reply_markup=get_room_lobby_markup(room_chat_id)
        )

    elif action == "leave":
        if room.is_started:
            await query.answer("Match chal raha hai! Chhodne ke liye answer mat do ya /leaveroom likho.", show_alert=True)
            return
        if user.id not in room.players:
            await query.answer("Aap is room me nahi hain.", show_alert=True)
            return
        if user.id == room.host_id:
            await query.answer("Host leave nahi kar sakta, Cancel daba kar room band karein.", show_alert=True)
            return

        room.remove_player(user.id)
        multiplayer_manager.user_to_room.pop(user.id, None)
        await query.answer("Room chhod diya.")

        player_list = "\n".join([f"{i+1}. {p.first_name}" for i, p in enumerate(room.players.values())])
        await query.edit_message_text(
            f"👑 *BATTLE ROYALE ROOM LOBBY*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👑 *Host:* {room.players[room.host_id].first_name}\n"
            f"🎯 *Mode:* Elimination (Last Player Standing)\n\n"
            f"👥 *Players Joined ({len(room.players)}):*\n"
            f"{player_list}\n",
            parse_mode="Markdown",
            reply_markup=get_room_lobby_markup(room_chat_id)
        )

    elif action == "start":
        if user.id != room.host_id:
            await query.answer("Sirf Room Host hi game start kar sakta hai!", show_alert=True)
            return
        if len(room.players) < 2:
            await query.answer("Kam se kam 2 players chahiye match shuru karne ke liye!", show_alert=True)
            return

        await query.answer("Game shuru!")
        await query.edit_message_reply_markup(reply_markup=None)
        await start_multiplayer_match(room_chat_id, context)

    elif action == "cancel":
        if user.id != room.host_id:
            await query.answer("Sirf host is room ko cancel kar sakta hai!", show_alert=True)
            return
        multiplayer_manager.cleanup_room(room_chat_id)
        await query.answer("Room cancel ho gaya.")
        await query.edit_message_text("🛑 *Room Cancelled by Host!*", parse_mode="Markdown", reply_markup=get_mp_restart_markup())

async def start_multiplayer_match(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    room = multiplayer_manager.get_room(chat_id)
    if not room:
        return
    room.is_started = True
    room.initial_player_count = len(room.players)
    room.current_level = 1
    room.is_sudden_death = False

    await context.bot.send_message(
        chat_id=chat_id,
        text="🚀 *BATTLE ROYALE STARTED!*\n\n"
             "• Har player ko alag question milega (Same Level).\n"
             "• Sahi answer dene par *Instant XP* milega aur survive karoge.\n"
             "• Wrong answers allowed hain (jab tak time hai try karte raho).\n"
             "• Timer khatam hua toh sidha *ELIMINATED*!\n\n"
             "Starting Round 1...",
        parse_mode="Markdown"
    )
    await init_level_round(chat_id, context)

async def init_level_round(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    room = multiplayer_manager.get_room(chat_id)
    if not room:
        return

    async with room.lock:
        room.round_start_active_ids = [p.user_id for p in room.alive_players]
        room.current_turn_index = 0

    label = f"⚡ Sudden Death ({room.sudden_death_round})" if room.is_sudden_death else f"Level Q{room.current_level}"
    active_names = ", ".join([room.players[uid].first_name for uid in room.round_start_active_ids])

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"━━━━━━━━━━━━━━━━━━━━\n"
             f"🏁 *ROUND START: {label}*\n"
             f"Surviving Players: {active_names}\n"
             f"━━━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown"
    )
    await run_next_player_turn(chat_id, context)

async def run_next_player_turn(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    room = multiplayer_manager.get_room(chat_id)
    if not room:
        return

    async with room.lock:
        if room.current_turn_index >= len(room.round_start_active_ids):
            asyncio.create_task(evaluate_level_completion(chat_id, context))
            return

        current_uid = room.round_start_active_ids[room.current_turn_index]
        player = room.players[current_uid]

        if not player.is_alive:
            room.current_turn_index += 1
            asyncio.create_task(run_next_player_turn(chat_id, context))
            return

        effective_level = min(20, room.current_level)
        spec = LEVEL_SPECS.get(effective_level, LEVEL_SPECS[20])
        q_text, ans = generate_question(effective_level)

        msg_text = (
            f"👤 *TURN: {player.first_name}* (@{player.username})\n"
            f"🎯 Level Q{room.current_level}\n\n"
            f"{q_text}\n\n"
            f"⏱️ `{spec.time_limit} seconds`"
        )
        msg = await context.bot.send_message(chat_id=chat_id, text=msg_text, parse_mode="Markdown")

        turn = RoomTurn(
            player_id=current_uid,
            question=q_text,
            correct_answer=int(ans),
            message_id=msg.message_id,
            start_time=time.time()
        )
        room.current_turn = turn

        turn.timer_task = asyncio.create_task(
            multiplayer_manager.start_turn_timer(
                chat_id, current_uid, room.current_level, spec.time_limit, mp_timeout_wrapper(context)
            )
        )

def mp_timeout_wrapper(context: ContextTypes.DEFAULT_TYPE):
    async def _on_timeout(chat_id: int, player_id: int, level: int):
        await handle_mp_turn_timeout(chat_id, player_id, level, context)
    return _on_timeout

async def handle_mp_turn_timeout(
    chat_id: int, player_id: int, level: int, context: ContextTypes.DEFAULT_TYPE
) -> None:
    room = multiplayer_manager.get_room(chat_id)
    if not room:
        return

    player_name = ""
    correct_ans = 0

    async with room.lock:
        turn = room.current_turn
        if not turn or turn.player_id != player_id or turn.is_resolved:
            return
        turn.is_resolved = True
        correct_ans = turn.correct_answer

        player = room.players.get(player_id)
        if player:
            player.is_alive = False
            player_name = player.first_name

        room.current_turn_index += 1

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"⏰ *TIME'S UP!*\n"
             f"❌ *{player_name}* time pe answer nahi de paya aur *ELIMINATE* ho gaya!\n"
             f"✅ Sahi Answer: `{correct_ans}`",
        parse_mode="Markdown"
    )

    await run_next_player_turn(chat_id, context)

async def handle_mp_message_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    message = update.message
    if not message or not message.text:
        return False

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    room = multiplayer_manager.get_room(chat_id)
    if not room or not room.is_started:
        return False

    clean_text = message.text.strip().replace("−", "-").replace("—", "-").replace("–", "-")
    try:
        val = int(clean_text)
    except ValueError:
        return False

    async with room.lock:
        turn = room.current_turn
        if not turn or turn.is_resolved or turn.player_id != user_id:
            return False

        if val != turn.correct_answer:
            # Wrong answer is allowed, player continues till timeout
            return True

        # Correct answer
        turn.is_resolved = True
        if turn.timer_task:
            turn.timer_task.cancel()

        time_taken = max(0.1, round(time.time() - turn.start_time, 2))
        player = room.players[user_id]
        player.current_round_time = time_taken

        room.current_turn_index += 1

    # Level XP award
    effective_lvl = min(20, room.current_level)
    spec = LEVEL_SPECS.get(effective_lvl, LEVEL_SPECS[20])
    earned_xp = spec.xp_reward
    await add_xp(user_id, earned_xp)

    await message.reply_text(
        f"✅ *CORRECT!* {player.first_name} ne `{time_taken}s` me solve kiya!\n"
        f"🎉 Survived & earned *+{earned_xp} XP*!",
        parse_mode="Markdown"
    )

    await run_next_player_turn(chat_id, context)
    return True

async def evaluate_level_completion(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    room = multiplayer_manager.get_room(chat_id)
    if not room:
        return

    async with room.lock:
        survivors = room.alive_players
        completed_level = room.current_level

        for p in survivors:
            p.cumulative_time += p.current_round_time
            p.current_round_time = 0.0

        # CASE 2: Everyone eliminated in Level 1
        if len(survivors) == 0 and completed_level == 1 and not room.is_sudden_death:
            multiplayer_manager.cleanup_room(chat_id)
            await context.bot.send_message(
                chat_id=chat_id,
                text="💥 *ROUND 1 ME SABHI ELIMINATE HO GAYE!*\n❌ *NO WINNER*\n(Previous rounds ka koi data nahi hai compare karne ke liye)",
                parse_mode="Markdown",
                reply_markup=get_mp_restart_markup()
            )
            return

        # CASE 3: Everyone eliminated in Level N (N > 1)
        if len(survivors) == 0:
            candidates = [room.players[uid] for uid in room.round_start_active_ids]
            min_time = min(p.cumulative_time for p in candidates)
            winners = [p for p in candidates if abs(p.cumulative_time - min_time) < 0.001]

            score_lines = "\n".join([
                f"• {p.first_name}: `{p.cumulative_time:.2f}s`"
                for p in sorted(candidates, key=lambda x: x.cumulative_time)
            ])

            if len(winners) == 1:
                w = winners[0]
                # Winner Bonus XP
                bonus_xp = room.initial_player_count * completed_level * 10
                await add_xp(w.user_id, bonus_xp)

                text = (
                    f"💥 *Q{completed_level} ME SABHI ELIMINATE HO GAYE!*\n\n"
                    f"⏱️ *TIEBREAKER APPLIED (Past Completed Rounds Time):*\n"
                    f"{score_lines}\n\n"
                    f"🏆 *WINNER: {w.first_name}* (@{w.username})\n"
                    f"Sabse fast total time: `{w.cumulative_time:.2f}s`!\n"
                    f"🎁 *Winner Bonus XP:* `+{bonus_xp} XP`"
                )
            else:
                joint_names = " & ".join([f"*{w.first_name}*" for w in winners])
                bonus_xp = (room.initial_player_count * completed_level * 10) // len(winners)
                for w in winners:
                    await add_xp(w.user_id, bonus_xp)

                text = (
                    f"💥 *Q{completed_level} ME SABHI ELIMINATE HO GAYE!*\n\n"
                    f"⏱️ *TIEBREAKER APPLIED:*\n"
                    f"{score_lines}\n\n"
                    f"🤝 *TIE! JOINT WINNERS:*\n"
                    f"🏆 {joint_names} (Equal time: `{min_time:.2f}s`)!\n"
                    f"🎁 *Split Bonus XP:* `+{bonus_xp} XP each`"
                )

            multiplayer_manager.cleanup_room(chat_id)
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown", reply_markup=get_mp_restart_markup())
            return

        # CASE 1 & 4: Exactly one player remains alive
        if len(survivors) == 1:
            winner = survivors[0]
            bonus_xp = room.initial_player_count * completed_level * 15
            await add_xp(winner.user_id, bonus_xp)

            text = (
                f"🏆 *VICTORY! LAST PLAYER STANDING!*\n\n"
                f"👑 *WINNER:* {winner.first_name} (@{winner.username})\n"
                f"🎯 Level Cleared: Q{completed_level}\n"
                f"⏱️ Total Speed Time: `{winner.cumulative_time:.2f}s`\n"
                f"🎁 *Winner Champion Bonus:* `+{bonus_xp} XP`\n\n"
                f"Sabhi opponents eliminate ho gaye!"
            )
            multiplayer_manager.cleanup_room(chat_id)
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown", reply_markup=get_mp_restart_markup())
            return

        # Progress to Next Level
        if room.current_level >= 20:
            room.is_sudden_death = True
            room.sudden_death_round += 1
        else:
            room.current_level += 1

    await init_level_round(chat_id, context)

async def cmd_cancelroom(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    room = multiplayer_manager.get_room(chat.id)
    if not room:
        await update.message.reply_text("Is group me koi active room nahi hai.")
        return
    if user.id != room.host_id:
        await update.message.reply_text("Sirf room host hi match cancel kar sakta hai.")
        return

    multiplayer_manager.cleanup_room(chat.id)
    await update.message.reply_text("🛑 Multiplayer room cancel kar diya gaya hai.", reply_markup=get_mp_restart_markup())

async def cmd_leaveroom(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat
    room = multiplayer_manager.get_room(chat.id)
    if not room or user.id not in room.players:
        await update.message.reply_text("Aap is group ke kisi room me nahi hain.")
        return

    if not room.is_started:
        if user.id == room.host_id:
            await update.message.reply_text("Host room leave nahi kar sakta. Cancel karne ke liye `/cancelroom` use karein.")
            return
        room.remove_player(user.id)
        multiplayer_manager.user_to_room.pop(user.id, None)
        await update.message.reply_text(f"👋 {user.first_name} lobby chhod kar chala gaya.")
    else:
        async with room.lock:
            p = room.players[user.id]
            p.is_alive = False
            if room.current_turn and room.current_turn.player_id == user.id:
                if room.current_turn.timer_task:
                    room.current_turn.timer_task.cancel()
                room.current_turn.is_resolved = True
                room.current_turn_index += 1
                asyncio.create_task(run_next_player_turn(chat.id, context))

        await update.message.reply_text(f"🛑 {user.first_name} ne surrender kiya aur eliminate ho gaya!")