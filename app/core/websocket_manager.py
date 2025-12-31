"""
WebSocket connection manager for real-time updates
"""
from fastapi import WebSocket
from typing import Dict, List, Set, Optional
import json
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # user_id -> Set of WebSocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # Global broadcast connections
        self.broadcast_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket, user_id: Optional[int] = None):
        """Accept websocket connection"""
        await websocket.accept()

        if user_id:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()
            self.active_connections[user_id].add(websocket)
        else:
            self.broadcast_connections.add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: Optional[int] = None):
        """Remove websocket connection"""
        if user_id and user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        else:
            self.broadcast_connections.discard(websocket)

    async def send_personal_message(self, message: dict, user_id: int):
        """Send message to specific user's all connections"""
        if user_id in self.active_connections:
            message_str = json.dumps({
                **message,
                "timestamp": datetime.utcnow().isoformat()
            })

            disconnected = set()
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_text(message_str)
                except Exception as e:
                    print(f"Error sending to user {user_id}: {e}")
                    disconnected.add(websocket)

            # Clean up disconnected websockets
            for ws in disconnected:
                self.disconnect(ws, user_id)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        message_str = json.dumps({
            **message,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Broadcast to global connections
        disconnected = set()
        for websocket in self.broadcast_connections:
            try:
                await websocket.send_text(message_str)
            except Exception as e:
                print(f"Error broadcasting: {e}")
                disconnected.add(websocket)

        for ws in disconnected:
            self.disconnect(ws)

        # Broadcast to all user connections
        for user_id, connections in list(self.active_connections.items()):
            await self.send_personal_message(message, user_id)

    async def notify_account_update(self, user_id: int, account_data: dict):
        """Notify user of account update"""
        await self.send_personal_message({
            "type": "account_update",
            "data": account_data
        }, user_id)

    async def notify_position_update(self, user_id: int, position_data: dict):
        """Notify user of position update"""
        await self.send_personal_message({
            "type": "position_update",
            "data": position_data
        }, user_id)

    async def notify_order_update(self, user_id: int, order_data: dict):
        """Notify user of order update"""
        await self.send_personal_message({
            "type": "order_update",
            "data": order_data
        }, user_id)

    async def notify_signal_update(self, user_id: int, signal_data: dict):
        """Notify user of signal processing update"""
        await self.send_personal_message({
            "type": "signal_update",
            "data": signal_data
        }, user_id)

    async def notify_error(self, user_id: int, error_message: str):
        """Notify user of error"""
        await self.send_personal_message({
            "type": "error",
            "data": {"message": error_message}
        }, user_id)

    def get_connected_users(self) -> List[int]:
        """Get list of connected user IDs"""
        return list(self.active_connections.keys())

    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        user_connections = sum(len(conns) for conns in self.active_connections.values())
        return user_connections + len(self.broadcast_connections)
    
    async def start_heartbeat(self):
        """Start heartbeat task to keep connections alive"""
        while True:
            try:
                await asyncio.sleep(30)  # Send heartbeat every 30 seconds
                heartbeat_msg = {"type": "heartbeat", "timestamp": datetime.now().isoformat()}
                await self.broadcast(heartbeat_msg)
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(5)


# Global WebSocket manager instance
ws_manager = ConnectionManager()
