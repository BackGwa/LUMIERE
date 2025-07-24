import json
import os
import logging
from typing import Dict, Any
import sys
sys.path.append(os.path.dirname(__file__))

from config import config

logger = logging.getLogger(__name__)

class Language:
    def __init__(self):
        self._texts = self._load_language()
    
    def _load_language(self) -> Dict[str, Any]:
        try:
            lang = config.get_language()
        except Exception:
            lang = "en"
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        lang_path = os.path.join(project_root, "language", f"{lang}.json")
        
        try:
            with open(lang_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Language file not found: {lang_path}")
            return {}
    
    def get(self, key_path: str, default: str = None, **kwargs) -> str:
        keys = key_path.split('.')
        value = self._texts
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default if default is not None else key_path
        
        if isinstance(value, str) and kwargs:
            try:
                return value.format(**kwargs)
            except KeyError:
                return value
        
        return str(value)

lang = Language()