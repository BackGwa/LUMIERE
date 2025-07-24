import json
import os
from typing import Dict, Any

class ConfigError(Exception):
    pass

class Config:
    def __init__(self, config_path: str = None):
        if config_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
            config_path = os.path.join(project_root, "config.json")
        self.config_path = config_path
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            raise ConfigError(f"Configuration file not found: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                full_config = json.load(f)
                if 'core-api' not in full_config:
                    raise ConfigError("'core-api' section not found in config.json")
                return full_config['core-api']
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid JSON in config file: {e}")
    
    def reload(self):
        self._config = self._load_config()
    
    def get(self, key_path: str):
        keys = key_path.split('.')
        value = self._config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                raise ConfigError(f"Configuration key '{key_path}' not found in core-api config")
        
        return value
    
    def get_server_host(self):
        return self.get('server.host')
    
    def get_server_port(self):
        return self.get('server.port')
    
    def get_model_path(self):
        return self.get('model.model_path')
    
    def get_vae_file(self):
        return self.get('model.vae_file')
    
    def get_apply_lora(self):
        return self.get('model.apply_lora')
    
    def get_apply_embeddings(self):
        return self.get('model.apply_embeddings')
    
    def get_positive_prompt(self):
        return self.get('generation.positive_prompt')
    
    def get_negative_prompt(self):
        return self.get('generation.negative_prompt')
    
    def get_guidance_scale(self):
        return self.get('generation.guidance_scale')
    
    def get_quality_steps(self):
        quality_steps = self.get('generation.quality_steps')
        if not quality_steps:
            raise ConfigError("quality_steps is empty in config")
        return quality_steps
    
    def get_aspect_ratios(self):
        aspect_ratios = self.get('generation.aspect_ratios')
        if not aspect_ratios:
            raise ConfigError("aspect_ratios is empty in config")
        return aspect_ratios
    

config = Config()