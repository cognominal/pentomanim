# Eponymous Artifact Sync Spec

## Reformulated Requirement

When a Manim script `X.py` changes, the project must keep `X.md` and `X.mp4`
up to date automatically, including for newly added scripts.

## Scope

- Directory: `/Users/cog/mine/pentomanim/manim`
- Source artifacts: `*.py` Manim scene scripts
- Target artifacts: same-stem `*.md` and `*.mp4`

## Naming Rule

For a source file with stem `X`:

- Markdown spec file: `X.md`
- Rendered video file: `X.mp4`

The three files are considered an eponymous set.

## Freshness Rule

For each `X.py`:

- `X.md` is stale when:
  - it does not exist, or
  - its embedded `source_sha256` does not match the current hash of `X.py`
- `X.mp4` is stale when:
  - it does not exist, or
  - its mtime is older than `X.py`

## Required Behavior

1. Discover all `*.py` files in the manim directory (excluding the sync script
   itself).
2. Detect the first class inheriting from `Scene` or `MovingCameraScene`.
3. If `X.md` is stale:
   - create it if missing, or
   - replace/update the `AUTO-SYNC` metadata block if present, otherwise append
     one.
4. If `X.mp4` is stale:
   - render the detected scene with Manim,
   - copy the newest rendered `X.mp4` from the media tree to
     `/Users/cog/mine/pentomanim/manim/X.mp4`.
5. Non-scene helper `*.py` files are skipped by default (opt-in strict mode can
   fail on them).

## CLI Contract

Script: `/Users/cog/mine/pentomanim/manim/sync_eponymous.py`

- `--dir PATH`: scan directory (default is script directory)
- `--file NAME.py` (repeatable): process only selected files
- `--quality {low,medium,high,production}`: render quality
- `--skip-render`: update only markdown
- `--dry-run`: report actions without writing/rendering
- `--no-skip-non-scene`: fail on python files without Scene subclasses

## Operational Guarantees

- Adding a new scene script `new_scene.py` and running the script creates:
  - `new_scene.md`
  - `new_scene.mp4` (unless `--skip-render` is used)
- Existing manual markdown content is preserved; only the auto-sync block is
  managed.
- Runs are idempotent when sources are unchanged.

