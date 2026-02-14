from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Set, Tuple

from manim import (
    Create,
    DARK_GRAY,
    DOWN,
    FadeIn,
    FadeOut,
    Line,
    ORIGIN,
    Rectangle,
    Square,
    Scene,
    Text,
    UL,
    UP,
    VGroup,
    config,
)


Coord = Tuple[int, int]
Placement = Tuple[str, Tuple[Coord, ...]]


PENTOMINOES: Dict[str, Tuple[Coord, ...]] = {
    # Coordinates are unit-cell offsets for each pentomino.
    "F": ((0, 1), (1, 0), (1, 1), (1, 2), (2, 0)),
    "I": ((0, 0), (0, 1), (0, 2), (0, 3), (0, 4)),
    "L": ((0, 0), (1, 0), (2, 0), (3, 0), (3, 1)),
    "P": ((0, 0), (0, 1), (1, 0), (1, 1), (2, 0)),
    "N": ((0, 0), (1, 0), (1, 1), (2, 1), (3, 1)),
    "T": ((0, 0), (0, 1), (0, 2), (1, 1), (2, 1)),
    "U": ((0, 0), (0, 2), (1, 0), (1, 1), (1, 2)),
    "V": ((0, 0), (1, 0), (2, 0), (2, 1), (2, 2)),
    "W": ((0, 0), (1, 0), (1, 1), (2, 1), (2, 2)),
    "X": ((0, 1), (1, 0), (1, 1), (1, 2), (2, 1)),
    "Y": ((0, 1), (1, 1), (2, 0), (2, 1), (3, 1)),
    "Z": ((0, 0), (0, 1), (1, 1), (2, 1), (2, 2)),
}


@dataclass
class SearchState:
    rows: int = 6
    cols: int = 10
    max_steps: int = 100

    def __post_init__(self) -> None:
        self.board: List[List[str | None]] = [
            [None for _ in range(self.cols)] for _ in range(self.rows)]
        self.used: Set[str] = set()
        self.events: List[Tuple[str, Placement]] = []
        self.orientations: Dict[str, List[Tuple[Coord, ...]]] = {
            name: unique_orientations(cells) for name, cells in PENTOMINOES.items()
        }

    def record(self, op: str, piece: Placement) -> bool:
        if len(self.events) >= self.max_steps:
            return True
        self.events.append((op, piece))
        return len(self.events) >= self.max_steps

    def first_empty(self) -> Coord | None:
        for r in range(self.rows):
            for c in range(self.cols):
                if self.board[r][c] is None:
                    return (r, c)
        return None

    def can_place(self, cells: Sequence[Coord]) -> bool:
        for r, c in cells:
            if r < 0 or r >= self.rows or c < 0 or c >= self.cols:
                return False
            if self.board[r][c] is not None:
                return False
        return True

    def apply_place(self, name: str, cells: Sequence[Coord]) -> None:
        for r, c in cells:
            self.board[r][c] = name
        self.used.add(name)

    def apply_remove(self, name: str, cells: Sequence[Coord]) -> None:
        for r, c in cells:
            self.board[r][c] = None
        self.used.remove(name)

    def search(self) -> bool:
        if len(self.events) >= self.max_steps:
            return True

        spot = self.first_empty()
        if spot is None:
            return True

        anchor_r, anchor_c = spot

        for name in sorted(PENTOMINOES):
            if name in self.used:
                continue

            for orient in self.orientations[name]:
                # Force each candidate to cover the first empty spot.
                for cell_r, cell_c in orient:
                    dr = anchor_r - cell_r
                    dc = anchor_c - cell_c
                    shifted = tuple((r + dr, c + dc) for r, c in orient)
                    if not self.can_place(shifted):
                        continue

                    self.apply_place(name, shifted)
                    if self.record("place", (name, shifted)):
                        return True

                    if self.search():
                        return True

                    self.apply_remove(name, shifted)
                    if self.record("remove", (name, shifted)):
                        return True

        return False


def normalize(cells: Iterable[Coord]) -> Tuple[Coord, ...]:
    c_list = list(cells)
    min_r = min(r for r, _ in c_list)
    min_c = min(c for _, c in c_list)
    return tuple(sorted((r - min_r, c - min_c) for r, c in c_list))


def transform(cells: Iterable[Coord], k: int, reflect: bool) -> Tuple[Coord, ...]:
    out: List[Coord] = []
    for r, c in cells:
        x, y = r, c
        if reflect:
            y = -y
        for _ in range(k % 4):
            x, y = y, -x
        out.append((x, y))
    return normalize(out)


def unique_orientations(cells: Iterable[Coord]) -> List[Tuple[Coord, ...]]:
    seen: Set[Tuple[Coord, ...]] = set()
    variants: List[Tuple[Coord, ...]] = []
    for reflect in (False, True):
        for k in range(4):
            v = transform(cells, k, reflect)
            if v not in seen:
                seen.add(v)
                variants.append(v)
    return variants


def build_piece_outline(
    cells: Sequence[Coord],
    size: float,
    stroke_width: float = 2.0,
) -> VGroup:
    """Draw only outer boundary edges for a polyomino on a unit grid."""
    occupied = set(cells)
    group = VGroup()
    for r, c in occupied:
        x0 = c * size
        x1 = (c + 1) * size
        y0 = -r * size
        y1 = -(r + 1) * size
        if (r - 1, c) not in occupied:
            group.add(Line((x0, y0, 0), (x1, y0, 0),
                      stroke_width=stroke_width))
        if (r + 1, c) not in occupied:
            group.add(Line((x0, y1, 0), (x1, y1, 0),
                      stroke_width=stroke_width))
        if (r, c - 1) not in occupied:
            group.add(Line((x0, y0, 0), (x0, y1, 0),
                      stroke_width=stroke_width))
        if (r, c + 1) not in occupied:
            group.add(Line((x1, y0, 0), (x1, y1, 0),
                      stroke_width=stroke_width))
    return group


def build_piece(
    cells: Sequence[Coord],
    size: float,
    stroke_width: float = 2.0,
    fill_color=DARK_GRAY,
    fill_opacity: float = 0.85,
) -> VGroup:
    fill = VGroup()
    for r, c in cells:
        sq = Square(
            side_length=size,
            stroke_width=0.0,
            fill_color=fill_color,
            fill_opacity=fill_opacity,
        )
        sq.move_to(((c + 0.5) * size, -(r + 0.5) * size, 0))
        fill.add(sq)
    outline = build_piece_outline(cells, size=size, stroke_width=stroke_width)
    return VGroup(fill, outline)


class PentominoFillAnimation(Scene):
    def construct(self) -> None:
        state = SearchState(rows=6, cols=10, max_steps=100)
        state.search()

        board_cell = 0.5
        top_cell = 0.22

        board = self.make_board(rows=6, cols=10, cell=board_cell)
        board.to_edge(DOWN, buff=0.7)

        top_pieces = self.make_top_pieces(cell=top_cell)
        top_pieces.next_to(board, UP, buff=0.6)
        max_top = config["frame_y_radius"] - 0.15
        if top_pieces.get_top()[1] > max_top:
            available = max_top - top_pieces.get_bottom()[1]
            if available > 0:
                top_pieces.scale_to_fit_height(min(top_pieces.height, available))
                top_pieces.next_to(board, UP, buff=0.6)

        self.play(Create(board), run_time=1.5)
        self.play(FadeIn(top_pieces), run_time=1.5)

        board_origin = board.get_corner(UL)
        top_map = {
            group.name: group for group in top_pieces if hasattr(group, "name")}
        placed_map: Dict[str, VGroup] = {}

        for op, (name, cells) in state.events:
            if op == "place":
                piece = build_piece(cells, size=board_cell, stroke_width=3)
                piece.shift(board_origin - ORIGIN)
                placed_map[name] = piece

                fades = [FadeIn(piece)]
                if name in top_map:
                    fades.append(FadeOut(top_map[name]))
                self.play(*fades, run_time=1.0)

            else:
                fades = []
                if name in placed_map:
                    fades.append(FadeOut(placed_map[name]))
                    del placed_map[name]
                if name in top_map:
                    fades.append(FadeIn(top_map[name]))
                if fades:
                    self.play(*fades, run_time=1.0)

        self.wait(0.5)

    def make_board(self, rows: int, cols: int, cell: float) -> VGroup:
        return VGroup(
            Rectangle(
                width=cols * cell,
                height=rows * cell,
                stroke_width=2.5,
                fill_opacity=0.0,
            )
        )

    def make_top_pieces(self, cell: float) -> VGroup:
        layout = VGroup()
        names = sorted(PENTOMINOES.keys())
        cols = 4
        x_gap = 2.8
        y_gap = 1.6

        for idx, name in enumerate(names):
            r = idx // cols
            c = idx % cols
            shape = build_piece(PENTOMINOES[name], size=cell, stroke_width=2.0)
            label = Text(name, font_size=24)
            piece_group = VGroup(shape, label)
            label.next_to(shape, direction=DOWN, buff=0.08)
            piece_group.move_to(((c - 1.5) * x_gap, (1 - r) * y_gap, 0))
            piece_group.name = name
            layout.add(piece_group)

        return layout
