# DLX 3x2 Three Tiles (Links Inset)

Scene class: `DLXBoard3x2ThreeTilesLinks`
File: `manim/dlx_3x2_three_tiles_links.py`

## Goal

Show exact-cover matrix state and make Dancing Links visible as pointer
rewiring during Algorithm X search.

## Layout

- Left pane: matrix table (columns, row memberships, OR row).
- Right top: DLX links inset (hidden during pre-search).
- Right bottom: board + picker.
- Status line under board/picker.

This keeps matrix, pointer mechanics, and placement result visible at the same
moment.

## Links Inset

The links inset renders:

- Column header boxes for all exact-cover columns.
- Row nodes at intersections where row has a `1`.
- Horizontal row links between nodes in each row.
- Vertical column links between nodes in each column.
- A yellow cursor rectangle showing current focus.

## Animation Semantics

`apply_links_state(...)` is called every search step.

- Pre-search:
  - Matrix is built row by row.
  - OR row accumulates as rows are added.
  - Links inset remains hidden.
- `choose` step:
  - Focus column is highlighted in yellow.
  - Cursor moves to focused column header.
- `select` step:
  - Nodes/links in selected row are highlighted.
  - Covered columns are accented (cover-like unlink emphasis).
  - Inactive columns/rows are dimmed.
- `backtrack` step:
  - Previously covered columns are accented green
    (uncover-like relink emphasis).
- Chosen rows remain green to match board and picker state.
- Non-focused active rows are intentionally dimmed so chosen row placement
  reads clearly.

The animation is synchronized with existing updates:

- matrix state,
- board fill,
- picker availability,
- status text.

## Render

From repo root:

```bash
manim -pql manim/dlx_3x2_three_tiles_links.py DLXBoard3x2ThreeTilesLinks
```

Use `-pqh` for higher-quality output once timing and spacing are confirmed.

## Notes

- The inset is intentionally compact to fit above board/picker.
- It is a visual model of cover/uncover transitions, not a literal mutable
  pointer structure implementation.
