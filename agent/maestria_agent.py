"""
MaestrIA Agent — Claude operates Higgsfield like a human.

Flow:
  1. User gives a high-level brief (text)
  2. Claude decides: what prompt, what model, what settings, what references
  3. Agent calls Higgsfield via tool calls
  4. Results are downloaded and returned
"""

import os
import json
import datetime
from pathlib import Path
from typing import Optional

import anthropic
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

import higgsfield_tools as hf

load_dotenv()

console = Console()

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Tool definitions exposed to Claude
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "generate_image",
        "description": (
            "Generate a high-quality image from a text prompt using Higgsfield. "
            "Use this when the brief asks for a still image, a reference frame, "
            "or as a first step before animating."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": (
                        "Detailed, cinematic prompt in English. Include style, lighting, "
                        "camera angle, mood, color palette, and subject details."
                    ),
                },
                "resolution": {
                    "type": "string",
                    "enum": ["1K", "2K", "4K"],
                    "description": "Output resolution. Default: 2K",
                },
                "aspect_ratio": {
                    "type": "string",
                    "enum": ["16:9", "9:16", "1:1", "4:3", "3:4", "21:9"],
                    "description": "Aspect ratio. Default: 16:9 for cinematic.",
                },
                "camera_fixed": {
                    "type": "boolean",
                    "description": "Lock camera position for stable composition.",
                },
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "generate_video_from_text",
        "description": (
            "Generate a video from a text prompt. Best for scenes described "
            "purely in words without a reference image."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": (
                        "Detailed cinematic prompt in English. Describe the scene, "
                        "camera movement, lighting, mood, and action."
                    ),
                },
                "model_key": {
                    "type": "string",
                    "enum": ["kling-t2v", "wan-t2v", "sora-t2v", "veo-t2v"],
                    "description": (
                        "Video model to use. "
                        "kling-t2v: best for realistic motion; "
                        "wan-t2v: good quality/cost balance; "
                        "sora-t2v: OpenAI, great physics; "
                        "veo-t2v: Google, excellent cinematic quality."
                    ),
                },
                "duration": {
                    "type": "integer",
                    "enum": [5, 10, 15],
                    "description": "Video duration in seconds. Default: 5.",
                },
                "resolution": {
                    "type": "string",
                    "enum": ["720p", "1080p"],
                    "description": "Output resolution. Default: 1080p.",
                },
                "aspect_ratio": {
                    "type": "string",
                    "enum": ["16:9", "9:16", "1:1"],
                    "description": "Aspect ratio. 16:9 for cinematic, 9:16 for Reels/TikTok.",
                },
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "upload_reference_image",
        "description": (
            "Upload a local image file to Higgsfield CDN. "
            "Use this before generate_video_from_image or generate_video_with_frames "
            "when the user provides a reference image path."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or relative path to the local image file.",
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "generate_video_from_image",
        "description": (
            "Animate an existing image into a video. "
            "Use this when the user provides a reference image or when you just "
            "generated an image and want to animate it."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "image_url": {
                    "type": "string",
                    "description": "Higgsfield CDN URL of the image (from upload_reference_image or generate_image).",
                },
                "prompt": {
                    "type": "string",
                    "description": (
                        "Motion/animation prompt. Describe how the scene should move: "
                        "camera motion, wind, waves, character action, etc."
                    ),
                },
                "model_key": {
                    "type": "string",
                    "enum": ["kling-i2v", "wan-i2v", "sora-i2v", "veo-i2v"],
                    "description": "Image-to-video model. kling-i2v is the safest default.",
                },
                "duration": {
                    "type": "integer",
                    "enum": [5, 10, 15],
                    "description": "Duration in seconds.",
                },
                "resolution": {
                    "type": "string",
                    "enum": ["720p", "1080p"],
                },
                "aspect_ratio": {
                    "type": "string",
                    "enum": ["16:9", "9:16", "1:1"],
                },
            },
            "required": ["image_url", "prompt"],
        },
    },
    {
        "name": "generate_video_with_frames",
        "description": (
            "Generate a video with full control over the first and/or last frame. "
            "Use this for precise compositions or when you need the video to start "
            "or end at a specific visual state."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Motion and content description for the video.",
                },
                "first_frame_url": {
                    "type": "string",
                    "description": "CDN URL for the first frame (optional).",
                },
                "last_frame_url": {
                    "type": "string",
                    "description": "CDN URL for the last frame (optional).",
                },
                "model_key": {
                    "type": "string",
                    "enum": ["kling-i2v", "wan-i2v", "sora-i2v", "veo-i2v"],
                },
                "duration": {"type": "integer", "enum": [5, 10, 15]},
                "resolution": {"type": "string", "enum": ["720p", "1080p"]},
                "aspect_ratio": {"type": "string", "enum": ["16:9", "9:16", "1:1"]},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "list_models",
        "description": "List all available Higgsfield models and their keys.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


# ---------------------------------------------------------------------------
# Tool executor
# ---------------------------------------------------------------------------

def _timestamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def execute_tool(tool_name: str, tool_input: dict) -> dict:
    """Execute a tool call and return a result dict."""

    if tool_name == "list_models":
        return hf.list_available_models()

    if tool_name == "upload_reference_image":
        path = tool_input["path"]
        console.print(f"[yellow]↑ Uploading reference image:[/yellow] {path}")
        url = hf.upload_image(path)
        console.print(f"[green]✓ Uploaded:[/green] {url}")
        return {"cdn_url": url}

    if tool_name == "generate_image":
        console.print(f"[yellow]🎨 Generating image...[/yellow]")
        console.print(f"   Prompt: [dim]{tool_input['prompt'][:120]}...[/dim]")
        result = hf.generate_image(
            prompt=tool_input["prompt"],
            resolution=tool_input.get("resolution", "2K"),
            aspect_ratio=tool_input.get("aspect_ratio", "16:9"),
            camera_fixed=tool_input.get("camera_fixed", False),
            model_key=tool_input.get("model_key", hf.DEFAULT_IMAGE_MODEL),
        )
        out_path = str(OUTPUT_DIR / f"image_{_timestamp()}.jpg")
        hf.download_file(result["url"], out_path)
        console.print(f"[green]✓ Image saved:[/green] {out_path}")
        result["local_path"] = out_path
        return result

    if tool_name == "generate_video_from_text":
        console.print(f"[yellow]🎬 Generating video from text...[/yellow]")
        console.print(f"   Model: [cyan]{tool_input.get('model_key', hf.DEFAULT_VIDEO_MODEL)}[/cyan]")
        console.print(f"   Prompt: [dim]{tool_input['prompt'][:120]}...[/dim]")
        result = hf.generate_video_from_text(
            prompt=tool_input["prompt"],
            duration=tool_input.get("duration", 5),
            resolution=tool_input.get("resolution", "1080p"),
            aspect_ratio=tool_input.get("aspect_ratio", "16:9"),
            model_key=tool_input.get("model_key", hf.DEFAULT_VIDEO_MODEL),
        )
        out_path = str(OUTPUT_DIR / f"video_{_timestamp()}.mp4")
        hf.download_file(result["url"], out_path)
        console.print(f"[green]✓ Video saved:[/green] {out_path}")
        result["local_path"] = out_path
        return result

    if tool_name == "generate_video_from_image":
        console.print(f"[yellow]🎬 Animating image into video...[/yellow]")
        console.print(f"   Model: [cyan]{tool_input.get('model_key', hf.DEFAULT_I2V_MODEL)}[/cyan]")
        console.print(f"   Prompt: [dim]{tool_input['prompt'][:120]}...[/dim]")
        result = hf.generate_video_from_image(
            image_url=tool_input["image_url"],
            prompt=tool_input["prompt"],
            duration=tool_input.get("duration", 5),
            resolution=tool_input.get("resolution", "1080p"),
            aspect_ratio=tool_input.get("aspect_ratio", "16:9"),
            model_key=tool_input.get("model_key", hf.DEFAULT_I2V_MODEL),
        )
        out_path = str(OUTPUT_DIR / f"video_{_timestamp()}.mp4")
        hf.download_file(result["url"], out_path)
        console.print(f"[green]✓ Video saved:[/green] {out_path}")
        result["local_path"] = out_path
        return result

    if tool_name == "generate_video_with_frames":
        console.print(f"[yellow]🎬 Generating video with frame control...[/yellow]")
        result = hf.generate_video_with_frames(
            prompt=tool_input["prompt"],
            first_frame_url=tool_input.get("first_frame_url"),
            last_frame_url=tool_input.get("last_frame_url"),
            duration=tool_input.get("duration", 5),
            resolution=tool_input.get("resolution", "1080p"),
            aspect_ratio=tool_input.get("aspect_ratio", "16:9"),
            model_key=tool_input.get("model_key", hf.DEFAULT_I2V_MODEL),
        )
        out_path = str(OUTPUT_DIR / f"video_{_timestamp()}.mp4")
        hf.download_file(result["url"], out_path)
        console.print(f"[green]✓ Video saved:[/green] {out_path}")
        result["local_path"] = out_path
        return result

    return {"error": f"Unknown tool: {tool_name}"}


# ---------------------------------------------------------------------------
# Core agent loop
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are MaestrIA, an expert AI cinematographer and creative director.
You operate the Higgsfield AI video/image generation platform with full autonomy.

Your job:
1. Receive a brief from the user (in Spanish or English — doesn't matter).
2. Translate it into one or more Higgsfield API calls using your tools.
3. Craft masterful, detailed cinematic prompts in English for each call.
4. Select the right model, settings, and workflow.
5. Execute everything and report what was created.

Guidelines for prompts you write:
- Always write prompts in English (Higgsfield models perform best in English).
- Be extremely detailed: lighting, camera lens/angle/movement, mood, color grade,
  film stock, depth of field, time of day, weather, texture.
- For videos: always include camera motion (slow push-in, dolly, pan, crane, handheld, etc.)
- Use cinematic reference language: "anamorphic lens", "golden hour", "film grain",
  "volumetric light", "bokeh", "cinematic color grade", etc.
- Match the style and tone the user asks for.

Workflow decision logic:
- User gives image path → upload it first, then generate_video_from_image
- User wants an image → generate_image
- User wants a video with no reference → generate_video_from_text
- User wants maximum control (start/end frame) → generate_video_with_frames
- Multi-shot production → chain multiple calls in sequence

Always explain your creative choices briefly after completing the work."""


def run(
    brief: str,
    reference_image: Optional[str] = None,
    verbose: bool = True,
) -> list[dict]:
    """
    Run the MaestrIA agent on a brief.

    Args:
        brief: High-level description of what to create (any language).
        reference_image: Optional path to a local image file.
        verbose: Print progress to console.

    Returns:
        List of result dicts with 'local_path' and 'url' for each generated file.
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Build initial user message
    user_content = brief
    if reference_image:
        user_content += f"\n\nReference image provided at path: {reference_image}"

    messages = [{"role": "user", "content": user_content}]

    if verbose:
        console.print(Panel(f"[bold]Brief:[/bold] {brief}", title="MaestrIA Agent", style="blue"))

    results = []

    # Agentic loop
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Collect tool calls and text
        tool_calls = []
        text_parts = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(block)

        # Print any text Claude produced
        if text_parts and verbose:
            console.print(Markdown("\n".join(text_parts)))

        # If no tool calls, we're done
        if response.stop_reason == "end_turn" or not tool_calls:
            break

        # Append Claude's response to messages
        messages.append({"role": "assistant", "content": response.content})

        # Execute each tool call
        tool_results = []
        for tc in tool_calls:
            if verbose:
                console.print(f"\n[bold cyan]→ Tool:[/bold cyan] {tc.name}")

            result = execute_tool(tc.name, tc.input)

            # Collect any file outputs
            if "local_path" in result:
                results.append(result)

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tc.id,
                "content": json.dumps(result),
            })

        messages.append({"role": "user", "content": tool_results})

    if verbose and results:
        console.print(Panel(
            "\n".join(f"[green]✓[/green] {r['local_path']}" for r in results),
            title="Generated Files",
            style="green",
        ))

    return results
