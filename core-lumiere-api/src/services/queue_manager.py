import asyncio
from typing import Dict, Optional
from datetime import datetime

from ..api.schemas import GenerationRequest
from ..models.image_generator import ImageGenerator
from ..utils.logger import get_logger, get_output_dir

logger = get_logger(__name__)

class TaskInfo:
    def __init__(self, task_id: str, request: GenerationRequest):
        self.task_id = task_id
        self.request = request
        self.status = "queued"
        self.progress = "0%"
        self.image_url = None
        self.error_message = None
        self.created_at = datetime.now()

class QueueManager:
    def __init__(self):
        self.task_queue: Optional[asyncio.Queue] = None
        self.tasks: Dict[str, TaskInfo] = {}
        self.current_task: Optional[str] = None
        self.image_generator = ImageGenerator()
        self.worker_task: Optional[asyncio.Task] = None
        self._initialized = False
    
    async def initialize(self):
        if not self._initialized:
            self.task_queue = asyncio.Queue()
            self._initialized = True
            await self._start_worker()
    
    async def _start_worker(self):
        if self.worker_task is None or self.worker_task.done():
            self.worker_task = asyncio.create_task(self._worker())
            logger.info("Queue worker task started")
    
    async def add_task(self, task_id: str, request: GenerationRequest):
        await self.initialize()
        task_info = TaskInfo(task_id, request)
        self.tasks[task_id] = task_info
        await self.task_queue.put(task_id)
        logger.info(f"Task {task_id} added to queue")
    
    async def get_task_status(self, task_id: str) -> Optional[Dict]:
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        queue_position = self._get_queue_position(task_id)
        
        status_data = {
            "status": task.status,
            "progress": task.progress,
            "image_url": task.image_url,
            "error_message": task.error_message
        }
        
        if task.status == "queued" and queue_position is not None:
            status_data["queue_position"] = queue_position
        
        return status_data
    
    def _get_queue_position(self, task_id: str) -> Optional[int]:
        if self.current_task == task_id:
            return 0
        
        if self.task_queue is None:
            return None
        
        queue_list = list(self.task_queue._queue)
        try:
            return queue_list.index(task_id) + (1 if self.current_task else 0)
        except ValueError:
            return None
    
    def get_queue_size(self) -> int:
        if self.task_queue is None:
            return 0
        return self.task_queue.qsize() + (1 if self.current_task else 0)
    
    async def _worker(self):
        try:
            await self.image_generator.load_model()
            logger.info("Image generator loaded, worker started")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return
        
        while True:
            try:
                task_id = await self.task_queue.get()
                self.current_task = task_id
                
                if task_id not in self.tasks:
                    continue
                
                task = self.tasks[task_id]
                task.status = "processing"
                task.progress = "0%"
                
                logger.info(f"Starting generation for task {task_id}")

                from ..utils.constants import get_positive_prompt, get_negative_prompt, get_apply_lora, get_apply_embeddings
                full_positive_prompt = task.request.prompt + get_positive_prompt()
                full_negative_prompt = get_negative_prompt()
                
                logger.info(f"Task {task_id} - Full Positive Prompt: {full_positive_prompt}")
                logger.info(f"Task {task_id} - Full Negative Prompt: {full_negative_prompt}")
                
                config_loras = get_apply_lora()
                config_embeddings = get_apply_embeddings()
                request_embedding = task.request.embedding_model
                
                if config_loras:
                    logger.info(f"Task {task_id} - Config LoRAs: {', '.join(config_loras)}")
                if config_embeddings:
                    logger.info(f"Task {task_id} - Config Embeddings: {', '.join(config_embeddings)}")
                if request_embedding:
                    logger.info(f"Task {task_id} - Additional Request Embedding: {request_embedding}")
                
                embedding_info = f", embedding_model={task.request.embedding_model}" if task.request.embedding_model else ""
                logger.info(f"Task {task_id} - Options: quality={task.request.quality}, aspect_ratio={task.request.aspect_ratio}{embedding_info}")
                
                def progress_callback(step: int, total_steps: int):
                    progress_percent = int((step / total_steps) * 100)
                    task.progress = f"{progress_percent}%"
                
                try:
                    filename = await self.image_generator.generate_image(
                        prompt=task.request.prompt,
                        quality=task.request.quality,
                        aspect_ratio=task.request.aspect_ratio,
                        embedding_model=task.request.embedding_model,
                        progress_callback=progress_callback
                    )
                    
                    task.status = "completed"
                    task.image_url = f"/image/{filename}"
                    task.progress = "100%"
                    
                    logger.info(f"Task {task_id} completed successfully")
                    
                except Exception as e:
                    task.status = "error"
                    task.error_message = str(e)
                    logger.error(f"Task {task_id} failed: {str(e)}")
                
                finally:
                    self.current_task = None
                    self.task_queue.task_done()
                    
            except Exception as e:
                logger.error(f"Worker error: {str(e)}")
                if self.current_task:
                    task = self.tasks.get(self.current_task)
                    if task:
                        task.status = "error"
                        task.error_message = "Internal server error"
                    self.current_task = None