import asyncio
from typing import Dict, Optional, Callable, Awaitable
from dataclasses import dataclass

@dataclass
class ActiveRound:
    round_id: int
    question_level: int
    question: str
    correct_answer: int
    message_id: int
    task: Optional[asyncio.Task] = None
    is_resolved: bool = False

class GroupSession:
    def __init__(self, chat_id: int):
        self.chat_id: int = chat_id
        self.current_level: int = 1
        self.active_round: Optional[ActiveRound] = None
        self.lock: asyncio.Lock = asyncio.Lock()

class GameManager:
    def __init__(self):
        self.sessions: Dict[int, GroupSession] = {}

    def get_session(self, chat_id: int) -> GroupSession:
        if chat_id not in self.sessions:
            self.sessions[chat_id] = GroupSession(chat_id)
        return self.sessions[chat_id]

    async def end_session(self, chat_id: int) -> None:
        if chat_id in self.sessions:
            session = self.sessions[chat_id]
            async with session.lock:
                current_task = asyncio.current_task()
                if session.active_round and session.active_round.task:
                    if session.active_round.task != current_task:
                        session.active_round.task.cancel()
                session.active_round = None
            del self.sessions[chat_id]

    async def start_timer(
        self, 
        chat_id: int, 
        round_id: int, 
        duration: int, 
        on_timeout: Callable[[int, int], Awaitable[None]]
    ) -> None:
        try:
            await asyncio.sleep(duration)
            await on_timeout(chat_id, round_id)
        except asyncio.CancelledError:
            pass

game_manager = GameManager()