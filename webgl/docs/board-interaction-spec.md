# Board Interaction Rewrite Spec

## Scope
This document defines the clean interaction model for board piece placing, removing, and dragging.
The model is device-agnostic: no separate behavior by touch vs mouse vs pen.

## Core Rules

### 1. Place
- Precondition: a piece is selected with a concrete orientation.
- User chooses a target anchor cell.
- System computes candidate placement from selection + anchor.
- If candidate is valid, commit immediately.
- If candidate is invalid, reject with no board mutation.
- No filled ghost preview is rendered.

### 2. Remove
- User starts interaction on a cell occupied by a placed piece.
- System lifts/removes the full piece from board state.
- Removed piece becomes current selection.
- Drag origin is recorded for comparison and commit.

### 3. Drag / Move Existing Piece
- Drag can only begin from an existing placed piece.
- While dragging:
  - Piece position follows pointer continuously (fractional board coordinates).
  - Drag rendering is not cell-locked while moving.
  - Candidate snapped anchor is updated continuously as nearest-cell mapping.
  - A settle indicator is shown for predicted landing.
- Settle trigger:
  - after pointer pause >= 1s, or
  - immediately on pointer release/end.
- Settle finalize animation duration: 250ms.
- Finalize result:
  - valid candidate -> commit at snapped anchor.
  - invalid candidate -> keep the piece removed from the board.
  - no meaningful movement -> keep the piece removed from the board.

### 4. Settle Indicator (required)
- Show a semitransparent gray border-only outline of the piece at the predicted snapped landing position.
- Indicator must not use piece fill color.
- Indicator appears only during drag/snap flow.
- Indicator disappears after commit or removal.

### 5. No Ghost Fill
- Do not render colored/tinted ghost fill previews during drag/release/settle.
- Only two transient visuals are allowed:
  - the dragged piece itself,
  - the semitransparent gray border settle indicator.

## State Machine

### States
- `idle`
- `placing`
- `dragging`
- `snap_finalizing`

### Events (abstract, normalized)
- `boardStart(position, hitPieceId?)`
- `boardMove(position)`
- `boardEnd(position?)`
- `boardCancel()`
- `settleTimeout()` (1s inactivity during drag)
- `settleDone()` (250ms finalize complete)

### Transition Intent
- `idle -> placing`: start on empty cell with selected piece.
- `idle -> dragging`: start on an occupied cell.
- `dragging -> snap_finalizing`: on `boardEnd` or `settleTimeout`.
- `snap_finalizing -> idle`: on `settleDone`, then commit or remove.

## Drag Rendering Model (required)
- Drag visual uses continuous pointer offsets in board space.
- Snapped landing anchor is computed independently from drag visual.
- During drag:
  - render dragged piece at continuous position,
  - render settle indicator at snapped anchor.
- During snap finalize (250ms):
  - animate from continuous drag position to snapped anchor.
- Final commit/remove occurs only when snap finalize completes.

## Implementation Plan (from clean state)

1. Introduce a single interaction reducer/state model in app logic (no device branches).
2. Normalize pointer/mouse/touch into abstract board events inside board component only.
3. Keep placement validation/commit as pure helper functions.
4. Add explicit drag origin and drag candidate tracking.
5. Add settle indicator render layer:
   - border-only, semitransparent gray.
6. Implement settle timing:
   - 1s inactivity timer,
   - 250ms finalize timer.
7. Move expensive counting off critical path (worker), trigger only after successful commit.
8. Remove legacy ghost fill rendering paths.

## Acceptance Criteria

1. Place valid candidate commits immediately.
2. Place invalid candidate makes no board mutation.
3. Removing a piece lifts the full piece and marks it active selection.
4. Dragging shows smooth continuous movement (not grid-step movement).
5. During drag, settle indicator is visible as semitransparent gray border-only outline.
6. During drag, no colored/tinted ghost fill is visible.
7. Releasing pointer starts 250ms settle finalize.
8. 1s drag pause (without release) starts 250ms settle finalize.
9. Valid settle candidate commits; invalid/no-move leaves dragged piece removed.
10. Behavior is identical across touch and click projects (same semantic outcomes).
11. Drag path and settle animation are visually smooth in both click and touch
    projects.
