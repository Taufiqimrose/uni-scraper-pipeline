#!/usr/bin/env python3
"""Rich CLI dashboard for watching a scrape job's pipeline progress.

Usage:
    python scripts/pipeline_watch.py <job_id>
    python scripts/pipeline_watch.py <job_id> --api-url http://localhost:8000
    python scripts/pipeline_watch.py <job_id> --poll 3
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import httpx
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

TERMINAL_STATUSES = {"completed", "failed", "partial"}

STATUS_ICONS = {
    "completed": "[green]\u2705[/green]",
    "running": "[cyan]\ud83d\udd04[/cyan]",
    "pending": "[dim]\u23f3[/dim]",
    "failed": "[red]\u274c[/red]",
    "skipped": "[dim]\u23ed\ufe0f[/dim]",
}

OVERALL_COLORS = {
    "queued": "dim",
    "running": "cyan",
    "discovering": "blue",
    "extracting": "yellow",
    "validating": "magenta",
    "completed": "green",
    "failed": "red",
    "partial": "yellow",
}


def format_duration(seconds: float | None) -> str:
    """Format seconds into a human-readable duration."""
    if seconds is None:
        return ""
    if seconds < 1:
        return f"{seconds:.1f}s"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.0f}s"


def build_progress_bar(progress: float, width: int = 30) -> str:
    """Build a text-based progress bar."""
    filled = int(progress * width)
    empty = width - filled
    bar = "\u2588" * filled + "\u2591" * empty
    pct = f"{progress * 100:.0f}%"
    return f"{bar} {pct}"


def build_dashboard(data: dict) -> Panel:
    """Build a Rich Panel dashboard from pipeline API response."""
    university = data.get("university_name", "Unknown")
    major = data.get("major_name")
    overall = data.get("overall_status", "unknown")
    progress = data.get("progress", 0.0)
    elapsed = data.get("elapsed_seconds")
    steps = data.get("steps", [])
    metrics = data.get("metrics", {})

    # Title
    title_parts = [university]
    if major:
        title_parts.append(major)
    title = " \u2014 ".join(title_parts)

    # Header: status + progress bar + elapsed
    color = OVERALL_COLORS.get(overall, "white")
    header = Text()
    header.append("  Status: ", style="bold")
    header.append(overall.upper(), style=f"bold {color}")
    header.append("  ")
    header.append(build_progress_bar(progress))
    if elapsed is not None:
        header.append(f"   Elapsed: {format_duration(elapsed)}", style="dim")
    header.append("\n")

    # Steps table
    step_table = Table(
        show_header=False,
        show_edge=False,
        box=None,
        padding=(0, 2),
        expand=True,
    )
    step_table.add_column("icon", width=4, no_wrap=True)
    step_table.add_column("name", min_width=22, no_wrap=True)
    step_table.add_column("duration", width=10, justify="right")
    step_table.add_column("detail", ratio=1)

    for step in steps:
        icon = STATUS_ICONS.get(step.get("status", "pending"), "\u2753")
        name = step.get("name", "")
        duration = format_duration(step.get("duration_seconds"))
        detail = step.get("detail") or ""

        name_style = "bold" if step.get("status") == "running" else ""
        if step.get("status") == "completed":
            name_style = "green"
        elif step.get("status") == "failed":
            name_style = "red"
        elif step.get("status") in ("pending", "skipped"):
            name_style = "dim"

        step_table.add_row(icon, Text(name, style=name_style), duration, Text(detail, style="dim"))

    # Metrics footer
    tokens = metrics.get("tokens_used", 0)
    pages = metrics.get("pages_fetched", 0)
    programs_found = metrics.get("programs_found", 0)
    programs_scraped = metrics.get("programs_scraped", 0)
    courses = metrics.get("courses_found", 0)

    footer = Text()
    footer.append("\n  ")
    footer.append(f"Tokens: {tokens:,}", style="cyan")
    footer.append("  \u2502  ")
    footer.append(f"Pages: {pages}", style="blue")
    footer.append("  \u2502  ")
    footer.append(f"Programs: {programs_scraped}/{programs_found}", style="yellow")
    footer.append("  \u2502  ")
    footer.append(f"Courses: {courses}", style="green")

    # Compose the panel
    from rich.console import Group

    content = Group(header, step_table, footer)

    border_color = color if overall not in TERMINAL_STATUSES else ("green" if overall == "completed" else "red")

    return Panel(
        content,
        title=f"[bold]Pipeline: {title}[/bold]",
        border_style=border_color,
        expand=True,
        padding=(1, 2),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Watch a scrape job pipeline in real time")
    parser.add_argument("job_id", help="The scrape job UUID to watch")
    parser.add_argument(
        "--api-url",
        default=os.getenv("API_URL", "http://localhost:8000"),
        help="Base URL of the API server (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("API_KEY", ""),
        help="API key for authentication (default: from API_KEY env var)",
    )
    parser.add_argument(
        "--poll",
        type=float,
        default=2.0,
        help="Polling interval in seconds (default: 2.0)",
    )
    args = parser.parse_args()

    console = Console()
    url = f"{args.api_url.rstrip('/')}/api/v1/scrape/{args.job_id}/pipeline"
    headers = {}
    if args.api_key:
        headers["X-API-Key"] = args.api_key

    console.print(f"\n[dim]Watching job [bold]{args.job_id}[/bold] at {url}[/dim]\n")

    try:
        with Live(console=console, refresh_per_second=2) as live:
            while True:
                try:
                    resp = httpx.get(url, headers=headers, timeout=10)
                    if resp.status_code == 404:
                        live.update(Panel("[red]Job not found[/red]", title="Error"))
                        break
                    resp.raise_for_status()
                    data = resp.json()
                except httpx.HTTPError as e:
                    live.update(Panel(f"[red]API error: {e}[/red]", title="Error"))
                    time.sleep(args.poll)
                    continue

                panel = build_dashboard(data)
                live.update(panel)

                overall = data.get("overall_status", "")
                if overall in TERMINAL_STATUSES:
                    # Final update, then exit
                    time.sleep(0.5)
                    break

                time.sleep(args.poll)

    except KeyboardInterrupt:
        console.print("\n[dim]Stopped watching.[/dim]")

    console.print()


if __name__ == "__main__":
    main()
