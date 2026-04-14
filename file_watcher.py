"""
Generic file watcher for MonkeyLogic auto-analysis pipeline.

Monitors a data directory for new .bhv2 files and triggers analysis.
Features:
- Configurable poll interval
- Age filtering (skip files still being written)
- State persistence (track processed files across restarts)
- Graceful shutdown via stop file
- Optional system tray icon (pystray + PIL)

SETUP:
    from file_watcher import FileWatcher
    
    def my_analysis_function(file_path):
        # Your analysis code here
        print(f"Processing {file_path}")
    
    watcher = FileWatcher(
        watch_dir="/path/to/data",
        analysis_func=my_analysis_function,
        poll_interval=10,
        min_file_age=60
    )
    watcher.run()
"""

import os
import json
import time
import logging
import hashlib
from pathlib import Path
from datetime import datetime
from threading import Thread, Event
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class FileWatcher:
    """
    Watches a directory for new files and triggers a callback.
    
    Features:
    - Polls directory at fixed interval
    - Skips files younger than min_file_age (handles files still being written)
    - Persists state to avoid re-processing on restart
    - Graceful shutdown via stop_file or stop() method
    - Optional system tray icon
    
    Attributes:
        watch_dir: Directory to monitor
        analysis_func: Callback(file_path) called when new file detected
        poll_interval: Seconds between directory checks
        min_file_age: Seconds to wait before processing a file
        state_file: Path to JSON file tracking processed files
        stop_file: Path to file that triggers graceful shutdown
    """
    
    def __init__(
        self,
        watch_dir: str | Path,
        analysis_func: Callable[[str], None],
        poll_interval: int = 10,
        min_file_age: int = 60,
        file_extension: str = ".bhv2",
        state_file: Optional[str | Path] = None,
        stop_file: Optional[str | Path] = None,
        enable_tray: bool = False
    ):
        self.watch_dir = Path(watch_dir)
        self.analysis_func = analysis_func
        self.poll_interval = poll_interval
        self.min_file_age = min_file_age
        self.file_extension = file_extension.lower()
        self.enable_tray = enable_tray
        
        # Default paths
        self.state_file = Path(state_file) if state_file else self.watch_dir / ".watcher_state.json"
        self.stop_file = Path(stop_file) if stop_file else self.watch_dir / "watcher.stop"
        
        # Threading
        self._stop_event = Event()
        self._watcher_thread: Optional[Thread] = None
        
        # Load state
        self.processed_files: set[str] = self._load_state()
        
        # System tray (optional)
        self._tray = None
        
        logger.info(f"FileWatcher initialized for {self.watch_dir}")
        logger.info(f"  Poll interval: {self.poll_interval}s")
        logger.info(f"  Min file age: {self.min_file_age}s")
        logger.info(f"  File extension: {self.file_extension}")
        logger.info(f"  State file: {self.state_file}")
        logger.info(f"  Processed files: {len(self.processed_files)}")
    
    def _load_state(self) -> set[str]:
        """Load previously processed files from state file."""
        if not self.state_file.exists():
            return set()
        
        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
            processed = set(data.get('processed_files', []))
            logger.info(f"Loaded {len(processed)} processed files from state")
            return processed
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Could not load state file: {e}")
            return set()
    
    def _save_state(self):
        """Persist processed files to state file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump({
                    'processed_files': list(self.processed_files),
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
        except IOError as e:
            logger.error(f"Could not save state file: {e}")
    
    def _get_file_key(self, file_path: Path) -> str:
        """Generate unique key for file (path + modification time)."""
        mtime = os.path.getmtime(file_path)
        return hashlib.md5(f"{file_path}{mtime}".encode()).hexdigest()[:16]
    
    def _is_new_file(self, file_path: Path) -> bool:
        """Check if file is new (not previously processed)."""
        file_key = self._get_file_key(file_path)
        return file_key not in self.processed_files
    
    def _is_file_ready(self, file_path: Path) -> bool:
        """Check if file is old enough to process (not still being written)."""
        try:
            mtime = os.path.getmtime(file_path)
            age = time.time() - mtime
            return age >= self.min_file_age
        except OSError:
            return False
    
    def _should_stop(self) -> bool:
        """Check if shutdown has been requested."""
        if self._stop_event.is_set():
            return True
        if self.stop_file.exists():
            logger.info(f"Stop file detected: {self.stop_file}")
            self.stop_file.unlink(missing_ok=True)
            return True
        return False
    
    def _scan_directory(self) -> list[Path]:
        """Get all files matching extension in watch directory."""
        if not self.watch_dir.exists():
            logger.warning(f"Watch directory does not exist: {self.watch_dir}")
            return []
        
        files = []
        for item in self.watch_dir.iterdir():
            if item.is_file() and item.suffix.lower() == self.file_extension:
                files.append(item)
        
        return sorted(files, key=lambda p: p.stat().st_mtime)
    
    def _process_new_files(self):
        """Scan directory and process any new files."""
        files = self._scan_directory()
        
        for file_path in files:
            try:
                # Check if new
                if not self._is_new_file(file_path):
                    continue
                
                # Check if ready (old enough)
                if not self._is_file_ready(file_path):
                    logger.debug(f"File not ready (too new): {file_path.name}")
                    continue
                
                # Process!
                logger.info(f"New file detected: {file_path.name}")
                self.analysis_func(str(file_path))
                
                # Mark as processed
                file_key = self._get_file_key(file_path)
                self.processed_files.add(file_key)
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}", exc_info=True)
        
        # Save state periodically
        self._save_state()
    
    def _watch_loop(self):
        """Main polling loop."""
        logger.info("Watcher thread started")
        
        while not self._should_stop():
            try:
                self._process_new_files()
            except Exception as e:
                logger.error(f"Error in watch loop: {e}", exc_info=True)
            
            # Wait for next poll or stop signal
            self._stop_event.wait(timeout=self.poll_interval)
        
        logger.info("Watcher thread stopping")
    
    def _setup_tray(self):
        """Initialize system tray icon (optional)."""
        if not self.enable_tray:
            return
        
        try:
            import pystray
            from PIL import Image
        except ImportError:
            logger.warning("pystray or PIL not installed, skipping system tray")
            return
        
        # Create simple icon (1x1 pixel placeholder)
        icon_image = Image.new('RGB', (64, 64), color='blue')
        
        def show_log(icon, item):
            # Could open log file in editor
            pass
        
        def stop_watcher(icon, item):
            self.stop()
        
        menu = pystray.Menu(
            pystray.MenuItem("Show Log", show_log),
            pystray.MenuItem("Stop", stop_watcher)
        )
        
        self._tray = pystray.Icon(
            "MonkeyLogic Watcher",
            icon_image,
            "MonkeyLogic Auto-Analysis",
            menu
        )
    
    def _run_tray(self):
        """Run system tray (blocking)."""
        if self._tray:
            self._tray.run()
    
    def start(self):
        """Start watching in a background thread."""
        if self._watcher_thread and self._watcher_thread.is_alive():
            logger.warning("Watcher already running")
            return
        
        self._stop_event.clear()
        self._watcher_thread = Thread(target=self._watch_loop, daemon=True)
        self._watcher_thread.start()
        logger.info("File watcher started in background")
    
    def run(self):
        """Run watcher in foreground (blocks)."""
        if self.enable_tray and self._tray:
            # Run tray in background, watch loop in foreground
            tray_thread = Thread(target=self._run_tray, daemon=True)
            tray_thread.start()
            self._watch_loop()
        else:
            self._watch_loop()
    
    def stop(self):
        """Request graceful shutdown."""
        logger.info("Stop requested")
        self._stop_event.set()
        self._save_state()
        
        if self._tray:
            self._tray.stop()
    
    def reset_state(self):
        """Clear processed file history (will re-process all files)."""
        self.processed_files.clear()
        self._save_state()
        logger.info("State reset - all files will be re-processed")


def create_stop_file(watch_dir: str | Path):
    """Create stop file to gracefully shutdown watcher."""
    stop_path = Path(watch_dir) / "watcher.stop"
    stop_path.touch()
    return stop_path
