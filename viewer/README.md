# Possession Lab (local viewer)

One HTML file that plays a match with our predicted possession labels: video (or a tactical
pitch), live possession share, head-to-head shape stats, the full-match H/A/D timeline and a
clickable spell list. It runs offline and holds no match content itself (rule R1).

## Use

```bash
# 1. make the file the page loads (writes viewer/out/, git-ignored)
python scripts/export_viewer.py --match metrica1                     # external demo (+ reference labels)
python scripts/export_viewer.py --match BAR-ATH --predictor learned  # the match — humans only

# 2. open it
cd viewer && python -m http.server 8765
#    http://127.0.0.1:8765/possession_viewer.html?data=out/BAR-ATH_learned.json
#    then "Load video" → the match video. Use "Sync" if the labels are offset.
```

Without the server, open the HTML directly and use **Load data** + **Load video** (or drop
both files on the page). The page warns when the video length and the loaded file disagree,
which means they come from different matches.

## What "Load data" expects

A JSON file written by `scripts/export_viewer.py` (`mtah.viewer.viewer_payload`):

| key | content |
|---|---|
| `meta` | `home`, `away`, `fps`, `step` (tracking sampled every `step` frames), `n_frames`, `pitch` [length, width] m, `periods` [[start, stop], …], `source` |
| `team` | team per tracked slot: 0 home, 1 away (referees dropped) |
| `players` | base64 little-endian int16, shape (samples, slots, 2), decimetres; −32768 = not tracked |
| `ball` | same encoding, shape (samples, 2) |
| `pred` | model labels as runs `[[start, stop, "H"\|"A"\|"D"], …]` covering every frame |
| `truth` | optional reference labels, same shape (external matches only) |

Frame *i* of the file is video frame *i* (submission row *i*), at `fps` frames per second.

## Tests

`make e2e` drives the page in your installed Chrome with Playwright, on synthetic tracking.
