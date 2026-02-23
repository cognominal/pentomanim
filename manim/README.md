# Manim Scenes

This directory contains Manim scene scripts and helper utilities.

## Scene scripts

- `/Users/cog/mine/pentomanim/manim/pentomino_6x10.py`
- `/Users/cog/mine/pentomanim/manim/pentomino_6x10_five.py`
- `/Users/cog/mine/pentomanim/manim/rect_6x10_dfs_tree.py`
- `/Users/cog/mine/pentomanim/manim/triplication_dfs_tree.py`
- `/Users/cog/mine/pentomanim/manim/dlx_3x2_two_tiles.py`
- `/Users/cog/mine/pentomanim/manim/dlx_3x2_three_tiles.py`
- `/Users/cog/mine/pentomanim/manim/dlx_3x2_three_tiles_links.py`
- `/Users/cog/mine/pentomanim/manim/dancing-links-anim.py`

## Non-scene helpers

- `/Users/cog/mine/pentomanim/manim/dancing_links.py`
- `/Users/cog/mine/pentomanim/manim/sync_eponymous.py`

`dancing_links.py` implements DLX pointer operations and is not a Manim scene.
`dancing-links-anim.py` is the Manim animation scene (`DancingLinksDemo`).

## Run a single scene

From repo root:

```bash
manim -pqh manim/dancing-links-anim.py DancingLinksDemo
```

Low-quality preview:

```bash
manim -pql manim/dancing-links-anim.py DancingLinksDemo
```

## Eponymous sync (`X.py` -> `X.md` + `X.mp4`)

Use this to keep scene docs and videos aligned with scene scripts:

```bash
python3 /Users/cog/mine/pentomanim/manim/sync_eponymous.py
```

Render/sync one file only:

```bash
python3 /Users/cog/mine/pentomanim/manim/sync_eponymous.py \
  --file dancing-links-anim.py
```

Useful flags:

- `--quality low|medium|high|production`
- `--dry-run`
- `--skip-render`
- `--no-skip-non-scene` (strict mode)

## Output paths

Manim render output is written under:

- `/Users/cog/mine/pentomanim/manim/media/videos/`
- `/Users/cog/mine/pentomanim/manim/media/texts/`

`sync_eponymous.py` also copies the newest render to same-stem output files in
this directory (for example `triplication_dfs_tree.mp4`).

## Spec

- `/Users/cog/mine/pentomanim/manim/EPONYMOUS_SYNC_SPEC.md`
