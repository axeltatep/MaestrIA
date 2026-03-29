"""
Higgsfield API wrapper.
All direct calls to higgsfield_client live here.

Native Higgsfield models (confirmed endpoints):
  - Soul    → /v1/text2image/soul        (text-to-image)
  - DoP     → /v1/image2video/dop        (image-to-video, Higgsfield's flagship)
  - Seedream→ bytedance/seedream/v4/text-to-image

DoP quality variants (passed as 'model' argument):
  dop-preview  = máxima calidad (plan Unlimited)
  dop-turbo    = 2x más rápido
  dop-lite     = más barato
"""

import os
import requests
from pathlib import Path
from typing import Optional
import higgsfield_client


# ---------------------------------------------------------------------------
# Model registry — endpoints confirmados
# ---------------------------------------------------------------------------
ENDPOINTS = {
    # --- Imágenes ---
    "soul":        "/v1/text2image/soul",
    "seedream":    "bytedance/seedream/v4/text-to-image",
    "flux":        "flux-pro/kontext/max/text-to-image",

    # --- Video image-to-video (DoP = Director of Photography) ---
    "dop":         "/v1/image2video/dop",   # quality se pasa como argumento
}

# Variantes de calidad DoP
DOP_QUALITY = {
    "preview": "dop-preview",   # máxima calidad — plan Unlimited
    "turbo":   "dop-turbo",     # velocidad 2×
    "lite":    "dop-lite",      # más económico
}

# Defaults
DEFAULT_IMAGE_ENDPOINT  = "soul"         # modelo nativo Higgsfield
DEFAULT_VIDEO_QUALITY   = "dop-preview"  # plan Unlimited → siempre preview


def upload_image(path: str) -> str:
    """Sube una imagen local al CDN de Higgsfield y devuelve la URL pública."""
    return higgsfield_client.upload_file(path)


def generate_image(
    prompt: str,
    quality: str = "1080p",
    aspect_ratio: str = "16:9",
    model_key: str = DEFAULT_IMAGE_ENDPOINT,
    extra: Optional[dict] = None,
) -> dict:
    """
    Text-to-image con Soul (nativo Higgsfield) o Seedream/Flux.
    Returns: {"url": str, "endpoint": str, "prompt": str}
    """
    endpoint = ENDPOINTS.get(model_key, model_key)
    arguments = {
        "prompt": prompt,
        "quality": quality,
        "aspect_ratio": aspect_ratio,
        **(extra or {}),
    }
    result = higgsfield_client.subscribe(endpoint, arguments=arguments)

    # Soul devuelve 'images', Seedream también
    images = result.get("images") or result.get("output") or []
    if not images:
        raise ValueError(f"No images in response: {result}")

    image_url = images[0]["url"] if isinstance(images[0], dict) else images[0]
    return {"url": image_url, "endpoint": endpoint, "prompt": prompt}


def generate_video_from_image(
    image_url: str,
    prompt: str,
    quality: str = DEFAULT_VIDEO_QUALITY,
    motion_id: Optional[str] = None,
) -> dict:
    """
    Image-to-video con DoP (Director of Photography).
    quality: "dop-preview" | "dop-turbo" | "dop-lite"
    motion_id: preset de movimiento de cámara (opcional, UUID de Higgsfield)
    Returns: {"url": str, "endpoint": str, "prompt": str}
    """
    endpoint = ENDPOINTS["dop"]
    arguments: dict = {
        "model": quality,
        "prompt": prompt,
        "input_images": [
            {"type": "image_url", "image_url": image_url}
        ],
    }
    if motion_id:
        arguments["motion_id"] = motion_id

    result = higgsfield_client.subscribe(endpoint, arguments=arguments)

    videos = result.get("videos") or result.get("output") or []
    if not videos:
        raise ValueError(f"No videos in response: {result}")

    video_url = videos[0]["url"] if isinstance(videos[0], dict) else videos[0]
    return {"url": video_url, "endpoint": endpoint, "prompt": prompt}


def generate_video_with_frames(
    prompt: str,
    first_frame_url: Optional[str] = None,
    last_frame_url: Optional[str] = None,
    quality: str = DEFAULT_VIDEO_QUALITY,
) -> dict:
    """
    Video con primer y/o último frame bloqueados (DoP).
    """
    endpoint = ENDPOINTS["dop"]
    input_images = []
    if first_frame_url:
        input_images.append({"type": "image_url", "image_url": first_frame_url})
    if last_frame_url:
        input_images.append({"type": "image_url", "image_url": last_frame_url})

    arguments: dict = {
        "model": quality,
        "prompt": prompt,
    }
    if input_images:
        arguments["input_images"] = input_images

    result = higgsfield_client.subscribe(endpoint, arguments=arguments)
    videos = result.get("videos") or result.get("output") or []
    if not videos:
        raise ValueError(f"No videos in response: {result}")

    video_url = videos[0]["url"] if isinstance(videos[0], dict) else videos[0]
    return {"url": video_url, "endpoint": endpoint, "prompt": prompt}


def download_file(url: str, output_path: str) -> str:
    """Descarga un archivo de una URL a disco. Devuelve el path local."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(url, stream=True, timeout=300)
    response.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    return output_path


def list_available_models() -> dict:
    return {
        "endpoints": ENDPOINTS,
        "dop_quality_variants": DOP_QUALITY,
        "defaults": {
            "image": DEFAULT_IMAGE_ENDPOINT,
            "video_quality": DEFAULT_VIDEO_QUALITY,
        },
    }
