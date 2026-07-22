#!/usr/bin/env python3
"""
Pinterest API (v5) Idea Pin Uploader.
Requires PINTEREST_ACCESS_TOKEN and PINTEREST_BOARD_ID env vars.
"""
import os
import sys
import time
import argparse
import requests
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Pinterest API Uploader")
    parser.add_argument("--file", required=True, help="Local path to .mp4 file")
    parser.add_argument("--title", required=True, help="Pin Title")
    parser.add_argument("--description", required=True, help="Pin Description")
    parser.add_argument("--link", default="https://publixion.com", help="Destination link for the Pin")
    args = parser.parse_args()

    access_token = os.environ.get("PINTEREST_ACCESS_TOKEN")
    board_id = os.environ.get("PINTEREST_BOARD_ID")

    if not all([access_token, board_id]):
        print("ERROR: PINTEREST_ACCESS_TOKEN and PINTEREST_BOARD_ID must be set. Skipping Pinterest upload.", file=sys.stderr)
        sys.exit(0)  # Exit 0 so workflow doesn't fail if just missing credentials

    local_file = Path(args.file)
    if not local_file.exists():
        print(f"ERROR: Video file not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Step 1: Register media upload
    print("Step 1: Registering media upload with Pinterest API...")
    media_reg_url = "https://api.pinterest.com/v5/media"
    media_reg_payload = {
        "media_type": "video"
    }
    
    reg_res = requests.post(media_reg_url, headers=headers, json=media_reg_payload)
    if reg_res.status_code != 201:
        print(f"API Error (Media Register): {reg_res.status_code} - {reg_res.text}", file=sys.stderr)
        sys.exit(1)
        
    reg_data = reg_res.json()
    media_id = reg_data.get("media_id")
    upload_url = reg_data.get("upload_url")
    upload_parameters = reg_data.get("upload_parameters")
    
    print(f"Media registered. Media ID: {media_id}")

    # Step 2: Upload binary to S3
    print("Step 2: Uploading binary data...")
    with open(local_file, "rb") as f:
        files = {"file": f}
        # upload_parameters already contains the required S3 fields (x-amz-date, signature, policy, etc.)
        upload_res = requests.post(upload_url, data=upload_parameters, files=files)
        
        if upload_res.status_code not in (200, 204):
            print(f"S3 Upload Error: {upload_res.status_code} - {upload_res.text}", file=sys.stderr)
            sys.exit(1)
            
    print("Binary upload successful.")

    # Step 3: Poll media status until "succeeded"
    print("Step 3: Polling media processing status...")
    status_url = f"https://api.pinterest.com/v5/media/{media_id}"
    media_ready = False
    
    for attempt in range(15):
        time.sleep(5)
        status_res = requests.get(status_url, headers=headers)
        if status_res.status_code == 200:
            status = status_res.json().get("status")
            print(f"  Check {attempt + 1}: {status}")
            if status == "succeeded":
                media_ready = True
                break
            elif status == "failed":
                print("Media processing failed on Pinterest side.", file=sys.stderr)
                sys.exit(1)
        else:
            print(f"Status check failed: {status_res.status_code}", file=sys.stderr)
            
    if not media_ready:
        print("Timeout waiting for media processing.", file=sys.stderr)
        sys.exit(1)

    # Step 4: Create the Pin
    print("Step 4: Creating the Idea Pin...")
    pins_url = "https://api.pinterest.com/v5/pins"
    pin_payload = {
        "board_id": board_id,
        "title": args.title,
        "description": args.description,
        "link": args.link,
        "media_source": {
            "source_type": "video_id",
            "cover_image_url": "", # Optional
            "media_id": media_id
        }
    }
    
    pin_res = requests.post(pins_url, headers=headers, json=pin_payload)
    if pin_res.status_code == 201:
        pin_id = pin_res.json().get("id")
        print(f"SUCCESS: Pinterest Pin Published! Pin ID: {pin_id}")
    else:
        print(f"API Error (Pin Creation): {pin_res.status_code} - {pin_res.text}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
