#!/usr/bin/env bash
# Cut the hero film from the rendered shots (render.mjs) and the HUD overlay (hud-overlay.mjs).
#   tools/hero/assemble.sh <shotDir> <hudDir> <out.mp4>
set -euo pipefail
shots="$1"; hud="$2"; out="$3"
ffmpeg -v error -y -i "$shots/onboard.mp4" -framerate 30 -i "$hud/hud-%04d.png" \
  -filter_complex "[0:v][1:v]overlay=shortest=1,format=yuv420p" -c:v libx264 -preset slow -crf 16 "$shots/onboard-hud.mp4"
list="$shots/cut.txt"; : > "$list"
for name in top bow quarter side onboard-hud chase dock; do echo "file '$name.mp4'" >> "$list"; done
total=$(for name in top bow quarter side onboard-hud chase dock; do ffprobe -v error -show_entries format=duration -of csv=p=0 "$shots/$name.mp4"; done | paste -sd+ | bc)
fade=$(echo "$total - 0.6" | bc)
ffmpeg -v error -y -f concat -safe 0 -i "$list" -vf "fade=t=in:st=0:d=0.5,fade=t=out:st=$fade:d=0.6" -an \
  -c:v libx264 -preset slow -crf "${HERO_CRF:-23}" -pix_fmt yuv420p -movflags +faststart "$out"
echo "wrote $out ($total s)"
