"""
Configuration Template for MonkeyLogic Auto-Analysis Pipeline.

Copy this file to `config.py` and customize the settings for your setup.
All paths, credentials, and task-specific settings should be defined here.

SETUP INSTRUCTIONS:
1. Copy this file to config.py
2. Fill in your DATA_DIR (where .bhv2 files are stored)
3. Set up Slack credentials (or disable notifications)
4. Configure your analyzer settings
5. Run the pipeline with: python run_analysis.py

For more details, see README.md
"""

import os
from pathlib import Path

# =============================================================================
# PATH CONFIGURATION
# =============================================================================

# Base directory for analysis outputs (plots, cache)
BASE_DIR = Path(__file__).parent

# Directory containing MonkeyLogic .bhv2 data files
# Example: /path/to/your/datafolder/
DATA_DIR = BASE_DIR / "data"

# Local cache directory for processed sessions (.pkl files)
CACHE_DIR = BASE_DIR / "cache"

# Output directory for plots and reports
OUTPUT_DIR = BASE_DIR / "outputs"

# Log file location
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "analysis.log"

# Ensure directories exist
for directory in [CACHE_DIR, OUTPUT_DIR, LOG_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


# =============================================================================
# PLATFORM CONFIGURATION
# =============================================================================

# File extension for MonkeyLogic data files
BHV2_EXTENSION = ".bhv2"

# File watcher settings
WATCHER_POLL_INTERVAL = 10  # seconds between directory checks
WATCHER_MIN_FILE_AGE = 60  # seconds to wait before processing new files


# =============================================================================
# SLACK NOTIFICATION CONFIGURATION
# =============================================================================
# Set SLACK_ENABLED = True and fill in your credentials to enable notifications

SLACK_ENABLED = False  # Set to True to enable Slack notifications

# -----------------------------------------------------------------------------
# To set up Slack notifications:
# 1. Create a Slack App at https://api.slack.com/apps
# 2. Enable "Bot Token" OAuth scope: "chat:write", "files:write"
# 3. Install the app to your workspace
# 4. Copy the Bot Token (starts with xoxb-) and paste below
# 5. Get your Channel ID (right-click channel > Copy link, extract ID)
# -----------------------------------------------------------------------------

SLACK_BOT_TOKEN = "xoxb-YOUR-BOT-TOKEN-HERE"
SLACK_CHANNEL_ID = "YOUR-CHANNEL-ID-HERE"
SLACK_API_URL = "https://slack.com/api/"


# =============================================================================
# ANALYZER CONFIGURATION
# =============================================================================
# Configure your task-specific analysis settings below.
# These are used by the analyzer classes to parse behavioral data.

# Example configuration for a Pavlovian-Instrumental Transfer (PIT) task:
PIT_TASK_CONFIG = {
    # Behavioral event codes (standard MonkeyLogic defaults)
    "trial_types": {
        "pavlovian_code": 90,      # Pavlovian trial indicator
        "instrumental_code": 91,   # Instrumental trial indicator
    },
    "stimulus_codes": {
        "stim1_base": 101,  # First stimulus ID base (101=A, 102=B, 103=C...)
        "stim2_base": 201,  # Second stimulus ID base
    },
    "probability_codes": {
        "stim1_base": 121,  # First stimulus probability base (121=10%, 129=90%)
        "stim2_base": 221,  # Second stimulus probability base
    },
    "position_codes": {
        "stim1_left": 46,   # First stimulus on left
        "stim1_right": 47, # First stimulus on right
        "stim2_left": 146, # Second stimulus on left
        "stim2_right": 147,# Second stimulus on right
    },
    "choice_codes": {
        "left": 42,
        "right": 43,
    },
    "response_codes": {
        "left_validated": 36,
        "right_validated": 37,
    },
    "outcome_codes": {
        "reward": 65,
        "go_signal": 50,
        "break_trial": 98,
    },
    # Hierarchy definition (for PIT/hierarchical learning tasks)
    # Format: list of stimuli in order of value (highest first)
    # e.g., ["A", "B", "C", "D", "E"] for 90/70/50/30/10% probabilities
    "hierarchy": ["A", "B", "C", "D", "E"],
}

# Example configuration for a probabilistic reversal learning task
REVERSAL_LEARNING_CONFIG = {
    "choice_codes": {
        "left": 42,
        "right": 43,
    },
    "response_codes": {
        "left_validated": 36,
        "right_validated": 37,
    },
    "outcome_codes": {
        "reward": 65,
        "go_signal": 50,
        "break_trial": 98,
    },
    "stimulus_codes": {
        "stim_A": 101,
        "stim_B": 102,
        "stim_C": 103,
    },
    "probability_codes": {
        "prob_base": 121,  # 121=10%, 129=90% (or 121-130 for 0-100%)
    },
}


# =============================================================================
# PLOTTING CONFIGURATION
# =============================================================================

PLOT_CONFIG = {
    "dpi": 150,
    "fig_size": (12, 8),
    "style": "seaborn-v0_8-darkgrid",
    "color_palette": "Set2",
}


# =============================================================================
# CACHE SETTINGS
# =============================================================================

# Maximum age of cache files before requiring refresh (days)
CACHE_MAX_AGE_DAYS = 30


# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
