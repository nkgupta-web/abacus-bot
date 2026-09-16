import os
import asyncpg
from typing import Optional, Dict, Any, List

DATABASE_URL = os.environ.get("DATABASE_URL")

_pool: Optional[asyncpg.Pool] = None

async def get_db_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable set nahi hai!")
        
        dsn = DATABASE_URL
        if dsn.startswith("postgres://"):
            dsn = dsn.replace("postgres://", "postgresql://", 1)
            
        _pool = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=10)
    return _pool

async def init_db() -> None:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Players table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS abacus_players (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                total_xp INTEGER DEFAULT 0,
                correct_answers INTEGER DEFAULT 0,
                mp_played INTEGER DEFAULT 0,
                mp_wins INTEGER DEFAULT 0
            );
        """)
        # Sub-admins table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS bot_admins (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                added_by BIGINT
            );
        """)
        # Broadcast tracking (Groups and DMs)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS bot_chats (
                chat_id BIGINT PRIMARY KEY,
                chat_type TEXT
            );
        """)

async def get_or_create_player(user_id: int, username: Optional[str]) -> Dict[str, Any]:
    clean_username = username if username else f"User_{user_id}"
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM abacus_players WHERE user_id = $1", user_id)
        if row:
            if username and row["username"] != username:
                await conn.execute("UPDATE abacus_players SET username = $1 WHERE user_id = $2", username, user_id)
            return dict(row)

        await conn.execute(
            """
            INSERT INTO abacus_players (user_id, username, total_xp, correct_answers, mp_played, mp_wins)
            VALUES ($1, $2, 0, 0, 0, 0)
            ON CONFLICT (user_id) DO NOTHING
            """,
            user_id, clean_username
        )
        return {
            "user_id": user_id,
            "username": clean_username,
            "total_xp": 0,
            "correct_answers": 0,
            "mp_played": 0,
            "mp_wins": 0
        }

async def record_correct_answer(user_id: int, username: Optional[str], xp_gained: int) -> Dict[str, Any]:
    player = await get_or_create_player(user_id, username)
    new_xp = player["total_xp"] + xp_gained
    new_correct = player["correct_answers"] + 1

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE abacus_players 
            SET total_xp = $1, correct_answers = $2, username = $3 
            WHERE user_id = $4
            """,
            new_xp, new_correct, username or player["username"], user_id
        )

    player["total_xp"] = new_xp
    player["correct_answers"] = new_correct
    return player

async def record_mp_match_played(user_id: int, username: Optional[str]) -> None:
    player = await get_or_create_player(user_id, username)
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE abacus_players SET mp_played = mp_played + 1, username = $1 WHERE user_id = $2",
            username or player["username"], user_id
        )

async def record_mp_match_win(user_id: int, username: Optional[str]) -> None:
    player = await get_or_create_player(user_id, username)
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE abacus_players SET mp_wins = mp_wins + 1, username = $1 WHERE user_id = $2",
            username or player["username"], user_id
        )

async def get_leaderboard(limit: int = 10) -> List[Dict[str, Any]]:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT user_id, username, total_xp, correct_answers, mp_played, mp_wins FROM abacus_players ORDER BY total_xp DESC LIMIT $1",
            limit
        )
        return [dict(r) for r in rows]

async def set_player_xp(username: str, new_xp: int) -> bool:
    clean_user = username.replace("@", "").strip()
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        res = await conn.execute(
            "UPDATE abacus_players SET total_xp = $1 WHERE LOWER(username) = LOWER($2)",
            new_xp, clean_user
        )
        return res != "UPDATE 0"

async def get_player_by_target(target: str) -> Optional[Dict[str, Any]]:
    pool = await get_db_pool()
    clean_target = target.replace("@", "").strip()
    
    async with pool.acquire() as conn:
        if clean_target.isdigit():
            row = await conn.fetchrow("SELECT * FROM abacus_players WHERE user_id = $1", int(clean_target))
            if row:
                return dict(row)
        
        row = await conn.fetchrow("SELECT * FROM abacus_players WHERE LOWER(username) = LOWER($1)", clean_target)
        return dict(row) if row else None

async def get_player_rank(user_id: int) -> int:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rank = await conn.fetchval("""
            SELECT COUNT(*) + 1 
            FROM abacus_players 
            WHERE total_xp > (SELECT COALESCE(total_xp, 0) FROM abacus_players WHERE user_id = $1)
        """, user_id)
        return rank or 1
    # --- ADMIN & BROADCAST HELPERS ---

async def add_bot_admin(user_id: int, username: Optional[str], added_by: int) -> bool:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        res = await conn.execute(
            """
            INSERT INTO bot_admins (user_id, username, added_by)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id) DO NOTHING
            """,
            user_id, username.replace("@", "") if username else None, added_by
        )
        return "INSERT 0 1" in res

async def remove_bot_admin(user_id: int) -> bool:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        res = await conn.execute("DELETE FROM bot_admins WHERE user_id = $1", user_id)
        return res != "DELETE 0"

async def get_all_admins() -> List[Dict[str, Any]]:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM bot_admins")
        return [dict(r) for r in rows]

async def register_chat(chat_id: int, chat_type: str) -> None:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO bot_chats (chat_id, chat_type)
            VALUES ($1, $2)
            ON CONFLICT (chat_id) DO UPDATE SET chat_type = $2
            """,
            chat_id, chat_type
        )

async def unregister_chat(chat_id: int) -> None:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM bot_chats WHERE chat_id = $1", chat_id)

async def get_all_broadcast_chats() -> List[int]:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT chat_id FROM bot_chats")
        return [r["chat_id"] for r in rows]

async def reset_player_full_stats(user_id: int) -> bool:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        res = await conn.execute(
            """
            UPDATE abacus_players 
            SET total_xp = 0, correct_answers = 0, mp_played = 0, mp_wins = 0 
            WHERE user_id = $1
            """,
            user_id
        )
        return res != "UPDATE 0"

async def set_player_full_stats(user_id: int, xp: int, solves: int, played: int, wins: int) -> bool:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        res = await conn.execute(
            """
            UPDATE abacus_players 
            SET total_xp = $1, correct_answers = $2, mp_played = $3, mp_wins = $4 
            WHERE user_id = $5
            """,
            xp, solves, played, wins, user_id
        )
        return res != "UPDATE 0"