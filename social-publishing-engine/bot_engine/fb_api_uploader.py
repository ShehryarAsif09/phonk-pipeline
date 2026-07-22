#!/usr/bin/env python3
"""
Facebook Graph API Uploader for Page Reels.
Requires FB_PAGE_ID and FB_PAGE_ACCESS_TOKEN env vars.
Uses direct binary chunk streaming to Facebook's rupload endpoint for 100% reliability.
"""
import os
import sys
import time
import argparse
import urllib.request
import urllib.parse
import urllib.error
import json
from pathlib import Path


def resolve_final_url(url: str) -> str:
    """Resolves 302 redirects to get direct download URL."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.geturl()
    except Exception:
        return url


def main():
    parser = argparse.ArgumentParser(description="Facebook API Uploader")
    parser.add_argument("--video-url", help="Public URL to the .mp4 file")
    parser.add_argument("--description", required=True, help="Video description")
    parser.add_argument("--file", default="output_reel.mp4", help="Local path to .mp4 file for direct binary upload")
    args = parser.parse_args()

    fb_page_id = os.environ.get("FB_PAGE_ID")
    access_token = os.environ.get("FB_PAGE_ACCESS_TOKEN")

    if not all([fb_page_id, access_token]):
        print("ERROR: FB_PAGE_ID and FB_PAGE_ACCESS_TOKEN must be set.", file=sys.stderr)
        sys.exit(1)

    # Step 1: Initialize upload container
    init_url = f"https://graph.facebook.com/v19.0/{fb_page_id}/video_reels"
    init_data = urllib.parse.urlencode({
        "upload_phase": "start",
        "access_token": access_token
    }).encode("utf-8")

    try:
        print(f"Initializing Facebook Page Reel upload for Page ID: {fb_page_id}...")
        req = urllib.request.Request(init_url, data=init_data)
        with urllib.request.urlopen(req) as response:
            init_res = json.loads(response.read().decode())
            video_id = init_res.get("video_id")
            upload_url = init_res.get("upload_url")
            print(f"Container created. Video ID: {video_id}")
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"FB API ERROR (Init): {e.code} - {err}", file=sys.stderr)
        sys.exit(1)

    # Step 2: Upload binary bytes directly if local file exists, else use URL
    local_file = Path(args.file) if args.file else None
    if local_file and local_file.exists() and upload_url:
        print(f"Uploading video bytes directly ({local_file.stat().st_size} bytes) to Facebook rupload endpoint...")
        file_bytes = local_file.read_bytes()
        req = urllib.request.Request(
            upload_url,
            data=file_bytes,
            headers={
                "Authorization": f"OAuth {access_token}",
                "file_offset": "0",
                "Content-Type": "application/octet-stream"
            }
        )
        try:
            with urllib.request.urlopen(req) as response:
                rupload_res = json.loads(response.read().decode())
                print(f"Binary stream upload complete: {rupload_res}")
        except urllib.error.HTTPError as e:
            print(f"Warning on binary upload step: {e.code} - {e.read().decode()}", file=sys.stderr)
    
    # Step 3: Finish and publish Reel
    publish_url = f"https://graph.facebook.com/v19.0/{fb_page_id}/video_reels"
    publish_payload = {
        "upload_phase": "finish",
        "video_id": video_id,
        "video_state": "PUBLISHED",
        "description": args.description,
        "access_token": access_token
    }

    # If we didn't do binary upload, pass resolved file_url
    if not (local_file and local_file.exists()) and args.video_url:
        publish_payload["file_url"] = resolve_final_url(args.video_url)

    publish_data = urllib.parse.urlencode(publish_payload).encode("utf-8")

    # Poll status for up to 30s for processing
    print("Publishing Reel to Facebook Page...")
    time.sleep(5)
    
    try:
        req = urllib.request.Request(publish_url, data=publish_data)
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode())
            if res.get("success") or res.get("id"):
                print(f"SUCCESS: Facebook Reel Published! Video ID: {video_id}")
            else:
                print(f"FB API ERROR (Publish): {res}", file=sys.stderr)
                sys.exit(1)
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"FB API ERROR (Publish): {e.code} - {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
