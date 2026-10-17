# Method details and O2 reference numbers

## Skin measurement (`concert_wb.py measure`)

- **Where skin comes from:** Face boxes come from `photo.inspect` → `meta.regions` (kind `Face`), normalized to the full upright frame. Exports are cropped, so boxes are mapped through `develop.crop.geometry.rect`.
- **Sample area:** The cheek and nose area, which is the box's central 50% horizontally and from 40% to 75% of its height. This avoids hair, eyes, teeth and mouth corners. Pixels darker than 25 or with a channel at 250 or above are dropped.
- **Per face:** The median sRGB is converted to linear, then reported as log2(R/G) and log2(B/G).
- **Per photo:** Faces are averaged, weighted by box width; boxes under 12px wide are skipped.
- **Noise:** About ±0.05–0.07 between frames of one burst under the same light.

## Why compare at a fixed white balance

The iPhone's as-shot white balance differed by up to 2500K between frames of one song (4444K vs 7063K at the O2). Copy-pasting white balance in LightCraft copies absolute Temp/Tint values, so the question to answer is "which photos share a light", not "which look alike as shot". Rendering every photo at 5000K / tint 0 answers that directly.

## Slider model (`calibrate`, `solve`, `verify`)

- **What it predicts:** The shift in skin log-ratios from the 5000/0 baseline.
- **Inputs:** Mired offset `m = 1e6/T − 200` and tint `t`.
- **Form:** Quadratic in both: `[m, t, m·t, m², t²] @ coef`.
- **Fitting:** Least squares over about 22 photos, each set to a different grid point. Each photo's shift is measured against its *own* baseline render, which removes skin, make-up and angle differences between photos.
- **Excluded sample:** 3500K/+100 is left out of the grid because blue clips there; including it raised the B/G error from 0.03 to 0.15.
- **Correction:** `verify` corrects from the current setting using model *differences*, which cancels most of the model's local bias. One pass got the main groups within 0.03 of target; deep amber (B/G −2.8 at baseline) needed two.

Typical slider behaviour around 5000K:
- Tint +30 moves R/G by about +0.2 and B/G by about +0.35.
- Lowering Temp raises B/G and lowers R/G.
- Green-looking stage skin needs mostly magenta tint, plus some warming.

## Balanced strength (`solve --strength balanced`)

- **The two extremes:** `effect_match = target − baseline_skin` is what fully matches the reference skin. "Whites after match" is how far white objects would then sit from neutral; it's each white reading plus its group's `effect_match`.
- **Balanced:** `effect_match − whites_after_match / 2`, which is halfway to neutral whites.
- **Why one median works:** Under a skin match, the whites offset depends on how the LEDs render skin relative to white rather than on the light's colour. At the O2 it was nearly constant across lights, at about +0.53 R/G and +0.27 B/G, so the default `--whites-scope global` uses the median of all solid readings for every group.
- **When white readings mislead:** Groups with no white clothing, or where the "whites" are really hair, skin or a video screen (the cool/blue ballad group at the O2), would otherwise get wrong values.

## O2 Arena, 2026-10-16: numbers to sanity-check against

The set was LE SSERAFIM, shot on an iPhone 17 Pro as DNGs and processed in LightCraft process 2.

**Reference skin as Jon saw it** (IMG_5342/5351/5352, pink stage light, as shot): `[0.98, −0.17]`.

**Groups at the 5000/0 baseline, and the Balanced value applied:**

| Group | Baseline skin | Balanced Temp/Tint |
|---|---|---|
| Warm white, yellowest (opening, start of set 2, 20:41) | [0.32, −0.89] | 5000 / +55 |
| Warm white, main show | [0.34, −0.78] | 5250 / +51 |
| Warm white, encore | [0.31, −0.70] | 5400 / +50 |
| Amber (yellow-plaid section) | [0.42, −1.72] | 4350 / +76 |
| Deep amber (IMG_5321, 5316, 5317) | [0.53, −2.77] | 3950 / +90 |
| Cool / blue (ballad, side-stage) | [−0.06, −0.18] | 7650 / +55 |
| Neutral white (IMG_5340, 5356, 5337) | [0.21, −0.16] | 6950 / +31 (5337: 7000 / +15) |

**Skin after Balanced:** about `[0.71, −0.30]` in every group. White T-shirts and confetti read about +0.25 R/G, which looks slightly warm. Jon reviewed the result and couldn't improve on it by hand.

**Full skin match** (rejected) needed, for example, 5750/+79 for the main show; whites then read +0.55 R/G, clearly pink.

**Odd cases at the O2:**
- IMG_5374: the face read cool, but its white T-shirt matched the encore light, so it was given the encore value.
- IMG_5198 and 5196: confetti covered the faces, so they were placed by time.
- IMG_5168: a blue-mood ballad shot, flagged for Jon in case he wanted the cold look kept.
