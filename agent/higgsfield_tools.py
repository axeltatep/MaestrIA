"""
Higgsfield API wrapper.
All direct calls to higgsfield_client live here.
"""

import os
import requests
from pathlib import Path
from typing import Optional
import higgsfield_client


# ---------------------------------------------------------------------------
# Available models
# Verify exact IDs in your Higgsfield dashboard → API → Models
# ---------------------------------------------------------------------------
MODELS = {
    # Images
    "seedream":        "bytedance/seedream/v4/text-to-image",

    # Videos – text-to-video
    "kling-t2v":       "kling-ai/kling/v3/text-to-video",
    "wan-t2v":         "wan-video/wan/v2-5/text-to-video",
    "sora-t2v":        "openai/sora/v2/text-to-video",
    "veo-t2v":         "google/veo/v3-1/text-to-video",

    # Videos – image-to-video
    "kling-i2v":       "kling-ai/kling/v3/image-to-video",
    "wan-i2v":         "wan-video/wan/v2-5/image-to-video",
    "sora-i2v":        "openai/sora/v2/image-to-video",
    "veo-i2v":         "google/veo/v3-1/image-to-video",
}

DEFAULT_IMAGE_MODEL = "seedream"
DEFAULT_VIDEO_MODEL = "kling-t2v"
DEFAULT_I2V_MODEL   = "kling-i2v"


def upload_image(path: str) -> str:
    """Upload a local image to Higgsfield and return its CDN URL."""
    url = higgsfield_client.upload_file(path)
    return url


def generate_image(
    prompt: str,
    resolution: str = "2K",
    aspect_ratio: str = "16:9",
    camera_fixed: bool = False,
    model_key: str = DEFAULT_IMAGE_MODEL,
) -> dict:
    """
    Text-to-image generation.
    Returns: {"url": str, "model": str, "prompt": str}
    """
    model_id = MODELS.get(model_key, model_key)
    result = higgsfield_client.subscribe(
        model_id,
        arguments={
            "prompt": prompt,
            "resolution": resolution,
            "aspect_ratio": aspect_ratio,
            "camera_fixed": camera_fixed,
        },
    )
    image_url = result["images"][0]["url"]
    return {"url": image_url, "model": model_id, "prompt": prompt}


def generate_video_from_text(
    prompt: str,
    duration: int = 5,
    resolution: str = "1080p",
    aspect_ratio: str = "16:9",
    model_key: str = DEFAULT_VIDEO_MODEL,
    webhook_url: Optional[str] = None,
) -> dict:
    """
    Text-to-video generation.
    Returns: {"url": str, "model": str, "prompt": str}
    """
    model_id = MODELS.get(model_key, model_key)
    arguments = {
        "prompt": prompt,
        "duration": duration,
        "resolution": resolution,
        "aspect_ratio": aspect_ratio,
    }

    if webhook_url:
        request_controller = higgsfield_client.submit(
            model_id, arguments=arguments, webhook_url=webhook_url
        )
        return {
            "request_id": request_controller.request_id,
            "model": model_id,
            "prompt": prompt,
            "status": "submitted",
        }

    result = higgsfield_client.subscribe(model_id, arguments=arguments)
    video_url = result["videos"][0]["url"]
    return {"url": video_url, "model": model_id, "prompt": prompt}


def generate_video_from_image(
    image_url: str,
    prompt: str,
    duration: int = 5,
    resolution: str = "1080p",
    aspect_ratio: str = "16:9",
    model_key: str = DEFAULT_I2V_MODEL,
) -> dict:
    """
    Image-to-video generation. image_url can be a Higgsfield CDN URL
    (returned by upload_image) or any public HTTPS URL.
    Returns: {"url": str, "model": str, "prompt": str}
    """
    model_id = MODELS.get(model_key, model_key)
    result = higgsfield_client.subscribe(
        model_id,
        arguments={
            "image_url": image_url,
            "prompt": prompt,
            "duration": duration,
            "resolution": resolution,
            "aspect_ratio": aspect_ratio,
        },
    )
    video_url = result["videos"][0]["url"]
    return {"url": video_url, "model": model_id, "prompt": prompt}


def generate_video_with_frames(
    prompt: str,
    first_frame_url: Optional[str] = None,
    last_frame_url: Optional[str] = None,
    duration: int = 5,
    resolution: str = "1080p",
    aspect_ratio: str = "16:9",
    model_key: str = DEFAULT_I2V_MODEL,
) -> dict:
    """
    Video generation with locked first/last frames.
    Gives precise control over how the video starts and ends.
    """
    model_id = MODELS.get(model_key, model_key)
    arguments: dict = {
        "prompt": prompt,
        "duration": duration,
        "resolution": resolution,
        "aspect_ratio": aspect_ratio,
    }
    if first_frame_url:
        arguments["first_frame_url"] = first_frame_url
    if last_frame_url:
        arguments["last_frame_url"] = last_frame_url

    result = higgsfield_client.subscribe(model_id, arguments=arguments)
    video_url = result["videos"][0]["url"]
    return {"url": video_url, "model": model_id, "prompt": prompt}


def download_file(url: str, output_path: str) -> str:
    """Download a file from a URL to a local path. Returns the path."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(url, stream=True, timeout=120)
    response.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    return output_path


def list_available_models() -> dict:
    """Return the models dictionary."""
    return MODELS
