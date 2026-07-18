#!/usr/bin/env bash
# make_reel.sh - Generates a 1080x1920 vertical .mp4 from an audio file and cover image.
# Usage: ./make_reel.sh <cover_image> <audio_file> <output_mp4>

set -e

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <cover_image> <audio_file> <output_mp4>"
    exit 1
fi

COVER="$1"
AUDIO="$2"
OUTPUT="$3"

echo "=== Generating 1080x1920 Reel ==="
echo "Cover: $COVER"
echo "Audio: $AUDIO"

# ffmpeg command explanation:
# 1. Inputs: loop the image, input the audio.
# 2. Filter_complex:
#    - Scale original image to 1080x1920 with cropping/stretching, then blur it heavily to act as background [bg]
#    - Scale original image to fit within 1080x1920 without cropping [fg]
#    - Overlay [fg] on top of [bg] centered.
# 3. Codec: libx264, aac, yuv420p.
# 4. -shortest: stops encoding when the audio finishes.
# 5. -tune stillimage to optimize for static frame encoding.

ffmpeg -y -loop 1 -i "$COVER" -i "$AUDIO" -filter_complex \
  "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=luma_radius=min(h\,w)/20:luma_power=1:chroma_radius=min(cw\,ch)/20:chroma_power=1[bg]; \
   [0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg]; \
   [bg][fg]overlay=(W-w)/2:(H-h)/2" \
  -c:v libx264 -tune stillimage -c:a aac -b:a 192k -pix_fmt yuv420p -shortest "$OUTPUT"

echo "=== Reel generated successfully: $OUTPUT ==="
