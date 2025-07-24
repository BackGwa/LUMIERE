import discord
from discord import app_commands
from typing import Optional, List
import aiohttp
import asyncio
import websockets
import json
import io
import logging

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.config import config, ConfigError
from utils.language import lang
from utils.template_loader import template_loader
from utils.prompt_enhancer import prompt_enhancer

logger = logging.getLogger(__name__)

async def get_quality_choices(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    try:
        quality_steps = config.get_quality_steps()
        choices = []
        for key in quality_steps.keys():
            localized_name = lang.get(f"discord.options.quality.{key}", default=key)
            choices.append(app_commands.Choice(name=localized_name, value=key))
        return choices
    except ConfigError:
        return []

async def get_ratio_choices(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    try:
        aspect_ratios = config.get_aspect_ratios()
        choices = []
        for key in aspect_ratios.keys():
            localized_name = lang.get(f"discord.options.ratio.{key}", default=key)
            choices.append(app_commands.Choice(name=localized_name, value=key))
        return choices
    except ConfigError:
        return []

async def create_image_command(
    interaction: discord.Interaction,
    prompt: str,
    ratio: Optional[str] = None,
    quality: Optional[str] = None,
    private: bool = False,
    sensitive: bool = False
):
    try:
        quality_steps = config.get_quality_steps()
        aspect_ratios = config.get_aspect_ratios()
        api_endpoint = config.get_api_endpoint()
        guild_ids = config.get_guild_ids()
        
    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        await interaction.response.send_message(
            lang.get("discord.errors.general"), 
            ephemeral=True
        )
        return
    
    if guild_ids and interaction.guild_id not in guild_ids:
        logger.warning(f"Bot access denied for guild {interaction.guild_id}")
        await interaction.response.send_message(
            lang.get("discord.errors.general"), 
            ephemeral=True
        )
        return
    
    if not quality:
        quality = list(quality_steps.keys())[0]
    if not ratio:
        ratio = list(aspect_ratios.keys())[0]
    
    if quality not in quality_steps:
        logger.warning(f"Invalid quality option: {quality}")
        await interaction.response.send_message(
            lang.get("discord.errors.general"), 
            ephemeral=True
        )
        return
    
    if ratio not in aspect_ratios:
        logger.warning(f"Invalid ratio option: {ratio}")
        await interaction.response.send_message(
            lang.get("discord.errors.general"), 
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=private)
    
    try:
        enhanced_prompt = await prompt_enhancer.enhance_prompt(prompt)
        logger.info(f"Prompt enhanced: '{prompt}' -> '{enhanced_prompt}'")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{api_endpoint}/generator",
                json={
                    "prompt": enhanced_prompt,
                    "quality": quality,
                    "aspect_ratio": ratio
                }
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"API error {response.status}: {error_text}")
                    await interaction.followup.send(lang.get("discord.errors.general"))
                    return
                
                result = await response.json()
                task_id = result["task_id"]
        
        embed = template_loader.create_embed(
            "queue",
            title=lang.get("discord.generation.title_queue", queue_position="1"),
            description="",
            author_name=interaction.user.display_name,
            author_icon_url=interaction.user.display_avatar.url
        )
        
        message = await interaction.followup.send(embed=embed, ephemeral=private)
        
        ws_url = api_endpoint.replace('http://', 'ws://').replace('https://', 'wss://') + f"/ws/{task_id}"
        
        async with websockets.connect(ws_url) as websocket:
            while True:
                try:
                    data = await asyncio.wait_for(websocket.recv(), timeout=120.0)
                    status_update = json.loads(data)
                    
                    if status_update.get("status") == "processing":
                        description = ""
                        quality_value = quality_steps.get(quality, 0)
                        max_quality_value = max(quality_steps.values())
                        if quality_value == max_quality_value:
                            description = lang.get("discord.generation.high_quality_warning")
                        
                        embed = template_loader.create_embed(
                            "processing",
                            title=lang.get("discord.generation.title_processing", progress=status_update.get("progress", "0%")),
                            description=description,
                            author_name=interaction.user.display_name,
                            author_icon_url=interaction.user.display_avatar.url
                        )
                        await message.edit(embed=embed)
                    elif status_update.get("status") == "queued" and "queue_position" in status_update:
                        embed = template_loader.create_embed(
                            "queue",
                            title=lang.get("discord.generation.title_queue", queue_position=str(status_update["queue_position"])),
                            description="",
                            author_name=interaction.user.display_name,
                            author_icon_url=interaction.user.display_avatar.url
                        )
                        await message.edit(embed=embed)
                    
                    if status_update.get("status") == "completed":
                        image_url = api_endpoint + status_update['image_url']
                        
                        async with aiohttp.ClientSession() as session:
                            async with session.get(image_url) as img_response:
                                if img_response.status == 200:
                                    image_data = await img_response.read()
                                    file = discord.File(io.BytesIO(image_data), filename="generated_image.png")
                                    
                                    if sensitive:
                                        view = discord.ui.View()
                                        button = discord.ui.Button(label=lang.get("discord.generation.sensitive_warning_button_label"), style=discord.ButtonStyle.primary, custom_id=f"show_sensitive_image_{task_id}")
                                        
                                        async def button_callback(interaction: discord.Interaction):
                                            ephemeral_file = discord.File(io.BytesIO(image_data), filename="generated_image.png")
                                            success_embed = template_loader.create_embed(
                                                "success",
                                                title=lang.get("discord.generation.title_success"),
                                                description="",
                                                author_name=interaction.user.display_name,
                                                author_icon_url=interaction.user.display_avatar.url,
                                                footer_text=prompt
                                            )
                                            await interaction.response.send_message(embed=success_embed, file=ephemeral_file, ephemeral=True)
                                        
                                        button.callback = button_callback
                                        view.add_item(button)
                                        
                                        embed = template_loader.create_embed(
                                            "sensitive_warning",
                                            title=lang.get("discord.generation.sensitive_warning_title"),
                                            description=lang.get("discord.generation.sensitive_warning_description"),
                                            author_name=interaction.user.display_name,
                                            author_icon_url=interaction.user.display_avatar.url
                                        )
                                        await message.edit(embed=embed, view=view, attachments=[])
                                    else:
                                        final_embed = template_loader.create_embed(
                                            "success",
                                            title=lang.get("discord.generation.title_success"),
                                            description="",
                                            author_name=interaction.user.display_name,
                                            author_icon_url=interaction.user.display_avatar.url,
                                            footer_text=prompt
                                        )
                                        await message.edit(embed=final_embed, attachments=[file])
                                else:
                                    logger.error(f"Failed to download image: {img_response.status}")
                                    await message.edit(embed=template_loader.create_embed(
                                        "error",
                                        title=lang.get("discord.generation.title_failed"),
                                        description=lang.get("discord.generation.description_failed"),
                                        author_name=interaction.user.display_name,
                                        author_icon_url=interaction.user.display_avatar.url
                                    ))
                        break
                    
                    elif status_update.get("status") == "error":
                        error_embed = template_loader.create_embed(
                            "error",
                            title=lang.get("discord.generation.title_failed"),
                            description=lang.get("discord.generation.description_failed"),
                            author_name=interaction.user.display_name,
                            author_icon_url=interaction.user.display_avatar.url
                        )
                        await message.edit(embed=error_embed)
                        break
                        
                except asyncio.TimeoutError:
                    logger.error(f"WebSocket timeout for task {task_id}")
                    await message.edit(embed=template_loader.create_embed(
                        "error",
                        title=lang.get("discord.generation.title_failed"),
                        description=lang.get("discord.generation.description_failed"),
                        author_name=interaction.user.display_name,
                        author_icon_url=interaction.user.display_avatar.url
                    ))
                    break
                except websockets.exceptions.ConnectionClosed:
                    break
    
    except Exception as e:
        logger.error(f"Unexpected error in create command: {e}", exc_info=True)
        await interaction.followup.send(lang.get("discord.errors.general"), ephemeral=True)