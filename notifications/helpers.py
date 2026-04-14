"""
Notification helpers for formatting Slack messages with analysis metrics.

These functions make it easy to format rich notifications with:
- Session summary stats
- Performance metrics
- Embedded plots

USAGE:
    from notifications.helpers import notify_session_complete
    
    notify_session_complete(
        session_name="260315",
        metrics={"accuracy": 0.85, "n_trials": 100, "mean_rt": 450},
        plot_path="/path/to/plot.png",
        notifier=slack_notifier
    )
"""

from pathlib import Path
from typing import Dict, Optional, Any


def format_session_summary(
    session_name: str,
    metrics: Dict[str, Any],
    include_rt: bool = True,
    include_choices: bool = True
) -> str:
    """
    Format a session summary message.
    
    Args:
        session_name: Name/ID of the session
        metrics: Dict with metric values (accuracy, n_trials, mean_rt, etc.)
        include_rt: Include reaction time in message
        include_choices: Include choice distribution
    
    Returns:
        Formatted message string
    """
    lines = [
        f"*Session Complete: {session_name}*",
        f"• Trials: {metrics.get('n_trials', '?')}",
    ]
    
    # Accuracy
    accuracy = metrics.get('accuracy')
    if accuracy is not None:
        lines.append(f"• Accuracy: {accuracy:.1%}")
    
    # Reward count
    n_rewarded = metrics.get('n_rewarded')
    if n_rewarded is not None:
        lines.append(f"• Rewarded: {n_rewarded}/{metrics.get('n_trials', '?')}")
    
    # RT
    if include_rt:
        mean_rt = metrics.get('mean_rt')
        if mean_rt is not None:
            lines.append(f"• Mean RT: {mean_rt:.0f}ms")
    
    # Choices
    if include_choices:
        left_pct = metrics.get('left_pct')
        if left_pct is not None:
            lines.append(f"• Choices: {left_pct:.0%}L / {metrics.get('right_pct', 1-left_pct):.0%}R")
    
    return "\n".join(lines)


def format_error_message(session_name: str, error: str) -> str:
    """Format an error notification."""
    return f"""
:x: *Analysis Error*

Session: {session_name}
Error: {error}
""".strip()


def format_new_session(session_name: str, task_name: str = "Unknown") -> str:
    """Format a new session detected notification."""
    return f"""
:eyes: *New Session Detected*

_{session_name}_
Task: {task_name}
""".strip()


def notify_session_complete(
    session_name: str,
    metrics: Dict[str, Any],
    plot_path: Optional[str] = None,
    notifier=None,
    include_rt: bool = True,
    include_choices: bool = True
) -> bool:
    """
    Send a session complete notification with metrics and optional plot.
    
    Args:
        session_name: Name/ID of the session
        metrics: Dict with accuracy, n_trials, mean_rt, etc.
        plot_path: Optional path to performance plot
        notifier: SlackNotifier instance (or None to log only)
        include_rt: Include RT in message
        include_choices: Include choice distribution
    
    Returns:
        True if notification sent successfully
    """
    import logging
    logger = logging.getLogger(__name__)
    
    message = format_session_summary(
        session_name, metrics,
        include_rt=include_rt,
        include_choices=include_choices
    )
    
    if notifier is None:
        logger.info(f"Notification (disabled): {message}")
        return False
    
    success = notifier.send_notification(
        message=message,
        file_path=plot_path,
        file_title=f"Performance: {session_name}"
    )
    
    return success


def notify_analysis_error(
    session_name: str,
    error: str,
    notifier=None
) -> bool:
    """
    Send an error notification.
    
    Args:
        session_name: Name of the session that failed
        error: Error message
        notifier: SlackNotifier instance
    
    Returns:
        True if sent successfully
    """
    import logging
    logger = logging.getLogger(__name__)
    
    message = format_error_message(session_name, error)
    
    if notifier is None:
        logger.info(f"Error notification (disabled): {message}")
        return False
    
    return notifier.send_message(message)


# =============================================================================
# BLOCK KIT FORMATTING (for rich Slack messages)
# =============================================================================

def make_blocks_header(title: str, subtitle: Optional[str] = None) -> list:
    """Create header blocks for a Slack message."""
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": title,
                "emoji": True
            }
        }
    ]
    
    if subtitle:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": subtitle
            }
        })
    
    return blocks


def make_metric_block(label: str, value: str, accessory: Optional[dict] = None) -> dict:
    """Create a section block with a metric (label: value)."""
    block = {
        "type": "section",
        "fields": [
            {
                "type": "mrkdwn",
                "text": f"* {label}\n{value}"
            }
        ]
    }
    
    if accessory:
        block["accessory"] = accessory
    
    return block


def make_divider() -> dict:
    """Create a divider block."""
    return {"type": "divider"}


def make_metrics_blocks(metrics: Dict[str, Any]) -> list:
    """
    Create a series of metric blocks from a metrics dict.
    
    Args:
        metrics: Dict like {"Accuracy": "85%", "Trials": "100", ...}
    
    Returns:
        List of Slack block dicts
    """
    blocks = []
    
    # Pair up metrics (2 per row)
    items = list(metrics.items())
    
    for i in range(0, len(items), 2):
        pair = items[i:i+2]
        fields = []
        
        for label, value in pair:
            fields.append({
                "type": "mrkdwn",
                "text": f"*{label}*\n{value}"
            })
        
        blocks.append({
            "type": "section",
            "fields": fields
        })
    
    return blocks


def notify_session_rich(
    session_name: str,
    metrics: Dict[str, Any],
    plot_path: Optional[str] = None,
    notifier=None
) -> bool:
    """
    Send a rich formatted session notification with blocks.
    
    Args:
        session_name: Session name
        metrics: Dict of metrics (accuracy, n_trials, mean_rt, etc.)
        plot_path: Optional path to plot image
        notifier: SlackNotifier instance
    
    Returns:
        True if sent successfully
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Format metric values
    formatted = {}
    if 'accuracy' in metrics:
        formatted['Accuracy'] = f"{metrics['accuracy']:.1%}"
    if 'n_trials' in metrics:
        formatted['Trials'] = str(metrics['n_trials'])
    if 'n_rewarded' in metrics:
        total = metrics.get('n_trials', '?')
        formatted['Rewarded'] = f"{metrics['n_rewarded']}/{total}"
    if 'mean_rt' in metrics and metrics['mean_rt'] is not None:
        formatted['Mean RT'] = f"{metrics['mean_rt']:.0f}ms"
    if 'left_pct' in metrics:
        l = metrics['left_pct'] * 100
        r = (1 - metrics['left_pct']) * 100
        formatted['Choices'] = f"{l:.0f}%L / {r:.0f}%R"
    
    # Build blocks
    blocks = []
    blocks.extend(make_blocks_header(
        f"Session Complete: {session_name}",
        "Analysis finished successfully"
    ))
    blocks.append(make_divider())
    blocks.extend(make_metrics_blocks(formatted))
    
    if plot_path and Path(plot_path).exists():
        blocks.append(make_divider())
        # Image block
        blocks.append({
            "type": "image",
            "image_url": f"file://{plot_path}",
            "alt_text": f"Performance plot for {session_name}"
        })
    
    if notifier is None:
        logger.info(f"Rich notification (disabled): {formatted}")
        return False
    
    return notifier.send_message(
        text=f"Session complete: {session_name}",
        blocks=blocks
    )
