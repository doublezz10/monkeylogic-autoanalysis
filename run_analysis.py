#!/usr/bin/env python3
"""
Main entry point for MonkeyLogic auto-analysis pipeline.

This script demonstrates how to wire together:
- FileWatcher: monitors data directory for new .bhv2 files
- Your analysis: placeholder for your specific processing
- SlackNotifier: sends notifications when analysis completes

USAGE:
    # As a module (for integration)
    from run_analysis import setup_pipeline
    setup_pipeline()
    
    # From command line (standalone mode)
    python run_analysis.py --watch

CUSTOMIZATION:
    Replace the `run_session_analysis()` function with your own analysis code.
    See the placeholder section marked with "[YOUR ANALYSIS CODE HERE]".
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Configuration - import from config_template (copy to config.py)
try:
    from config import (
        DATA_DIR, CACHE_DIR, OUTPUT_DIR, LOG_FILE,
        WATCHER_POLL_INTERVAL, WATCHER_MIN_FILE_AGE,
        SLACK_ENABLED, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    )
except ImportError:
    print("ERROR: config.py not found. Copy config_template.py to config.py and configure it.")
    sys.exit(1)

from file_watcher import FileWatcher
from notifications.slack import SlackNotifier


# =============================================================================
# LOGGING SETUP
# =============================================================================

def setup_logging():
    """Configure logging to file and console."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)


# =============================================================================
# NOTIFICATION SETUP
# =============================================================================

def setup_notifier() -> SlackNotifier:
    """Initialize Slack notifier if configured."""
    if not SLACK_ENABLED:
        logging.info("Slack notifications disabled")
        return SlackNotifier(bot_token=None, channel_id=None)
    
    notifier = SlackNotifier(
        bot_token=SLACK_BOT_TOKEN,
        channel_id=SLACK_CHANNEL_ID
    )
    
    if notifier.enabled:
        logging.info("Slack notifications enabled")
    else:
        logging.warning("Slack notifier failed to initialize")
    
    return notifier


# =============================================================================
# YOUR ANALYSIS CODE HERE
# =============================================================================
# Replace this function with your own analysis pipeline

def run_session_analysis(bhv2_file: str, notifier: SlackNotifier) -> bool:
    """
    Run analysis on a single session's .bhv2 file.
    
    This is a PLACEHOLDER - replace with your specific analysis code.
    
    Your analysis should:
    1. Read the .bhv2 file (see mlread.py or use MATLAB's mlread)
    2. Parse behavioral codes to extract trial information
    3. Compute your metrics (accuracy, RT, learning curves, etc.)
    4. Generate plots and save to OUTPUT_DIR
    5. Return True on success, False on failure
    
    Args:
        bhv2_file: Path to .bhv2 file to analyze
        notifier: SlackNotifier instance for sending notifications
    
    Returns:
        True if analysis succeeded, False otherwise
    """
    logger = logging.getLogger(__name__)
    session_name = Path(bhv2_file).stem
    
    logger.info(f"Starting analysis for {session_name}")
    
    try:
        # ---------------------------------------------------------------------
        # [YOUR ANALYSIS CODE HERE]
        # ---------------------------------------------------------------------
        # Example structure:
        #
        # 1. Read the data
        #    from mlread import mlread
        #    data, config, record = mlread(bhv2_file)
        #
        # 2. Parse into trials
        #    trials = parse_behavioral_codes(data)
        #
        # 3. Compute metrics
        #    accuracy = compute_accuracy(trials)
        #    rt = compute_reaction_times(trials)
        #
        # 4. Generate plots
        #    plot_path = OUTPUT_DIR / f"{session_name}_performance.png"
        #    create_performance_plot(trials, accuracy, rt, plot_path)
        #
        # 5. Send notification
        #    notifier.send_notification(
        #        f"Session complete! Accuracy: {accuracy:.1%}",
        #        file_path=str(plot_path)
        #    )
        #
        # ---------------------------------------------------------------------
        
        # Placeholder: just log and simulate success
        logger.info(f"[PLACEHOLDER] Would analyze {bhv2_file}")
        logger.info(f"  - Read .bhv2 file")
        logger.info(f"  - Parse behavioral codes")
        logger.info(f"  - Compute metrics")
        logger.info(f"  - Generate plots")
        logger.info(f"  - Save to {OUTPUT_DIR}")
        
        # Simulate work
        import time
        time.sleep(1)
        
        # Send notification
        notifier.send_notification(
            f"Analysis complete for {session_name}",
            file_path=None  # Add your plot path here
        )
        
        logger.info(f"Analysis complete for {session_name}")
        return True
        
    except Exception as e:
        logger.error(f"Analysis failed for {session_name}: {e}", exc_info=True)
        notifier.send_notification(f"Analysis failed for {session_name}: {e}")
        return False


# =============================================================================
# FILE WATCHER CALLBACK
# =============================================================================

def analysis_callback(bhv2_file: str):
    """
    Callback for FileWatcher - runs analysis on detected file.
    
    Args:
        bhv2_file: Path to newly detected .bhv2 file
    """
    logger = logging.getLogger(__name__)
    logger.info(f"File detected: {bhv2_file}")
    
    # Create notifier here to avoid issues with pickling
    notifier = setup_notifier()
    
    run_session_analysis(bhv2_file, notifier)


# =============================================================================
# PIPELINE SETUP
# =============================================================================

def setup_pipeline():
    """
    Set up the complete analysis pipeline.
    
    Returns:
        Configured FileWatcher instance (call .start() or .run() on it)
    """
    logger = logging.getLogger(__name__)
    
    # Ensure directories exist
    for directory in [DATA_DIR, CACHE_DIR, OUTPUT_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Data directory: {DATA_DIR}")
    logger.info(f"Cache directory: {CACHE_DIR}")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    
    # Create notifier
    notifier = setup_notifier()
    
    # Create watcher
    watcher = FileWatcher(
        watch_dir=str(DATA_DIR),
        analysis_func=analysis_callback,
        poll_interval=WATCHER_POLL_INTERVAL,
        min_file_age=WATCHER_MIN_FILE_AGE,
        file_extension=".bhv2"
    )
    
    return watcher


# =============================================================================
# STANDALONE MODE
# =============================================================================

def run_once(bhv2_file: str = None):
    """Run analysis on a single file (no watching)."""
    logger = logging.getLogger(__name__)
    
    notifier = setup_notifier()
    
    if bhv2_file:
        run_session_analysis(bhv2_file, notifier)
    else:
        # Find most recent .bhv2 file
        bhv2_files = sorted(DATA_DIR.glob("*.bhv2"), key=lambda p: p.stat().st_mtime)
        if bhv2_files:
            latest = bhv2_files[-1]
            logger.info(f"Most recent file: {latest}")
            run_session_analysis(str(latest), notifier)
        else:
            logger.warning(f"No .bhv2 files found in {DATA_DIR}")


def run_watcher():
    """Run the file watcher continuously."""
    logger = logging.getLogger(__name__)
    
    watcher = setup_pipeline()
    
    logger.info("Starting file watcher...")
    logger.info("Press Ctrl+C to stop, or create a watcher.stop file")
    
    try:
        watcher.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        watcher.stop()


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="MonkeyLogic Auto-Analysis Pipeline")
    parser.add_argument("--watch", action="store_true", help="Run file watcher continuously")
    parser.add_argument("--once", metavar="FILE", help="Run analysis on single file and exit")
    parser.add_argument("--reset-state", action="store_true", help="Clear processed file history")
    
    args = parser.parse_args()
    
    logger = setup_logging()
    
    if args.reset_state:
        state_file = DATA_DIR / ".watcher_state.json"
        if state_file.exists():
            state_file.unlink()
            print(f"State cleared: {state_file}")
        else:
            print("No state file found")
        return
    
    if args.once:
        run_once(args.once)
    elif args.watch:
        run_watcher()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
