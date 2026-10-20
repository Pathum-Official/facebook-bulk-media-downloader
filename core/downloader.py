"""
PTM Prime - Facebook Media Downloader
Core Downloader Engine
Powered by PTM Prime
"""

import os
import re
import sys
import json
import shutil
import subprocess
import urllib.parse
from pathlib import Path
from typing import Generator, Dict, Any, Optional

from core.config import BASE_DIR, DOWNLOADS_DIR, COOKIES_FILE


def is_facebook_url(url: str) -> bool:
    """Validate if the URL is a recognized Facebook URL."""
    clean_url = url.strip().lower()
    return any(domain in clean_url for domain in [
        "facebook.com",
        "fb.watch",
        "fb.com",
        "m.facebook.com",
        "web.facebook.com",
        "touch.facebook.com"
    ])


def detect_url_media_type(url: str) -> str:
    """
    Heuristically detect media type from URL structure:
    returns 'video', 'photo', or 'mixed'
    """
    url_lower = url.lower()
    if any(k in url_lower for k in ["/watch", "/reel", "/videos/", "fb.watch", "/share/v/", "/share/r/"]):
        return "video"
    if any(k in url_lower for k in ["/photo", "/photos", "/albums", "media/set", "/share/p/"]):
        return "photo"
    return "mixed"


def extract_facebook_video_ids(html: str) -> list:
    """Extract all unique Facebook video IDs from post HTML."""
    if not html:
        return []
    patterns = [
        r'"video_id":"(\d+)"',
        r'\"video_id\":\"(\d+)\"',
        r'/videos/pcb\.\d+/(\d+)',
        r'watch/\?v=(\d+)',
        r'"id":"(\d+)","__typename":"Video"',
        r'"videoId":"(\d+)"'
    ]
    found = []
    seen = set()
    for p in patterns:
        for vid in re.findall(p, html):
            if len(vid) >= 10 and vid not in seen:
                seen.add(vid)
                found.append(vid)
    return found


def resolve_and_probe_facebook(url: str, browser_cookies: Optional[str] = None) -> tuple:
    """
    Expands Facebook /share/p/, /share/v/, /share/r/ and /posts/ links into direct canonical permalinks,
    and returns (canonical_url, html_content).
    Preserves story_fbid and user id parameters correctly.
    """
    clean_input = url.strip()
    if "/share/" not in clean_input and "/posts/" not in clean_input:
        return clean_input, ""

    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
    }
    if browser_cookies:
        ydl_opts['cookiesfrombrowser'] = (browser_cookies,)
    elif COOKIES_FILE.exists() and COOKIES_FILE.stat().st_size > 0:
        ydl_opts['cookiefile'] = str(COOKIES_FILE)

    resolved_url = clean_input
    html = ""

    try:
        import yt_dlp
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ie = ydl.get_info_extractor('Generic')
            res = ie._download_webpage_handle(clean_input, 'share_probe')
            redirected = res[1].url if hasattr(res[1], 'url') else res[1].geturl()
            html = res[0]

            if redirected:
                parsed = urllib.parse.urlparse(redirected)
                qs = urllib.parse.parse_qs(parsed.query)

                # Check if it redirected to a permalink.php (preserve story_fbid and id)
                if "permalink.php" in parsed.path:
                    story_fbid = qs.get("story_fbid", [None])[0]
                    user_id = qs.get("id", [None])[0]
                    if story_fbid:
                        clean_link = f"https://web.facebook.com/permalink.php?story_fbid={story_fbid}"
                        if user_id:
                            clean_link += f"&id={user_id}"
                        resolved_url = clean_link
                else:
                    # Check if it redirected to /posts/
                    match = re.search(r'facebook\.com/([^/?#]+)/posts/([^/?#]+)', redirected)
                    if match:
                        user_id, fbid = match.group(1), match.group(2)
                        resolved_url = f"https://web.facebook.com/permalink.php?story_fbid={fbid}&id={user_id}"
                    else:
                        resolved_url = redirected.split("?")[0]
    except Exception:
        pass

    return resolved_url, html


class FBMediaDownloader:
    """
    Main engine combining gallery-dl (photos & albums) and yt-dlp (videos & reels)
    with unified real-time event streaming.
    """

    def __init__(self, output_dir: Optional[str] = None, browser_cookies: Optional[str] = None):
        self.output_dir = Path(output_dir) if output_dir else DOWNLOADS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.browser_cookies = browser_cookies

    def _get_cookie_args_gallery_dl(self) -> list:
        args = []
        if COOKIES_FILE.exists() and COOKIES_FILE.stat().st_size > 0:
            args.extend(["--cookies", str(COOKIES_FILE)])
        elif self.browser_cookies:
            args.extend(["--cookies-from-browser", self.browser_cookies])
        return args

    def _get_cookie_args_ytdlp(self) -> list:
        args = []
        if COOKIES_FILE.exists() and COOKIES_FILE.stat().st_size > 0:
            args.extend(["--cookies", str(COOKIES_FILE)])
        elif self.browser_cookies:
            args.extend(["--cookies-from-browser", self.browser_cookies])
        return args

    def download_photos(self, url: str) -> Generator[Dict[str, Any], None, list]:
        """
        Download Facebook photos/albums using gallery-dl.
        Yields real-time events.
        """
        yield {"type": "log", "message": "🔍 Initializing Photo Extraction engine (gallery-dl)..."}
        yield {"type": "progress", "percent": 10, "text": "Connecting to Facebook..."}

        target_folder = self.output_dir / "Facebook_Photos"
        target_folder.mkdir(parents=True, exist_ok=True)

        cmd = [
            "gallery-dl",
            "--directory", str(target_folder),
            "--retries", "3",
            "--no-mtime"
        ]
        cmd.extend(self._get_cookie_args_gallery_dl())
        cmd.append(url)

        downloaded_files = []
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace"
            )

            photo_count = 0
            for line in process.stdout:
                line_str = line.strip()
                if not line_str:
                    continue

                # Check if downloading or saved a file
                if any(ext in line_str.lower() for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                    photo_count += 1
                    file_name = Path(line_str.replace("#", "").strip()).name
                    downloaded_files.append(file_name)
                    yield {
                        "type": "item_downloaded",
                        "media_type": "photo",
                        "index": photo_count,
                        "filename": file_name,
                        "message": f"📸 Downloaded photo #{photo_count}: {file_name}"
                    }
                    yield {
                        "type": "progress",
                        "percent": min(15 + photo_count * 2, 90),
                        "text": f"Downloaded {photo_count} photos..."
                    }
                elif "[facebook]" in line_str or "[gallery-dl]" in line_str:
                    yield {"type": "log", "message": line_str}
                elif "error" in line_str.lower():
                    yield {"type": "log", "level": "warning", "message": line_str}

            process.wait()

            if process.returncode == 0 or photo_count > 0:
                yield {
                    "type": "log",
                    "level": "success",
                    "message": f"✅ Photos download completed! Total saved: {photo_count}"
                }
            else:
                yield {
                    "type": "log",
                    "level": "info",
                    "message": "No photos found with gallery-dl in this link (might be a video post)."
                }

        except Exception as e:
            yield {"type": "error", "message": f"Photo download error: {str(e)}"}

        return downloaded_files

    def _download_single_video(self, video_url: str, index: int = 1, total: int = 1) -> Generator[Dict[str, Any], None, list]:
        """Download an individual video URL via yt-dlp."""
        prefix = f"Video {index}/{total}: " if total > 1 else ""
        yield {"type": "log", "message": f"🎬 {prefix}Extracting video stream: {video_url}"}
        yield {"type": "progress", "percent": 25, "text": f"{prefix}Extracting video stream..."}

        target_folder = self.output_dir / "Facebook_Videos"
        target_folder.mkdir(parents=True, exist_ok=True)

        output_template = str(target_folder / "%(uploader,channel|Facebook)s_%(upload_date,id)s_%(title).50B.%(ext)s")

        cmd = [
            "yt-dlp",
            "--newline",
            "--no-warnings",
            "--no-playlist",
            "-f", "bestvideo+bestaudio/best",
            "--merge-output-format", "mp4",
            "-o", output_template
        ]
        cmd.extend(self._get_cookie_args_ytdlp())
        cmd.append(video_url)

        downloaded_videos = []
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace"
            )

            current_percent = 30
            video_title = "Facebook Video"
            for line in process.stdout:
                line_str = line.strip()
                if not line_str:
                    continue

                if "[download] Destination:" in line_str:
                    filename = Path(line_str.split("Destination:")[-1].strip()).name
                    video_title = filename
                    yield {"type": "log", "message": f"📥 {prefix}Starting download: {filename}"}

                elif "[download]" in line_str and "%" in line_str:
                    match = re.search(r"(\d+(?:\.\d+)?)%", line_str)
                    if match:
                        pct = float(match.group(1))
                        if total > 1:
                            video_slice = 70.0 / total
                            base_pct = 20.0 + (index - 1) * video_slice
                            mapped_pct = int(base_pct + (pct * video_slice / 100.0))
                        else:
                            mapped_pct = int(30 + (pct * 0.6))
                        current_percent = min(mapped_pct, 95)
                        yield {
                            "type": "progress",
                            "percent": current_percent,
                            "text": f"{prefix}Downloading video: {pct}%"
                        }
                    yield {"type": "log", "message": line_str}

                elif "[Merger]" in line_str or "[ffmpeg]" in line_str:
                    yield {"type": "log", "message": f"🎞️ {prefix}Merging audio & video streams..."}
                    yield {"type": "progress", "percent": 95, "text": f"{prefix}Finalizing video..."}

                elif "[download] 100%" in line_str:
                    downloaded_videos.append(video_title)
                    yield {
                        "type": "item_downloaded",
                        "media_type": "video",
                        "filename": video_title,
                        "message": f"🎬 Downloaded video: {video_title}"
                    }

                elif "ERROR:" in line_str:
                    yield {"type": "log", "level": "warning", "message": line_str}
                else:
                    yield {"type": "log", "message": line_str}

            process.wait()

            if process.returncode == 0 or len(downloaded_videos) > 0:
                yield {
                    "type": "log",
                    "level": "success",
                    "message": f"✅ {prefix}Video download completed successfully!"
                }
            else:
                yield {
                    "type": "log",
                    "level": "info",
                    "message": f"Note: yt-dlp did not detect a video on {video_url}"
                }

        except Exception as e:
            yield {"type": "error", "message": f"Video download error: {str(e)}"}

        return downloaded_videos

    def download_videos(self, url: str, html: str = "") -> Generator[Dict[str, Any], None, list]:
        """
        Download Facebook video / reels / multi-videos using yt-dlp.
        Supports multi-video posts by extracting individual video IDs!
        """
        yield {"type": "log", "message": "🎬 Initializing Video Extraction engine (yt-dlp)..."}
        yield {"type": "progress", "percent": 20, "text": "Analyzing video content..."}

        # Check if URL is already a single video watch or reel
        is_single_direct_video = any(k in url.lower() for k in ["/watch?v=", "/watch/?v=", "/reel/"]) and "pcb." not in url

        video_ids = []
        if not is_single_direct_video:
            if html:
                video_ids = extract_facebook_video_ids(html)
            if not video_ids:
                try:
                    import yt_dlp
                    ydl_opts = {'skip_download': True, 'quiet': True, 'no_warnings': True}
                    if self.browser_cookies:
                        ydl_opts['cookiesfrombrowser'] = (self.browser_cookies,)
                    elif COOKIES_FILE.exists() and COOKIES_FILE.stat().st_size > 0:
                        ydl_opts['cookiefile'] = str(COOKIES_FILE)

                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ie = ydl.get_info_extractor('Generic')
                        probe_res = ie._download_webpage_handle(url, 'video_probe')
                        video_ids = extract_facebook_video_ids(probe_res[0])
                except Exception:
                    pass

        downloaded_all = []

        if video_ids:
            yield {
                "type": "log",
                "level": "success",
                "message": f"🎥 Multi-video post detected! Found {len(video_ids)} video(s) in this post. Downloading all..."
            }
            for i, vid in enumerate(video_ids, 1):
                watch_url = f"https://www.facebook.com/watch/?v={vid}"
                for ev in self._download_single_video(watch_url, index=i, total=len(video_ids)):
                    if ev.get("type") == "item_downloaded":
                        downloaded_all.append(ev.get("filename"))
                    yield ev
        else:
            # Single video download
            for ev in self._download_single_video(url, index=1, total=1):
                if ev.get("type") == "item_downloaded":
                    downloaded_all.append(ev.get("filename"))
                yield ev

        return downloaded_all

    def download(self, url: str, mode: str = "auto") -> Generator[Dict[str, Any], None, Dict[str, Any]]:
        """
        Unified download dispatcher supporting:
        - 'auto': automatically checks and downloads photos & videos
        - 'photos': photo posts / albums only
        - 'videos': videos / reels / watch only
        - 'both': explicit dual download
        """
        if not is_facebook_url(url):
            yield {
                "type": "error",
                "message": "Invalid Facebook URL. Please provide a valid facebook.com or fb.watch link."
            }
            return {"success": False, "photos": 0, "videos": 0}

        yield {
            "type": "log",
            "message": f"🚀 Starting PTM Prime FB Downloader | Mode: {mode.upper()}"
        }
        yield {"type": "log", "message": f"🔗 Target URL: {url}"}
        yield {"type": "log", "message": f"📁 Save Directory: {self.output_dir}"}

        # Resolve modern Facebook /share/ and /posts/ links into canonical permalinks & probe HTML
        html = ""
        if "/share/" in url or "/posts/" in url:
            yield {"type": "log", "message": "🔍 Analyzing Facebook link and resolving canonical post..."}
            resolved_url, html = resolve_and_probe_facebook(url, browser_cookies=self.browser_cookies)
            if resolved_url != url:
                yield {"type": "log", "level": "success", "message": f"🔗 Resolved canonical post: {resolved_url}"}
                url = resolved_url

        photos_count = 0
        videos_count = 0

        detected = detect_url_media_type(url)
        yield {"type": "log", "message": f"ℹ️ Heuristic Media Analysis: Detected '{detected}' link structure."}

        # Determine execution flow based on mode
        run_photos = mode in ("auto", "photos", "both")
        run_videos = mode in ("auto", "videos", "both")

        # Optimization: If mode is auto and link is clearly a video/reel, prioritize video first
        if mode == "auto" and detected == "video":
            # Video first
            for event in self.download_videos(url, html=html):
                if event.get("type") == "item_downloaded":
                    videos_count += 1
                yield event

            # If no video was found, fallback to photos
            if videos_count == 0:
                yield {"type": "log", "message": "Checking if post contains photos..."}
                for event in self.download_photos(url):
                    if event.get("type") == "item_downloaded":
                        photos_count += 1
                    yield event

        elif mode == "auto" and detected == "photo":
            # Photo first
            for event in self.download_photos(url):
                if event.get("type") == "item_downloaded":
                    photos_count += 1
                yield event

            # If no photos found, fallback to video check
            if photos_count == 0:
                yield {"type": "log", "message": "Checking if post contains video(s)..."}
                for event in self.download_videos(url, html=html):
                    if event.get("type") == "item_downloaded":
                        videos_count += 1
                    yield event

        else:
            # For mixed or explicit modes
            if run_photos:
                for event in self.download_photos(url):
                    if event.get("type") == "item_downloaded":
                        photos_count += 1
                    yield event

            if run_videos:
                for event in self.download_videos(url, html=html):
                    if event.get("type") == "item_downloaded":
                        videos_count += 1
                    yield event

        total_saved = photos_count + videos_count
        yield {"type": "progress", "percent": 100, "text": "Completed!"}
        yield {
            "type": "finished",
            "success": total_saved > 0,
            "photos_count": photos_count,
            "videos_count": videos_count,
            "total_count": total_saved,
            "output_dir": str(self.output_dir),
            "message": f"🎉 Process finished! Successfully saved {photos_count} photo(s) and {videos_count} video(s)."
        }

        return {
            "success": total_saved > 0,
            "photos": photos_count,
            "videos": videos_count,
            "output_dir": str(self.output_dir)
        }
