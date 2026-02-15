from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
import sys
from time import perf_counter
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from manim import (
    BLACK,
    DARK_GRAY,
    DOWN,
    FadeIn,
    FadeOut,
    LEFT,
    Line,
    ReplacementTransform,
    RIGHT,
    Scene,
    Square,
    Text,
    UP,
    VGroup,
    WHITE,
)

Coord = Tuple[int, int]
PieceName = str


PIECES: Dict[PieceName, Tuple[Coord, ...]] = {
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

# Same color conventions as webgl/src/lib/pentomino.ts
PIECE_COLORS: Dict[PieceName, str] = {
    "F": "#c98592",
    "I": "#c6a07a",
    "L": "#ccb57f",
    "P": "#78b39f",
    "N": "#6ea8b0",
    "T": "#638faa",
    "U": "#7f88b7",
    "V": "#8574af",
    "W": "#9b7eb9",
    "X": "#c07690",
    "Y": "#c89a70",
    "Z": "#7ab1a8",
}


def normalize(cells: Iterable[Coord]) -> Tuple[Coord, ...]:
    c_list = list(cells)
    min_r = min(r for r, _ in c_list)
    min_c = min(c for _, c in c_list)
    return tuple(sorted((r - min_r, c - min_c) for r, c in c_list))


def unique_orientations(cells: Sequence[Coord]) -> List[Tuple[Coord, ...]]:
    seen: Set[Tuple[Coord, ...]] = set()
    out: List[Tuple[Coord, ...]] = []
    for flipped in (False, True):
        for k in range(4):
            variant: List[Coord] = []
            for r0, c0 in cells:
                x, y = r0, c0
                if flipped:
                    y = -y
                for _ in range(k):
                    x, y = y, -x
                variant.append((x, y))
            norm = normalize(variant)
            if norm not in seen:
                seen.add(norm)
                out.append(norm)
    return out


ORIENTATIONS: Dict[PieceName, List[Tuple[Coord, ...]]] = {
    name: unique_orientations(cells) for name, cells in PIECES.items()
}

TIME_SCALE = 3.0
LABEL_FONT = "Andale Mono"


class SliceComplete(Exception):
    pass


@dataclass
class Problem:
    rows: int
    cols: int
    mask_cells: List[Coord]
    selected_pieces: List[PieceName]


@dataclass
class NodeData:
    node_id: int
    parent_id: Optional[int]
    depth: int
    board: Dict[Coord, PieceName]
    children: List[int] = field(default_factory=list)
    elapsed_ms: Optional[float] = None
    explored_subnodes: int = 0


@dataclass
class Event:
    kind: str  # enter | exit
    node_id: int


@dataclass
class TraceResult:
    nodes: Dict[int, NodeData]
    events: List[Event]


def triplicate_piece_cells(piece: PieceName) -> Tuple[int, int, List[Coord]]:
    base = PIECES[piece]
    max_r = max(r for r, _ in base) + 1
    max_c = max(c for _, c in base) + 1
    cells: List[Coord] = []
    for r, c in base:
        for dr in range(3):
            for dc in range(3):
                cells.append((r * 3 + dr, c * 3 + dc))
    return max_r * 3, max_c * 3, cells


def key(rc: Coord) -> str:
    return f"{rc[0]},{rc[1]}"


def has_only_five_multiple_void_regions(
    rows: int,
    cols: int,
    allowed_keys: Set[str],
    sorted_mask: List[Coord],
    filled_keys: Set[str],
) -> bool:
    visited: Set[str] = set()
    deltas: Tuple[Coord, ...] = ((-1, 0), (1, 0), (0, -1), (0, 1))

    for r, c in sorted_mask:
        start = key((r, c))
        if start in filled_keys or start in visited:
            continue

        region_size = 0
        stack: List[Coord] = [(r, c)]
        visited.add(start)

        while stack:
            cr, cc = stack.pop()
            region_size += 1
            for dr, dc in deltas:
                nr, nc = cr + dr, cc + dc
                if nr < 0 or nr >= rows or nc < 0 or nc >= cols:
                    continue
                kk = key((nr, nc))
                if kk not in allowed_keys or kk in filled_keys or kk in visited:
                    continue
                visited.add(kk)
                stack.append((nr, nc))

        if region_size % 5 != 0:
            return False

    return True


def build_trace(
    problem: Problem,
    enable_pruning: bool,
    max_display_depth: int = 3,
    max_display_children: int = 3,
    max_nodes: int = 1_500_000,
) -> TraceResult:
    mask_set = set(problem.mask_cells)
    sorted_mask = sorted(problem.mask_cells)
    allowed_keys = {key(rc) for rc in problem.mask_cells}

    used: Set[PieceName] = set()
    filled_keys: Set[str] = set()
    board: Dict[Coord, PieceName] = {}

    nodes: Dict[int, NodeData] = {}
    events: List[Event] = []
    next_node_id = 0
    node_counter = 0

    def create_node(parent_id: Optional[int], depth: int) -> int:
        nonlocal next_node_id
        nid = next_node_id
        next_node_id += 1
        nodes[nid] = NodeData(
            node_id=nid,
            parent_id=parent_id,
            depth=depth,
            board=dict(board),
        )
        events.append(Event("enter", nid))
        if parent_id is not None:
            nodes[parent_id].children.append(nid)
        return nid

    def first_empty() -> Optional[Coord]:
        for rc in sorted_mask:
            if key(rc) not in filled_keys:
                return rc
        return None

    def can_place(cells: Sequence[Coord]) -> bool:
        for rc in cells:
            kk = key(rc)
            if kk not in allowed_keys or kk in filled_keys:
                return False
        return True

    def apply(name: PieceName, cells: Sequence[Coord]) -> None:
        used.add(name)
        for rc in cells:
            filled_keys.add(key(rc))
            board[rc] = name

    def unapply(name: PieceName, cells: Sequence[Coord]) -> None:
        used.remove(name)
        for rc in cells:
            filled_keys.remove(key(rc))
            del board[rc]

    def dfs(depth: int, display_node_id: Optional[int]) -> Tuple[bool, int, bool]:
        nonlocal node_counter
        node_counter += 1
        if node_counter > max_nodes:
            return False, 1, True

        start_t = perf_counter()
        subtree_nodes = 1

        anchor = first_empty()
        if anchor is None:
            if display_node_id is not None:
                node = nodes[display_node_id]
                node.elapsed_ms = (perf_counter() - start_t) * 1000.0
                node.explored_subnodes = 0
                events.append(Event("exit", display_node_id))
            return True, subtree_nodes, False

        ar, ac = anchor
        shown_children = 0

        for name in problem.selected_pieces:
            if name in used:
                continue
            for orient in ORIENTATIONS[name]:
                for cr, cc in orient:
                    dr, dc = ar - cr, ac - cc
                    shifted = tuple((r + dr, c + dc) for r, c in orient)
                    if not can_place(shifted):
                        continue

                    apply(name, shifted)
                    if enable_pruning and not has_only_five_multiple_void_regions(
                        problem.rows,
                        problem.cols,
                        allowed_keys,
                        sorted_mask,
                        filled_keys,
                    ):
                        unapply(name, shifted)
                        continue

                    child_display_id: Optional[int] = None
                    if (
                        display_node_id is not None
                        and depth < max_display_depth
                        and shown_children < max_display_children
                    ):
                        child_display_id = create_node(
                            display_node_id, depth + 1)
                        shown_children += 1

                    solved, child_count, aborted = dfs(
                        depth + 1, child_display_id)
                    subtree_nodes += child_count
                    unapply(name, shifted)

                    if aborted:
                        if display_node_id is not None:
                            node = nodes[display_node_id]
                            node.elapsed_ms = (
                                perf_counter() - start_t) * 1000.0
                            node.explored_subnodes = max(0, subtree_nodes - 1)
                            events.append(Event("exit", display_node_id))
                        return False, subtree_nodes, True

                    if solved:
                        if display_node_id is not None:
                            node = nodes[display_node_id]
                            node.elapsed_ms = (
                                perf_counter() - start_t) * 1000.0
                            node.explored_subnodes = max(0, subtree_nodes - 1)
                            events.append(Event("exit", display_node_id))
                        return True, subtree_nodes, False

        if display_node_id is not None:
            node = nodes[display_node_id]
            node.elapsed_ms = (perf_counter() - start_t) * 1000.0
            node.explored_subnodes = max(0, subtree_nodes - 1)
            events.append(Event("exit", display_node_id))

        return False, subtree_nodes, False

    root_id = create_node(parent_id=None, depth=0)
    dfs(depth=0, display_node_id=root_id)
    return TraceResult(nodes=nodes, events=events)


def compute_layout(nodes: Dict[int, NodeData]) -> Dict[int, Tuple[float, float, float]]:
    by_id = nodes
    root_id = 0
    leaf_cursor = 0
    x_pos: Dict[int, float] = {}

    def assign_x(nid: int) -> float:
        nonlocal leaf_cursor
        kids = by_id[nid].children
        if not kids:
            x = float(leaf_cursor)
            leaf_cursor += 1
            x_pos[nid] = x
            return x
        child_x = [assign_x(kid) for kid in kids]
        x = sum(child_x) / len(child_x)
        x_pos[nid] = x
        return x

    assign_x(root_id)

    min_x = min(x_pos.values()) if x_pos else 0.0
    max_x = max(x_pos.values()) if x_pos else 1.0
    span = max(1.0, max_x - min_x)

    out: Dict[int, Tuple[float, float, float]] = {}
    for nid, node in by_id.items():
        # Wider span keeps larger node cards readable at deeper levels.
        xn = ((x_pos[nid] - min_x) / span) * 13.0 - 6.5
        yn = 2.7 - node.depth * 1.8
        out[nid] = (xn, yn, 0.0)
    return out


class TriplicationDFSTreeSeparate(Scene):
    def _init_slice(self) -> None:
        self._timeline_t = 0.0
        self._slice_start = 0.0
        self._slice_end = float("inf")
        for arg in sys.argv:
            if arg.startswith("--slice="):
                raw = arg.split("=", 1)[1].strip()
                if ":" not in raw:
                    raise ValueError("Invalid --slice format. Expected --slice=START:END")
                start_str, end_str = raw.split(":", 1)
                start = float(start_str)
                end = float(end_str)
                if start < 0 or end <= start:
                    raise ValueError("Invalid --slice values. Require 0 <= START < END")
                self._slice_start = start
                self._slice_end = end
                break

    def _apply_final_state(self, animations: Sequence[object]) -> None:
        for anim in animations:
            if isinstance(anim, FadeIn):
                self.add(anim.mobject)
            elif isinstance(anim, FadeOut):
                self.remove(anim.mobject)
            else:
                self.play(anim, run_time=0.001)

    def _slice_play(self, *animations: object, run_time: float) -> None:
        seg_start = self._timeline_t
        seg_end = seg_start + run_time

        if seg_start >= self._slice_end:
            raise SliceComplete()

        if seg_end <= self._slice_start:
            self._apply_final_state(animations)
            self._timeline_t = seg_end
            return

        visible_duration = min(seg_end, self._slice_end) - max(seg_start, self._slice_start)
        if visible_duration <= 0:
            self._timeline_t = seg_end
            if seg_end >= self._slice_end:
                raise SliceComplete()
            return

        # If a segment starts before the slice window, fast-forward to its end state.
        # This keeps scene state coherent for subsequent animations.
        if seg_start < self._slice_start:
            self._apply_final_state(animations)
            self._timeline_t = seg_end
            return

        self.play(*animations, run_time=visible_duration)
        self._timeline_t = seg_end
        if seg_end >= self._slice_end:
            raise SliceComplete()

    def _slice_wait(self, duration: float) -> None:
        seg_start = self._timeline_t
        seg_end = seg_start + duration

        if seg_start >= self._slice_end:
            raise SliceComplete()

        if seg_end <= self._slice_start:
            self._timeline_t = seg_end
            return

        visible_duration = min(seg_end, self._slice_end) - max(seg_start, self._slice_start)
        if visible_duration > 0 and seg_start >= self._slice_start:
            self.wait(visible_duration)

        self._timeline_t = seg_end
        if seg_end >= self._slice_end:
            raise SliceComplete()

    def construct(self) -> None:
        self._init_slice()
        # Deterministic solvable triplication problem found offline.
        rows, cols, mask_cells = triplicate_piece_cells("Z")
        problem = Problem(
            rows=rows,
            cols=cols,
            mask_cells=mask_cells,
            selected_pieces=["T", "I", "P", "X", "W", "U", "Y", "N", "V"],
        )

        try:
            title = Text(
                "DFS Tree Build (separate animation)",
                font_size=30,
                color=WHITE,
                font=LABEL_FONT,
            ).to_edge(UP, buff=0.25)
            self._slice_play(FadeIn(title), run_time=0.4 * TIME_SCALE)

            left = self.animate_single_tree(
                problem, enable_pruning=True, title_text="With modulo-5 pruning")
            self._slice_play(FadeOut(left), run_time=0.35 * TIME_SCALE)

            right = self.animate_single_tree(
                problem, enable_pruning=False, title_text="Without modulo-5 pruning")
            self._slice_play(FadeOut(right), FadeOut(title), run_time=0.4 * TIME_SCALE)
            self._slice_wait(0.2 * TIME_SCALE)
        except SliceComplete:
            return

    def animate_single_tree(self, problem: Problem, enable_pruning: bool, title_text: str) -> VGroup:
        trace = build_trace(
            problem=problem,
            enable_pruning=enable_pruning,
            max_display_depth=3,
            max_display_children=3,
            max_nodes=1_500_000,
        )
        positions = compute_layout(trace.nodes)
        mask_set = set(problem.mask_cells)

        subtitle = Text(
            title_text,
            font_size=24,
            color=WHITE,
            font=LABEL_FONT,
        ).next_to(
            self.mobjects[0], DOWN, buff=0.2
        )
        self._slice_play(FadeIn(subtitle), run_time=0.25 * TIME_SCALE)

        node_groups: Dict[int, VGroup] = {}
        node_status_texts: Dict[int, Text] = {}
        edge_map: Dict[int, Line] = {}

        layer = VGroup(subtitle)

        for event in trace.events:
            node = trace.nodes[event.node_id]
            if event.kind == "enter":
                card, status_text = self.build_node_card(
                    rows=problem.rows,
                    cols=problem.cols,
                    mask_set=mask_set,
                    board=node.board,
                )
                card.move_to(positions[event.node_id])
                node_groups[event.node_id] = card
                node_status_texts[event.node_id] = status_text

                animations = [FadeIn(card)]
                if node.parent_id is not None:
                    parent = node_groups[node.parent_id]
                    edge = Line(
                        parent.get_bottom(),
                        card.get_top(),
                        stroke_width=1.1,
                        color=DARK_GRAY,
                    )
                    edge_map[event.node_id] = edge
                    animations.insert(0, FadeIn(edge))
                    layer.add(edge)

                self._slice_play(*animations, run_time=0.13 * TIME_SCALE)
                layer.add(card)

            elif event.kind == "exit":
                status = node_status_texts[event.node_id]
                ms_value = 0.0 if node.elapsed_ms is None else node.elapsed_ms
                new_status = Text(
                    f"{ms_value:.1f} ms",
                    font_size=13,
                    color=WHITE,
                    font=LABEL_FONT,
                )
                new_status.move_to(status)

                parent = node_groups[event.node_id]
                sub_text_old = parent[2]
                sub_text_new = Text(
                    f"subnodes: {node.explored_subnodes}",
                    font_size=12,
                    color=WHITE,
                    font=LABEL_FONT,
                )
                sub_text_new.move_to(sub_text_old)

                self._slice_play(
                    ReplacementTransform(status, new_status),
                    ReplacementTransform(sub_text_old, sub_text_new),
                    run_time=0.08 * TIME_SCALE,
                )
                node_status_texts[event.node_id] = new_status
                parent.submobjects[1] = new_status
                parent.submobjects[2] = sub_text_new

        self._slice_wait(0.6 * TIME_SCALE)
        self._slice_play(FadeOut(subtitle), run_time=0.2 * TIME_SCALE)
        return layer

    def build_node_card(
        self,
        rows: int,
        cols: int,
        mask_set: Set[Coord],
        board: Dict[Coord, PieceName],
    ) -> Tuple[VGroup, Text]:
        def piece_outline(cells: Sequence[Coord], cell_size: float) -> VGroup:
            occupied = set(cells)
            lines = VGroup()
            for r, c in occupied:
                x0 = c * cell_size
                x1 = (c + 1) * cell_size
                y0 = -r * cell_size
                y1 = -(r + 1) * cell_size
                if (r - 1, c) not in occupied:
                    lines.add(Line((x0, y0, 0), (x1, y0, 0), stroke_color=BLACK, stroke_width=1.0))
                if (r + 1, c) not in occupied:
                    lines.add(Line((x0, y1, 0), (x1, y1, 0), stroke_color=BLACK, stroke_width=1.0))
                if (r, c - 1) not in occupied:
                    lines.add(Line((x0, y0, 0), (x0, y1, 0), stroke_color=BLACK, stroke_width=1.0))
                if (r, c + 1) not in occupied:
                    lines.add(Line((x1, y0, 0), (x1, y1, 0), stroke_color=BLACK, stroke_width=1.0))
            return lines

        board_group = VGroup()
        cell = 0.05

        for r in range(rows):
            for c in range(cols):
                rc = (r, c)
                if rc in mask_set:
                    fill = "#2e3445"
                    opacity = 0.8
                else:
                    fill = "#171a22"
                    opacity = 0.25

                sq = Square(
                    side_length=cell,
                    stroke_width=0.0,
                    stroke_color=DARK_GRAY,
                    fill_color=fill,
                    fill_opacity=opacity,
                )
                sq.move_to(((c + 0.5) * cell, -(r + 0.5) * cell, 0))
                board_group.add(sq)

        # Draw each placed pentomino as a continuous fill with an outer border.
        by_piece: Dict[PieceName, List[Coord]] = defaultdict(list)
        for rc, name in board.items():
            by_piece[name].append(rc)

        for name, cells in by_piece.items():
            fill_group = VGroup()
            for r, c in cells:
                sq = Square(
                    side_length=cell,
                    stroke_width=0.0,
                    fill_color=PIECE_COLORS[name],
                    fill_opacity=1.0,
                )
                sq.move_to(((c + 0.5) * cell, -(r + 0.5) * cell, 0))
                fill_group.add(sq)
            board_group.add(fill_group)
            board_group.add(piece_outline(cells, cell))

        status = Text(
            "pending",
            font_size=13,
            color=WHITE,
            font=LABEL_FONT,
        )
        subnodes = Text(
            "subnodes: 0",
            font_size=12,
            color=WHITE,
            font=LABEL_FONT,
        )

        status.next_to(board_group, DOWN, buff=0.05)
        subnodes.next_to(status, DOWN, buff=0.03)

        card = VGroup(board_group, status, subnodes)
        return card, status
