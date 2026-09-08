import aiosqlite
from typing import Optional, Dict, Any, List
from config import DB_PATH

async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                total_xp INTEGER DEFAULT 0,
                correct_answers INTEGER DEFAULT 0
            )
        """)
        await db.commit()

async def get_or_create_player(user_id: int, username: Optional[str]) -> Dict[str, Any]:
    clean_username = username if username else f"User_{user_id}"
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM players WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                if username and row["username"] != username:
                    await db.execute("UPDATE players SET username = ? WHERE user_id = ?", (username, user_id))
                    await db.commit()
                return dict(row)

        await db.execute(
            "INSERT INTO players (user_id, username, total_xp, correct_answers) VALUES (?, ?, 0, 0)",
            (user_id, clean_username)
        )
        await db.commit()
        return {"user_id": user_id, "username": clean_username, "total_xp": 0, "correct_answers": 0}

async def record_correct_answer(user_id: int, username: Optional[str], xp_gained: int) -> Dict[str, Any]:
    player = await get_or_create_player(user_id, username)
    new_xp = player["total_xp"] + xp_gained
    new_correct = player["correct_answers"] + 1

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE players SET total_xp = ?, correct_answers = ?, username = ? WHERE user_id = ?",
            (new_xp, new_correct, username or player["username"], user_id)
        )
        await db.commit()

    player["total_xp"] = new_xp
    player["correct_answers"] = new_correct
    return player

async def get_leaderboard(limit: int = 10) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT user_id, username, total_xp, correct_answers FROM players ORDER BY total_xp DESC LIMIT ?",
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]