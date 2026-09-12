import time
import asyncio
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable, Awaitable

@dataclass
class RoomPlayer:
    user_id: int
    username: str
    first_name: str
    is_alive: bool = True
    cumulative_time: float = 0.0  # Sum of successful times from COMPLETED rounds
    current_round_time: float = 0.0  # Time taken in the active turn

@dataclass
class RoomTurn:
    player_id: int
    question: str
    correct_answer: int
    message_id: int
    start_time: float
    timer_task: Optional[asyncio.Task] = None
    is_resolved: bool = False

class MultiplayerRoom:
    def __init__(self, chat_id: int, host_id: int, host_name: str):
        self.chat_id: int = chat_id
        self.host_id: int = host_id
        self.is_started: bool = False
        self.current_level: int = 1
        self.is_sudden_death: bool = False
        self.sudden_death_round: int = 0
        
        # Preserves join order
        self.players: Dict[int, RoomPlayer] = {}
        # Initial joined player count for bonus XP calculation
        self.initial_player_count: int = 0
        
        # Players alive at the start of current level
        self.round_start_active_ids: List[int] = []
        self.current_turn_index: int = 0
        
        self.current_turn: Optional[RoomTurn] = None
        self.lock: asyncio.Lock = asyncio.Lock()

    @property
    def alive_players(self) -> List[RoomPlayer]:
        return [p for p in self.players.values() if p.is_alive]

    def add_player(self, user_id: int, username: str, first_name: str) -> bool:
        if self.is_started or user_id in self.players:
            return False
        self.players[user_id] = RoomPlayer(
            user_id=user_id,
            username=username or first_name,
            first_name=first_name
        )
        return True

    def remove_player(self, user_id: int) -> bool:
        if user_id in self.players:
            if self.is_started:
                self.players[user_id].is_alive = False
            else:
                del self.players[user_id]
            return True
        return False

class MultiplayerManager:
    def __init__(self):
        self.rooms: Dict[int, MultiplayerRoom] = {}
        self.user_to_room: Dict[int, int] = {}

    def get_room(self, chat_id: int) -> Optional[MultiplayerRoom]:
        return self.rooms.get(chat_id)

    def create_room(self, chat_id: int, host_id: int, host_name: str) -> Optional[MultiplayerRoom]:
        if chat_id in self.rooms or host_id in self.user_to_room:
            return None
        room = MultiplayerRoom(chat_id, host_id, host_name)
        room.add_player(host_id, "", host_name)
        self.rooms[chat_id] = room
        self.user_to_room[host_id] = chat_id
        return room

    def cleanup_room(self, chat_id: int) -> None:
        if chat_id in self.rooms:
            room = self.rooms[chat_id]
            if room.current_turn and room.current_turn.timer_task:
                if room.current_turn.timer_task != asyncio.current_task():
                    room.current_turn.timer_task.cancel()
            for uid in list(room.players.keys()):
                self.user_to_room.pop(uid, None)
            del self.rooms[chat_id]

    async def start_turn_timer(
        self,
        chat_id: int,
        player_id: int,
        level: int,
        duration: int,
        on_timeout: Callable[[int, int, int], Awaitable[None]]
    ) -> None:
        try:
            await asyncio.sleep(duration)
            await on_timeout(chat_id, player_id, level)
        except asyncio.CancelledError:
            pass

multiplayer_manager = MultiplayerManager()