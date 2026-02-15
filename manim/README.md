# Manim Pentomino Scenes

This folder contains Manim scene scripts for pentomino tilings on a `6x10` rectangle.

## Files
- `/Users/cog/mine/pentomanim/manim/pentomino_6x10.py`
- `/Users/cog/mine/pentomanim/manim/pentomino_6x10_five.py`

## Main Scene
`pentomino_6x10_five.py` defines `PentominoFiveRectangles`, which:
- solves pentomino tilings with DFS,
- finds unique solutions,
- animates piece placement,
- shows five solved rectangles.

`pentomino_6x10.py` contains the base single-board variant and shared pentomino/solver logic.

## Run
From repo root:

```bash
manim -pqh manim/pentomino_6x10_five.py PentominoFiveRectangles
```

Lower quality preview:

```bash
manim -pql manim/pentomino_6x10_five.py PentominoFiveRectangles
```

## Output
Rendered media is written under:
- `/Users/cog/mine/pentomanim/manim/media/videos/`
- `/Users/cog/mine/pentomanim/manim/media/texts/`
