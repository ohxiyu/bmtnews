"""CLI entry point for Horizon."""

import argparse
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console

from .storage.manager import ConfigError, StorageManager
from .orchestrator import HorizonOrchestrator


console = Console()


def print_banner():
    """Print the application banner."""
    banner = r"""
[bold blue]
  _    _            _
 | |  | |          (_)
 | |__| | ___  _ __ _ ___  ___  _ __
 |  __  |/ _ \| '__| |_  / / _ \| '_ \
 | |  | | (_) | |  | |/ / | (_) | | | |
 |_|  |_|\___/|_|  |_/___| \___/|_| |_|
[/bold blue]
[cyan]  AI-Driven Information Aggregation System[/cyan]
    """
    console.print(banner)


def main():
    """Main CLI entry point."""
    print_banner()

    parser = argparse.ArgumentParser(description="Horizon - AI-Driven Information Aggregation System")
    parser.add_argument("--hours", type=int, help="Force fetch from last N hours")
    parser.add_argument(
        "--mode",
        choices=("full", "fetch", "publish"),
        default="full",
        help=(
            "full runs the legacy pipeline; fetch only updates the staging cache; "
            "publish builds one fixed-window daily edition"
        ),
    )
    parser.add_argument(
        "--staging-path",
        type=Path,
        default=Path("data/staging-items.json"),
        help="Cross-run raw item staging file",
    )
    parser.add_argument(
        "--cutoff-hour",
        type=int,
        default=20,
        help="Daily edition cutoff hour in filtering.daily_timezone",
    )
    args = parser.parse_args()
    if args.hours is not None and args.hours <= 0:
        parser.error("--hours must be positive")
    if not 0 <= args.cutoff_hour <= 23:
        parser.error("--cutoff-hour must be between 0 and 23")

    try:
        # Load environment variables from .env file
        load_dotenv()

        # Ensure we're in the project directory or use data/ in current dir
        data_dir = Path("data")

        # Initialize storage manager
        storage = StorageManager(data_dir=str(data_dir))

        # Load configuration
        try:
            config = storage.load_config()
        except FileNotFoundError:
            console.print("[bold red]❌ Configuration file not found![/bold red]\n")
            data_dir_path = data_dir if isinstance(data_dir, Path) else Path(data_dir)
            example_path = data_dir_path / "config.example.json"
            if example_path.exists():
                console.print(
                    f"Copy the example config and edit it:\n"
                    f"  [cyan]cp {example_path} {data_dir_path / 'config.json'}[/cyan]\n"
                )
            console.print(
                "Or run [bold cyan]uv run horizon-wizard[/bold cyan] to launch the interactive setup wizard.\n"
            )
            sys.exit(1)
        except ConfigError as e:
            console.print(f"[bold red]❌ Error loading configuration: {e}[/bold red]")
            sys.exit(1)
        except Exception as e:
            console.print(f"[bold red]❌ Error loading configuration: {e}[/bold red]")
            sys.exit(1)

        # Create and run orchestrator
        orchestrator = HorizonOrchestrator(config, storage)
        if args.mode == "fetch":
            asyncio.run(
                orchestrator.fetch_to_staging(
                    force_hours=args.hours,
                    staging_path=args.staging_path,
                )
            )
        elif args.mode == "publish":
            asyncio.run(
                orchestrator.run_daily_edition(
                    force_hours=args.hours,
                    staging_path=args.staging_path,
                    cutoff_hour=args.cutoff_hour,
                )
            )
        else:
            asyncio.run(orchestrator.run(force_hours=args.hours))

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]❌ Fatal error: {e}[/bold red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def print_config_template():
    """Print configuration template."""
    template = """
{
  "version": "1.0",
  "ai": {
    "provider": "anthropic",
    "model": "claude-sonnet-4.5-20250929",
    "api_key_env": "ANTHROPIC_API_KEY",
    "temperature": 0.3,
    "max_tokens": 4096
  },
  "sources": {
    "github": [
      {
        "type": "user_events",
        "username": "torvalds",
        "enabled": true
      }
    ],
    "hackernews": {
      "enabled": true,
      "fetch_top_stories": 30,
      "min_score": 100
    },
    "rss": [
      {
        "name": "Example Blog",
        "url": "https://example.com/feed.xml",
        "enabled": true,
        "category": "software-engineering"
      }
    ]
  },
  "filtering": {
    "ai_score_threshold": 7.0,
    "time_window_hours": 24,
    "daily_timezone": "UTC",
    "preserve_daily_items": false,
    "max_items": null,
    "category_groups": {},
    "default_group": "other",
    "default_group_limit": null,
    "primary_groups": [],
    "primary_group_min_items": null
  }
}

Also create a .env file with:
ANTHROPIC_API_KEY=your_api_key_here
GITHUB_TOKEN=your_github_token_here (optional but recommended)
"""
    console.print(template)


if __name__ == "__main__":
    main()
