"""
PTM Prime - Facebook Media Downloader
Configuration Module
Powered by PTM Prime
"""

import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

COOKIES_FILE = BASE_DIR / "cookies.txt"

# Default App Settings
DEFAULT_CONFIG = {
    "downloads_dir": str(DOWNLOADS_DIR),
    "use_browser_cookies": None,  # e.g., 'chrome', 'firefox', 'edge'
    "video_quality": "best",       # 'best', '1080p', '720p', 'audio_only'
    "photo_quality": "original",   # 'original'
    "max_concurrent_photos": 4
}
