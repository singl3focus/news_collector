# This file should not contain any credentials
# All credentials should be loaded from .env file via tg_config.py
# See tg_config.py for actual credential loading

import json
import threading
from typing import List, Dict
import logging
from tg_config import JSONDB_API_URL

logger = logging.getLogger(__name__)

class JsonDB:
    def __init__(self, filename="channels.json"):
        self.filename = filename
        self.lock = threading.Lock()
        try:
            with open(self.filename, "r") as f:
                self.data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.data = {"channels": []}
            self._save()

    def _save(self):
        """Save data to JSON file with thread safety."""
        with self.lock:
            try:
                with open(self.filename, "w") as f:
                    json.dump(self.data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"Error saving to {self.filename}: {e}")
                raise

    def get_channels(self) -> List[Dict]:
        """Get list of all channels."""
        with self.lock:
            return list(self.data["channels"])

    def add_channel(self, channel: Dict):
        """Add a new channel if it doesn't exist."""
        with self.lock:
            if not any(c["link"] == channel["link"] for c in self.data["channels"]):
                self.data["channels"].append(channel)
                self._save()
                logger.info(f"Added channel: {channel['link']}")
            else:
                logger.info(f"Channel already exists: {channel['link']}")

    def remove_channel(self, link: str):
        """Remove a channel by its link."""
        with self.lock:
            initial_length = len(self.data["channels"])
            self.data["channels"] = [c for c in self.data["channels"] if c["link"] != link]
            if len(self.data["channels"]) < initial_length:
                self._save()
                logger.info(f"Removed channel: {link}")
            else:
                logger.info(f"Channel not found: {link}")
