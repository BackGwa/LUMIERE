from .config import config

def get_model_path():
    return config.get_model_path()

def get_vae_file():
    return config.get_vae_file()

def get_apply_lora():
    return config.get_apply_lora()

def get_apply_embeddings():
    return config.get_apply_embeddings()

def get_positive_prompt():
    return config.get_positive_prompt()

def get_negative_prompt():
    return config.get_negative_prompt()

def get_guidance_scale():
    return config.get_guidance_scale()

def get_quality_steps():
    return config.get_quality_steps()

def get_aspect_ratios():
    _aspect_ratios = config.get_aspect_ratios()
    return {k: tuple(v) for k, v in _aspect_ratios.items()}

