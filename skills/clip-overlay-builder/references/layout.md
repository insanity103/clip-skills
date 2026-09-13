# Overlay layout reference

## Spec fields (build_overlay.py)

Top level: `margin` (px kept clear at left and right, default 60), `defaults` (applied to every element),
`elements` (drawn in order).

| Field | Elements | Meaning |
|---|---|---|
| `id` | all | name used by `below`, by `overlay.boxes.json` and by `hud_map.py` collisions |
| `type` | all | `text` or `image` |
| `y` | all | top edge in px; or place with `below` |
| `below` + `gap` | all | top edge = bottom of element `below` + `gap` px |
| `align` | all | `center` (default), `left`, `right` - left/right sit against the margin |
| `text` | text | written exactly as given, case kept |
| `size` | text | font size px; `min_size` (default 70% of size) is the shrink floor before wrapping |
| `max_lines` | text | wrap limit (default 2); beyond it the text shrinks further |
| `font` | text | .ttf/.otf/.ttc path or family name, or a list of them - the first installed one is used (recorded in boxes.json); none installed is an error. Default chain: DIN Condensed Bold (macOS), Barlow/Oswald/Roboto Condensed, DejaVu Sans Condensed Bold (most Linux), Liberation Sans Narrow Bold |
| `color` | text | hex colour |
| `stroke`, `shadow` | text | outline width and shadow strength (defaults 6 and 0.85) so light text survives bright footage |
| `src`, `width` | image | image path (relative to the spec) scaled to `width`, aspect kept |

`overlay.boxes.json` records each element's drawn box, final size and wrapped lines, plus `safe_zone_hits`.

## Platform safe zones used by --check-safe

Approximations - no platform publishes these, and they vary by device and caption length. `--zones` adds or
overrides zones: `{"tiktok": {"caption and username": [0, 1500, 1080, 1920]}}`.

| Platform | Top bar | Bottom caption area | Action buttons |
|---|---|---|---|
| tiktok | [0, 0, 1080, 130] | [0, 1536, 1080, 1920] | [960, 600, 1080, 1536] |
| reels | [0, 0, 1080, 108] | [0, 1600, 1080, 1920] | [960, 900, 1080, 1600] |
| shorts | [0, 0, 1080, 140] | [0, 1632, 1080, 1920] | [945, 900, 1080, 1632] |

Worst cases (long captions, small phones) are larger - see the campaign producer's `references/platforms.md`. The
approved MW4 layout (text from y 150, logo at y 1340-1472) cleared all three sets above. Instagram's main feed also
shows Reels cropped to 4:5, cutting about 285 px from the top and bottom: keep required text below y ≈ 290 if feed
appearance matters.

## Brief placement rules

- Corner logos: `"align": "left"` or `"right"` plus `"y"`; the margin sets the side gap. Top corners must clear the
  top bar (y ≥ 140); bottom corners sit where captions and the right-hand buttons are - put them just above the bottom
  zone (bottom edge ≤ 1530) and on the left if the brief allows either side.
- Minimum or maximum logo width ("at least 120 px", "no more than 15% of the frame" = 162 px): set `width`.
- Not supported yet: a backing bar behind text ("dark semi-transparent bar") and a check that overlays cover under
  N% of the frame. Elements may not overlap, so a bar cannot be faked with an image element - raise it with the user.

## Logos (prepare_logo.py)

- Background (black, white or checkerboard) is detected from the image border; alpha comes from each pixel's
  distance to it and colour is un-premultiplied, so edges keep their true colour.
- `--floor` (default 16) drops faint JPEG noise near the background.
- Brand portals often export "large" previews of transparent logos with the checkerboard burned in. Light ink on those
  cannot be recovered: take the dark-ink variant and `--recolor-neutral "#FFFFFF"` (colours stay, neutrals repaint).

## HUD detection (hud_map.py)

- Analyse a draft WITHOUT the overlay; non-9:16 input goes through the same centred crop as the renderer (`--x`).
- HUD and banners are edges that stay put while the camera moves; samples where the camera is still are skipped
  (the whole scene is still then).
- Persistent HUD = on screen in 80% or more of moving samples; banners = fixed-place edges lasting ~0.5-6 s.
- Settings were chosen by scoring variants against hand-labelled frames (0.5 s resolution) from two real clips:
  270x480 analysis, 3-sample stability, cell density 0.10, persistent share 0.8 -> precision 0.88, recall 0.95.
  The labelled data and scorer live in the build folder (`~/Downloads/clip-skills/tests/hud_calibration/`) if it
  still exists; re-score there before changing a constant.
- Collisions merge into one time range per element when events are under 0.5 s apart; `--margin` (default 16 px)
  pads overlay boxes before testing overlap.
