# MonkeyLogic Auto-Analysis Pipeline

Generic infrastructure for automated behavioral data analysis with MonkeyLogic.

## What This Is

A reusable framework for automatically detecting new MonkeyLogic `.bhv2` files and running your custom analysis pipeline on them. Includes:

- **File watcher** - monitors data directory, waits for files to finish writing, tracks processed files
- **Slack notifications** - sends messages and plot attachments when analysis completes
- **Clean structure** - plug in your own analysis code without touching the infrastructure

## What This Is NOT

This is **not** a complete analysis pipeline for any specific task. Your MonkeyLogic task uses unique behavioral codes, trial structures, and metrics. The analysis portion is intentionally left as a placeholder that you replace with your own code.

## Included Tools

### `mlread.py` - Reading .bhv2 Files

Reads MonkeyLogic binary files and returns structured Python data:

```python
from mlread import mlread, find_code_times

data, config, record, fname = mlread("session.bhv2")

# data is a list of trials
for trial_idx, trial in enumerate(data):
    codes = trial['BehavioralCodes']
    print(f"Trial {trial_idx}: {codes['CodeNumbers']}")
```

To find what codes your task uses, add `--inspect` or just print the codes for a few trials.

### `example_analysis.py` - Working Example

A minimal but complete analysis showing:
1. Reading .bhv2 files
2. Parsing behavioral codes
3. Computing accuracy and RT
4. Creating a plot

Run it directly on any .bhv2 file to see it work.

## Quick Start

### 1. Clone/Fork this repository

```bash
git clone https://github.com/yourusername/monkeylogic-autoanalysis.git
cd monkeylogic-autoanalysis
```

### 2. Copy and configure

```bash
cp config_template.py config.py
# Edit config.py with your settings
```

In `config.py`, set your data directory:

```python
DATA_DIR = "/path/to/your/monkeylogic/data"
```

### 3. Install dependencies

```bash
# With conda/mamba:
conda env create -f environment.yml
conda activate monkeylogic_env

# Or with pip:
pip install numpy pandas matplotlib h5py requests seaborn
```

### 4. Run analysis on existing files

```bash
python run_analysis.py --once
```

### 5. Start watching for new files

```bash
python run_analysis.py --watch
```

## Configuration

Edit `config.py` to customize:

| Setting | Description | Default |
|---------|-------------|---------|
| `DATA_DIR` | Directory containing .bhv2 files | (required) |
| `CACHE_DIR` | Local cache for processed sessions | `./cache` |
| `OUTPUT_DIR` | Where plots are saved | `./outputs` |
| `WATCHER_POLL_INTERVAL` | Seconds between directory checks | 10 |
| `WATCHER_MIN_FILE_AGE` | Seconds before processing new file | 60 |

## Slack Notifications

### Setup

1. Create a Slack App at https://api.slack.com/apps

2. Click **"Create New App"** → **"From scratch"**

3. Under **OAuth & Permissions**, add these scopes:
   - `chat:write`
   - `files:write`

4. Click **"Install to Workspace"** and copy the **Bot Token** (starts with `xoxb-`)

5. Get your **Channel ID**:
   - Right-click your channel → **Copy link**
   - The ID is the last part (e.g., `C01ABC23456`)

6. In `config.py`:
   ```python
   SLACK_ENABLED = True
   SLACK_BOT_TOKEN = "xoxb-123-..."
   SLACK_CHANNEL_ID = "C01ABC23456"
   ```

### Testing

```python
from notifications.slack import SlackNotifier

notifier = SlackNotifier(bot_token="xoxb-...", channel_id="C...")
notifier.send_message("Test message!")
notifier.upload_file("/path/to/plot.png", "My Plot")
```

### Sending Metric Notifications

The `notifications.helpers` module provides easy formatting:

```python
from notifications import SlackNotifier
from notifications.helpers import notify_session_complete

notifier = SlackNotifier(...)

# Simple notification with metrics
metrics = {
    "accuracy": 0.85,      # 0.85 → "85.0%"
    "n_trials": 100,
    "n_rewarded": 85,
    "mean_rt": 450,        # → "450ms"
    "left_pct": 0.6,       # → "60%L / 40%R"
}

notify_session_complete(
    session_name="260315",
    metrics=metrics,
    plot_path="/path/to/plot.png",
    notifier=notifier
)
```

**Message format:**
```
*Session Complete: 260315*
• Trials: 100
• Accuracy: 85.0%
• Rewarded: 85/100
• Mean RT: 450ms
• Choices: 60%L / 40%R
```

### Rich Block Formatting

For fancy Slack messages with blocks:

```python
from notifications.helpers import notify_session_rich

notify_session_rich(
    session_name="260315",
    metrics=metrics,
    plot_path="/path/to/plot.png",
    notifier=notifier
)
```

This creates a rich message with header, metrics grid, and embedded image.

## Adding Your Analysis

### Quick Start with `example_analysis.py`

Before customizing, try the working example:

```bash
# Install dependencies
pip install numpy matplotlib

# Run on a single file
python example_analysis.py /path/to/session.bhv2
```

This creates a `session_performance.png` plot and shows the basic pattern.

### Full Integration

**Pro tip:** Design your MonkeyLogic task to use `EventMarker` liberally. The more codes you send, the easier analysis becomes. Common codes to track:
- Trial type / condition markers
- Stimulus identity and positions
- Choice and outcome
- Eye tracking events (fixation acquire, break, etc.)
- Block transitions

Base your analysis around these codes rather than inferring from timing or other heuristics.

Find the `run_session_analysis()` function in `run_analysis.py`. Replace the placeholder with your code:

```python
def run_session_analysis(bhv2_file: str, notifier: SlackNotifier) -> bool:
    # 1. Read .bhv2 file
    #    from mlread import mlread
    #    data, config, record = mlread(bhv2_file)
    
    # 2. Parse behavioral codes
    #    trials = parse_behavioral_codes(data, your_config)
    
    # 3. Compute your metrics
    #    accuracy = compute_accuracy(trials)
    
    # 4. Generate plots
    #    plot_path = OUTPUT_DIR / f"{session_name}_performance.png"
    #    create_plot(trials, accuracy, plot_path)
    
    # 5. Notify
    #    notifier.send_notification(
    #        f"Session complete! Accuracy: {accuracy:.1%}",
    #        file_path=str(plot_path)
    #    )
    
    return True
```

## File Watcher Features

### State Persistence

The watcher tracks processed files in `.watcher_state.json`. If you restart the watcher, it won't re-process already-analyzed files. To force re-analysis:

```bash
python run_analysis.py --reset-state
```

### Graceful Shutdown

**Option 1:** Press Ctrl+C

**Option 2:** Create a `watcher.stop` file in your data directory:
```bash
touch /path/to/data/watcher.stop
```

### System Tray Icon

Install optional dependencies for a monkey face system tray icon:
```bash
conda install -c conda-forge pystray pillow
# or
pip install pystray Pillow
```

Enable in `FileWatcher` initialization:
```python
watcher = FileWatcher(..., enable_tray=True)
```

When enabled, you'll see a 🐵 monkey icon in your system tray while watching:
- **Click icon** to see menu options
- **"Open Log"** - opens the log file  
- **"Stop Watcher"** - gracefully stops the watcher

The icon is created programmatically (see `utils/tray_icon.py`) - no external image files needed.

## Common Issues

### "No .bhv2 files found"

Check that `DATA_DIR` points to the correct folder containing `.bhv2` files.

### Files not being processed

Files younger than `WATCHER_MIN_FILE_AGE` (default 60s) are skipped. This prevents processing files that are still being written. Use `--reset-state` to re-trigger analysis.

### Slack notifications not working

1. Verify `SLACK_ENABLED = True`
2. Check your bot token is valid (not expired)
3. Ensure the bot is added to your channel
4. Check logs for API error details

## Dependencies

**Required:**
- Python 3.8+
- numpy
- pandas
- matplotlib
- h5py (for reading .bhv2 files): `pip install h5py`
- requests (for Slack notifications)

**Optional:**
- `pystray` + `Pillow` (system tray icon)

## Project Structure

```
monkeylogic-autoanalysis/
├── README.md              # This file
├── PATTERNS.md            # Common patterns & conventions
├── environment.yml        # Conda environment
├── config_template.py     # Configuration template
├── config.py              # Your settings (not in git)
├── run_analysis.py        # Main entry point
├── file_watcher.py        # Directory monitoring
├── mlread.py              # .bhv2 file reader
├── example_analysis.py    # Minimal working example
├── notifications/
│   ├── __init__.py
│   ├── slack.py           # Slack integration
│   └── helpers.py         # Notification formatting
├── utils/                 # (placeholder)
├── analyzers/             # (placeholder)
└── plots/                 # (placeholder)
```

## Adapting Existing Code

If you have an existing MATLAB analysis pipeline, you can call it from Python:

```python
def run_matlab_analysis(bhv2_file):
    import subprocess
    result = subprocess.run([
        "matlab", "-batch",
        f"mlread('{bhv2_file}'); your_analysis;"
    ], capture_output=True)
    return result.returncode == 0
```

Or use `mlread.py` from this project (Python implementation of MATLAB's mlread.m) to read .bhv2 files directly in Python.

## Common Workflows

### Single Session Analysis

```bash
python example_analysis.py /path/to/session.bhv2 --output-dir ./outputs
```

### Batch Process All Sessions

```python
from pathlib import Path
from example_analysis import analyze_session
from notifications import SlackNotifier

data_dir = Path("/path/to/data")
notifier = SlackNotifier(...)

for bhv2_file in sorted(data_dir.glob("*.bhv2")):
    print(f"Processing {bhv2_file.name}...")
    analyze_session(str(bhv2_file), output_dir="outputs", notifier=notifier)
```

### Continuous Watching

```bash
# Start watcher (runs until Ctrl+C or stop file)
python run_analysis.py --watch

# From another terminal, gracefully stop:
touch /path/to/data/watcher.stop
```

## Further Reading

- [PATTERNS.md](PATTERNS.md) - Common patterns and conventions:
  - Session caching (avoid re-parsing .bhv2 files)
  - Conditions files (stimulus mapping separate from .bhv2)
  - Block structure (multi-block sessions)
  - Cross-session aggregation
  - Excluding invalid trials
  - RT calculation
  - Hierarchy analysis (for PIT tasks)

## Quick Reference

| Task | Command |
|------|---------|
| Analyze one file | `python example_analysis.py file.bhv2` |
| Watch for new files | `python run_analysis.py --watch` |
| Reset processed state | `python run_analysis.py --reset-state` |
| Stop watcher | `touch data/watcher.stop` |

## Related Projects

[monkeylogic_slackbot](https://github.com/doublezz10/monkeylogic_slackbot) - Real-time MonkeyLogic file monitoring with Slack alerts. Watches your MonkeyLogic data folder and sends Slack notifications when sessions complete, with the ability to copy files to remote locations.

## License

MIT - do whatever you want with it.
