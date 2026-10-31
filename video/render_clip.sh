#!/usr/bin/env bash
# Live broadcast shot -> TV-style rewind -> slow-motion 3D replay, assembled into one clip.
# Motion: IDSSE/DFL open tracking (CC-BY 4.0). Never the competition match.
set -euo pipefail
cd "$(dirname "$0")/.."

B="${BLENDER:-$HOME/Applications/Blender.app/Contents/MacOS/Blender}"
STADIUM="video/assets/blendswap/Soccer Arena Large 03.blend"
MOMENT="video/out/moment_J03WMX_13222.json"
OUT=video/out/clip
LIVE_START=40; LIVE_END=140; REPLAY_START=85; REPLAY_END=125; WIDTH=1280

mkdir -p "$OUT/live" "$OUT/replay" "$OUT/rewind"
echo "live render $(date +%T)"
"$B" -b "$STADIUM" -P video/scene_v3.py -- "$MOMENT" "$OUT/live" $LIVE_START $LIVE_END $WIDTH broadcast \
  > "$OUT/live.log" 2>&1
echo "replay render $(date +%T)"
"$B" -b "$STADIUM" -P video/scene_v3.py -- "$MOMENT" "$OUT/replay" $REPLAY_START $REPLAY_END $WIDTH replay \
  > "$OUT/replay.log" 2>&1

echo "assemble $(date +%T)"
# rewind = live frames from the end back to the replay start, every 2nd frame (2x speed)
n=0
for ((f=LIVE_END; f>=REPLAY_START; f-=2)); do
  cp "$(printf "$OUT/live/f_%04d.png" $f)" "$(printf "$OUT/rewind/r_%04d.png" $n)"; n=$((n+1))
done

ffmpeg -loglevel error -y -framerate 25 -start_number $LIVE_START -i "$OUT/live/f_%04d.png" \
  -c:v libx264 -pix_fmt yuv420p -crf 17 "$OUT/1_live.mov"
ffmpeg -loglevel error -y -framerate 25 -i "$OUT/rewind/r_%04d.png" \
  -vf "eq=saturation=0.6:contrast=1.1,drawbox=x=40:y=40:w=230:h=56:color=black@0.55:t=fill,drawtext=text='REPLAY':x=60:y=52:fontsize=34:fontcolor=white:font=Helvetica" \
  -c:v libx264 -pix_fmt yuv420p -crf 17 "$OUT/2_rewind.mov" \
  || ffmpeg -loglevel error -y -framerate 25 -i "$OUT/rewind/r_%04d.png" -vf "eq=saturation=0.6" \
       -c:v libx264 -pix_fmt yuv420p -crf 17 "$OUT/2_rewind.mov"
ffmpeg -loglevel error -y -framerate 25 -start_number $((REPLAY_START * 3)) -i "$OUT/replay/f_%04d.png" \
  -c:v libx264 -pix_fmt yuv420p -crf 17 "$OUT/3_replay.mov"
printf "file '%s'\n" 1_live.mov 2_rewind.mov 3_replay.mov > "$OUT/list.txt"
ffmpeg -loglevel error -y -f concat -safe 0 -i "$OUT/list.txt" -c copy video/out/ghost_ball_clip_v1.mov
echo "done $(date +%T)"
