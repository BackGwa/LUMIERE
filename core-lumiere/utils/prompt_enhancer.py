import asyncio
import json
import logging
from typing import Optional
from google import genai
from google.genai import types

from .config import config, ConfigError

logger = logging.getLogger(__name__)

class PromptEnhancer:
    def __init__(self):
        self.translator_client: Optional[genai.Client] = None
        self.enhancer_client: Optional[genai.Client] = None
        
    def _get_translator_client(self):
        if self.translator_client is None and genai is not None:
            api_key = config.get_translator_api_key()
            if not api_key:
                logger.warning("Translator API key is empty, skipping translation")
                return None
            self.translator_client = genai.Client(api_key=api_key)
            logger.info("Translator GenAI client configured")
        return self.translator_client
    
    def _get_enhancer_client(self):
        if self.enhancer_client is None and genai is not None:
            api_key = config.get_enhancer_api_key()
            if not api_key:
                raise ConfigError("Enhancer API key is empty")
            self.enhancer_client = genai.Client(api_key=api_key)
            logger.info("Enhancer GenAI client configured")
        return self.enhancer_client
    
    async def _translate_to_english(self, text: str) -> str:
        client = self._get_translator_client()
        if not client:
            logger.debug("Translator client not available, using original text")
            return text
        
        try:
            config_data = types.GenerateContentConfig(
                temperature=0.3,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
                response_mime_type="application/json",
                response_schema=genai.types.Schema(
                    type=genai.types.Type.OBJECT,
                    required=["translation"],
                    properties={"translation": genai.types.Schema(type=genai.types.Type.STRING)},
                ),
                system_instruction=[types.Part.from_text(text=config.get_translator_system_prompt())],
            )
            
            contents = [types.Content(role="user", parts=[types.Part.from_text(text=text)])]
            
            def _translate():
                response = client.models.generate_content(
                    model=config.get_translator_model(),
                    contents=contents,
                    config=config_data,
                )
                return response.text.strip() if response.text else None
            
            response_text = await asyncio.get_event_loop().run_in_executor(None, _translate)
            
            if response_text:
                try:
                    translated = json.loads(response_text).get("translation", "")
                    if translated:
                        logger.info(f"Translated prompt: '{text}' -> '{translated}'")
                        return translated
                except json.JSONDecodeError as e:
                    logger.warning(f"Translation JSON parse error: {e}")
            
            return text
        except Exception as e:
            logger.warning(f"Translation failed: {e}, using original text")
            return text
    
    async def enhance_prompt(self, original_prompt: str) -> str:
        if genai is None or types is None:
            logger.error("google-genai package not installed")
            return original_prompt
            
        try:
            translated_prompt = await self._translate_to_english(original_prompt)
            
            client = self._get_enhancer_client()
            if not client:
                return original_prompt
                
            config_data = types.GenerateContentConfig(
                temperature=1.5,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
                response_mime_type="application/json",
                response_schema=genai.types.Schema(
                    type=genai.types.Type.OBJECT,
                    required=["prompt"],
                    properties={"prompt": genai.types.Schema(type=genai.types.Type.STRING)},
                ),
                system_instruction=[types.Part.from_text(text=config.get_enhancer_system_prompt())],
            )
            
            contents = [types.Content(role="user", parts=[types.Part.from_text(text=translated_prompt)])]
            
            def _generate():
                response = client.models.generate_content(
                    model=config.get_enhancer_model(),
                    contents=contents,
                    config=config_data,
                )
                return response.text.strip() if response.text else None
            
            response_text = await asyncio.get_event_loop().run_in_executor(None, _generate)
            
            if response_text:
                try:
                    enhanced_prompt = json.loads(response_text).get("prompt", "")
                    if enhanced_prompt:
                        logger.info(f"Prompt enhanced: '{original_prompt}' -> '{enhanced_prompt[:50]}...'")
                        return enhanced_prompt
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON parse error: {e}")
            
            return original_prompt
                
        except Exception as e:
            logger.error(f"Error enhancing prompt: {e}")
            return original_prompt

prompt_enhancer = PromptEnhancer()