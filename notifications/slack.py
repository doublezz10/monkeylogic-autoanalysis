"""
Slack notification module for MonkeyLogic auto-analysis pipeline.

Handles sending text messages and file uploads to Slack channels.

SETUP INSTRUCTIONS:
    1. Create a Slack App at https://api.slack.com/apps
    2. Enable "Bot Token" OAuth scope: "chat:write", "files:write"
    3. Install the app to your workspace
    4. Copy the Bot Token (starts with xoxb-) 
    5. Get your Channel ID (right-click channel > Copy link, extract ID)
    6. Set SLACK_BOT_TOKEN and SLACK_CHANNEL_ID in config.py

USAGE:
    from notifications.slack import SlackNotifier
    
    notifier = SlackNotifier(
        bot_token="xoxb-...",
        channel_id="C1234567890"
    )
    
    notifier.send_message("Session 42 complete! Accuracy: 85%")
    notifier.send_file("/path/to/plot.png", "Learning curves for today")
    notifier.send_notification("Analysis complete", "/path/to/plot.png")
"""

import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class SlackNotifier:
    """
    Sends notifications to Slack via Web API.
    
    Supports:
    - Text messages with markdown formatting
    - File uploads with captions
    - Automatic message + file combinations
    
    Attributes:
        bot_token: Slack OAuth bot token (xoxb-...)
        channel_id: Target channel ID (C...)
        api_url: Slack API base URL
    """
    
    def __init__(
        self,
        bot_token: Optional[str] = None,
        channel_id: Optional[str] = None,
        api_url: str = "https://slack.com/api/"
    ):
        self.bot_token = bot_token or os.getenv("SLACK_BOT_TOKEN")
        self.channel_id = channel_id or os.getenv("SLACK_CHANNEL_ID")
        self.api_url = api_url
        
        if not self.bot_token or not self.channel_id:
            logger.warning("Slack credentials not configured - notifications disabled")
            self._enabled = False
        elif self.bot_token == "xoxb-YOUR-BOT-TOKEN-HERE":
            logger.warning("Slack placeholder token detected - notifications disabled")
            self._enabled = False
        else:
            self._enabled = True
            logger.info(f"Slack notifications enabled for channel {self.channel_id}")
    
    @property
    def enabled(self) -> bool:
        """Check if Slack notifications are enabled."""
        return self._enabled
    
    def _make_request(self, endpoint: str, data: dict) -> dict:
        """Make authenticated request to Slack API."""
        import requests
        
        url = f"{self.api_url}{endpoint}"
        headers = {"Authorization": f"Bearer {self.bot_token}"}
        
        try:
            response = requests.post(url, headers=headers, data=data, timeout=30)
            result = response.json()
            
            if not result.get("ok"):
                logger.error(f"Slack API error: {result.get('error', 'Unknown')}")
                return {"ok": False, "error": result.get("error")}
            
            return result
        except Exception as e:
            logger.error(f"Slack request failed: {e}")
            return {"ok": False, "error": str(e)}
    
    def send_message(self, text: str, blocks: Optional[list] = None) -> bool:
        """
        Send a text message to the configured channel.
        
        Args:
            text: Message text (supports basic markdown-like formatting)
            blocks: Optional Slack block kit format for rich messages
        
        Returns:
            True if successful, False otherwise
        """
        if not self._enabled:
            logger.info(f"Slack message (disabled): {text[:50]}...")
            return False
        
        data = {
            "channel": self.channel_id,
            "text": text,
            "unfurl_links": False
        }
        
        if blocks:
            data["blocks"] = blocks
        
        result = self._make_request("chat.postMessage", data)
        
        if result.get("ok"):
            logger.info(f"Slack message sent: {text[:50]}...")
            return True
        else:
            logger.error(f"Failed to send Slack message: {result.get('error')}")
            return False
    
    def get_upload_url(self, filename: str, file_type: str = "png") -> Optional[dict]:
        """
        Get a temporary upload URL for a file.
        
        Args:
            filename: Name of file to upload
            file_type: MIME type (e.g., "png", "pdf")
        
        Returns:
            Dict with "upload_url" and "file_id" if successful
        """
        if not self._enabled:
            return None
        
        data = {
            "filename": filename,
            "length": os.path.getsize(filename),
            "initial_comment": "",
            "channels": self.channel_id
        }
        
        # Determine content type
        content_types = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "pdf": "application/pdf",
            "txt": "text/plain"
        }
        data["content_type"] = content_types.get(file_type, "application/octet-stream")
        
        result = self._make_request("files.getUploadURLExternal", data)
        
        if result.get("ok"):
            return {
                "upload_url": result.get("upload_url"),
                "file_id": result.get("file_id")
            }
        return None
    
    def upload_file(self, file_path: str, title: Optional[str] = None) -> bool:
        """
        Upload a file to Slack.
        
        Args:
            file_path: Path to file to upload
            title: Optional title/caption
        
        Returns:
            True if successful, False otherwise
        """
        if not self._enabled:
            logger.info(f"Slack upload (disabled): {file_path}")
            return False
        
        file_path = Path(file_path)
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return False
        
        # Get upload URL
        upload_info = self.get_upload_url(file_path.name, file_path.suffix[1:])
        if not upload_info:
            return False
        
        # Upload file content
        import requests
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.name, f)}
                response = requests.post(
                    upload_info['upload_url'],
                    files=files,
                    timeout=60
                )
            
            if response.status_code != 200:
                logger.error(f"File upload failed: {response.status_code}")
                return False
            
            # Complete the upload
            result = self._make_request("files.completeUploadExternal", {
                "files": [{
                    "id": upload_info['file_id'],
                    "title": title or file_path.name
                }],
                "channels": self.channel_id
            })
            
            if result.get("ok"):
                logger.info(f"Slack file uploaded: {file_path.name}")
                return True
            else:
                logger.error(f"Failed to complete upload: {result.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"File upload error: {e}")
            return False
    
    def send_notification(
        self,
        message: str,
        file_path: Optional[str] = None,
        file_title: Optional[str] = None
    ) -> bool:
        """
        Send a message with optional file attachment.
        
        Combines send_message and upload_file into one operation.
        
        Args:
            message: Text message to send
            file_path: Optional path to file to upload and attach
            file_title: Optional title for uploaded file
        
        Returns:
            True if all operations successful, False otherwise
        """
        if not self._enabled:
            logger.info(f"Slack notification (disabled): {message}")
            return False
        
        success = True
        
        # Send message first
        if not self.send_message(message):
            success = False
        
        # Upload file if provided
        if file_path and os.path.exists(file_path):
            if not self.upload_file(file_path, file_title):
                success = False
        
        return success


# =============================================================================
# NOTIFICATION TEMPLATES
# =============================================================================
# Pre-built message templates for common notification types

def session_complete_template(
    session_name: str,
    n_trials: int,
    accuracy: float,
    **kwargs
) -> str:
    """Template for session completion notification."""
    return f"""
*Session Complete: {session_name}*

• Trials: {n_trials}
• Accuracy: {accuracy:.1%}
• See plot for details
""".strip()


def new_session_started_template(
    session_name: str,
    task_name: str,
    **kwargs
) -> str:
    """Template for new session detection."""
    return f"""
:eyes: *New Session Detected*
_{session_name}_
Task: {task_name}
""".strip()


def error_template(
    session_name: str,
    error_message: str,
    **kwargs
) -> str:
    """Template for error notifications."""
    return f"""
:x: *Analysis Error*
Session: {session_name}
Error: {error_message}
""".strip()
