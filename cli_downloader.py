"""
PTM Prime - Facebook Media Downloader (CLI)
Powered by PTM Prime
"""

import sys
import argparse
from pathlib import Path

# Ensure local imports work
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Set UTF-8 encoding for Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    CYAN = Fore.CYAN
    GREEN = Fore.GREEN
    YELLOW = Fore.YELLOW
    RED = Fore.RED
    BRIGHT = Style.BRIGHT
    RESET = Style.RESET_ALL
except ImportError:
    CYAN = GREEN = YELLOW = RED = BRIGHT = RESET = ""

from core.downloader import FBMediaDownloader, is_facebook_url
from core.config import DOWNLOADS_DIR


BANNER = rf"""
{CYAN}{BRIGHT}======================================================================
      ____ _____ __  __   ____       _                 
     |  _ \_   _|  \/  | |  _ \ _ __(_)_ __ ___   ___  
     | |_) || | | |\/| | | |_) | '__| | '_ ` _ \ / _ \ 
     |  __/ | | | |  | | |  __/| |  | | | | | | |  __/ 
     |_|    |_| |_|  |_| |_|   |_|  |_|_| |_| |_|\___| 
                                                       
          Facebook Media Downloader (Photos & Videos)
                   * Powered by PTM Prime *
======================================================================{RESET}
"""


def main():
    print(BANNER)

    parser = argparse.ArgumentParser(
        description="PTM Prime Facebook Media Downloader - Download Photos and Videos in Batch"
    )
    parser.add_argument("url", nargs="?", help="Facebook Post, Album, Video, or Reel URL")
    parser.add_argument(
        "--mode",
        choices=["auto", "photos", "videos", "both"],
        default="auto",
        help="Download mode: auto (default), photos, videos, both"
    )
    parser.add_argument(
        "--output", "-o",
        default=str(DOWNLOADS_DIR),
        help=f"Output directory (default: {DOWNLOADS_DIR})"
    )
    parser.add_argument(
        "--cookies-from-browser",
        help="Extract login cookies from browser (e.g. chrome, edge, firefox, brave)"
    )

    args = parser.parse_args()

    url = args.url
    if not url:
        print(f"{YELLOW}No URL specified. Please enter a Facebook URL below:{RESET}")
        url = input(f"{CYAN}Facebook URL > {RESET}").strip()

    if not url:
        print(f"{RED}Error: No URL provided. Exiting.{RESET}")
        sys.exit(1)

    if not is_facebook_url(url):
        print(f"{RED}Error: That does not appear to be a valid Facebook URL.{RESET}")
        print(f"{YELLOW}Supported: facebook.com, web.facebook.com, fb.watch, fb.com{RESET}")
        sys.exit(1)

    print(f"\n{GREEN}Mode:{RESET} {args.mode.upper()}")
    print(f"{GREEN}Output Folder:{RESET} {args.output}")
    print(f"{GREEN}Starting extraction...{RESET}\n")

    downloader = FBMediaDownloader(
        output_dir=args.output,
        browser_cookies=args.cookies_from_browser
    )

    for event in downloader.download(url, mode=args.mode):
        etype = event.get("type")
        msg = event.get("message", "")

        if etype == "item_downloaded":
            print(f"{GREEN}{BRIGHT}[✓] {msg}{RESET}")
        elif etype == "error":
            print(f"{RED}{BRIGHT}[!] {msg}{RESET}")
        elif etype == "finished":
            print(f"\n{CYAN}{BRIGHT}======================================================================{RESET}")
            print(f"{GREEN}{BRIGHT}{msg}{RESET}")
            print(f"{CYAN}Saved in: {event.get('output_dir')}{RESET}")
            print(f"{CYAN}{BRIGHT}======================================================================{RESET}\n")
        elif etype == "log":
            level = event.get("level", "info")
            if level == "warning":
                print(f"{YELLOW}[WARN] {msg}{RESET}")
            elif level == "success":
                print(f"{GREEN}[OK] {msg}{RESET}")
            else:
                print(f"{CYAN}[LOG]{RESET} {msg}")


if __name__ == "__main__":
    main()
