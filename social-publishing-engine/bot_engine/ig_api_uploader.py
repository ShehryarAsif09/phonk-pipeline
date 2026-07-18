#!/usr/bin/env python3
"""
Instagram Graph API Uploader for Reels.
Requires IG_ACCOUNT_ID and IG_ACCESS_TOKEN env vars.
NOTE: Instagram Graph API requires a public URL for videos, not local files.
"""
import os
import sys
import time
import argparse
import urllib.request
import json

def main():
    parser = argparse.ArgumentParser(description="Instagram API Uploader")
    parser.add_argument("--video-url", required=True, help="Public URL to the .mp4 file")
    parser.add_argument("--caption", required=True, help="Caption text")
    args = parser.parse_args()

    ig_account_id = os.environ.get("IG_ACCOUNT_ID")
    access_token = os.environ.get("IG_ACCESS_TOKEN")

    if not all([ig_account_id, access_token]):
        print("ERROR: IG_ACCOUNT_ID and IG_ACCESS_TOKEN must be set.", file=sys.stderr)
        sys.exit(1)

    print(f"Initializing Instagram Reel upload for {args.video_url}...")

    # Step 1: Initialize container
    init_url = f"https://graph.facebook.com/v19.0/{ig_account_id}/media"
    init_data = urllib.parse.urlencode({
        "media_type": "REELS",
        "video_url": args.video_url,
        "caption": args.caption,
        "access_token": access_token
    }).encode("utf-8")

    try:
        req = urllib.request.Request(init_url, data=init_data)
        with urllib.request.urlopen(req) as response:
            init_res = json.loads(response.read().decode())
            creation_id = init_res.get("id")
            print(f"Container created. ID: {creation_id}")
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"IG API ERROR (Init): {e.code} - {err}", file=sys.stderr)
        sys.exit(1)

    # Step 2: Poll for status
    status_url = f"https://graph.facebook.com/v19.0/{creation_id}?fields=status_code&access_token={access_token}"
    max_retries = 15
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(status_url)
            with urllib.request.urlopen(req) as response:
                status_res = json.loads(response.read().decode())
                status = status_res.get("status_code")
                print(f"Status check {attempt+1}/{max_retries}: {status}")
                if status == "FINISHED":
                    break
                elif status == "ERROR":
                    print("IG API ERROR: Video processing failed on Instagram's end.", file=sys.stderr)
                    sys.exit(1)
        except urllib.error.HTTPError as e:
            err = e.read().decode()
            print(f"IG API ERROR (Status Check): {e.code} - {err}", file=sys.stderr)
            sys.exit(1)
        
        time.sleep(10) # Wait 10 seconds before polling again
    else:
        print("ERROR: Timeout waiting for Instagram to process the video.", file=sys.stderr)
        sys.exit(1)

    # Step 3: Publish container
    print("Publishing Reel...")
    pub_url = f"https://graph.facebook.com/v19.0/{ig_account_id}/media_publish"
    pub_data = urllib.parse.urlencode({
        "creation_id": creation_id,
        "access_token": access_token
    }).encode("utf-8")

    try:
        req = urllib.request.Request(pub_url, data=pub_data)
        with urllib.request.urlopen(req) as response:
            pub_res = json.loads(response.read().decode())
            print(f"SUCCESS: Instagram Reel Published! Post ID: {pub_res.get('id')}")
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"IG API ERROR (Publish): {e.code} - {err}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
