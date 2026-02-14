from __future__ import annotations

from dataclasses import dataclass
import random
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
    Scene,
    Square,
    Text,
    UL,
    UP,
    VGroup,
    config,
)

Coord = Tuple[int, int]
Placement = Tuple[str, Tuple[Coord, ...]]

PENTOMINOES: Dict[str, Tuple[Coord, ...]] = {
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
            variant = transform(cells, k, reflect)
            if variant not in seen:
                seen.add(variant)
                variants.append(variant)
    return variants


@dataclass
class DFSSolver:
    rows: int = 6
    cols: int = 10
    seed: int = 0

    def __post_init__(self) -> None:
        self.board: List[List[str | None]] = [
            [None for _ in range(self.cols)] for _ in range(self.rows)]
        self.used: Set[str] = set()
        self.rng = random.Random(self.seed)
        self.orientations: Dict[str, List[Tuple[Coord, ...]]] = {
            name: unique_orientations(cells) for name, cells in PENTOMINOES.items()
        }

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

    def solve(self) -> List[Placement] | None:
        empty = self.first_empty()
        if empty is None:
            return []

        anchor_r, anchor_c = empty
        names = [name for name in sorted(PENTOMINOES) if name not in self.used]
        self.rng.shuffle(names)
        for name in names:
            orientations = list(self.orientations[name])
            self.rng.shuffle(orientations)
            for orient in orientations:
                anchors = list(orient)
                self.rng.shuffle(anchors)
                for cell_r, cell_c in anchors:
                    dr = anchor_r - cell_r
                    dc = anchor_c - cell_c
                    shifted = tuple((r + dr, c + dc) for r, c in orient)
                    if not self.can_place(shifted):
                        continue

                    self.apply_place(name, shifted)
                    rest = self.solve()
                    if rest is not None:
                        return [(name, shifted)] + rest
                    self.apply_remove(name, shifted)

        return None


def build_piece_outline(cells: Sequence[Coord], size: float, stroke_width: float = 2.0) -> VGroup:
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


class PentominoFiveRectangles(Scene):
    def construct(self) -> None:
        board_cell = 0.42
        top_cell = 0.19
        step_time = 0.1
        solve_count = 5
        solved_scale = 1 / 3
        solutions = self.find_unique_solutions(count=solve_count, max_attempts=300)
        if len(solutions) < solve_count:
            raise RuntimeError(
                f"Only found {len(solutions)} unique solutions, expected {solve_count}"
            )

        board = self.make_board(rows=6, cols=10, cell=board_cell)
        board.move_to((-2.6, -1.45, 0))

        top_pieces = self.make_top_pieces(cell=top_cell)
        top_pieces.next_to(board, UP, buff=0.5)
        max_top = config["frame_y_radius"] - 0.2
        if top_pieces.get_top()[1] > max_top:
            top_pieces.shift((0, max_top - top_pieces.get_top()[1], 0))

        self.play(Create(board), run_time=0.8)
        self.play(FadeIn(top_pieces), run_time=0.8)

        top_map = {
            group.name: group for group in top_pieces if hasattr(group, "name")}
        board_origin = board.get_corner(UL)
        solved_slots = self.make_solved_slots(board, solve_count, solved_scale)

        for idx, solution in enumerate(solutions):
            placed_map: Dict[str, VGroup] = {}

            for name, cells in solution:
                piece = build_piece(cells, size=board_cell, stroke_width=2.6)
                piece.shift(board_origin - ORIGIN)
                placed_map[name] = piece

                animations = [FadeIn(piece)]
                if name in top_map:
                    animations.append(FadeOut(top_map[name]))
                self.play(*animations, run_time=step_time)

            solved_group = VGroup(
                board.copy(), *[piece.copy() for piece in placed_map.values()])
            self.add(solved_group)
            self.play(solved_group.animate.scale(solved_scale).move_to(
                solved_slots[idx]), run_time=0.45)

            reset_animations = [FadeOut(piece)
                                for piece in placed_map.values()]
            reset_animations.extend(
                FadeIn(top_map[name]) for name in sorted(top_map))
            self.play(*reset_animations, run_time=0.25)

        self.wait(0.4)

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
        x_gap = 1.9
        y_gap = 1.2

        for idx, name in enumerate(names):
            row = idx // cols
            col = idx % cols
            shape = build_piece(PENTOMINOES[name], size=cell, stroke_width=2.0)
            label = Text(name, font_size=22)
            piece_group = VGroup(shape, label)
            label.next_to(shape, direction=DOWN, buff=0.06)
            piece_group.move_to(((col - 1.5) * x_gap, (1 - row) * y_gap, 0))
            piece_group.name = name
            layout.add(piece_group)

        return layout

    def make_solved_slots(self, board: VGroup, count: int, scale: float) -> List[Tuple[float, float, float]]:
        mini_width = board.width * scale
        mini_height = board.height * scale
        right_edge = config["frame_x_radius"] - 0.3
        x = right_edge - mini_width / 2

        total_h = count * mini_height + (count - 1) * 0.18
        start_y = min(config["frame_y_radius"] - mini_height /
                      2 - 0.2, total_h / 2 - mini_height / 2)
        return [(x, start_y - i * (mini_height + 0.18), 0) for i in range(count)]

    def find_unique_solutions(self, count: int, max_attempts: int) -> List[List[Placement]]:
        unique: Dict[Tuple[Tuple[str, Tuple[Coord, ...]], ...], List[Placement]] = {}
        for attempt in range(max_attempts):
            solver = DFSSolver(rows=6, cols=10, seed=attempt + 1)
            solution = solver.solve()
            if solution is None:
                continue
            signature = self.solution_signature(solution)
            if signature not in unique:
                unique[signature] = solution
                if len(unique) >= count:
                    break
        return list(unique.values())

    def solution_signature(self, solution: List[Placement]) -> Tuple[Tuple[str, Tuple[Coord, ...]], ...]:
        normalized: List[Tuple[str, Tuple[Coord, ...]]] = []
        for name, cells in solution:
            normalized.append((name, tuple(sorted(cells))))
        return tuple(sorted(normalized))
