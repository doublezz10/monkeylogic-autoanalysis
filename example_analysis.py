#!/usr/bin/env python3
"""
Minimal working example - demonstrates how to analyze MonkeyLogic data.

This shows the basic pattern for:
1. Reading .bhv2 files with mlread
2. Parsing behavioral codes to extract trial info
3. Computing simple metrics
4. Creating a plot
5. Sending Slack notification

This is meant to be a starting template - your task will need different codes!

USAGE:
    python example_analysis.py /path/to/session.bhv2
    
    # Or import and adapt:
    from example_analysis import analyze_session
    analyze_session("/path/to/session.bhv2", output_dir=".")
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import matplotlib.pyplot as plt

from mlread import mlread, find_code_times, get_behavioral_codes
from notifications.helpers import notify_session_complete, notify_analysis_error


# =============================================================================
# CONFIGURATION - ADAPT THESE FOR YOUR TASK
# =============================================================================
# IMPORTANT: These codes are examples. You MUST identify the codes your task uses.
# Use mlread's --inspect mode or print behavioral codes to find them.

# Event codes for YOUR task (replace these!)
TASK_CONFIG = {
    # Which code numbers represent choices
    "codes": {
        "left_choice": 42,       # Code for left response
        "right_choice": 43,      # Code for right response
        "reward": 65,            # Code for reward delivery
        "go_signal": 50,        # Code for go signal (stimuli on)
        "break_trial": 98,      # Code for break/incorrect trial
    },
    
    # Which codes indicate stimulus identities (varies by task!)
    "stim_codes": {
        101: "A",
        102: "B", 
        103: "C",
        104: "D",
        105: "E",
    },
    
    # Reaction time: time between go_signal and choice
    "use_rt_validation": True,
    "rt_valid_code": 36,  # Validated response (use instead of raw choice)
}


# =============================================================================
# DATA PARSING FUNCTIONS
# =============================================================================

def extract_trial_info(trial_data: List[Dict], config: Dict) -> List[Dict]:
    """
    Parse trial data into structured format.
    
    Args:
        trial_data: List of trial dicts from mlread
        config: Task configuration with event codes
    
    Returns:
        List of dicts with parsed trial information
    """
    trials = []
    codes = config["codes"]
    
    for trial_idx, trial in enumerate(trial_data):
        bc = trial.get("BehavioralCodes", {})
        code_nums = bc.get("CodeNumbers", [])
        code_times = bc.get("CodeTimes", [])
        
        # Build code -> time lookup for this trial
        code_map = dict(zip(code_nums, code_times))
        
        # Extract basic info
        trial_info = {
            "trial_idx": trial_idx,
            "trial_error": trial.get("TrialError", 0),
            "block": trial.get("BlockCount", 0),
            "is_break": codes["break_trial"] in code_nums,
        }
        
        # Extract choice
        if codes["left_choice"] in code_nums:
            trial_info["choice"] = "left"
        elif codes["right_choice"] in code_nums:
            trial_info["choice"] = "right"
        else:
            trial_info["choice"] = None
        
        # Extract reward
        trial_info["reward"] = codes["reward"] in code_nums
        
        # Extract reaction time (time from go signal to response)
        if codes["go_signal"] in code_map and trial_info["choice"]:
            go_time = code_map[codes["go_signal"]]
            # Find response time (when choice code occurred)
            choice_code = codes["left_choice"] if trial_info["choice"] == "left" else codes["right_choice"]
            if choice_code in code_map:
                trial_info["rt"] = code_map[choice_code] - go_time
            else:
                trial_info["rt"] = None
        else:
            trial_info["rt"] = None
        
        # Extract stimulus info (if applicable)
        # Look for stim codes in this trial
        stim_info = {k: v for k, v in codes.items() if k in code_nums}
        
        trials.append(trial_info)
    
    return trials


def compute_session_metrics(trials: List[Dict]) -> Dict:
    """
    Compute summary metrics for a session.
    
    Args:
        trials: List of parsed trial info dicts
    
    Returns:
        Dict with summary metrics
    """
    # Filter to completed trials (non-break)
    completed = [t for t in trials if not t["is_break"]]
    
    if not completed:
        return {"n_trials": 0, "accuracy": 0, "mean_rt": None}
    
    # Accuracy (rewarded / completed)
    n_rewarded = sum(1 for t in completed if t["reward"])
    accuracy = n_rewarded / len(completed) if completed else 0
    
    # Mean RT for rewarded trials
    rts = [t["rt"] for t in completed if t["rt"] is not None]
    mean_rt = np.mean(rts) if rts else None
    
    # Choice distribution
    choices = [t["choice"] for t in completed if t["choice"]]
    n_left = sum(1 for c in choices if c == "left")
    left_pct = n_left / len(choices) if choices else 0.5
    
    return {
        "n_trials": len(completed),
        "n_break": len(trials) - len(completed),
        "n_rewarded": n_rewarded,
        "accuracy": accuracy,
        "mean_rt": mean_rt,
        "left_pct": left_pct,
        "right_pct": 1 - left_pct,
    }


def compute_learning_curve(trials: List[Dict], window_size: int = 10) -> Tuple[List, List]:
    """
    Compute accuracy over rolling window.
    
    Args:
        trials: List of parsed trial info
        window_size: Number of trials per window
    
    Returns:
        Tuple of (trial_numbers, accuracy_values)
    """
    completed = [t for t in trials if not t["is_break"]]
    
    trial_nums = []
    accuracies = []
    
    for i in range(len(completed) - window_size + 1):
        window = completed[i:i + window_size]
        acc = sum(t["reward"] for t in window) / window_size
        
        # Use midpoint trial number
        trial_nums.append(i + window_size // 2)
        accuracies.append(acc)
    
    return trial_nums, accuracies


# =============================================================================
# PLOTTING
# =============================================================================

def create_performance_plot(
    trials: List[Dict],
    metrics: Dict,
    output_path: Optional[Path] = None
) -> str:
    """
    Create a simple performance plot.
    
    Creates a 2-panel figure:
    - Top: Learning curve (accuracy over trials)
    - Bottom: Choice distribution (pie chart)
    
    Args:
        trials: List of parsed trial info
        metrics: Session metrics dict
        output_path: Where to save the figure
    
    Returns:
        Path to saved figure
    """
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    
    # Panel 1: Learning curve
    ax1 = axes[0]
    trial_nums, accuracies = compute_learning_curve(trials)
    
    if trial_nums:
        ax1.plot(trial_nums, accuracies, 'b-', linewidth=2, alpha=0.7)
        ax1.axhline(y=0.5, color='gray', linestyle='--', alpha=0.5, label='Chance')
        ax1.axhline(y=0.8, color='green', linestyle='--', alpha=0.5, label='80%')
    
    ax1.set_xlabel('Trial Number')
    ax1.set_ylabel('Accuracy (rolling 10)')
    ax1.set_title(f'Learning Curve')
    ax1.set_ylim(0, 1)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Panel 2: Choice distribution
    ax2 = axes[1]
    labels = ['Left', 'Right']
    sizes = [metrics['left_pct'], metrics['right_pct']]
    colors = ['#3498db', '#e74c3c']
    
    if sum(sizes) > 0:
        ax2.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    ax2.set_title(f'Choice Distribution\n(n={metrics["n_trials"]} trials)')
    
    # Overall title
    fig.suptitle(f'Session Performance: {metrics["n_trials"]} trials, {metrics["accuracy"]:.1%} accuracy', 
                 fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    
    # Save
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        return str(output_path)
    else:
        plt.show()
        return ""


# =============================================================================
# MAIN ANALYSIS FUNCTION
# =============================================================================

def analyze_session(
    bhv2_file: str,
    output_dir: str = ".",
    task_config: Optional[Dict] = None,
    notifier=None
) -> Dict:
    """
    Analyze a single session.
    
    This is the main entry point - call this for each session.
    
    Args:
        bhv2_file: Path to .bhv2 file
        output_dir: Directory for output plots
        task_config: Optional override for task configuration
        notifier: SlackNotifier instance for notifications
    
    Returns:
        Dict with analysis results
    """
    logger = logging.getLogger(__name__)
    config = task_config or TASK_CONFIG
    output_dir = Path(output_dir)
    
    session_name = Path(bhv2_file).stem
    logger.info(f"Analyzing {session_name}")
    
    try:
        # 1. Read the data
        trial_data, mlconfig, trial_record, filename = mlread(bhv2_file)
        logger.info(f"  Read {len(trial_data)} trials")
        
        # 2. Parse trials
        trials = extract_trial_info(trial_data, config)
        logger.info(f"  Parsed {len(trials)} trials")
        
        # 3. Compute metrics
        metrics = compute_session_metrics(trials)
        logger.info(f"  Accuracy: {metrics['accuracy']:.1%}")
        logger.info(f"  Mean RT: {metrics['mean_rt']:.0f}ms" if metrics['mean_rt'] else "  Mean RT: N/A")
        
        # 4. Create plot
        plot_path = output_dir / f"{session_name}_performance.png"
        create_performance_plot(trials, metrics, plot_path)
        logger.info(f"  Saved plot: {plot_path}")
        
        # 5. Send notification with metrics and plot
        notify_session_complete(
            session_name=session_name,
            metrics=metrics,
            plot_path=str(plot_path),
            notifier=notifier
        )
        
        return {
            "success": True,
            "session": session_name,
            "metrics": metrics,
            "plot_path": str(plot_path)
        }
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        notify_analysis_error(session_name, str(e), notifier)
        return {
            "success": False,
            "session": session_name,
            "error": str(e)
        }


# =============================================================================
# COMMAND LINE
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    parser = argparse.ArgumentParser(description="Minimal MonkeyLogic analysis example")
    parser.add_argument("bhv2_file", help="Path to .bhv2 file")
    parser.add_argument("--output-dir", "-o", default=".", help="Output directory")
    
    args = parser.parse_args()
    
    if not Path(args.bhv2_file).exists():
        print(f"File not found: {args.bhv2_file}")
        sys.exit(1)
    
    result = analyze_session(args.bhv2_file, args.output_dir)
    
    if result["success"]:
        print(f"\n✓ Analysis complete!")
        print(f"  Plot: {result['plot_path']}")
    else:
        print(f"\n✗ Analysis failed: {result['error']}")
        sys.exit(1)
