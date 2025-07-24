from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
import uuid
import asyncio

from ..api.schemas import GenerationRequest, GenerationResponse
from ..services.queue_manager import QueueManager
from ..services.websocket_manager import WebSocketManager
from ..utils.logger import get_output_dir

router = APIRouter()
queue_manager = QueueManager()
websocket_manager = WebSocketManager()

@router.post("/generator", response_model=GenerationResponse)
async def generate_image(request: GenerationRequest):
    task_id = str(uuid.uuid4())
    
    try:
        await queue_manager.add_task(task_id, request)
        
        return GenerationResponse(
            task_id=task_id,
            status="queued",
            message="Task added to queue successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add task to queue: {str(e)}")

@router.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    await websocket_manager.connect(websocket, task_id)
    try:
        last_status = None
        consecutive_errors = 0
        
        while True:
            try:
                await asyncio.sleep(0.5)
                status = await queue_manager.get_task_status(task_id)
                
                if status:
                    should_send = (status != last_status or 
                                 (status.get("status") == "processing" and 
                                  status.get("progress") != (last_status.get("progress") if last_status else None)))
                    
                    if should_send:
                        await websocket_manager.send_status_update(task_id, status)
                        last_status = status
                        consecutive_errors = 0
                    
                    if status["status"] in ["completed", "error"]:
                        await asyncio.sleep(0.5)
                        try:
                            await websocket.close(code=1000, reason="Task completed")
                        except:
                            pass
                        break
                else:
                    consecutive_errors += 1
                    if consecutive_errors > 5:
                        await websocket_manager.send_status_update(task_id, {
                            "status": "error",
                            "error_message": "Task not found"
                        })
                        break
                        
            except asyncio.CancelledError:
                break
            except Exception:
                consecutive_errors += 1
                if consecutive_errors > 10:
                    break
                    
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        websocket_manager.disconnect(task_id, websocket)

@router.get("/image/{filename}")
async def get_image(filename: str):
    import os
    file_path = os.path.join(get_output_dir(), filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")
    
    return FileResponse(file_path, media_type="image/png")