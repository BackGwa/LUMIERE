import torch
from diffusers import StableDiffusionXLPipeline, AutoencoderKL, EulerAncestralDiscreteScheduler
from compel import Compel, ReturnedEmbeddingsType
import asyncio
import os
from datetime import datetime
from typing import Optional, Callable

from ..utils.constants import (
    get_model_path, get_vae_file, get_positive_prompt, get_negative_prompt, 
    get_apply_lora, get_apply_embeddings, get_quality_steps, get_aspect_ratios, get_guidance_scale
)
from ..utils.logger import get_output_dir

class ImageGenerator:
    def __init__(self):
        self.pipeline: Optional[StableDiffusionXLPipeline] = None
        self.compel: Optional[Compel] = None
        self.device = self._get_device()
        self.is_loaded = False
    
    def _get_device(self):
        if torch.cuda.is_available():
            return "cuda"
        else:
            return "cpu"
    
    async def load_model(self):
        if self.is_loaded:
            return
        
        api_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        model_path = os.path.join(api_dir, "models", "checkpoint", get_model_path())
        vae_path = os.path.join(api_dir, "models", "vae", get_vae_file())
        
        vae = AutoencoderKL.from_pretrained(
            vae_path,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            local_files_only=True
        )
        
        self.pipeline = StableDiffusionXLPipeline.from_pretrained(
            model_path,
            vae=vae,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            use_safetensors=True,
            local_files_only=True
        )
        
        self.pipeline.scheduler = EulerAncestralDiscreteScheduler.from_config(self.pipeline.scheduler.config)
        
        if self.device == "cuda":
            self.pipeline = self.pipeline.to("cuda")
            self.pipeline.enable_model_cpu_offload()

            try:
                self.pipeline.enable_xformers_memory_efficient_attention()
                print("xformers memory efficient attention enabled")
            except Exception as e:
                print(f"Warning: Failed to enable xformers: {e}")

        self.compel = Compel(
            tokenizer=[self.pipeline.tokenizer, self.pipeline.tokenizer_2],
            text_encoder=[self.pipeline.text_encoder, self.pipeline.text_encoder_2],
            returned_embeddings_type=ReturnedEmbeddingsType.PENULTIMATE_HIDDEN_STATES_NON_NORMALIZED,
            requires_pooled=[False, True],
            device=self.device,
        )
        print("Compel initialized for enhanced prompt processing")

        for lora_file in get_apply_lora():
            lora_path = os.path.join(api_dir, "models", "lora", lora_file)
            if os.path.exists(lora_path):
                try:
                    self.pipeline.load_lora_weights(lora_path)
                    print(f"Successfully loaded LoRA: {lora_file}")
                except Exception as e:
                    print(f"Warning: Failed to load LoRA {lora_file}: {e}")
            else:
                print(f"Warning: LoRA file not found: {lora_path}")
        
        for embedding_file in get_apply_embeddings():
            await self._apply_embedding_model(embedding_file)
        
        self.is_loaded = True
    
    async def _apply_embedding_model(self, embedding_model: str):
        """Apply embedding model to the pipeline"""
        api_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        embedding_path = os.path.join(api_dir, "models", "embedding", f"{embedding_model}.pt")
        
        if os.path.exists(embedding_path):
            try:
                self.pipeline.load_textual_inversion(embedding_path, token=embedding_model)
                print(f"Successfully loaded embedding: {embedding_model}")
            except Exception as e:
                print(f"Warning: Failed to load embedding model {embedding_model}: {e}")
        else:
            print(f"Warning: Embedding model file not found: {embedding_path}")
    
    def _process_prompt_with_compel(self, prompt: str) -> tuple:
        """Process prompt using Compel for weight adjustment and long prompt handling"""
        try:
            conditioning, pooled = self.compel(prompt)
            return conditioning, pooled
        except Exception as e:
            print(f"Warning: Compel processing failed, using fallback: {e}")
            return None, None
    
    def _process_negative_prompt_with_compel(self, negative_prompt: str) -> tuple:
        """Process negative prompt using Compel"""
        try:
            negative_conditioning, negative_pooled = self.compel(negative_prompt)
            return negative_conditioning, negative_pooled
        except Exception as e:
            print(f"Warning: Compel negative prompt processing failed, using fallback: {e}")
            return None, None
    
    async def generate_image(
        self, 
        prompt: str, 
        quality: str, 
        aspect_ratio: str,
        embedding_model: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        use_compel: bool = True
    ) -> str:
        if not self.is_loaded:
            await self.load_model()
        
        if embedding_model:
            await self._apply_embedding_model(embedding_model)
        
        full_prompt = prompt + get_positive_prompt()
        negative_prompt = get_negative_prompt()
        
        steps = get_quality_steps()[quality]
        width, height = get_aspect_ratios()[aspect_ratio]
        
        def callback_wrapper(pipe, step: int, timestep: int, callback_kwargs):
            if progress_callback:
                progress_callback(step, steps)
            return callback_kwargs
        
        def run_pipeline():
            pipeline_kwargs = {
                "num_inference_steps": steps,
                "width": width,
                "height": height,
                "guidance_scale": get_guidance_scale(),
                "callback_on_step_end": callback_wrapper,
                "callback_on_step_end_tensor_inputs": ["latents"]
            }
            
            if use_compel and self.compel is not None:
                conditioning, pooled = self._process_prompt_with_compel(full_prompt)
                negative_conditioning, negative_pooled = self._process_negative_prompt_with_compel(negative_prompt)
                
                if conditioning is not None and negative_conditioning is not None:
                    pipeline_kwargs.update({
                        "prompt_embeds": conditioning,
                        "pooled_prompt_embeds": pooled,
                        "negative_prompt_embeds": negative_conditioning,
                        "negative_pooled_prompt_embeds": negative_pooled
                    })
                    print("Using Compel-processed embeddings for enhanced prompt weighting")
                else:
                    pipeline_kwargs.update({
                        "prompt": full_prompt,
                        "negative_prompt": negative_prompt
                    })
                    print("Fallback to standard prompt processing")
            else:
                pipeline_kwargs.update({
                    "prompt": full_prompt,
                    "negative_prompt": negative_prompt
                })
                print("Using standard prompt processing")
            
            return self.pipeline(**pipeline_kwargs).images[0]
        
        image = await asyncio.get_event_loop().run_in_executor(None, run_pipeline)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = f"{timestamp}.png"
        output_path = os.path.join(get_output_dir(), filename)
        
        image.save(output_path)
        
        return filename

    def unload_model(self):
        """Unload model and free memory"""
        if self.pipeline:
            del self.pipeline
            self.pipeline = None
        
        if self.compel:
            del self.compel
            self.compel = None
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        self.is_loaded = False
        print("Model and Compel unloaded, memory cleared")