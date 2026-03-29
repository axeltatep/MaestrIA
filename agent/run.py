#!/usr/bin/env python3
"""
MaestrIA CLI — Control Higgsfield like a human.

Usage examples:

  # Simple video from text brief
  python run.py "Un amanecer cinematográfico sobre montañas nevadas, estilo western"

  # With a reference image
  python run.py "Anima esta foto, viento suave y luz dorada" --ref foto.jpg

  # Quiet mode (no progress output)
  python run.py "Retrato cinematográfico nocturno" --quiet

  # Interactive mode (multi-turn session)
  python run.py --interactive
"""

import sys
import typer
from typing import Optional
from rich.console import Console
from rich.prompt import Prompt
from dotenv import load_dotenv

load_dotenv()

import maestria_agent as agent

app = typer.Typer(add_completion=False, rich_markup_mode="rich")
console = Console()


@app.command()
def main(
    brief: Optional[str] = typer.Argument(
        None,
        help="High-level description of what to create (any language).",
    ),
    ref: Optional[str] = typer.Option(
        None,
        "--ref", "-r",
        help="Path to a reference image file.",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet", "-q",
        help="Suppress progress output.",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive", "-i",
        help="Interactive multi-turn session.",
    ),
):
    """
    [bold]MaestrIA[/bold] — Claude operates Higgsfield autonomously.
    Give a brief and the agent writes prompts, selects models, and generates.
    """

    if interactive:
        _interactive_session()
        return

    if not brief:
        console.print("[red]Error:[/red] Provide a brief or use --interactive")
        raise typer.Exit(1)

    results = agent.run(brief=brief, reference_image=ref, verbose=not quiet)

    if not results:
        console.print("[yellow]No files were generated.[/yellow]")
    else:
        for r in results:
            console.print(r["local_path"])


def _interactive_session():
    """Multi-turn interactive session with the agent."""
    console.print("[bold blue]MaestrIA Interactive Session[/bold blue]")
    console.print("Type your brief in any language. Type [bold]exit[/bold] to quit.\n")

    while True:
        try:
            brief = Prompt.ask("[bold cyan]Brief[/bold cyan]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Bye.[/dim]")
            break

        if brief.strip().lower() in ("exit", "quit", "salir"):
            console.print("[dim]Bye.[/dim]")
            break

        if not brief.strip():
            continue

        ref = None
        ref_input = Prompt.ask("[dim]Reference image path (Enter to skip)[/dim]", default="")
        if ref_input.strip():
            ref = ref_input.strip()

        agent.run(brief=brief, reference_image=ref, verbose=True)
        console.print()


if __name__ == "__main__":
    app()
