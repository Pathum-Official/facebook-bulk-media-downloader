"""
PTM Prime - Facebook Media Downloader
Flask Web Application & SSE Server
Powered by PTM Prime
"""

import os
import sys
import json
import subprocess
import webbrowser
from pathlib import Path
from threading import Timer
from flask import Flask, render_template, request, Response, jsonify, send_from_directory

# Ensure local imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.downloader import FBMediaDownloader, is_facebook_url
from core.config import BASE_DIR, DOWNLOADS_DIR, COOKIES_FILE

app = Flask(__name__)
app.config["SECRET_KEY"] = "ptm-prime-fb-secret-key-2026"


@app.route("/")
def index():
    """Render the main PTM Prime UI dashboard."""
    return render_template("index.html", downloads_dir=str(DOWNLOADS_DIR))


@app.route("/api/status", methods=["GET"])
def get_status():
    """Return system status and config."""
    has_cookies = COOKIES_FILE.exists() and COOKIES_FILE.stat().st_size > 0
    return jsonify({
        "status": "online",
        "app_name": "PTM Prime FB Downloader",
        "version": "1.0.0",
        "downloads_dir": str(DOWNLOADS_DIR),
        "has_cookies": has_cookies
    })


@app.route("/api/download/stream")
def download_stream():
    """
    Server-Sent Events (SSE) endpoint for real-time download streaming.
    Streams progress, logs, and finished events.
    """
    url = request.args.get("url", "").strip()
    mode = request.args.get("mode", "auto").strip().lower()
    browser_cookies = request.args.get("browser_cookies", "").strip() or None

    if not url:
        def error_gen():
            yield f"data: {json.dumps({'type': 'error', 'message': 'No URL provided.'})}\n\n"
        return Response(error_gen(), mimetype="text/event-stream")

    if not is_facebook_url(url):
        def invalid_gen():
            yield f"data: {json.dumps({'type': 'error', 'message': 'Invalid Facebook URL. Please check the link.'})}\n\n"
        return Response(invalid_gen(), mimetype="text/event-stream")

    def event_stream():
        downloader = FBMediaDownloader(
            output_dir=str(DOWNLOADS_DIR),
            browser_cookies=browser_cookies
        )
        try:
            for event in downloader.download(url, mode=mode):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Server error: {str(e)}'})}\n\n"

    response = Response(event_stream(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response


@app.route("/api/open-folder", methods=["POST"])
def open_downloads_folder():
    """Open the downloads folder in Windows File Explorer."""
    try:
        data = request.get_json(silent=True) or {}
        subpath = data.get("subpath")
        target = DOWNLOADS_DIR / subpath if subpath else DOWNLOADS_DIR

        if not target.exists():
            target.mkdir(parents=True, exist_ok=True)

        if sys.platform == "win32":
            os.startfile(str(target))
        elif sys.platform == "darwin":
            os.system(f'open "{target}"')
        else:
            os.system(f'xdg-open "{target}"')

        return jsonify({"success": True, "path": str(target)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/history", methods=["GET"])
def get_download_history():
    """Fetch summary of downloaded media."""
    try:
        items = []
        if DOWNLOADS_DIR.exists():
            for root, dirs, files in os.walk(DOWNLOADS_DIR):
                for f in files:
                    file_path = Path(root) / f
                    ext = file_path.suffix.lower()
                    if ext in [".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mkv", ".webm"]:
                        stat = file_path.stat()
                        rel_path = file_path.relative_to(DOWNLOADS_DIR).as_posix()
                        items.append({
                            "name": file_path.name,
                            "folder": file_path.parent.name,
                            "rel_path": rel_path,
                            "type": "video" if ext in [".mp4", ".mkv", ".webm"] else "photo",
                            "size_bytes": stat.st_size,
                            "size_formatted": f"{stat.st_size / (1024 * 1024):.2f} MB" if stat.st_size > 1024*1024 else f"{stat.st_size / 1024:.1f} KB",
                            "modified": stat.st_mtime
                        })

        # Sort newest first
        items.sort(key=lambda x: x["modified"], reverse=True)
        return jsonify({"success": True, "items": items[:100]})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/open-file", methods=["POST"])
def open_downloaded_file():
    """Open a specific downloaded file or highlight it in Windows File Explorer."""
    try:
        data = request.get_json(silent=True) or {}
        rel_path = data.get("rel_path")
        action = data.get("action", "open")  # 'open' (default app) or 'locate' (highlight in explorer)

        if not rel_path:
            return jsonify({"success": False, "error": "No file path provided"}), 400

        target = (DOWNLOADS_DIR / rel_path).resolve()
        # Security: ensure file resides inside DOWNLOADS_DIR
        if not str(target).startswith(str(DOWNLOADS_DIR.resolve())):
            return jsonify({"success": False, "error": "Access denied"}), 403

        if not target.exists():
            return jsonify({"success": False, "error": "File does not exist on disk"}), 404

        if sys.platform == "win32":
            if action == "locate":
                subprocess.Popen(f'explorer /select,"{str(target)}"')
            else:
                os.startfile(str(target))
        elif sys.platform == "darwin":
            os.system(f'open "{target}"')
        else:
            os.system(f'xdg-open "{target}"')

        return jsonify({"success": True, "path": str(target)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/downloads/<path:filename>")
def serve_download(filename):
    """Serve downloaded files for preview or browser viewing."""
    return send_from_directory(str(DOWNLOADS_DIR), filename)


def open_browser():
    """Automatically open default web browser once server starts."""
    webbrowser.open_new("http://127.0.0.1:5000")


if __name__ == "__main__":
    port = 5000
    print(f"\n=======================================================")
    print(f"  PTM Prime - Facebook Media Downloader")
    print(f"  Powered by PTM Prime")
    print(f"  Dashboard available at: http://127.0.0.1:{port}")
    print(f"=======================================================\n")
    # Open browser after 1.2 seconds
    Timer(1.2, open_browser).start()
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
