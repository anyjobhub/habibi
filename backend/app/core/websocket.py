"""
WebSocket Connection Manager
Handles real-time connections for messaging
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set, Optional
from datetime import datetime
import json
import logging
from bson import ObjectId

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time messaging"""
    
    def __init__(self):
        # user_id -> Set of WebSocket connections (multi-device support)
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        
        # websocket -> user_id mapping
        self.connection_users: Dict[WebSocket, str] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """
        Connect a user's WebSocket
        
        Args:
            websocket: WebSocket connection
            user_id: User ID
        """
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        self.connection_users[websocket] = user_id
        
        logger.info(f"User {user_id} connected. Total connections: {len(self.active_connections[user_id])}")
        
        # Send connection acknowledgment
        await self.send_personal_message(
            {
                "type": "authenticated",
                "data": {
                    "user_id": user_id,
                    "connected_at": datetime.utcnow().isoformat()
                }
            },
            websocket
        )
    
    def disconnect(self, websocket: WebSocket):
        """
        Disconnect a WebSocket
        
        Args:
            websocket: WebSocket connection
        """
        user_id = self.connection_users.get(websocket)
        
        if user_id and user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            
            # Remove user entry if no more connections
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
            
            logger.info(f"User {user_id} disconnected")
        
        if websocket in self.connection_users:
            del self.connection_users[websocket]
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        Send message to a specific WebSocket connection
        
        Args:
            message: Message dict to send
            websocket: Target WebSocket
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    
    async def send_to_user(self, message: dict, user_id: str):
        """
        Send message to all connections of a user (multi-device)
        
        Args:
            message: Message dict to send
            user_id: Target user ID
        """
        if user_id in self.active_connections:
            disconnected = set()
            
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending to user {user_id}: {e}")
                    disconnected.add(connection)
            
            # Clean up disconnected connections
            for connection in disconnected:
                self.disconnect(connection)
    
    async def broadcast_to_conversation(self, message: dict, conversation_id: str, participant_ids: list, exclude_user: Optional[str] = None):
        """
        Broadcast message to all participants in a conversation
        
        Args:
            message: Message dict to send
            conversation_id: Conversation ID
            participant_ids: List of participant user IDs
            exclude_user: Optional user ID to exclude from broadcast
        """
        for user_id in participant_ids:
            if user_id != exclude_user:
                await self.send_to_user(message, user_id)
    
    def is_user_online(self, user_id: str) -> bool:
        """
        Check if user is online
        
        Args:
            user_id: User ID to check
            
        Returns:
            True if user has active connections
        """
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0
    
    def get_online_users(self) -> Set[str]:
        """
        Get set of all online user IDs
        
        Returns:
            Set of online user IDs
        """
        return set(self.active_connections.keys())
    
    def get_user_connection_count(self, user_id: str) -> int:
        """
        Get number of active connections for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Number of active connections
        """
        return len(self.active_connections.get(user_id, set()))


# Global connection manager instance
manager = ConnectionManager()
