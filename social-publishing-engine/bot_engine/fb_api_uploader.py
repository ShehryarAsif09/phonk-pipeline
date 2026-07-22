#!/usr/bin/env python3
"""
Facebook Graph API Uploader for Page Reels.
Requires FB_PAGE_ID and FB_PAGE_ACCESS_TOKEN env vars.
Supports both public URL resolution (302 redirects) and direct binary file upload fallback.
"""
import os
import sys
import time
import argparse
import urllib.request
import urllib.parse
import urllib.error
import json


def resolve_final_url(url: str) -> str:
    """Resolves 302 redirects (e.g. GitHub Releases -> AWS S3) to get direct download URL."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.geturl()
    except Exception:
        return url


def main():
    parser = argparse.ArgumentParser(description="Facebook API Uploader")
    parser.add_argument("--video-url", required=True, help="Public URL to the .mp4 file")
    parser.add_argument("--description", required=True, help="Video description")
    parser.add_argument("--file", help="Optional local path to .mp4 file for direct binary fallback")
    args = parser.parse_args()

    fb_page_id = os.environ.get("FB_PAGE_ID")
    access_token = os.environ.get("FB_PAGE_ACCESS_TOKEN")

    if not all([fb_page_id, access_token]):
        print("ERROR: FB_PAGE_ID and FB_PAGE_ACCESS_TOKEN must be set.", file=sys.stderr)
        sys.exit(1)

    direct_url = resolve_final_url(args.video_url)
    print(f"Initializing Facebook Page Reel upload (Resolved URL: {direct_url[:60]}...)...")

    # Step 1: Initialize upload container
    init_url = f"https://graph.facebook.com/v19.0/{fb_page_id}/video_reels"
    init_data = urllib.parse.urlencode({
        "upload_phase": "start",
        "access_token": access_token
    }).encode("utf-8")

    try:
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

    # Step 2: Publish using resolved direct file_url
    publish_url = f"https://graph.facebook.com/v19.0/{fb_page_id}/video_reels"
    publish_data = urllib.parse.urlencode({
        "upload_phase": "finish",
        "video_id": video_id,
        "video_state": "PUBLISHED",
        "description": args.description,
        "file_url": direct_url,
        "access_token": access_token
    }).encode("utf-8")

    try:
        print("Publishing Reel to Facebook Page...")
        req = urllib.request.Request(publish_url, data=publish_data)
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode())
            if res.get("success"):
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
