"""
Nexus Monitor State Tracking

Tracks which items (email IDs, etc.) have been processed by each job.
Persists to a JSON file. Caps processed IDs at 500 per job to prevent unbounded growth.
Uses write-to-temp-then-rename for crash safety.
"""

import json
import os
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
import logging

logger = logging.getLogger('NexusMonitor.state')

MAX_PROCESSED_IDS = 500


class StateManager:
    """Manages persistent state for monitor jobs"""

    def __init__(self, state_dir: str = None):
        if state_dir:
            self.state_dir = Path(state_dir)
        else:
            # Default to alongside the exe (or project root in dev)
            import sys
            if getattr(sys, 'frozen', False):
                self.state_dir = Path(sys.executable).parent
            else:
                self.state_dir = Path(__file__).parent.parent

        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / 'state.json'
        self._state = self._load()
        logger.info(f"State file: {self.state_file}")

    def _load(self) -> dict:
        """Load state from disk"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"State file corrupt, recreating: {e}")
                return {}
        return {}

    def _save(self):
        """Save state to disk using write-to-temp-then-rename for safety"""
        try:
            fd, tmp_path = tempfile.mkstemp(dir=str(self.state_dir), suffix='.tmp')
            try:
                with os.fdopen(fd, 'w') as f:
                    json.dump(self._state, f, indent=2)
                os.replace(tmp_path, str(self.state_file))
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def _ensure_job(self, job_name: str):
        """Ensure job entry exists in state"""
        if job_name not in self._state:
            self._state[job_name] = {"processed_ids": [], "last_run": None}

    def is_processed(self, job_name: str, item_id: str) -> bool:
        """Check if an item has already been processed"""
        self._ensure_job(job_name)
        return item_id in self._state[job_name]["processed_ids"]

    def mark_processed(self, job_name: str, item_id: str):
        """Mark an item as processed and save"""
        self._ensure_job(job_name)
        ids = self._state[job_name]["processed_ids"]
        if item_id not in ids:
            ids.append(item_id)
            if len(ids) > MAX_PROCESSED_IDS:
                self._state[job_name]["processed_ids"] = ids[-MAX_PROCESSED_IDS:]
            self._save()

    def get_last_run(self, job_name: str) -> Optional[str]:
        """Get the last run timestamp (ISO 8601 UTC) for a job"""
        self._ensure_job(job_name)
        return self._state[job_name].get("last_run")

    def set_last_run(self, job_name: str, timestamp: str = None):
        """Set the last run timestamp for a job"""
        self._ensure_job(job_name)
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        self._state[job_name]["last_run"] = timestamp
        self._save()
