"""Notifications package for MonkeyLogic auto-analysis pipeline."""

from .slack import SlackNotifier
from .helpers import (
    notify_session_complete,
    notify_analysis_error,
    notify_session_rich,
    format_session_summary,
    format_error_message,
)

__all__ = [
    "SlackNotifier",
    "notify_session_complete",
    "notify_analysis_error",
    "notify_session_rich",
    "format_session_summary",
    "format_error_message",
]
