import json
import os
from typing import Dict, Any

class ConfigError(Exception):
    pass

class Config:
    def __init__(self, config_path: str = None):
        if config_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            config_path = os.path.join(project_root, "config.json")
        
        self.config_path = config_path
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            raise ConfigError(f"Configuration file not found: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid JSON in config file: {e}")
    
    def get_core_config(self) -> Dict[str, Any]:
        if 'core' not in self._config:
            raise ConfigError("'core' section not found in config.json")
        return self._config['core']
    
    def get_api_config(self) -> Dict[str, Any]:
        if 'core-api' not in self._config:
            raise ConfigError("'core-api' section not found in config.json")
        return self._config['core-api']
    
    def get_discord_config(self) -> Dict[str, Any]:
        core_config = self.get_core_config()
        if 'discord' not in core_config:
            raise ConfigError("'discord' section not found in core config")
        return core_config['discord']
    
    def get_discord_token(self) -> str:
        discord_config = self.get_discord_config()
        if 'token' not in discord_config or not discord_config['token']:
            raise ConfigError("Discord token not found or empty in config.json")
        return discord_config['token']
    
    def get_api_endpoint(self) -> str:
        core_config = self.get_core_config()
        if 'api' not in core_config or 'endpoint' not in core_config['api']:
            raise ConfigError("API endpoint not found in config.json")
        return core_config['api']['endpoint']
    
    def get_quality_steps(self) -> Dict[str, int]:
        api_config = self.get_api_config()
        if 'generation' not in api_config:
            raise ConfigError("'generation' section not found in core-api config")
        generation = api_config['generation']
        if 'quality_steps' not in generation:
            raise ConfigError("'quality_steps' not found in generation config")
        quality_steps = generation['quality_steps']
        if not quality_steps:
            raise ConfigError("quality_steps is empty in config")
        return quality_steps
    
    def get_aspect_ratios(self) -> Dict[str, list]:
        api_config = self.get_api_config()
        if 'generation' not in api_config:
            raise ConfigError("'generation' section not found in core-api config")
        generation = api_config['generation']
        if 'aspect_ratios' not in generation:
            raise ConfigError("'aspect_ratios' not found in generation config")
        aspect_ratios = generation['aspect_ratios']
        if not aspect_ratios:
            raise ConfigError("aspect_ratios is empty in config")
        return aspect_ratios
    
    def get_guild_ids(self) -> list:
        discord_config = self.get_discord_config()
        return discord_config.get('guild_ids', [])
    
    def get_language(self) -> str:
        core_config = self.get_core_config()
        return core_config.get('language', 'ko')
    
    def get_enhancer_api_key(self) -> str:
        core_config = self.get_core_config()
        if 'enhancer' not in core_config:
            raise ConfigError("'enhancer' section not found in core config")
        enhancer_config = core_config['enhancer']
        if 'api_key' not in enhancer_config:
            raise ConfigError("'api_key' not found in enhancer config")
        return enhancer_config['api_key']
    
    def get_enhancer_model(self) -> str:
        core_config = self.get_core_config()
        if 'enhancer' not in core_config:
            raise ConfigError("'enhancer' section not found in core config")
        enhancer_config = core_config['enhancer']
        if 'model' not in enhancer_config:
            raise ConfigError("'model' not found in enhancer config")
        return enhancer_config['model']
    
    def get_enhancer_system_prompt(self) -> str:
        core_config = self.get_core_config()
        if 'enhancer' not in core_config:
            raise ConfigError("'enhancer' section not found in core config")
        enhancer_config = core_config['enhancer']
        if 'system_prompt' not in enhancer_config:
            raise ConfigError("'system_prompt' not found in enhancer config")
        return enhancer_config['system_prompt']
    
    def get_translator_api_key(self) -> str:
        core_config = self.get_core_config()
        if 'translator' not in core_config:
            return ""
        translator_config = core_config['translator']
        return translator_config.get('api_key', "")
    
    def get_translator_model(self) -> str:
        core_config = self.get_core_config()
        if 'translator' not in core_config:
            raise ConfigError("'translator' section not found in core config")
        translator_config = core_config['translator']
        if 'model' not in translator_config:
            raise ConfigError("'model' not found in translator config")
        return translator_config['model']
    
    def get_translator_system_prompt(self) -> str:
        core_config = self.get_core_config()
        if 'translator' not in core_config:
            raise ConfigError("'translator' section not found in core config")
        translator_config = core_config['translator']
        if 'system_prompt' not in translator_config:
            raise ConfigError("'system_prompt' not found in translator config")
        return translator_config['system_prompt']

config = Config()