#!/usr/bin/env python3
"""
YouTube Shorts API Uploader.
Uploads an mp4 as a YouTube Short.
Requires GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REFRESH_TOKEN env vars.
"""
import os
import sys
import argparse
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

def main():
    parser = argparse.ArgumentParser(description="YouTube API Uploader")
    parser.add_argument("--file", required=True, help="Absolute path to .mp4 file")
    parser.add_argument("--title", required=True, help="Video title")
    parser.add_argument("--description", required=True, help="Video description")
    parser.add_argument("--tags", required=False, default="", help="Comma separated tags")
    args = parser.parse_args()

    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        print("ERROR: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REFRESH_TOKEN must be set.", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.file):
        print(f"ERROR: Video file not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    try:
        # Reconstruct OAuth2 credentials using the refresh token
        credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret
        )

        youtube = build("youtube", "v3", credentials=credentials)

        print(f"Uploading to YouTube: {args.title}...")
        
        # Tags formatting
        tags = [tag.strip() for tag in args.tags.split(",")] if args.tags else []

        body = {
            "snippet": {
                "title": args.title,
                "description": args.description,
                "tags": tags,
                "categoryId": "10" # Music
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False
            }
        }

        media = MediaFileUpload(args.file, chunksize=-1, resumable=True, mimetype="video/mp4")

        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        response = request.execute()
        print(f"SUCCESS: YouTube Video Uploaded! Video ID: {response.get('id')}")

    except HttpError as e:
        print(f"YOUTUBE API ERROR: {e.resp.status} - {e.content}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"UNEXPECTED ERROR: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
