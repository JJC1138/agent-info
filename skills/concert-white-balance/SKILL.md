---
name: concert-white-balance
description: Fix stage-lighting skin tones across a whole concert photo set in LightCraft (via the lightcraft-app MCP) by grouping photos by stage light, measuring skin colour from face boxes, calibrating the Temp/Tint sliders and applying a "Balanced" white balance per group. Use this whenever Jon wants white balance or skin-tone fixes on concert, gig, idol or stage photos; mentions green, yellow or sallow skin, LED stage-light casts or "make the skin look like these ones"; wants photos grouped into albums by lighting so he can copy-paste white balance; or adds more photos (e.g. the 3-star keepers) to a set already balanced this way. Use it even if he only says "do the white balance pass" or "same white balance as before".
---

# Concert white balance in LightCraft

Stage LEDs render skin green-yellow, and the iPhone's as-shot white balance guesses differently on every frame, even within a burst. Jon's manual method is to eyeball one photo and paste its white balance onto others under the same light. This skill does the grouping and drafts the values, so his job shrinks to a quick review.

The core ideas, and why they matter:

- **Compare photos at one fixed white balance (5000K, tint 0), not as shot.** As-shot values differ per frame, so photos that look different as shot can share a light, and vice versa. Photos under the same light want the same *absolute* Temp/Tint, which is exactly what copy-pasting white balance does.
- **Measure skin, not the whole frame.** LightCraft's face boxes locate skin. The cheek area's linear-light log2(R/G) and log2(B/G) are what white balance scales, so they move predictably with the sliders.
- **Target "Balanced", not an exact match.** Jon picks reference photos whose skin he likes. Matching them exactly needed tint around +80 at the O2 (2026-10-16), which turned white clothes and confetti pink-purple, because his references happened to be under pink light. Shown Original | Balanced | Skin match, he chose **Balanced**: skin moved halfway in slider-effect space, so white objects end up only slightly warm. Use Balanced by default; offer the comparison only if he asks or the set looks unusual.

`references/method.md` has the measurement and model details, plus the O2 numbers to sanity-check against. `references/lightcraft.md` covers the MCP commands and quirks. Read them when a step below doesn't behave as described.

## Ground rules

- **Only touch white balance.** Jon does crops and exposure himself, often after this pass, so leave them alone. Never use `develop.reset`, because it wipes crops and exposure too.
- **Back up first, restore after every temporary change.** Baseline renders need every photo at 5000/0 for a moment. Make that change in a *single* `develop.set` call so it's one undo step, then `edit.undo` and verify every photo against the backup before doing anything else.
- **Ask Jon for the reference photos** (2–3 whose skin he likes) and which ratings to include, unless he already said. Don't guess references: what looks natural to him is the whole point.
- **Flag mood shots instead of silently "fixing" them**, e.g. a blue-lit ballad where cold light suits the song. Apply the group value, but name them in your report so he can revert them to As Shot.
- **Leave non-people shots as shot**, such as title screens and big-screen captures. There's no skin to balance.

## Setup

1. **Load the LightCraft tools.** Run `ToolSearch` with "lightcraft"; it waits for the server to connect. Load `command_batch`, `export`, `query_photos`, `select_photos` and `render_preview` as needed.
2. **Create a Python env in the scratchpad.** The system Python lacks Pillow:
   ```bash
   python -m venv "$SCRATCH/venv" && "$SCRATCH/venv/Scripts/python.exe" -m pip install -r ~/.claude/skills/concert-white-balance/scripts/requirements.txt
   ```
   Run the scripts with `"$SCRATCH/venv/Scripts/python.exe" -I ~/.claude/skills/concert-white-balance/scripts/concert_wb.py <subcommand> ...`. The Windows console is cp1252 and `-I` ignores `PYTHONIOENCODING`, so keep printed text ASCII.
3. **Make a work dir in the scratchpad.** Large MCP results (any `photo.inspect` batch) get saved under `tool-results/`; copy them into the work dir with sensible names.

## Workflow

### 1. Gather and back up

- **List the photos.** Use `query_photos` with a filter, e.g. `{"rating": 4, "ratingOp": "atLeast"}` or `{"rating": 3, "ratingOp": "exactly"}`, `limit` 200.
- **Inspect them.** Run `command_batch` with one `photo.inspect` step per id. Inspect records carry face `regions`, the crop rect, the current `wb` and `as_shot_wb`.
- **Back up white balance:** `concert_wb.py backup-wb wb_backup.json inspect.json`.
- **Export "before" renders now.** Export every photo at its current settings, with `ids`, `dir: before/`, `naming: "{name}"`, `longEdge: 1000`, `metadata: "none"`, `conflict: "overwrite"`. These become the before side of the before/after sheets. The reference photos' renders here also define the target.

### 2. Baseline renders at 5000K / 0

- **Apply the baseline:** one `command_run` of `develop.set {ids: [...all...], values: {wb.temp: 5000, wb.tint: 0}}`.
- **Export:** same export settings as step 1, into `base/`.
- **Undo:** `command_run edit.undo`, which should report `{"undone": "Edit"}`.
- **Verify:** re-run the `photo.inspect` batch, then `concert_wb.py check-wb wb_backup.json inspect_after.json`. Don't continue until it reports that all white balances match.

### 3. Measure

```bash
concert_wb.py measure before/ skin_before.json inspect.json   # gives the target: median of the reference photos as Jon sees them
concert_wb.py measure base/   skin_base.json   inspect.json
concert_wb.py whites  base/   whites_base.json inspect.json
```

The target is the median `[R/G, B/G]` of the reference photos in `skin_before.json`; at the O2 it was about `[0.98, -0.17]`. Photos with no usable face, because of confetti, a turned head or a tiny face, are listed so you can place them by hand.

### 4. Group by light

Sort photos by capture time, then read their baseline skin values:

- **The same song usually means the same light.** Bursts seconds apart share light even if one face measures oddly. Measurement noise within a burst is about ±0.07, so differences under ~0.1 in either number are the same light, or close cousins.
- **Expect a few families.** At the O2 there were warm white (B/G about −0.7 to −0.9), amber (about −1.7), deep amber (about −2.8), cool/blue (R/G about −0.1) and neutral white (about 0.2, −0.15). The reference shots were under pink light (R/G about +1.2).
- **Split big families by show section** when the sections differ consistently (about 0.1 or more). Jon then gets intuitive groups like "main show" and "encore", and one pasted value fits each.
- **Place photos without a usable face** with their time neighbours.
- **Check by eye:** `concert_wb.py montage base/ groups.json montage_base.jpg inspect.json`. Within a row, faces should look alike.

Write `groups.json` as `{"2 · Warm white, main show": [ids...], ...}`, numbered and descriptively named. The references go in their own group (album "1 · Pink light (reference)" at the O2), excluded from solving.

### 5. Albums

Use `album.create {name: "White balance groups", folder: true}`, then one `album.create {name, parent}` per group, `album.addPhotos {id, ids}`, and `album.setCover {id, photo}` with the clearest, largest face in the group. Jon liked this, because it's where he'd tweak one photo and paste to the rest.

### 6. Slider model

- **Reuse the bundled model when it fits.** `assets/model_iphone17pro_lightcraft-process2.json` was fitted for iPhone 17 Pro DNGs on LightCraft process 2 (`develop.get` reports `process`). Check that the camera, process version and baseline 5000/0 all match.
- **Otherwise, calibrate.** It takes two tool calls plus a script run:
  1. Pick 22 photos from the biggest group, then `concert_wb.py grid grid.json <22 ids>`. This prints `command_batch` steps that set each photo to a different Temp/Tint; run them.
  2. Export those 22 into `calib/`, run `measure` on that folder into `skin_calib.json`, then `concert_wb.py calibrate skin_base.json skin_calib.json grid.json model.json`. Expect an RMS error of about 0.02 to 0.03.
  3. Leave the calibration photos as they are. Step 7 sets their final values.

### 7. Solve and apply

```bash
concert_wb.py solve model.json groups.json skin_base.json solution.json --base-whites whites_base.json --target <RG> <BG>
concert_wb.py steps solution.json --albums albums.json   # prints command_batch steps; albums.json maps group name -> album id
```

Run the printed steps with `command_batch`. Expect strong magenta tint for warm-white light; that's normal. O2 Balanced values were warm white 5000–5400/+50–55, amber 4350/+76, deep amber 3950/+90, cool/blue 7650/+55 and neutral white 6950/+31.

### 8. Verify, fix and show

- **Re-measure.** Export everything to `after/`, then `measure after/ skin_after.json` and `concert_wb.py verify model.json solution.json skin_after.json`.
- **Correct groups that are off.** Group medians more than ~0.05 off get a suggested corrected value; apply it to the whole group. The model is least accurate at the extremes, and deep amber took a second iteration at the O2.
- **Look at outliers before correcting them.** Confetti on a face, a face half in shadow, or a second face lit differently can all mislead the measurement. If the photo's white clothing (`whites after/ ...`) agrees with its group, the face reading is wrong, so keep the group value.
- **Check white objects.** After Balanced, whites should read about half of the "whites after match" median that `solve` prints: about +0.25 R/G at the O2. A clearly pinker white T-shirt means that photo needs its own value.
- **Build the sheets:** `montage after/ ...` for faces, and `beforeafter before/ after/ ba.jpg <8–12 names across groups>` for whole photos. Look at them yourself, then send them with `SendUserFile`.

### 9. Report

- **Table:** one row per album with its Temp/Tint, and any photo with its own value.
- **Flags:** mood shots, extreme-light photos, and anything left as shot.
- **How to undo:** set white balance to As Shot in LightCraft, or restore exact values from `wb_backup.json` with `develop.set`. The mode becomes custom, but the look is identical.

## Adding photos to an already-balanced set

This is common when the 3★ keepers come after the 4–5★ ones.

- **Gather and measure as above:** steps 1–3 for the new photos only.
- **Assign each to the nearest existing group in baseline skin space.** When two groups are within ~0.1, or the face reading is unreliable, prefer the group of its time neighbours.
- **Apply and verify:** give each photo its group's current value, add it to the album, then verify. Reuse the existing model and solution values. Don't re-solve groups Jon has already reviewed.
