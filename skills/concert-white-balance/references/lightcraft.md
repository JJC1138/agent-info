# LightCraft MCP notes for this workflow

The server is `lightcraft-app`; its tools are named `mcp__lightcraft-app__*`. It talks to the running desktop app at 127.0.0.1:7980. Load the tools with `ToolSearch` "lightcraft". The tools stay deferred until the server finishes connecting, and the search waits for it.

## Commands that worked

| Purpose | Call |
|---|---|
| List photos by rating | `query_photos {filter: {"rating": 4, "ratingOp": "atLeast"}, limit: 200}`; use `"exactly"` for one rating |
| Faces, crop, WB per photo | `command_batch` of `photo.inspect {id}` steps, about 5 KB each, so the result is saved to a file |
| Current develop settings | `develop.get {id}` or `get_develop {id}` |
| Set WB on many photos | `command_run develop.set {ids: [...], values: {"wb.temp": T, "wb.tint": t}}`, one undo step |
| Nudge relative to each photo's value | `develop.quickAdjust {ids, control: "wb.tint", delta}` |
| Undo / redo | `command_run edit.undo` → `{"undone": "<label>"}`, `edit.redo` |
| Export small renders | `export {ids, dir, naming: "{name}", format: "jpeg", quality: 92, longEdge: 1000, metadata: "none", conflict: "overwrite"}` |
| Albums | `album.create {name, folder: true}`, `album.create {name, parent}`, `album.addPhotos {id, ids}`, `album.removePhotos`, `album.rename`, `album.setCover {id, photo}`, `albums.list` |
| Select / make active | `select_photos {ids}` (`cmd_library_select` didn't select anything) |

## Quirks

- **Export matches what you'll judge.** `export` and `render_preview` output agree, and both apply crops and all edits. Judge from exports.
- **Setting WB switches mode.** `develop.set` on `wb.*` switches the mode from `asShot` to `custom`. That's harmless, but it's why restoring from a backup uses values rather than the mode.
- **Versions are single-photo.** `version.create` acts only on the active photo, so it isn't practical for bulk A/B versions.
- **Avoid `app.about`.** It opens a modal dialog instead of returning info.
- **Apple Photos is macOS-only.** `export.addToPhotos` is disabled on Jon's Windows PC.
- **Assisted Culling can time out.** `photo.analyze` on hundreds of photos times out on the MCP side, but still finishes in the app. Its focus scores were a weak signal for Jon's keepers.
- **Large results go to a file.** Results over the size limit are saved under the session's `tool-results/` folder; copy them before parsing.
