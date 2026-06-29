"""
파이프라인 결과를 터미널에 단계별로 출력한다.
터미널 출력(사람용)과 results.json(분석용)은 분리한다.
"""

from typing import Optional
from rich.console import Console
from rich.rule import Rule

from facts.types import PerceptionResult

console = Console()


def report_segment(
    result: PerceptionResult,
    trigger_name: Optional[str],
    trigger_reason: Optional[str],
    agent_output: Optional[dict],
) -> None:
    ts = f"{int(result.timestamp // 60):02d}:{int(result.timestamp % 60):02d}"
    console.print(Rule(f"[bold]{ts}[/bold]", style="dim"))

    # PERCEPTION
    zones = "  ".join(f"{z}={n}" for z, n in result.zone_counts.items())
    console.print(
        f" [bold cyan]PERCEPTION[/bold cyan]  "
        f"total=[bold]{result.total}[/bold]  "
        f"density=[bold]{result.density:.0f}[/bold]  "
        f"avg_speed={result.avg_speed:.2f}"
    )
    console.print(f"            zones: {zones}")

    # TRIGGER
    if trigger_name:
        console.print(
            f" [bold yellow]TRIGGER    [/bold yellow]"
            f" [yellow]{trigger_name}[/yellow] ({trigger_reason})"
        )
    else:
        console.print(f" [bold green]TRIGGER    [/bold green] — (정상)")

    # AGENT — 트리거가 없을 때 'AGENT skip'이 명시적으로 보여야 한다
    if agent_output:
        tool_tag = "  [dim][tool called][/dim]" if agent_output.get("tool_called") else ""
        console.print(
            f" [bold magenta]AGENT      [/bold magenta]"
            f" 호출됨 (트리거: {trigger_name}){tool_tag}"
        )
        if agent_output.get("tool_raw"):
            console.print("   [dim]├ tool    track_people(...)[/dim]")
        assess   = agent_output.get("assessment", "?")
        reasoning = (agent_output.get("reasoning") or "")[:80]
        level    = agent_output.get("congestion_level", "?")
        action   = agent_output.get("action", "?")
        console.print(f'   [dim]├ assess  {assess} — "{reasoning}"[/dim]')
        console.print(f"   [dim]├ level   {level}[/dim]")
        console.print(f"   [dim]└ action  {action}[/dim]")
    else:
        console.print(f" [bold dim]AGENT      [/bold dim] skip")

    console.print()
