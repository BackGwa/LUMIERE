from pydantic import BaseModel, Field
from ..utils.constants import get_quality_steps, get_aspect_ratios

class GenerationRequest(BaseModel):
    prompt: str = Field(..., description="User's positive prompt for image generation")
    quality: str = Field(..., description="Image generation quality")
    aspect_ratio: str = Field(..., description="Image aspect ratio")
    embedding_model: str = Field(None, description="Optional SDXL embedding model name")
    
    def __init__(self, **data):
        super().__init__(**data)
        quality_options = list(get_quality_steps().keys())
        aspect_options = list(get_aspect_ratios().keys())
        
        if self.quality not in quality_options:
            raise ValueError(f"Quality must be one of: {quality_options}")
        if self.aspect_ratio not in aspect_options:
            raise ValueError(f"Aspect ratio must be one of: {aspect_options}")

class GenerationResponse(BaseModel):
    task_id: str = Field(..., description="Unique task identifier")
    status: str = Field(..., description="Initial task status")
    message: str = Field(..., description="Response message")

class StatusUpdate(BaseModel):
    status: str = Field(..., description="Task status")
    queue_position: int = Field(None, description="Position in queue (if queued)")
    progress: str = Field(None, description="Progress percentage (if processing)")
    image_url: str = Field(None, description="Generated image URL (if completed)")
    error_message: str = Field(None, description="Error details (if error)")