# Vision Video: "GHOST BALL — The Replay"

Status: **DRAFT, awaiting approval** · 2026-10-31 · personal piece (audience: the team lead only)

## 1. Intent

A ~20-second, football-TV-grade film that makes the team's goal feel real: the competition's required
outcome (every one of 199,319 frames labelled, a valid file, spellF1 above the floor, top 20 →
Barcelona) shown the way real football shows a decisive moment: a live broadcast shot, then a
**freeze-frame and 3D avatar replay** like FIFA's semi-automated offside animations, Viz Libero and
Piero, and EA FC's replay camera.

The **wow** is one idea: *the ball disappears and we still know who has it.* That is literally the
challenge (the ball is invisible on 41% of frames), shown as a broadcast replay.

## 2. Goals / non-goals / anti-goals

- **Goals:** looks like real football TV (camera grammar, glass/flat broadcast graphics), real
  player motion, one clear story, ends on the required outcome, 1080p MP4.
- **Non-goals:** photoreal faces or likenesses, real club crests or league logos, commentary voice,
  a publishable or marketing asset.
- **Anti-goals (failure even if pretty):** any frame, coordinate or derivative of the BAR–ATH match
  (rule R1 and the data terms); a dizzy "board-game" tilt that doesn't read as TV; more than one
  idea competing for attention.

## 3. Hard constraints

- **Motion source: IDSSE / DFL open Bundesliga tracking (CC-BY 4.0)**, already cached in
  `~/.cache/mtah/idsse` and loaded by `mtah.io.external.load_idsse`. Attribution goes in the end card.
- Never touches `data/`. All renders are external-data only, so Claude may view them.
- Machine: Apple M1, 16 GB RAM. Blender (Eevee) for 3D, ffmpeg for assembly.
- Lives in `video/` (scripts committed; renders in `video/out/`, git-ignored).

## 4. Story beats (~21 s @ 25 fps, 1920×1080)

| t (s) | Shot | What happens | Graphics | Sound |
|---|---|---|---|---|
| 0–4 | **Main broadcast camera**: halfway line, ~20 m up, 12–15° down, telephoto following the ball | a real attacking move; avatars run, ball visible | flat score bug top-left (BAR · 62:14 · ATH), "● MODEL LIVE" | stadium ambience |
| 4–7 | same camera | **ball vanishes**; a dashed ghost ball keeps following; a yellow AR ring on the grass under the carrier | glass lower third: possession bar keeps updating; caption "Ball not visible · 41% of the match" | low riser |
| 7–8 | same | an interception happens → **freeze frame**, white flash, slight desaturation | "REPLAY" sting | whoosh + impact |
| 8–14 | **3D replay camera** (Libero-style flight) | swings off the broadcast angle to a low hero angle behind the play, 0.3× slow motion through the switch; the ring flips team colour and an **"A" stamps onto the grass** | AR labels in perspective | heartbeat bass, hit on the switch |
| 14–17 | crane to top-down tactical | the pitch flattens and the whole match becomes a **possession barcode** ("match DNA") streaming across | frame counter racing to 199,319 | ticks accelerating |
| 17–21 | broadcast angle, wide | **glass slates rise out of the pitch**: 199,319 FRAMES · 100% LABELLED · SPELL F1 0.4x · **TOP 20**; floodlights flare | end card + "Tracking: IDSSE/DFL, CC-BY" | crowd roar, hold |

Scores and rank are placeholders until results day (swappable text).

## 5. Look

- **Camera grammar from TV:** main cam on halfway line at broadcast height; offside-cam angle
  allowed for the freeze; replay flight is the only "free" camera move.
- **Graphics:** LaLiga-style flat, minimal typography for the bug; frosted glass (blur plus a thin
  light border) for the lower third and slates; AR elements drawn on the grass in perspective.
- **Colours:** home = blaugrana split, away = red/white stripes (generic kits, no crests); AR
  accent = broadcast yellow `#FFD23F`.
- **Stadium:** stylised bowl, crowd cards, LED boards, four floodlight banks, evening light.

## 6. How it gets made (decided)

- **Blender, driven by a Python script** (`video/build_scene.py`, headless): pitch, stadium,
  avatars, ball and cameras, with players keyed from the tracking at 25 fps.
- **Avatars:** rigged low-poly footballers with run and idle cycles blended by speed. Source:
  Adobe Mixamo (free, needs the user's Adobe login). **Fallback:** stylised mannequins without a
  rig, so the pipeline never blocks on an account.
- **Graphics overlay:** rendered as transparent PNG sequences and composited with ffmpeg; the
  glass blur comes from blurring the underlying frame region.
- **Music/SFX:** royalty-free (e.g. Pixabay/YouTube Audio Library), picked by the user.

## 7. Left to the builder

- Which IDSSE moment to use: pick a ~6 s sequence containing a clean interception (the possession
  label flips between teams) in open play.
- Exact easing curves, the freeze-flash timing within ±3 frames, and render sampling for M1 speed.

## 8. Process

1. **Spike (throwaway):** 4-second test render: IDSSE moment, mannequins, broadcast camera, to
   check look and M1 render time. Shown to the user before any polish.
2. Full plan (superpowers:writing-plans) → build → render → review.
