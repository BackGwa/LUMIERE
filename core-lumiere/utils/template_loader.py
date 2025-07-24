import json
import os
import logging
from typing import Dict, Any
import discord

logger = logging.getLogger(__name__)

class TemplateLoader:
    def __init__(self):
        self._templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, Dict[str, Any]]:
        templates = {}
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        template_dir = os.path.join(project_root, "template")
        
        template_files = ["queue.json", "processing.json", "success.json", "error.json", "sensitive_warning.json"]
        
        for template_file in template_files:
            template_path = os.path.join(template_dir, template_file)
            template_name = template_file.replace(".json", "")
            
            try:
                with open(template_path, 'r', encoding='utf-8') as f:
                    templates[template_name] = json.load(f)
            except FileNotFoundError:
                logger.error(f"Template file not found: {template_path}")
                raise FileNotFoundError(f"Required template file not found: {template_path}")
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in template file {template_path}: {e}")
                raise json.JSONDecodeError(f"Invalid JSON in template file {template_path}: {e}")
        
        return templates
    
    
    def create_embed(self, template_name: str, **kwargs) -> discord.Embed:
        if template_name not in self._templates:
            raise KeyError(f"Template '{template_name}' not found")
        
        template = self._templates[template_name]
        
        title = template.get("title", "").format(**kwargs)
        description = template.get("description", "").format(**kwargs)
        color_str = template.get("color", "0x000000")
        
        try:
            color = int(color_str, 16) if isinstance(color_str, str) else color_str
        except ValueError:
            color = 0x000000
        
        embed = discord.Embed(title=title, description=description, color=color)
        
        if "fields" in template:
            for field in template["fields"]:
                name = field.get("name", "").format(**kwargs)
                value = field.get("value", "").format(**kwargs)
                inline = field.get("inline", False)
                embed.add_field(name=name, value=value, inline=inline)
        
        if "author" in template:
            author_name = template["author"].get("name", "").format(**kwargs)
            author_icon_url = template["author"].get("icon_url", "").format(**kwargs)
            embed.set_author(name=author_name, icon_url=author_icon_url)
        
        if "image" in template:
            image_url = template["image"].get("url", "").format(**kwargs)
            embed.set_image(url=image_url)
        
        if "footer" in template:
            footer_text = template["footer"].get("text", "").format(**kwargs)
            embed.set_footer(text=footer_text)
        
        return embed

template_loader = TemplateLoader()