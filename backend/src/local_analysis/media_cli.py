from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

# Add local lib directory (for questionary/rich installs)
lib_path = Path(__file__).parent / "lib"
if lib_path.exists():
    sys.path.insert(0, str(lib_path))

import questionary
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..cli.archive_utils import ensure_zip
from ..cli.display import format_media_summary
from ..scanner.errors import ParserError
from ..scanner.media import AUDIO_EXTENSIONS, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS, is_media_candidate
from ..scanner.parser import parse_zip
from .media_analyzer import MediaAnalyzer


console = Console()
MEDIA_TYPE_LOOKUP = {
    **{ext: "Image" for ext in IMAGE_EXTENSIONS},
    **{ext: "Audio" for ext in AUDIO_EXTENSIONS},
    **{ext: "Video" for ext in VIDEO_EXTENSIONS},
}


def _render_banner() -> None:
    console.print()
    console.rule("[bold cyan]MEDIA ANALYZER[/bold cyan]")
    console.print(
        Panel.fit(
            "[bold]Understand your media assets in seconds![/bold]\n\n"
            "This tool summarizes images, audio, and video files so you can:\n"
            " • Review counts and aggregate metrics\n"
            " • Spot low-resolution images or super-short clips\n"
            " • Capture insights for downstream reports and LLM-free workflows\n",
            border_style="cyan",
        )
    )


def _prompt_for_path() -> Path:
    instructions = (
        "Enter the path to a project or archive to scan.\n"
        "Examples:\n"
        "  • Current directory: .\n"
        "  • Relative path: ./media-folder\n"
        "  • Absolute path: /Users/me/projects/app\n"
        "  • Drag & drop a folder or .zip file directly into the terminal"
    )
    console.print(Panel(instructions, title="Select Target", border_style="blue", expand=False))
    use_questionary = sys.stdin.isatty() and sys.stdout.isatty()
    while True:
        answer: Optional[str] = None
        if use_questionary:
            prompt_func = getattr(questionary, "path", questionary.text)
            try:
                answer = prompt_func("📁 Path").ask()
            except Exception:
                use_questionary = False
        if answer is None:
            try:
                answer = input("📁 Path: ")
            except EOFError:
                answer = ""
        answer = answer.strip()
        if not answer:
            answer = "."
        path = Path(answer).expanduser()
        if path.exists():
            return path
        console.print(f"[red]Path '{path}' does not exist. Try again.[/red]")


def _render_summary(summary: Dict[str, Any]) -> None:
    table = Table(title="Summary", box=box.ROUNDED)
    table.add_column("Metric", style="cyan", justify="right")
    table.add_column("Value", style="white")
    table.add_row("Files processed", str(summary.get("files_processed", 0)))
    table.add_row("Media files processed", str(summary.get("media_files_processed", 0)))
    if summary.get("media_files_too_large"):
        table.add_row("Media files skipped (too large)", str(summary["media_files_too_large"]))
    if summary.get("media_metadata_errors"):
        table.add_row("Metadata errors", str(summary["media_metadata_errors"]))
    if summary.get("media_read_errors"):
        table.add_row("Read errors", str(summary["media_read_errors"]))
    table.add_row("Bytes processed", f"{summary.get('bytes_processed', 0):,}")
    if (filtered := summary.get("filtered_out")) is not None:
        table.add_row("Filtered out", str(filtered))
    console.print(table)


def _render_media_files(files: Iterable[Any]) -> None:
    table = Table(title="Media Files", box=box.ROUNDED, show_header=True)
    table.add_column("Path", style="green")
    table.add_column("Type", style="cyan")
    table.add_column("Details", style="white")
    added = False
    for meta in files:
        if not getattr(meta, "media_info", None):
            continue
        media_type = _infer_media_type(meta.path)
        table.add_row(meta.path, media_type, format_media_summary(meta.media_info))
        added = True
    if added:
        console.print(table)
    else:
        console.print("[dim]No media files detected.[/dim]")


def _infer_media_type(path: str) -> str:
    suffix = Path(path).suffix.lower()
    return MEDIA_TYPE_LOOKUP.get(suffix, "Media")


def _render_analysis(analysis: Dict[str, Any]) -> None:
    summary = analysis["summary"]
    metrics = analysis["metrics"]
    insights = analysis["insights"]
    issues = analysis["issues"]

    console.print(Panel.fit("ANALYSIS RESULTS", border_style="magenta"))
    stats_table = Table(box=box.ROUNDED)
    stats_table.add_column("Type", style="cyan")
    stats_table.add_column("Count", justify="right")
    stats_table.add_column("Notes", style="white")
    stats_table.add_row("Images", str(summary["image_files"]), _format_image_metrics(metrics["images"]))
    stats_table.add_row("Audio", str(summary["audio_files"]), _format_audio_metrics(metrics["audio"]))
    stats_table.add_row("Video", str(summary["video_files"]), _format_audio_metrics(metrics["video"]))
    console.print(stats_table)

    if insights:
        console.print(Panel("\n".join(f"• {item}" for item in insights), title="Insights", border_style="green"))
    if issues:
        console.print(Panel("\n".join(f"• {item}" for item in issues), title="Issues", border_style="red"))


def _format_image_metrics(metrics: Dict[str, Any]) -> str:
    if metrics["count"] == 0:
        return "—"
    bits = [
        f"avg {metrics['average_width']:.0f}x{metrics['average_height']:.0f}",
    ]
    if metrics.get("max_resolution"):
        max_res = metrics["max_resolution"]
        bits.append(f"max {max_res['dimensions'][0]}x{max_res['dimensions'][1]}")
    return ", ".join(bits)


def _format_audio_metrics(metrics: Dict[str, Any]) -> str:
    if metrics["count"] == 0:
        return "—"
    bits = [f"total {metrics['total_duration_seconds']:.1f}s"]
    avg = metrics["average_duration_seconds"]
    if avg:
        bits.append(f"avg {avg:.1f}s")
    return ", ".join(bits)


def run_media_cli() -> None:
    _render_banner()
    try:
        target = _prompt_for_path()
        console.print()
        console.rule("[bold cyan]STARTING ANALYSIS[/bold cyan]")
        console.print(f"🎯 Target: [bold]{target}[/bold]")
        console.print("[bold cyan]⚙️  Preparing project...[/bold cyan]")
        archive = ensure_zip(target)
    except (ValueError, SystemExit):
        raise
    except Exception as exc:
        console.print(f"[red]Failed to prepare archive: {exc}[/red]")
        raise SystemExit(1)

    try:
        console.print("[bold cyan]🔍 Scanning archive...[/bold cyan]")
        parse_result = parse_zip(archive, relevant_only=False)
    except ParserError as exc:
        console.print(f"[red]Parsing failed: {exc}[/red]")
        raise SystemExit(1)

    media_files = [meta for meta in parse_result.files if meta.media_info]
    console.print()
    console.print(Panel(f"Media files discovered: {len(media_files)}", border_style="green"))
    _render_summary(parse_result.summary)
    console.print()
    _render_media_files(parse_result.files)
    analyzer = MediaAnalyzer()
    analysis = analyzer.analyze(parse_result.files)
    console.print()
    _render_analysis(analysis)

    console.print()
    if sys.stdin.isatty():
        console.print(Panel.fit("Press Enter to exit...", border_style="cyan"))
        try:
            input()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    try:
        run_media_cli()
    except KeyboardInterrupt:
        console.print("\n[red]Aborted by user.[/red]")
        sys.exit(1)
