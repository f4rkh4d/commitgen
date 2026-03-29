"""click entrypoint. stitches diff -> detect -> format -> output."""

from __future__ import annotations

import subprocess
import sys

import click
from rich.console import Console

from . import __version__
from .detect import VALID_TYPES, compute_stats, detect_scope, detect_type
from .diff import get_staged
from .format import assemble

console = Console()
err = Console(stderr=True)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--commit", "do_commit", is_flag=True, help="run the commit instead of just printing.")
@click.option("--body", "with_body", is_flag=True, help="include a bullet body.")
@click.option("--no-scope", is_flag=True, help="omit the (scope) parens.")
@click.option("--type", "force_type", type=click.Choice(VALID_TYPES), default=None, help="force a commit type.")
@click.option("--dry-run", is_flag=True, help="print, don't commit. default behavior.")
@click.version_option(__version__, prog_name="commitgen")
def main(do_commit: bool, with_body: bool, no_scope: bool, force_type: str | None, dry_run: bool) -> None:
    """reads your staged diff, suggests a conventional-commit message. rule-based."""
    try:
        diff = get_staged()
    except RuntimeError as e:
        err.print(f"[red]git said no:[/red] {e}")
        sys.exit(1)
    except FileNotFoundError:
        err.print("[red]can't find git on your PATH. is it installed?[/red]")
        sys.exit(1)

    if not diff.files:
        err.print("[yellow]nothing staged.[/yellow] `git add` something first.")
        sys.exit(1)

    stats = compute_stats(diff)
    commit_type = force_type or detect_type(diff, stats)
    scope = None if no_scope else detect_scope(diff)
    msg = assemble(commit_type, scope, diff, stats, include_body=with_body)
    rendered = msg.render()

    if do_commit and not dry_run:
        try:
            subprocess.run(["git", "commit", "-m", rendered], check=True)
        except subprocess.CalledProcessError as e:
            err.print(f"[red]commit failed:[/red] {e}")
            sys.exit(e.returncode)
        return

    # pretty print to stdout
    header = f"[bold]{msg.type}[/bold]"
    if msg.scope:
        header += f"([cyan]{msg.scope}[/cyan])"
    header += f": {msg.subject}"
    console.print(header)
    if msg.body:
        console.print()
        console.print(msg.body)


if __name__ == "__main__":
    main()
