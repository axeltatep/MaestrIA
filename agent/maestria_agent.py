"""
MaestrIA Agent — Claude opera Higgsfield como un humano.

Modelos confirmados:
  - Soul         /v1/text2image/soul          → imágenes (nativo Higgsfield)
  - DoP-preview  /v1/image2video/dop          → video (plan Unlimited)
  - Seedream     bytedance/seedream/v4/...    → imágenes alternativas

Flujo:
  1. Usuario da un brief (cualquier idioma)
  2. Claude decide: qué generar, qué prompt, qué modelo, qué parámetros
  3. Agente ejecuta las llamadas a Higgsfield
  4. Los archivos se descargan a ./output/
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
# Herramientas expuestas a Claude
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "generate_image",
        "description": (
            "Genera una imagen de alta calidad con el modelo Soul de Higgsfield. "
            "Úsalo cuando el brief pide una imagen fija, un frame de referencia, "
            "o como primer paso antes de animar con DoP."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": (
                        "Prompt cinematográfico detallado en inglés. Incluye: "
                        "sujeto, iluminación, ángulo de cámara, estado de ánimo, "
                        "paleta de color, textura, profundidad de campo."
                    ),
                },
                "quality": {
                    "type": "string",
                    "enum": ["720p", "1080p"],
                    "description": "Resolución de salida. Default: 1080p.",
                },
                "aspect_ratio": {
                    "type": "string",
                    "enum": ["16:9", "9:16", "1:1", "4:3", "3:4", "21:9"],
                    "description": "Relación de aspecto. 16:9 para cinematográfico.",
                },
                "model_key": {
                    "type": "string",
                    "enum": ["soul", "seedream", "flux"],
                    "description": (
                        "Modelo de imagen. soul=nativo Higgsfield (default), "
                        "seedream=ByteDance, flux=Flux Pro Kontext."
                    ),
                },
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "upload_reference_image",
        "description": (
            "Sube una imagen local al CDN de Higgsfield. "
            "Úsalo cuando el usuario proporciona una imagen de referencia "
            "antes de llamar a generate_video_from_image."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Ruta local a la imagen (absoluta o relativa).",
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "generate_video_from_image",
        "description": (
            "Anima una imagen en video usando DoP (Director of Photography), "
            "el modelo cinematográfico nativo de Higgsfield. "
            "Es el modelo principal del plan Unlimited. "
            "Úsalo cuando tengas una imagen de referencia (subida o generada) "
            "o cuando el brief pida movimiento a partir de una imagen."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "image_url": {
                    "type": "string",
                    "description": "URL CDN de la imagen (de upload_reference_image o generate_image).",
                },
                "prompt": {
                    "type": "string",
                    "description": (
                        "Prompt de movimiento en inglés. Describe el movimiento de cámara, "
                        "acción del sujeto, viento, luz, atmósfera. "
                        "Ej: 'slow dolly push-in, golden dust particles floating, "
                        "cinematic depth of field, film grain'."
                    ),
                },
                "quality": {
                    "type": "string",
                    "enum": ["dop-preview", "dop-turbo", "dop-lite"],
                    "description": (
                        "Calidad DoP. "
                        "dop-preview=máxima calidad (plan Unlimited, default), "
                        "dop-turbo=2× más rápido, "
                        "dop-lite=más económico."
                    ),
                },
                "motion_id": {
                    "type": "string",
                    "description": "UUID de preset de movimiento de cámara (opcional).",
                },
            },
            "required": ["image_url", "prompt"],
        },
    },
    {
        "name": "generate_video_with_frames",
        "description": (
            "Genera video con control total del primer y/o último frame (DoP). "
            "Úsalo para composiciones precisas o cuando el brief especifica "
            "cómo debe empezar y terminar el clip."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Prompt de movimiento y contenido del video.",
                },
                "first_frame_url": {
                    "type": "string",
                    "description": "URL CDN del primer frame (opcional).",
                },
                "last_frame_url": {
                    "type": "string",
                    "description": "URL CDN del último frame (opcional).",
                },
                "quality": {
                    "type": "string",
                    "enum": ["dop-preview", "dop-turbo", "dop-lite"],
                    "description": "Calidad DoP. Default: dop-preview.",
                },
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "list_models",
        "description": "Lista los modelos disponibles en Higgsfield.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


# ---------------------------------------------------------------------------
# Ejecutor de herramientas
# ---------------------------------------------------------------------------

def _ts() -> str:
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def execute_tool(tool_name: str, tool_input: dict) -> dict:
    if tool_name == "list_models":
        return hf.list_available_models()

    if tool_name == "upload_reference_image":
        path = tool_input["path"]
        console.print(f"[yellow]↑ Subiendo imagen de referencia:[/yellow] {path}")
        url = hf.upload_image(path)
        console.print(f"[green]✓ Subida:[/green] {url}")
        return {"cdn_url": url}

    if tool_name == "generate_image":
        console.print("[yellow]🎨 Generando imagen (Soul)...[/yellow]")
        console.print(f"   [dim]{tool_input['prompt'][:120]}[/dim]")
        result = hf.generate_image(
            prompt=tool_input["prompt"],
            quality=tool_input.get("quality", "1080p"),
            aspect_ratio=tool_input.get("aspect_ratio", "16:9"),
            model_key=tool_input.get("model_key", hf.DEFAULT_IMAGE_ENDPOINT),
        )
        out_path = str(OUTPUT_DIR / f"image_{_ts()}.jpg")
        hf.download_file(result["url"], out_path)
        console.print(f"[green]✓ Imagen guardada:[/green] {out_path}")
        result["local_path"] = out_path
        return result

    if tool_name == "generate_video_from_image":
        quality = tool_input.get("quality", hf.DEFAULT_VIDEO_QUALITY)
        console.print(f"[yellow]🎬 Animando imagen → video (DoP {quality})...[/yellow]")
        console.print(f"   [dim]{tool_input['prompt'][:120]}[/dim]")
        result = hf.generate_video_from_image(
            image_url=tool_input["image_url"],
            prompt=tool_input["prompt"],
            quality=quality,
            motion_id=tool_input.get("motion_id"),
        )
        out_path = str(OUTPUT_DIR / f"video_{_ts()}.mp4")
        hf.download_file(result["url"], out_path)
        console.print(f"[green]✓ Video guardado:[/green] {out_path}")
        result["local_path"] = out_path
        return result

    if tool_name == "generate_video_with_frames":
        quality = tool_input.get("quality", hf.DEFAULT_VIDEO_QUALITY)
        console.print(f"[yellow]🎬 Generando video con frame control (DoP {quality})...[/yellow]")
        result = hf.generate_video_with_frames(
            prompt=tool_input["prompt"],
            first_frame_url=tool_input.get("first_frame_url"),
            last_frame_url=tool_input.get("last_frame_url"),
            quality=quality,
        )
        out_path = str(OUTPUT_DIR / f"video_{_ts()}.mp4")
        hf.download_file(result["url"], out_path)
        console.print(f"[green]✓ Video guardado:[/green] {out_path}")
        result["local_path"] = out_path
        return result

    return {"error": f"Herramienta desconocida: {tool_name}"}


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """Eres MaestrIA, un director de fotografía y cinematógrafo AI de élite.
Controlas la plataforma Higgsfield con total autonomía usando estas herramientas.

MODELOS DISPONIBLES:
- Soul (/v1/text2image/soul): generación de imágenes nativo Higgsfield
- DoP-preview (/v1/image2video/dop): el modelo cinematográfico insignia, plan Unlimited
- Seedream / Flux: modelos alternativos de imagen

FLUJO DE TRABAJO ESTÁNDAR:
1. Si el brief pide un video → genera primero la imagen con Soul, luego anímala con DoP
2. Si el usuario da una imagen → súbela con upload_reference_image, luego DoP
3. Si pide control inicio/fin → generate_video_with_frames con DoP
4. Si solo pide una imagen → generate_image con Soul

REGLAS PARA TUS PROMPTS (siempre en inglés):
- Sé extremadamente detallado: iluminación, lente, movimiento de cámara, hora del día,
  textura, grain, color grade, estado de ánimo, profundidad de campo
- Para videos: especifica SIEMPRE el movimiento de cámara
  (slow push-in, crane shot, handheld, dolly, pan, arc, etc.)
- Usa lenguaje cinematográfico profesional:
  "anamorphic lens flare", "volumetric light", "golden hour", "film grain",
  "bokeh", "rack focus", "shallow depth of field", "35mm film"
- El prompt de movimiento DoP debe describir cómo SE MUEVE la escena, no qué hay en ella

CALIDAD: Siempre usa dop-preview (plan Unlimited del usuario).

Después de generar, explica brevemente tus decisiones creativas."""


# ---------------------------------------------------------------------------
# Loop principal del agente
# ---------------------------------------------------------------------------

def run(
    brief: str,
    reference_image: Optional[str] = None,
    verbose: bool = True,
) -> list[dict]:
    """
    Ejecuta el agente MaestrIA sobre un brief.

    Args:
        brief: Descripción de alto nivel (cualquier idioma).
        reference_image: Ruta local a una imagen de referencia (opcional).
        verbose: Mostrar progreso en consola.

    Returns:
        Lista de dicts con 'local_path' y 'url' por cada archivo generado.
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    user_content = brief
    if reference_image:
        user_content += f"\n\nImagen de referencia en: {reference_image}"

    messages = [{"role": "user", "content": user_content}]

    if verbose:
        console.print(Panel(
            f"[bold]Brief:[/bold] {brief}",
            title="[bold blue]MaestrIA[/bold blue]",
            style="blue",
        ))

    results = []

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        tool_calls = []
        text_parts = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(block)

        if text_parts and verbose:
            console.print(Markdown("\n".join(text_parts)))

        if response.stop_reason == "end_turn" or not tool_calls:
            break

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tc in tool_calls:
            if verbose:
                console.print(f"\n[bold cyan]→ {tc.name}[/bold cyan]")

            result = execute_tool(tc.name, tc.input)

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
            title="Archivos generados",
            style="green",
        ))

    return results
