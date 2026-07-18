#!/usr/bin/env python3
"""
Facebook Graph API Uploader for Page Reels.
Requires FB_PAGE_ID and FB_PAGE_ACCESS_TOKEN env vars.
"""
import os
import sys
import time
import argparse
import urllib.request
import json

def main():
    parser = argparse.ArgumentParser(description="Facebook API Uploader")
    parser.add_argument("--video-url", required=True, help="Public URL to the .mp4 file")
    parser.add_argument("--description", required=True, help="Video description")
    args = parser.parse_args()

    fb_page_id = os.environ.get("FB_PAGE_ID")
    access_token = os.environ.get("FB_PAGE_ACCESS_TOKEN")

    if not all([fb_page_id, access_token]):
        print("ERROR: FB_PAGE_ID and FB_PAGE_ACCESS_TOKEN must be set.", file=sys.stderr)
        sys.exit(1)

    print(f"Initializing Facebook Page Reel upload for {args.video_url}...")

    # Step 1: Initialize upload
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
            print(f"Container created. Video ID: {video_id}")
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"FB API ERROR (Init): {e.code} - {err}", file=sys.stderr)
        sys.exit(1)

    # Step 2: Provide the file URL to Facebook
    # Note: FB supports file_url directly for Reels via the finish phase in some Graph API versions,
    # but the officially supported way is to upload binary chunk or use file_url.
    # We will use the direct upload from URL since we are running serverless.
    
    upload_url = f"https://graph.facebook.com/v19.0/{fb_page_id}/video_reels"
    upload_data = urllib.parse.urlencode({
        "upload_phase": "finish",
        "video_id": video_id,
        "video_state": "PUBLISHED",
        "description": args.description,
        "file_url": args.video_url,
        "access_token": access_token
    }).encode("utf-8")

    try:
        print("Publishing Reel...")
        req = urllib.request.Request(upload_url, data=upload_data)
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
