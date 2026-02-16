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

TIME_SCALE = 6.0
LABEL_FONT = "Andale Mono"
DEFAULT_DISPLAY_DEPTH = 3
RIGHTMOST_BRANCH_DEPTH = 12


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
    pruned: bool = False
    counterfactual: bool = False
    rightmost_chain: bool = False
    step_at_enter: int = 0
    elapsed_ms_at_enter: float = 0.0
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
    total_steps: int
    total_elapsed_ms: float
    step_elapsed_ms: List[float]


def board_signature(board: Dict[Coord, PieceName]) -> str:
    return "|".join(
        f"{r},{c}:{name}" for (r, c), name in sorted(board.items(), key=lambda item: (item[0][0], item[0][1]))
    )


def add_pruned_descendants_from_unpruned(
    pruned_trace: TraceResult,
    unpruned_trace: TraceResult,
    max_display_depth: int,
    max_display_children: int,
) -> TraceResult:
    nodes = {
        nid: NodeData(
            node_id=node.node_id,
            parent_id=node.parent_id,
            depth=node.depth,
            board=dict(node.board),
            pruned=node.pruned,
            counterfactual=node.counterfactual,
            rightmost_chain=node.rightmost_chain,
            children=list(node.children),
            elapsed_ms=node.elapsed_ms,
            explored_subnodes=node.explored_subnodes,
            step_at_enter=node.step_at_enter,
            elapsed_ms_at_enter=node.elapsed_ms_at_enter,
        )
        for nid, node in pruned_trace.nodes.items()
    }
    events: List[Event] = []
    next_id = (max(nodes.keys()) + 1) if nodes else 0

    unpruned_by_sig: Dict[str, int] = {}
    for ev in unpruned_trace.events:
        if ev.kind != "enter":
            continue
        sig = board_signature(unpruned_trace.nodes[ev.node_id].board)
        if sig not in unpruned_by_sig:
            unpruned_by_sig[sig] = ev.node_id

    def clone_subtree(un_id: int, parent_id: int) -> None:
        nonlocal next_id
        parent = nodes[parent_id]
        if parent.depth >= max_display_depth:
            return

        un_node = unpruned_trace.nodes[un_id]
        for un_child_id in un_node.children[:max_display_children]:
            if len(parent.children) >= max_display_children:
                break
            un_child = unpruned_trace.nodes[un_child_id]
            new_id = next_id
            next_id += 1
            nodes[new_id] = NodeData(
                node_id=new_id,
                parent_id=parent_id,
                depth=parent.depth + 1,
                board=dict(un_child.board),
                pruned=False,
                counterfactual=True,
                rightmost_chain=un_child.rightmost_chain,
                step_at_enter=un_child.step_at_enter,
                elapsed_ms_at_enter=un_child.elapsed_ms_at_enter,
            )
            parent.children.append(new_id)
            events.append(Event("enter", new_id))
            clone_subtree(un_child_id, new_id)
            events.append(Event("exit", new_id))

    for ev in pruned_trace.events:
        events.append(ev)
        if ev.kind != "enter":
            continue
        node = nodes[ev.node_id]
        if not node.pruned:
            continue
        sig = board_signature(node.board)
        un_id = unpruned_by_sig.get(sig)
        if un_id is not None:
            clone_subtree(un_id, ev.node_id)

    return TraceResult(
        nodes=nodes,
        events=events,
        total_steps=pruned_trace.total_steps,
        total_elapsed_ms=pruned_trace.total_elapsed_ms,
        step_elapsed_ms=list(pruned_trace.step_elapsed_ms),
    )


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
    sorted_mask = sorted(problem.mask_cells)
    allowed_keys = {key(rc) for rc in problem.mask_cells}

    used: Set[PieceName] = set()
    filled_keys: Set[str] = set()
    board: Dict[Coord, PieceName] = {}

    nodes: Dict[int, NodeData] = {}
    events: List[Event] = []
    next_node_id = 0
    node_counter = 0
    search_start = perf_counter()
    step_elapsed_ms: List[float] = [0.0]

    def create_node(
        parent_id: Optional[int],
        depth: int,
        pruned: bool = False,
        rightmost_chain: bool = False,
    ) -> int:
        nonlocal next_node_id
        nid = next_node_id
        next_node_id += 1
        elapsed_now = (perf_counter() - search_start) * 1000.0
        nodes[nid] = NodeData(
            node_id=nid,
            parent_id=parent_id,
            depth=depth,
            board=dict(board),
            pruned=pruned,
            rightmost_chain=rightmost_chain,
            step_at_enter=node_counter,
            elapsed_ms_at_enter=elapsed_now,
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
        step_elapsed_ms.append((perf_counter() - search_start) * 1000.0)
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
        attempts: List[Tuple[str, PieceName, Tuple[Coord, ...]]] = []
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
                    passes = True
                    if enable_pruning:
                        passes = has_only_five_multiple_void_regions(
                            problem.rows,
                            problem.cols,
                            allowed_keys,
                            sorted_mask,
                            filled_keys,
                        )
                    unapply(name, shifted)
                    attempts.append(
                        ("valid" if passes else "pruned", name, shifted))

        display_indices: Set[int] = set()
        can_display_children = False
        rightmost_idx = -1

        def solution_next_move() -> Optional[Tuple[PieceName, Tuple[Coord, ...]]]:
            def solve_first(first_move: Optional[Tuple[PieceName, Tuple[Coord, ...]]]) -> Optional[Tuple[PieceName, Tuple[Coord, ...]]]:
                spot = first_empty()
                if spot is None:
                    return first_move
                sar, sac = spot
                for sname in problem.selected_pieces:
                    if sname in used:
                        continue
                    for sorient in ORIENTATIONS[sname]:
                        for scr, scc in sorient:
                            sdr, sdc = sar - scr, sac - scc
                            sshifted = tuple((r + sdr, c + sdc)
                                             for r, c in sorient)
                            if not can_place(sshifted):
                                continue
                            apply(sname, sshifted)
                            ok = True
                            if enable_pruning:
                                ok = has_only_five_multiple_void_regions(
                                    problem.rows,
                                    problem.cols,
                                    allowed_keys,
                                    sorted_mask,
                                    filled_keys,
                                )
                            if ok:
                                next_first = first_move if first_move is not None else (
                                    sname, sshifted)
                                got = solve_first(next_first)
                                if got is not None:
                                    unapply(sname, sshifted)
                                    return got
                            unapply(sname, sshifted)
                return None

            return solve_first(None)

        if display_node_id is not None:
            parent = nodes[display_node_id]
            local_depth_cap = RIGHTMOST_BRANCH_DEPTH if parent.rightmost_chain else DEFAULT_DISPLAY_DEPTH
            can_display_children = depth < local_depth_cap
        if can_display_children and attempts:
            valid_indices = [i for i, (kind, _, _) in enumerate(
                attempts) if kind == "valid"]
            next_move = solution_next_move()
            if next_move is not None:
                rightmost_idx = next(
                    (
                        i
                        for i, (kind, name, shifted) in enumerate(attempts)
                        if kind == "valid" and name == next_move[0] and shifted == next_move[1]
                    ),
                    -1,
                )
            if rightmost_idx < 0:
                rightmost_idx = valid_indices[-1] if valid_indices else (
                    len(attempts) - 1)
            if parent is not None and parent.rightmost_chain:
                # On the highlighted deep branch, only keep the rightmost child.
                display_indices = {rightmost_idx}
            elif len(attempts) <= max_display_children:
                display_indices = set(range(len(attempts)))
            else:
                display_indices = {0, 1, rightmost_idx}

        found_solution = False

        for idx, (kind, name, shifted) in enumerate(attempts):
            parent = nodes[display_node_id] if display_node_id is not None else None
            parent_is_chain = parent.rightmost_chain if parent is not None else False
            chain_root_ok = depth == 0 or parent_is_chain
            is_rightmost_display = idx == rightmost_idx
            child_on_chain = chain_root_ok and is_rightmost_display

            # For the 6x10 visualization variant, only recurse along displayed
            # branches so rendering stays interactive.
            if idx not in display_indices:
                continue

            if kind == "pruned":
                if idx in display_indices and display_node_id is not None:
                    apply(name, shifted)
                    pruned_id = create_node(
                        display_node_id,
                        depth + 1,
                        pruned=True,
                        rightmost_chain=child_on_chain,
                    )
                    events.append(Event("exit", pruned_id))
                    unapply(name, shifted)
                continue

            apply(name, shifted)
            child_display_id: Optional[int] = None
            if idx in display_indices and display_node_id is not None:
                child_display_id = create_node(
                    display_node_id,
                    depth + 1,
                    rightmost_chain=child_on_chain,
                )

            solved, child_count, aborted = dfs(depth + 1, child_display_id)
            subtree_nodes += child_count
            unapply(name, shifted)

            if aborted:
                if display_node_id is not None:
                    node = nodes[display_node_id]
                    node.elapsed_ms = (perf_counter() - start_t) * 1000.0
                    node.explored_subnodes = max(0, subtree_nodes - 1)
                    events.append(Event("exit", display_node_id))
                return False, subtree_nodes, True

            if solved:
                # Keep rightmost-chain behavior as immediate success return.
                if parent_is_chain:
                    if display_node_id is not None:
                        node = nodes[display_node_id]
                        node.elapsed_ms = (perf_counter() - start_t) * 1000.0
                        node.explored_subnodes = max(0, subtree_nodes - 1)
                        events.append(Event("exit", display_node_id))
                    return True, subtree_nodes, False
                # For non-chain nodes, continue to materialize sibling structure.
                found_solution = True
                continue

        if display_node_id is not None:
            node = nodes[display_node_id]
            node.elapsed_ms = (perf_counter() - start_t) * 1000.0
            node.explored_subnodes = max(0, subtree_nodes - 1)
            events.append(Event("exit", display_node_id))

        if found_solution:
            return True, subtree_nodes, False
        return False, subtree_nodes, False

    root_id = create_node(parent_id=None, depth=0)
    dfs(depth=0, display_node_id=root_id)
    total_elapsed_ms = (perf_counter() - search_start) * 1000.0
    return TraceResult(
        nodes=nodes,
        events=events,
        total_steps=node_counter,
        total_elapsed_ms=total_elapsed_ms,
        step_elapsed_ms=step_elapsed_ms,
    )


def compute_layout(
    nodes: Dict[int, NodeData],
    total_width: float,
    top_y: float,
) -> Dict[int, Tuple[float, float, float]]:
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

    y_metric: Dict[int, float] = {root_id: 0.0}
    normal_step = 1.8
    # Fit rightmost-chain levels into the same vertical span as the normal depth cap.
    chain_step = (normal_step * DEFAULT_DISPLAY_DEPTH) / \
        float(RIGHTMOST_BRANCH_DEPTH)

    def assign_y(nid: int) -> None:
        base = y_metric[nid]
        for kid in by_id[nid].children:
            child = by_id[kid]
            # Keep the rightmost chain visually compact to show deeper lineage.
            step = chain_step if child.rightmost_chain else normal_step
            y_metric[kid] = base + step
            assign_y(kid)

    assign_y(root_id)

    min_x = min(x_pos.values()) if x_pos else 0.0
    max_x = max(x_pos.values()) if x_pos else 1.0
    span = max(1.0, max_x - min_x)

    out: Dict[int, Tuple[float, float, float]] = {}
    for nid, node in by_id.items():
        xn = (((x_pos[nid] - min_x) / span) - 0.5) * total_width
        yn = top_y - y_metric.get(nid, node.depth * 1.8)
        out[nid] = (xn, yn, 0.0)
    return out


class rect_6x10DFSTree(Scene):
    def _init_slice(self) -> None:
        self._timeline_t = 0.0
        self._slice_start = 0.0
        self._slice_end = float("inf")
        for arg in sys.argv:
            if arg.startswith("--slice="):
                raw = arg.split("=", 1)[1].strip()
                if ":" not in raw:
                    raise ValueError(
                        "Invalid --slice format. Expected --slice=START:END")
                start_str, end_str = raw.split(":", 1)
                start = float(start_str)
                end = float(end_str)
                if start < 0 or end <= start:
                    raise ValueError(
                        "Invalid --slice values. Require 0 <= START < END")
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

        visible_duration = min(seg_end, self._slice_end) - \
            max(seg_start, self._slice_start)
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

        visible_duration = min(seg_end, self._slice_end) - \
            max(seg_start, self._slice_start)
        if visible_duration > 0 and seg_start >= self._slice_start:
            self.wait(visible_duration)

        self._timeline_t = seg_end
        if seg_end >= self._slice_end:
            raise SliceComplete()

    def construct(self) -> None:
        self._init_slice()
        # Full rectangle problem: 10x6 board, all 12 pentominoes.
        rows, cols = 6, 10
        mask_cells = [(r, c) for r in range(rows) for c in range(cols)]
        problem = Problem(
            rows=rows,
            cols=cols,
            mask_cells=mask_cells,
            selected_pieces=list(PIECES.keys()),
        )

        try:
            tree = self.animate_single_tree(
                problem, enable_pruning=True, title_text="Pruned nodes are dark red")
            self._slice_play(FadeOut(tree), run_time=0.4 * TIME_SCALE)
            self._slice_wait(0.2 * TIME_SCALE)
        except SliceComplete:
            return

    def make_counter_line(
        self,
        label: str,
        step: int,
        elapsed_ms: float,
        label_col_x: float,
        time_col_x: float,
        step_col_x: float,
        ratio_col_x: float,
    ) -> Text:
        step_safe = max(1, step)
        per_step = elapsed_ms / step_safe
        row_y = 0.0

        label_text = Text(label, font_size=20, color=WHITE, font=LABEL_FONT)
        label_text.move_to((label_col_x, row_y, 0), aligned_edge=LEFT)

        time_text = Text(f"{elapsed_ms:.1f} ms",
                         font_size=20, color=WHITE, font=LABEL_FONT)
        time_text.move_to((time_col_x, row_y, 0), aligned_edge=LEFT)

        step_text = Text(f"{step}", font_size=20, color=WHITE, font=LABEL_FONT)
        step_text.move_to((step_col_x, row_y, 0), aligned_edge=LEFT)

        ratio_text = Text(f"{per_step:.3f} ms", font_size=20,
                          color=WHITE, font=LABEL_FONT)
        ratio_text.move_to((ratio_col_x, row_y, 0), aligned_edge=LEFT)

        return VGroup(label_text, time_text, step_text, ratio_text)

    def elapsed_at_step(self, trace: TraceResult, step: int) -> float:
        s = max(0, min(step, len(trace.step_elapsed_ms) - 1))
        return trace.step_elapsed_ms[s]

    def animate_single_tree(self, problem: Problem, enable_pruning: bool, title_text: str) -> VGroup:
        trace = build_trace(
            problem=problem,
            enable_pruning=enable_pruning,
            max_display_depth=DEFAULT_DISPLAY_DEPTH,
            max_display_children=3,
            max_nodes=1_500_000,
        )
        vanilla_trace = build_trace(
            problem=problem,
            enable_pruning=False,
            max_display_depth=DEFAULT_DISPLAY_DEPTH,
            max_display_children=3,
            max_nodes=1_500_000,
        )
        if enable_pruning:
            trace = add_pruned_descendants_from_unpruned(
                pruned_trace=trace,
                unpruned_trace=vanilla_trace,
                max_display_depth=DEFAULT_DISPLAY_DEPTH,
                max_display_children=3,
            )
        frame_w = float(self.camera.frame_width)
        frame_h = float(self.camera.frame_height)
        positions = compute_layout(
            trace.nodes,
            total_width=frame_w * 0.82,
            top_y=(frame_h * 0.5) - 2.0,
        )
        mask_set = set(problem.mask_cells)

        top = (frame_h * 0.5) - 0.25
        header_y = top
        row1_y = top - 0.50
        row2_y = top - 1.00
        left = -(frame_w * 0.5) + 0.35
        label_col_x = left
        time_col_x = left + frame_w * 0.18
        step_col_x = left + frame_w * 0.43
        ratio_col_x = left + frame_w * 0.60

        header_label = Text("", font_size=20, color=WHITE, font=LABEL_FONT)
        header_label.move_to((label_col_x, header_y, 0), aligned_edge=LEFT)
        header_time = Text("time-spent", font_size=20,
                           color=WHITE, font=LABEL_FONT)
        header_time.move_to((time_col_x, header_y, 0), aligned_edge=LEFT)
        header_step = Text("step-nr", font_size=20,
                           color=WHITE, font=LABEL_FONT)
        header_step.move_to((step_col_x, header_y, 0), aligned_edge=LEFT)
        header_ratio = Text("time/step:", font_size=20,
                            color=WHITE, font=LABEL_FONT)
        header_ratio.move_to((ratio_col_x, header_y, 0), aligned_edge=LEFT)
        header = VGroup(header_label, header_time, header_step, header_ratio)

        vanilla_line = self.make_counter_line(
            "vanilla", 0, 0.0, label_col_x, time_col_x, step_col_x, ratio_col_x)
        vanilla_line.shift((0, row1_y, 0))
        mod_line = self.make_counter_line(
            "mod-5", 0, 0.0, label_col_x, time_col_x, step_col_x, ratio_col_x)
        mod_line.shift((0, row2_y, 0))
        self._slice_play(
            FadeIn(header),
            FadeIn(vanilla_line),
            FadeIn(mod_line),
            run_time=0.25 * TIME_SCALE,
        )

        node_groups: Dict[int, VGroup] = {}
        layer = VGroup(header, vanilla_line, mod_line)
        shown_mod_step = 0

        for event in trace.events:
            if event.kind != "enter":
                continue
            node = trace.nodes[event.node_id]
            card = self.build_node_card(
                rows=problem.rows,
                cols=problem.cols,
                mask_set=mask_set,
                board=node.board,
                pruned=node.pruned,
                counterfactual=node.counterfactual,
            )
            card.move_to(positions[event.node_id])
            node_groups[event.node_id] = card

            # Keep the HUD monotonic even for grafted/counterfactual nodes.
            mod_step = max(shown_mod_step + 1, node.step_at_enter)
            mod_step = min(mod_step, trace.total_steps)
            mod_elapsed = self.elapsed_at_step(trace, mod_step)
            progress = mod_step / max(1, trace.total_steps)
            vanilla_step = int(round(progress * vanilla_trace.total_steps))
            vanilla_elapsed = self.elapsed_at_step(vanilla_trace, vanilla_step)

            vanilla_next = self.make_counter_line(
                "vanilla",
                vanilla_step,
                vanilla_elapsed,
                label_col_x,
                time_col_x,
                step_col_x,
                ratio_col_x,
            )
            vanilla_next.shift((0, row1_y, 0))
            mod_next = self.make_counter_line(
                "mod-5",
                mod_step,
                mod_elapsed,
                label_col_x,
                time_col_x,
                step_col_x,
                ratio_col_x,
            )
            mod_next.shift((0, row2_y, 0))

            # In-place updates are reliable for per-step HUD counters.
            vanilla_line.become(vanilla_next)
            mod_line.become(mod_next)

            animations = [
                FadeIn(card),
            ]
            if node.parent_id is not None:
                parent = node_groups[node.parent_id]
                edge = Line(
                    parent.get_bottom(),
                    card.get_top(),
                    stroke_width=1.1,
                    color=DARK_GRAY,
                )
                animations.insert(0, FadeIn(edge))
                layer.add(edge)

            self._slice_play(*animations, run_time=0.13 * TIME_SCALE)
            layer.add(card)
            shown_mod_step = mod_step

        # Snap counters to final totals after the build.
        vanilla_final = self.make_counter_line(
            "vanilla",
            vanilla_trace.total_steps,
            vanilla_trace.total_elapsed_ms,
            label_col_x,
            time_col_x,
            step_col_x,
            ratio_col_x,
        )
        vanilla_final.shift((0, row1_y, 0))
        mod_final = self.make_counter_line(
            "mod-5",
            trace.total_steps,
            trace.total_elapsed_ms,
            label_col_x,
            time_col_x,
            step_col_x,
            ratio_col_x,
        )
        mod_final.shift((0, row2_y, 0))
        vanilla_line.become(vanilla_final)
        mod_line.become(mod_final)
        self._slice_wait(0.6 * TIME_SCALE)
        return layer

    def build_node_card(
        self,
        rows: int,
        cols: int,
        mask_set: Set[Coord],
        board: Dict[Coord, PieceName],
        pruned: bool,
        counterfactual: bool,
    ) -> VGroup:
        def piece_outline(cells: Sequence[Coord], cell_size: float) -> VGroup:
            occupied = set(cells)
            lines = VGroup()
            for r, c in occupied:
                x0 = c * cell_size
                x1 = (c + 1) * cell_size
                y0 = -r * cell_size
                y1 = -(r + 1) * cell_size
                if (r - 1, c) not in occupied:
                    lines.add(Line((x0, y0, 0), (x1, y0, 0),
                              stroke_color=BLACK, stroke_width=1.0))
                if (r + 1, c) not in occupied:
                    lines.add(Line((x0, y1, 0), (x1, y1, 0),
                              stroke_color=BLACK, stroke_width=1.0))
                if (r, c - 1) not in occupied:
                    lines.add(Line((x0, y0, 0), (x0, y1, 0),
                              stroke_color=BLACK, stroke_width=1.0))
                if (r, c + 1) not in occupied:
                    lines.add(Line((x1, y0, 0), (x1, y1, 0),
                              stroke_color=BLACK, stroke_width=1.0))
            return lines

        board_group = VGroup()
        cell = 0.05
        if pruned:
            mask_color = "#4a2f36"
            outside_color = "#241a1d"
        elif counterfactual:
            mask_color = "#3e3236"
            outside_color = "#211a1d"
        else:
            mask_color = "#2e3445"
            outside_color = "#171a22"

        for r in range(rows):
            for c in range(cols):
                rc = (r, c)
                if rc in mask_set:
                    fill = mask_color
                    opacity = 0.8
                else:
                    fill = outside_color
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
        return board_group
