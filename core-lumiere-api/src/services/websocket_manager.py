from fastapi import WebSocket
import json
from typing import Dict, List

from ..utils.logger import get_logger

logger = get_logger(__name__)

class WebSocketManager:
    def __init__(self):
        self.connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, task_id: str):
        await websocket.accept()
        if task_id not in self.connections:
            self.connections[task_id] = []
        self.connections[task_id].append(websocket)
        logger.info(f"WebSocket connected for task {task_id}")
    
    def disconnect(self, task_id: str, websocket: WebSocket = None):
        if task_id in self.connections:
            if websocket:
                try:
                    self.connections[task_id].remove(websocket)
                except ValueError:
                    pass
            if not self.connections[task_id]:
                del self.connections[task_id]
        logger.info(f"WebSocket disconnected for task {task_id}")
    
    async def send_status_update(self, task_id: str, status_data: Dict):
        if task_id not in self.connections:
            return
        
        message = json.dumps(status_data)
        disconnected = []
        
        for websocket in self.connections[task_id]:
            try:
                if websocket.client_state.name == "CONNECTED":
                    await websocket.send_text(message)
                else:
                    disconnected.append(websocket)
            except Exception as e:
                logger.warning(f"Failed to send message to WebSocket: {str(e)}")
                disconnected.append(websocket)
        
        for websocket in disconnected:
            self.disconnect(task_id, websocket)
    
    async def broadcast_to_task(self, task_id: str, message: str):
        if task_id in self.connections:
            await self.send_status_update(task_id, {"message": message})