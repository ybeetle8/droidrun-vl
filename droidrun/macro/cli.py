"""
Command-line interface for DroidRun macro replay.
"""

import asyncio
import click
import logging
import os
from typing import Optional
from rich.console import Console
from rich.table import Table
from droidrun.macro.replay import MacroPlayer, replay_macro_file, replay_macro_folder
from droidrun.agent.utils.trajectory import Trajectory
from adbutils import adb

console = Console()


def configure_logging(debug: bool = False):
    """Configure logging for the macro CLI."""
    logger = logging.getLogger("droidrun-macro")
    logger.handlers = []
    
    handler = logging.StreamHandler()
    
    if debug:
        level = logging.DEBUG
        formatter = logging.Formatter("%(levelname)s %(name)s %(message)s", "%H:%M:%S")
    else:
        level = logging.INFO
        formatter = logging.Formatter("%(message)s", "%H:%M:%S")
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    
    return logger


@click.group()
def macro_cli():
    """Replay recorded automation sequences."""
    pass


@macro_cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--device", "-d", help="Device serial number", default=None)
@click.option("--delay", "-t", help="Delay between actions (seconds)", default=1.0, type=float)
@click.option("--start-from", "-s", help="Start from step number (1-based)", default=1, type=int)
@click.option("--max-steps", "-m", help="Maximum steps to execute", default=None, type=int)
@click.option("--debug", is_flag=True, help="Enable debug logging", default=False)
@click.option("--dry-run", is_flag=True, help="Show actions without executing", default=False)
def replay(path: str, device: Optional[str], delay: float, start_from: int, max_steps: Optional[int], debug: bool, dry_run: bool):
    """Replay a macro from a file or trajectory folder."""
    logger = configure_logging(debug)
    
    logger.info("🎬 DroidRun Macro Replay")
    
    # Convert start_from from 1-based to 0-based
    start_from_zero = max(0, start_from - 1)
    
    if device is None:
        logger.info("🔍 Finding connected device...")
        devices = adb.list()
        if not devices:
            raise ValueError("No connected devices found.")
        device = devices[0].serial
        logger.info(f"📱 Using device: {device}")
    else:
        logger.info(f"📱 Using device: {device}")
    
    asyncio.run(_replay_async(path, device, delay, start_from_zero, max_steps, dry_run, logger))


async def _replay_async(path: str, device: str, delay: float, start_from: int, max_steps: Optional[int], dry_run: bool, logger: logging.Logger):
    """Async function to handle macro replay."""
    try:
        if os.path.isfile(path):
            logger.info(f"📄 Loading macro from file: {path}")
            player = MacroPlayer(device_serial=device, delay_between_actions=delay)
            macro_data = player.load_macro_from_file(path)
        elif os.path.isdir(path):
            logger.info(f"📁 Loading macro from folder: {path}")
            player = MacroPlayer(device_serial=device, delay_between_actions=delay)
            macro_data = player.load_macro_from_folder(path)
        else:
            logger.error(f"❌ Invalid path: {path}")
            return
        
        if not macro_data:
            logger.error("❌ Failed to load macro data")
            return
        
        # Show macro information
        description = macro_data.get("description", "No description")
        total_actions = macro_data.get("total_actions", 0)
        version = macro_data.get("version", "unknown")
        
        logger.info("📋 Macro Information:")
        logger.info(f"   Description: {description}")
        logger.info(f"   Version: {version}")
        logger.info(f"   Total actions: {total_actions}")
        logger.info(f"   Device: {device}")
        logger.info(f"   Delay between actions: {delay}s")
        
        if start_from > 0:
            logger.info(f"   Starting from step: {start_from + 1}")
        if max_steps:
            logger.info(f"   Maximum steps: {max_steps}")
        
        if dry_run:
            logger.info("🔍 DRY RUN MODE - Actions will be shown but not executed")
            await _show_dry_run(macro_data, start_from, max_steps, logger)
        else:
            logger.info("▶️  Starting macro replay...")
            success = await player.replay_macro(macro_data, start_from_step=start_from, max_steps=max_steps)
            
            if success:
                logger.info("🎉 Macro replay completed successfully!")
            else:
                logger.error("💥 Macro replay completed with errors")
    
    except Exception as e:
        logger.error(f"💥 Error: {e}")
        if logger.isEnabledFor(logging.DEBUG):
            import traceback
            logger.debug(traceback.format_exc())


async def _show_dry_run(macro_data: dict, start_from: int, max_steps: Optional[int], logger: logging.Logger):
    """Show what actions would be executed in dry run mode."""
    actions = macro_data.get("actions", [])
    
    # Apply filters
    if start_from > 0:
        actions = actions[start_from:]
    if max_steps:
        actions = actions[:max_steps]
    
    logger.info(f"📋 Found {len(actions)} actions to execute:")
    
    table = Table(title="Actions to Execute")
    table.add_column("Step", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Details", style="white")
    table.add_column("Description", style="yellow")
    
    for i, action in enumerate(actions, start=start_from + 1):
        action_type = action.get("action_type", action.get("type", "unknown"))
        details = ""
        
        if action_type == "tap":
            x, y = action.get("x", 0), action.get("y", 0)
            element_text = action.get("element_text", "")
            details = f"({x}, {y}) - '{element_text}'"
        elif action_type == "swipe":
            start_x, start_y = action.get("start_x", 0), action.get("start_y", 0)
            end_x, end_y = action.get("end_x", 0), action.get("end_y", 0)
            details = f"({start_x}, {start_y}) → ({end_x}, {end_y})"
        elif action_type == "input_text":
            text = action.get("text", "")
            details = f"'{text}'"
        elif action_type == "key_press":
            key_name = action.get("key_name", "UNKNOWN")
            details = f"{key_name}"
        
        description = action.get("description", "")
        table.add_row(str(i), action_type, details, description[:50] + "..." if len(description) > 50 else description)
    
    # Still use console for table display as it's structured data
    console.print(table)


@macro_cli.command()
@click.argument("directory", type=click.Path(exists=True), default="trajectories")
@click.option("--debug", is_flag=True, help="Enable debug logging", default=False)
def list(directory: str, debug: bool):
    """List available trajectory folders in a directory."""
    logger = configure_logging(debug)
    
    logger.info(f"📁 Scanning directory: {directory}")
    
    try:
        folders = []
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isdir(item_path):
                macro_file = os.path.join(item_path, "macro.json")
                if os.path.exists(macro_file):
                    # Load macro info
                    try:
                        macro_data = Trajectory.load_macro_sequence(item_path)
                        description = macro_data.get("description", "No description")
                        total_actions = macro_data.get("total_actions", 0)
                        folders.append((item, description, total_actions))
                    except Exception as e:
                        logger.debug(f"Error loading macro from {item}: {e}")
                        folders.append((item, "Error loading", 0))
        
        if not folders:
            logger.info("📭 No trajectory folders found")
            return
        
        logger.info(f"🎯 Found {len(folders)} trajectory(s):")
        
        table = Table(title=f"Available Trajectories in {directory}")
        table.add_column("Folder", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Actions", style="green")
        
        for folder, description, actions in sorted(folders):
            table.add_row(folder, description[:80] + "..." if len(description) > 80 else description, str(actions))
        
        # Still use console for table display as it's structured data
        console.print(table)
        logger.info(f"💡 Use 'droidrun macro replay {directory}/<folder>' to replay a trajectory")
    
    except Exception as e:
        logger.error(f"💥 Error: {e}")
        if logger.isEnabledFor(logging.DEBUG):
            import traceback
            logger.debug(traceback.format_exc())


if __name__ == "__main__":
    macro_cli() 