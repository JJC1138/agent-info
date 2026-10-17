"""Measurement and solving helpers for the concert-white-balance skill.

Skin colour is measured as linear-light log2(R/G) and log2(B/G) of the cheek area inside LightCraft's face boxes. A white balance change scales R and B relative to G, so these two numbers move predictably with the Temp and Tint sliders. Photos under the same stage light read the same when rendered at one fixed white balance, even though the iPhone's as-shot white balance varies from frame to frame.

Every subcommand reads LightCraft output saved from the MCP tools (`photo.inspect` batches and exported JPEGs) and writes JSON or images, so the model can drive LightCraft between steps. Run `python concert_wb.py <subcommand> -h` for arguments.
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

# The fixed white balance every baseline render uses. The fitted slider model predicts shifts relative to it, so changing it means recalibrating:
BASE_TEMP, BASE_TINT = 5000, 0

# The calibration grid. 3500K/+100 is left out because blue clips there and the sample distorts the fit; 5000K/0 is the baseline itself:
GRID_TEMPS = [3500, 4000, 4500, 5000, 5500, 6500]
GRID_TINTS = [0, 30, 60, 100]


def load_inspect(paths):
    """Photo records keyed by id, from one or more saved `photo.inspect` batch results."""
    photos = {}
    for path in paths:
        batch = json.load(open(path, encoding='utf-8'))
        for r in batch['results']:
            if not r.get('ok'):
                continue
            p = r['result']
            # The MCP sometimes hands back a nested result as a JSON string rather than an object:
            if isinstance(p, str):
                p = json.loads(p)
            photos[p['id']] = p
    return photos


def export_name(photo):
    return os.path.splitext(photo['file_name'])[0]


def linear(srgb):
    c = np.asarray(srgb, float) / 255
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def face_boxes(photo, width, height):
    """Face boxes in the exported (cropped) image's pixel coordinates, largest first.

    LightCraft stores face regions normalized to the full upright frame, and exports are cropped, so each box is mapped through the crop rect. Straightened crops aren't accounted for; the box is then slightly off, which only matters for small faces.
    """
    cr = photo['develop']['crop']['geometry']['rect']
    cw, ch = cr['x1'] - cr['x0'], cr['y1'] - cr['y0']
    boxes = []
    for reg in photo['meta'].get('regions', []):
        if reg.get('kind') != 'Face':
            continue
        fr = reg['rect']
        x0, x1 = (fr['x0'] - cr['x0']) / cw * width, (fr['x1'] - cr['x0']) / cw * width
        y0, y1 = (fr['y0'] - cr['y0']) / ch * height, (fr['y1'] - cr['y0']) / ch * height
        if x1 < 0 or y1 < 0 or x0 > width or y0 > height:
            continue
        boxes.append((x0, y0, x1, y1))
    return sorted(boxes, key=lambda b: b[0] - b[2])


def model_features(temp, tint):
    # Mired is closer to linear in perceived colour shift than Kelvin, so the model works in mired offset from the baseline:
    m = 1e6 / np.asarray(temp, float) - 1e6 / BASE_TEMP
    t = np.asarray(tint, float) - BASE_TINT
    return np.stack([m, t, m * t, m * m, t * t], -1)


def load_model(path):
    return np.array(json.load(open(path))['coef'])


def solve_effect(coef, effect):
    """The Temp/Tint whose modelled shift from the baseline best matches `effect` (a log2 R/G, B/G pair)."""
    temps = 1e6 / np.linspace(1e6 / 16000, 1e6 / 2500, 800)
    tints = np.arange(-50, 151, 1)
    tt_temp, tt_tint = np.meshgrid(temps, tints)
    shifts = model_features(tt_temp, tt_tint) @ coef
    err = ((shifts - np.asarray(effect)) ** 2).sum(-1)
    k = np.unravel_index(err.argmin(), err.shape)
    return int(round(tt_temp[k] / 50) * 50), int(tt_tint[k]), float(np.sqrt(err[k]))


def cmd_backup_wb(a):
    photos = load_inspect(a.inspect)
    json.dump({pid: p['develop']['wb'] for pid, p in photos.items()}, open(a.out, 'w'), indent=0)
    print(f'backed up white balance of {len(photos)} photos to {a.out}')


def cmd_check_wb(a):
    backup = json.load(open(a.backup))
    photos = load_inspect(a.inspect)
    bad = [(pid, p['develop']['wb'], backup[str(pid)]) for pid, p in photos.items() if str(pid) in backup and p['develop']['wb'] != backup[str(pid)]]
    missing = [pid for pid in backup if int(pid) not in photos]
    for pid, now, was in bad:
        print(f'MISMATCH {pid}: now {now}, backup {was}')
    if missing:
        print(f'not in the after-inspect: {missing}')
    if bad or missing:
        sys.exit(1)
    print(f'all {len(backup)} white balances match the backup')


def cmd_measure(a):
    photos = load_inspect(a.inspect)
    out = {}
    for pid, p in photos.items():
        path = os.path.join(a.export_dir, export_name(p) + '.jpg')
        if not os.path.exists(path):
            continue
        img = np.asarray(Image.open(path).convert('RGB'))
        h, w = img.shape[:2]
        acc, wsum = np.zeros(3), 0.0
        for x0, y0, x1, y1 in face_boxes(p, w, h):
            bw, bh = x1 - x0, y1 - y0
            # Tiny faces are mostly noise and JPEG blocks:
            if bw < 12:
                continue
            # Sample the cheek and nose area: the centre of the box, below the eyes and above the mouth corners, avoiding hair and teeth:
            sx0, sx1 = int(max(0, x0 + bw * .25)), int(min(w, x1 - bw * .25))
            sy0, sy1 = int(max(0, y0 + bh * .40)), int(min(h, y1 - bh * .25))
            patch = img[sy0:sy1, sx0:sx1].reshape(-1, 3).astype(float)
            # Deep shadow and clipped highlights don't carry the light's colour reliably:
            keep = patch[(patch.mean(1) > 25) & (patch.max(1) < 250)]
            if len(keep) < 20:
                continue
            # Weight by face width: bigger faces are sharper, better lit and what a viewer judges skin by.
            acc += linear(np.median(keep, 0)) * bw
            wsum += bw
        if not wsum:
            continue
        r, g, b = acc / wsum
        out[pid] = [float(np.log2(r / g)), float(np.log2(b / g))]
    json.dump(out, open(a.out, 'w'))
    no_face = sorted(pid for pid, p in photos.items() if pid not in out)
    print(f'measured skin in {len(out)} photos; no usable face in {no_face}')


def cmd_whites(a):
    photos = load_inspect(a.inspect)
    out = {}
    for pid, p in photos.items():
        path = os.path.join(a.export_dir, export_name(p) + '.jpg')
        if not os.path.exists(path):
            continue
        img = np.asarray(Image.open(path).convert('RGB')).astype(float)
        h, w = img.shape[:2]
        # Exclude faces with a margin, so bright skin highlights aren't mistaken for white clothing:
        mask = np.ones((h, w), bool)
        for x0, y0, x1, y1 in face_boxes(p, w, h):
            mx, my = (x1 - x0) * .3, (y1 - y0) * .3
            mask[max(0, int(y0 - my)):max(0, int(y1 + my)), max(0, int(x0 - mx)):max(0, int(x1 + mx))] = False
        px = img[mask]
        mx, mn = px.max(1), px.min(1)
        sel = px[(mx < 245) & (mx > 140) & ((mx - mn) / np.maximum(mx, 1) < 0.30)]
        if len(sel) < a.min_pixels:
            continue
        # The brightest of the near-neutral pixels are the white T-shirts, hoodies and confetti rather than grey stage clutter:
        lum = sel.mean(1)
        top = sel[lum >= np.percentile(lum, 80)]
        r, g, b = linear(np.median(top, 0))
        out[pid] = [float(np.log2(r / g)), float(np.log2(b / g)), int(len(sel))]
    json.dump(out, open(a.out, 'w'))
    print(f'found white objects in {len(out)} of {len(photos)} photos')


def cmd_grid(a):
    """Assigns calibration white balances to photos under one light and prints the `command_batch` steps that apply them."""
    combos = [(t, n) for t in GRID_TEMPS for n in GRID_TINTS if (t, n) not in ((3500, 100), (BASE_TEMP, BASE_TINT))]
    if len(a.ids) < len(combos):
        sys.exit(f'need {len(combos)} photos for the grid, got {len(a.ids)}')
    grid = {pid: combo for pid, combo in zip(a.ids, combos)}
    json.dump(grid, open(a.out, 'w'))
    print(json.dumps([{'id': 'develop.set', 'params': {'ids': [pid], 'values': {'wb.temp': t, 'wb.tint': n}}} for pid, (t, n) in grid.items()]))


def cmd_calibrate(a):
    base = json.load(open(a.base_skin))
    calib = json.load(open(a.calib_skin))
    grid = json.load(open(a.grid))
    # Each photo's shift is measured against its own baseline render, which cancels out differences in skin, make-up and face angle between photos:
    rows = [(pid, tc, np.array(calib[pid]) - np.array(base[pid])) for pid, tc in grid.items() if pid in calib and pid in base]
    if len(rows) < 12:
        sys.exit(f'only {len(rows)} usable calibration samples; need at least 12')
    x = np.array([model_features(*tc) for _, tc, _ in rows] + [np.zeros(5)])
    y = np.array([d for _, _, d in rows] + [np.zeros(2)])
    coef, *_ = np.linalg.lstsq(x, y, rcond=None)
    resid = x @ coef - y
    print('rms fit error  R/G %.3f  B/G %.3f' % tuple(np.sqrt((resid ** 2).mean(0))))
    for (pid, tc, _), r in zip(rows, resid):
        if np.abs(r).max() > 0.1:
            print(f'  poorly fitted sample {pid} at {tc[0]}/{tc[1]}: residual {np.round(r, 2)}')
    json.dump({'base': [BASE_TEMP, BASE_TINT], 'features': 'mired offset m, tint t: [m, t, m*t, m^2, t^2]', 'coef': coef.tolist()}, open(a.out, 'w'), indent=1)
    print(f'wrote {a.out}')


def cmd_solve(a):
    coef = load_model(a.model)
    groups = json.load(open(a.groups))
    skin = json.load(open(a.base_skin))
    whites = json.load(open(a.base_whites)) if a.base_whites else {}
    target = np.array(a.target)
    bases = {name: np.median([skin[str(i)] for i in ids if str(i) in skin], 0) for name, ids in groups.items() if any(str(i) in skin for i in ids)}
    # "Balanced" sits halfway, in slider-effect space, between matching the reference skin and making white objects neutral. That needs how far white objects would sit from neutral once skin matches the reference ("whites after match"). Skin and white objects respond alike to the sliders, so it's each white reading shifted by its group's skin-match effect. Under a skin match the whites offset depends on how stage LEDs render skin relative to white, not on the light's own colour, so it was nearly the same in every light at the O2 (about +0.53 R/G, +0.27 B/G). That makes the median over all solid readings a good stand-in for groups whose own white readings are missing or are really hair, skin or a video screen:
    after_match = {}
    for name, ids in groups.items():
        if name not in bases:
            continue
        for i in ids:
            w = whites.get(str(i))
            if w and w[2] >= a.min_white_pixels:
                after_match.setdefault(name, []).append(np.array(w[:2]) + target - bases[name])
    all_after = [w for ws in after_match.values() for w in ws]
    if a.strength == 'balanced' and not all_after:
        sys.exit('balanced strength needs a whites file with at least one solid reading (try a lower --min-white-pixels)')
    global_after = np.median(all_after, 0) if all_after else None
    if global_after is not None:
        print(f'whites after match, median of {len(all_after)} readings: {np.round(global_after, 2)}  (O2 2026-10-16: [0.53 0.27])')
    out = {}
    for name, ids in groups.items():
        if name not in bases:
            print(f'{name}: no measured skin; assign these photos by time instead')
            continue
        base = bases[name]
        effect_match = target - base
        effect = effect_match
        source = 'match'
        n = sum(1 for i in ids if str(i) in skin)
        if a.strength == 'balanced':
            own = after_match.get(name, [])
            if a.whites_scope == 'group' and len(own) >= 3:
                w_after, source = np.median(own, 0), f'group whites ({len(own)})'
            else:
                w_after, source = global_after, 'global whites'
            effect = effect_match - w_after / 2
        temp, tint, resid = solve_effect(coef, effect)
        expected = base + effect
        out[name] = dict(ids=ids, temp=temp, tint=tint, expected_skin=expected.round(3).tolist(), whites_source=source)
        print(f'{name:32s} n={n:2d} base {np.round(base, 2)} -> {temp}/{tint:+d}  expected skin {np.round(expected, 2)}  ({source}, model residual {resid:.2f})')
    json.dump(out, open(a.out, 'w'), indent=1)


def cmd_steps(a):
    """`command_batch` steps that apply a solution's white balance per group, optionally adding each group to its album."""
    sol = json.load(open(a.solution))
    albums = json.load(open(a.albums)) if a.albums else {}
    steps = []
    for name, g in sol.items():
        steps.append({'id': 'develop.set', 'params': {'ids': g['ids'], 'values': {'wb.temp': g['temp'], 'wb.tint': g['tint']}}})
        if name in albums:
            steps.append({'id': 'album.addPhotos', 'params': {'id': albums[name], 'ids': g['ids']}})
    print(json.dumps(steps))


def cmd_verify(a):
    coef = load_model(a.model)
    sol = json.load(open(a.solution))
    after = json.load(open(a.after_skin))
    for name, g in sol.items():
        expected = np.array(g['expected_skin'])
        vals = {i: np.array(after[str(i)]) for i in g['ids'] if str(i) in after}
        if not vals:
            continue
        med = np.median(list(vals.values()), 0)
        # Correct from the current setting using model differences, which cancels most of the model's bias at that point:
        here = model_features(g['temp'], g['tint']) @ coef
        line = f'{name:32s} {g["temp"]}/{g["tint"]:+d}  measured {np.round(med, 2)} vs expected {np.round(expected, 2)}'
        if np.abs(med - expected).max() > 0.05:
            t, n, _ = solve_effect(coef, here + expected - med)
            line += f'  -> suggest {t}/{n:+d}'
        print(line)
        for i, v in vals.items():
            if np.abs(v - expected).max() <= a.tolerance:
                continue
            t, n, _ = solve_effect(coef, here + expected - v)
            print(f'    outlier {i}: {np.round(v, 2)} -> on its own {t}/{n:+d}  (check by eye: confetti on the face, odd angles and burst neighbours can mislead)')


def cmd_montage(a):
    photos = load_inspect(a.inspect)
    groups = json.load(open(a.groups))
    tile, pad, label_w, per_row = 96, 4, 190, 16
    rows = []
    for name, ids in groups.items():
        for k in range(0, len(ids), per_row):
            rows.append((name if k == 0 else '', ids[k:k + per_row]))
    sheet = Image.new('RGB', (label_w + per_row * (tile + pad), len(rows) * (tile + 18)), (35, 35, 35))
    d = ImageDraw.Draw(sheet)
    for ri, (name, chunk) in enumerate(rows):
        y = ri * (tile + 18)
        # PIL's default font is ASCII-only:
        d.text((6, y + tile // 2), name.encode('ascii', 'replace').decode(), fill=(255, 255, 255))
        for ci, pid in enumerate(chunk):
            p = photos.get(pid)
            if p is None:
                continue
            path = os.path.join(a.export_dir, export_name(p) + '.jpg')
            if not os.path.exists(path):
                continue
            img = Image.open(path).convert('RGB')
            boxes = face_boxes(p, *img.size)
            if boxes:
                x0, y0, x1, y1 = boxes[0]
                img = img.crop((int(max(0, x0)), int(max(0, y0)), int(min(img.width, x1)), int(min(img.height, y1))))
            x = label_w + ci * (tile + pad)
            sheet.paste(img.resize((tile, tile)), (x, y))
            d.text((x + 2, y + tile + 2), export_name(p)[-4:], fill=(220, 220, 220))
    sheet.save(a.out, quality=90)
    print(f'wrote {a.out}')


def cmd_beforeafter(a):
    h, cols = 360, 4
    tiles = []
    for n in a.names:
        before = Image.open(os.path.join(a.before_dir, n + '.jpg')).convert('RGB')
        after = Image.open(os.path.join(a.after_dir, n + '.jpg')).convert('RGB')
        before = before.resize((int(before.width * h / before.height), h))
        after = after.resize((int(after.width * h / after.height), h))
        t = Image.new('RGB', (before.width + after.width + 4, h + 16), (30, 30, 30))
        t.paste(before, (0, 16))
        t.paste(after, (before.width + 4, 16))
        ImageDraw.Draw(t).text((2, 2), f'{n[-4:]}  before | after', fill=(255, 255, 255))
        tiles.append(t)
    rows = [tiles[i:i + cols] for i in range(0, len(tiles), cols)]
    sheet = Image.new('RGB', (max(sum(t.width + 8 for t in r) for r in rows), len(rows) * (h + 24)), (30, 30, 30))
    for ri, r in enumerate(rows):
        x = 0
        for t in r:
            sheet.paste(t, (x, ri * (h + 24)))
            x += t.width + 8
    sheet.save(a.out, quality=88)
    print(f'wrote {a.out}')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('backup-wb', help='save every photo\'s current white balance')
    p.add_argument('out'); p.add_argument('inspect', nargs='+')
    p.set_defaults(fn=cmd_backup_wb)

    p = sub.add_parser('check-wb', help='confirm white balances match a backup (exit 1 if not)')
    p.add_argument('backup'); p.add_argument('inspect', nargs='+')
    p.set_defaults(fn=cmd_check_wb)

    p = sub.add_parser('measure', help='skin log2(R/G), log2(B/G) per photo from face boxes')
    p.add_argument('export_dir'); p.add_argument('out'); p.add_argument('inspect', nargs='+')
    p.set_defaults(fn=cmd_measure)

    p = sub.add_parser('whites', help='colour of near-white objects (clothes, confetti) per photo')
    p.add_argument('export_dir'); p.add_argument('out'); p.add_argument('inspect', nargs='+')
    p.add_argument('--min-pixels', type=int, default=300)
    p.set_defaults(fn=cmd_whites)

    p = sub.add_parser('grid', help='assign the calibration grid to photos under one light; prints command_batch steps')
    p.add_argument('out'); p.add_argument('ids', nargs='+', type=int)
    p.set_defaults(fn=cmd_grid)

    p = sub.add_parser('calibrate', help='fit the Temp/Tint -> skin shift model')
    p.add_argument('base_skin'); p.add_argument('calib_skin'); p.add_argument('grid'); p.add_argument('out')
    p.set_defaults(fn=cmd_calibrate)

    p = sub.add_parser('solve', help='white balance per group from baseline measurements')
    p.add_argument('model'); p.add_argument('groups'); p.add_argument('base_skin'); p.add_argument('out')
    p.add_argument('--base-whites')
    p.add_argument('--target', type=float, nargs=2, required=True, metavar=('RG', 'BG'), help='reference skin as the user sees it')
    p.add_argument('--strength', choices=['balanced', 'match'], default='balanced')
    p.add_argument('--whites-scope', choices=['global', 'group'], default='global', help='group: use a group\'s own white objects when it has 3+ solid readings')
    p.add_argument('--min-white-pixels', type=int, default=5000, help='white readings with fewer pixels are ignored as unreliable')
    p.set_defaults(fn=cmd_solve)

    p = sub.add_parser('steps', help='command_batch steps applying a solution')
    p.add_argument('solution'); p.add_argument('--albums', help='JSON {group name: album id}')
    p.set_defaults(fn=cmd_steps)

    p = sub.add_parser('verify', help='compare re-measured skin with the solution; suggest corrections')
    p.add_argument('model'); p.add_argument('solution'); p.add_argument('after_skin')
    p.add_argument('--tolerance', type=float, default=0.2)
    p.set_defaults(fn=cmd_verify)

    p = sub.add_parser('montage', help='largest face of each photo, one row per group')
    p.add_argument('export_dir'); p.add_argument('groups'); p.add_argument('out'); p.add_argument('inspect', nargs='+')
    p.set_defaults(fn=cmd_montage)

    p = sub.add_parser('beforeafter', help='whole-photo before/after strips')
    p.add_argument('before_dir'); p.add_argument('after_dir'); p.add_argument('out'); p.add_argument('names', nargs='+')
    p.set_defaults(fn=cmd_beforeafter)

    a = ap.parse_args()
    a.fn(a)


if __name__ == '__main__':
    main()
