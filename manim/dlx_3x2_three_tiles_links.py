from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from manim import (
    AnimationGroup,
    BLACK,
    BLUE,
    Create,
    DOWN,
    FadeIn,
    GREEN,
    GREY_B,
    LEFT,
    ORANGE,
    Line,
    Rectangle,
    RIGHT,
    Scene,
    Text,
    UP,
    VGroup,
    WHITE,
    YELLOW,
    config,
)

Coord = Tuple[int, int]


@dataclass(frozen=True)
class PieceDef:
    name: str
    cells: Tuple[Coord, ...]
    color: str


@dataclass(frozen=True)
class RowDef:
    name: str
    piece: str
    cells: Tuple[str, ...]
    orient_cells: Tuple[Coord, ...]


@dataclass(frozen=True)
class Step:
    kind: str
    active_cols: frozenset[str]
    active_rows: frozenset[str]
    chosen_rows: Tuple[str, ...]
    focus_col: Optional[str] = None
    focus_row: Optional[str] = None
    note: str = ""


PIECES: Dict[str, PieceDef] = {
    "M": PieceDef("M", ((0, 0),), BLUE),
    "D": PieceDef("D", ((0, 0), (0, 1)), ORANGE),
    "L": PieceDef("L", ((0, 0), (1, 0), (1, 1)), GREEN),
}

ROWS = 3
COLS = 2
CELL_COLUMNS: List[str] = [f"c{r}{c}" for r in range(ROWS) for c in range(COLS)]
COLUMNS: List[str] = ["M", "D", "L", *CELL_COLUMNS]


class DLXBoard3x2ThreeTilesLinks(Scene):
    PREVIEW_ROW_TIME = 0.55
    PREVIEW_RESET_TIME = 0.7
    SEARCH_STEP_TIME = 0.75
    SEARCH_SOLUTION_LIMIT = 10

    def construct(self) -> None:
        all_rows = self.build_rows()
        rows = all_rows
        row_lookup = {row.name: row for row in all_rows}

        title = Text(
            "Algorithm X / DLX: 3x2 with 1x1, 2x1, and 2x2-1 tiles",
            font_size=26,
            color=WHITE,
        )
        title.to_edge(UP, buff=0.16)

        table = self.build_matrix_table(COLUMNS, all_rows)
        table_group = table["group"]
        left_width = config.frame_width * 0.58
        top_limit = title.get_bottom()[1] - 0.22
        bottom_limit = -config.frame_height / 2 + 0.18
        left_height = top_limit - bottom_limit
        table_scale = min(
            left_width / table_group.width,
            left_height / table_group.height,
        )
        table_group.scale(table_scale)
        table_group.to_edge(LEFT, buff=0.22)
        table_group.shift(UP * (top_limit - table_group.get_top()[1]))

        board = self.build_board()
        board["group"].scale(0.78)

        picker = self.build_picker()
        picker["group"].scale(0.68)

        links = self.build_links_inset(all_rows)
        links["group"].scale(0.95)

        pane_explain = Text(
            "Pre-search: all rows\nSearch: first 10 solutions\n"
            "Right inset: DLX pointers",
            font_size=18,
            color=WHITE,
            line_spacing=0.8,
        )
        status = Text("", font_size=16, color=YELLOW)
        pane_top = VGroup(pane_explain, links["group"]).arrange(
            DOWN,
            aligned_edge=LEFT,
            buff=0.14,
        )
        board_picker = VGroup(board["group"], picker["group"]).arrange(
            RIGHT,
            aligned_edge=UP,
            buff=0.24,
        )
        right_pane = VGroup(pane_top, board_picker).arrange(
            DOWN,
            aligned_edge=LEFT,
            buff=0.34,
        )
        right_pane.next_to(table_group, RIGHT, buff=0.36, aligned_edge=UP)
        right_overflow = right_pane.get_right()[0] - (config.frame_width / 2 - 0.2)
        if right_overflow > 0:
            right_pane.shift(LEFT * right_overflow)
        status.next_to(board_picker, DOWN, buff=0.18, aligned_edge=LEFT)

        self.play(FadeIn(title), FadeIn(pane_top), run_time=0.9)
        self.play(
            Create(table_group),
            FadeIn(board_picker),
            FadeIn(status),
            run_time=1.2,
        )

        self.wait(0.25)
        self.row_preview_phase(
            rows,
            row_lookup,
            table,
            board,
            picker,
            status,
            board_picker,
        )
        steps = self.build_algorithm_x_steps(
            all_rows,
            solution_limit=self.SEARCH_SOLUTION_LIMIT,
        )
        self.search_phase(
            steps,
            row_lookup,
            table,
            links,
            board,
            picker,
            status,
            board_picker,
        )
        status.become(
            Text(
                "Done",
                font_size=16,
                color=YELLOW,
            )
        )
        status.next_to(board_picker, DOWN, buff=0.18, aligned_edge=LEFT)
        self.wait(1.2)

    def row_preview_phase(
        self,
        rows: Sequence[RowDef],
        row_lookup: Dict[str, RowDef],
        table: Dict[str, object],
        board: Dict[str, object],
        picker: Dict[str, object],
        status: Text,
        status_anchor,
    ) -> None:
        status.become(
            Text(
                "Preview: all rows",
                font_size=16,
                color=YELLOW,
            )
        )
        status.next_to(status_anchor, DOWN, buff=0.18, aligned_edge=LEFT)

        for row in rows:
            taken = {row.piece: row.orient_cells}
            status.become(
                Text(
                    f"Row preview: {row.name}",
                    font_size=16,
                    color=YELLOW,
                )
            )
            status.next_to(status_anchor, DOWN, buff=0.18, aligned_edge=LEFT)
            self.play(
                self.apply_preview_table_state(
                    table,
                    focus_row=row.name,
                ),
                self.apply_or_row(table, [row.name], row_lookup),
                self.apply_board_state(board, [row], row_lookup),
                self.apply_picker_state(picker, taken),
                run_time=self.PREVIEW_ROW_TIME,
            )

        self.play(
            self.apply_preview_table_state(
                table,
                focus_row=None,
            ),
            self.apply_or_row(table, [], row_lookup),
            self.apply_board_state(board, [], row_lookup),
            self.apply_picker_state(picker, {}),
            run_time=self.PREVIEW_RESET_TIME,
        )

    def search_phase(
        self,
        steps: Sequence[Step],
        row_lookup: Dict[str, RowDef],
        table: Dict[str, object],
        links: Dict[str, object],
        board: Dict[str, object],
        picker: Dict[str, object],
        status: Text,
        status_anchor,
    ) -> None:
        for step in steps:
            note_anim = self.update_status(status, step.note, status_anchor)
            taken_map = self.taken_map_from_chosen(step.chosen_rows, row_lookup)
            self.play(
                self.apply_table_state(
                    table,
                    active_cols=set(step.active_cols),
                    active_rows=set(step.active_rows),
                    chosen_rows=step.chosen_rows,
                    focus_col=step.focus_col,
                    focus_row=step.focus_row,
                ),
                self.apply_links_state(
                    links,
                    step,
                    row_lookup,
                ),
                self.apply_board_state(
                    board,
                    [row_lookup[name] for name in step.chosen_rows],
                    row_lookup,
                ),
                self.apply_or_row(table, step.chosen_rows, row_lookup),
                self.apply_picker_state(picker, taken_map),
                note_anim,
                run_time=self.SEARCH_STEP_TIME,
            )

    def build_links_inset(
        self,
        rows: Sequence[RowDef],
    ) -> Dict[str, object]:
        col_w = 0.42
        row_h = 0.16
        top_y = 0.0
        row_start = -0.28

        group = VGroup()
        title = Text("DLX links (active)", font_size=16, color=WHITE)
        group.add(title)

        x_map: Dict[str, float] = {
            col: idx * col_w for idx, col in enumerate(COLUMNS)
        }
        y_map: Dict[str, float] = {
            row.name: row_start - idx * row_h
            for idx, row in enumerate(rows)
        }

        col_boxes: Dict[str, Rectangle] = {}
        col_labels = VGroup()
        for col in COLUMNS:
            box = Rectangle(
                width=0.26,
                height=0.16,
                stroke_color=WHITE,
                stroke_width=0.9,
                fill_color=BLACK,
                fill_opacity=0.12,
            )
            box.move_to((x_map[col], top_y, 0))
            label = Text(col, font_size=9, color=WHITE)
            label.move_to(box.get_center())
            col_boxes[col] = box
            col_labels.add(box, label)

        node_boxes: Dict[Tuple[str, str], Rectangle] = {}
        row_memberships: Dict[str, Tuple[str, ...]] = {}
        for row in rows:
            cols = tuple(
                col for col in COLUMNS if col == row.piece or col in row.cells
            )
            row_memberships[row.name] = cols
            y = y_map[row.name]
            for col in cols:
                node = Rectangle(
                    width=0.12,
                    height=0.12,
                    stroke_color=WHITE,
                    stroke_width=0.8,
                    fill_color=WHITE,
                    fill_opacity=0.7,
                )
                node.move_to((x_map[col], y, 0))
                node_boxes[(row.name, col)] = node

        h_links_by_row: Dict[str, List[Line]] = {}
        v_links_by_col: Dict[str, List[Line]] = {col: [] for col in COLUMNS}
        h_lines = VGroup()
        v_lines = VGroup()

        for row in rows:
            cols = row_memberships[row.name]
            row_lines: List[Line] = []
            for left_col, right_col in zip(cols, cols[1:]):
                left_node = node_boxes[(row.name, left_col)]
                right_node = node_boxes[(row.name, right_col)]
                line = Line(
                    left_node.get_right(),
                    right_node.get_left(),
                    color=WHITE,
                    stroke_width=1.5,
                )
                row_lines.append(line)
                h_lines.add(line)
            h_links_by_row[row.name] = row_lines

        col_rows: Dict[str, List[str]] = {col: [] for col in COLUMNS}
        for row in rows:
            for col in row_memberships[row.name]:
                col_rows[col].append(row.name)

        for col, names in col_rows.items():
            for up_row, down_row in zip(names, names[1:]):
                up_node = node_boxes[(up_row, col)]
                down_node = node_boxes[(down_row, col)]
                line = Line(
                    up_node.get_bottom(),
                    down_node.get_top(),
                    color=BLUE,
                    stroke_width=1.2,
                )
                v_links_by_col[col].append(line)
                v_lines.add(line)

        nodes = VGroup(*node_boxes.values())

        cursor = Rectangle(
            width=0.22,
            height=0.22,
            stroke_color=YELLOW,
            stroke_width=1.4,
            fill_opacity=0.0,
        )
        cursor.set_opacity(0.0)

        graph = VGroup(col_labels, h_lines, v_lines, nodes, cursor)
        graph.next_to(title, DOWN, aligned_edge=LEFT, buff=0.1)
        group.add(graph)
        group.move_to((0, 0, 0))

        return {
            "group": group,
            "col_boxes": col_boxes,
            "nodes": node_boxes,
            "h_links_by_row": h_links_by_row,
            "v_links_by_col": v_links_by_col,
            "row_memberships": row_memberships,
            "cursor": cursor,
            "row_order": [row.name for row in rows],
        }

    def apply_links_state(
        self,
        links: Dict[str, object],
        step: Step,
        row_lookup: Dict[str, RowDef],
    ) -> AnimationGroup:
        anims = []
        active_cols = set(step.active_cols)
        active_rows = set(step.active_rows)
        chosen_rows = set(step.chosen_rows)

        for col, box in links["col_boxes"].items():
            if col in active_cols:
                color = YELLOW if col == step.focus_col else WHITE
                width = 1.8 if col == step.focus_col else 0.9
                anims.append(box.animate.set_stroke(color, width=width))
                anims.append(box.animate.set_fill(BLACK, opacity=0.12))
                anims.append(box.animate.set_opacity(1.0))
            else:
                anims.append(box.animate.set_stroke(WHITE, width=0.9))
                anims.append(box.animate.set_fill(YELLOW, opacity=0.24))
                anims.append(box.animate.set_opacity(0.3))

        for (row_name, col), node in links["nodes"].items():
            is_chosen = row_name in chosen_rows
            is_active = row_name in active_rows and col in active_cols
            if is_chosen:
                anims.append(node.animate.set_fill(GREEN, opacity=0.8))
                anims.append(node.animate.set_stroke(GREEN, width=1.0))
                anims.append(node.animate.set_opacity(1.0))
            elif is_active:
                color = ORANGE if row_name == step.focus_row else WHITE
                anims.append(node.animate.set_fill(color, opacity=0.72))
                anims.append(node.animate.set_stroke(color, width=0.9))
                anims.append(node.animate.set_opacity(1.0))
            else:
                anims.append(node.animate.set_fill(WHITE, opacity=0.18))
                anims.append(node.animate.set_stroke(WHITE, width=0.8))
                anims.append(node.animate.set_opacity(0.22))

        for row_name, row_lines in links["h_links_by_row"].items():
            row_live = row_name in active_rows or row_name in chosen_rows
            for line in row_lines:
                if row_name in chosen_rows:
                    anims.append(line.animate.set_color(GREEN))
                    anims.append(line.animate.set_opacity(0.92))
                elif row_live:
                    color = ORANGE if row_name == step.focus_row else WHITE
                    anims.append(line.animate.set_color(color))
                    anims.append(line.animate.set_opacity(0.75))
                else:
                    anims.append(line.animate.set_color(WHITE))
                    anims.append(line.animate.set_opacity(0.14))

        for col, col_lines in links["v_links_by_col"].items():
            for line in col_lines:
                if col in active_cols:
                    color = YELLOW if col == step.focus_col else BLUE
                    anims.append(line.animate.set_color(color))
                    anims.append(line.animate.set_opacity(0.74))
                else:
                    anims.append(line.animate.set_color(BLUE))
                    anims.append(line.animate.set_opacity(0.14))

        if step.focus_col and step.focus_col in links["col_boxes"]:
            target = links["col_boxes"][step.focus_col].get_center()
            anims.append(links["cursor"].animate.move_to(target))
            anims.append(links["cursor"].animate.set_opacity(1.0))
        elif step.focus_row:
            row_name = step.focus_row
            cols = links["row_memberships"].get(row_name, ())
            if cols:
                col = cols[0]
                target = links["nodes"][(row_name, col)].get_center()
                anims.append(links["cursor"].animate.move_to(target))
                anims.append(links["cursor"].animate.set_opacity(1.0))
        else:
            anims.append(links["cursor"].animate.set_opacity(0.0))

        if step.focus_row and step.focus_row in row_lookup:
            covered_cols = {row_lookup[step.focus_row].piece}
            covered_cols.update(row_lookup[step.focus_row].cells)
            if step.kind == "select":
                accent = ORANGE
                dim = 0.18
            elif step.kind == "backtrack":
                accent = GREEN
                dim = 0.8
            else:
                accent = WHITE
                dim = 0.0

            if accent != WHITE:
                for col in covered_cols:
                    if col in links["col_boxes"]:
                        anims.append(
                            links["col_boxes"][col].animate.set_fill(
                                accent,
                                opacity=0.26,
                            )
                        )
                    for line in links["v_links_by_col"].get(col, []):
                        anims.append(line.animate.set_color(accent))
                        anims.append(line.animate.set_opacity(dim))

        return AnimationGroup(*anims, lag_ratio=0.0)

    def apply_preview_table_state(
        self,
        table: Dict[str, object],
        focus_row: Optional[str],
    ) -> AnimationGroup:
        anims = []
        for box in table["col_boxes"].values():
            anims.append(box.animate.set_opacity(1.0))
            anims.append(box.animate.set_fill(opacity=0.0))
            anims.append(box.animate.set_stroke(WHITE, width=1.0))

        for row_name, row_group in table["row_groups"].items():
            label_box = table["row_labels"][row_name]
            anims.append(row_group[0].animate.set_opacity(1.0))
            anims.append(row_group[1].animate.set_opacity(1.0))
            for col, mark in table["row_marks"][row_name].items():
                base = 1.0 if col in table["row_memberships"][row_name] else 0.0
                anims.append(mark.animate.set_opacity(base))
            if row_name == focus_row:
                anims.append(label_box.animate.set_stroke(ORANGE, width=2.6))
                anims.append(
                    label_box.animate.set_fill(color=ORANGE, opacity=0.28)
                )
                anims.append(
                    row_group[1].animate.set_fill(color=ORANGE, opacity=0.25)
                )
                anims.append(row_group[1].animate.set_stroke(ORANGE, width=1.5))
            else:
                anims.append(label_box.animate.set_stroke(WHITE, width=0.9))
                anims.append(label_box.animate.set_fill(opacity=0.0))
                anims.append(row_group[1].animate.set_fill(opacity=0.0))
                anims.append(row_group[1].animate.set_stroke(WHITE, width=0.6))

        return AnimationGroup(*anims, lag_ratio=0.0)

    def apply_or_row(
        self,
        table: Dict[str, object],
        row_names: Sequence[str],
        row_lookup: Dict[str, RowDef],
    ) -> AnimationGroup:
        merged: Set[str] = set()
        for row_name in row_names:
            row = row_lookup[row_name]
            merged.add(row.piece)
            merged.update(row.cells)

        anims = []
        anims.append(
            table["or_label_box"].animate.set_fill(color=BLUE, opacity=0.18)
        )
        for col, mark in table["or_marks"].items():
            if col in merged:
                anims.append(mark.animate.set_opacity(1.0))
                anims.append(mark.animate.set_color(BLUE))
            else:
                anims.append(mark.animate.set_opacity(0.18))
                anims.append(mark.animate.set_color(WHITE))
        return AnimationGroup(*anims, lag_ratio=0.0)

    def build_rows(self) -> List[RowDef]:
        rows: List[RowDef] = []
        for piece_name, piece in PIECES.items():
            orients = self.unique_orientations(piece.cells)
            for orient_idx, orient in enumerate(orients):
                max_r = max(r for r, _ in orient)
                max_c = max(c for _, c in orient)
                for base_r in range(ROWS - max_r):
                    for base_c in range(COLS - max_c):
                        placed = tuple(
                            (base_r + r, base_c + c) for r, c in orient
                        )
                        if piece_name == "M":
                            row_name = f"M_c{base_r}{base_c}"
                        elif piece_name == "D":
                            is_h = all(r == orient[0][0] for r, _ in orient)
                            if is_h:
                                row_name = f"D_h_r{base_r}"
                            else:
                                row_name = f"D_v_c{base_c}_r{base_r}"
                        else:
                            row_name = (
                                f"L_o{orient_idx}_r{base_r}_c{base_c}"
                            )

                        rows.append(
                            RowDef(
                                row_name,
                                piece_name,
                                tuple(self.cell_name(r, c) for r, c in placed),
                                orient,
                            )
                        )

        return sorted(rows, key=lambda row: row.name)

    def build_algorithm_x_steps(
        self,
        rows: Sequence[RowDef],
        solution_limit: int,
    ) -> List[Step]:
        memberships = {
            row.name: {row.piece, *row.cells} for row in rows
        }
        row_names = [row.name for row in rows]
        steps: List[Step] = []
        solution_count = 0

        def record(
            kind: str,
            active_cols: Set[str],
            active_rows: Set[str],
            chosen_rows: List[str],
            focus_col: Optional[str] = None,
            focus_row: Optional[str] = None,
            note: str = "",
        ) -> None:
            steps.append(
                Step(
                    kind=kind,
                    active_cols=frozenset(active_cols),
                    active_rows=frozenset(active_rows),
                    chosen_rows=tuple(chosen_rows),
                    focus_col=focus_col,
                    focus_row=focus_row,
                    note=note,
                )
            )

        def solve(
            active_cols: Set[str],
            active_rows: Set[str],
            chosen_rows: List[str],
        ) -> bool:
            nonlocal solution_count
            if not active_cols:
                solution_count += 1
                record(
                    kind="solution",
                    active_cols=active_cols,
                    active_rows=active_rows,
                    chosen_rows=chosen_rows,
                    note=f"Solution {solution_count} found",
                )
                return solution_count >= solution_limit

            col = min(
                active_cols,
                key=lambda c: sum(
                    1
                    for name in active_rows
                    if c in memberships[name]
                ),
            )
            choices = [
                name for name in row_names
                if name in active_rows and col in memberships[name]
            ]

            record(
                kind="choose",
                active_cols=active_cols,
                active_rows=active_rows,
                chosen_rows=chosen_rows,
                focus_col=col,
                note=f"Choose column {col} (size={len(choices)})",
            )

            if not choices:
                record(
                    kind="dead",
                    active_cols=active_cols,
                    active_rows=active_rows,
                    chosen_rows=chosen_rows,
                    focus_col=col,
                    note="Dead end; backtrack",
                )
                return False

            for row_name in choices:
                chosen_rows.append(row_name)
                cover = memberships[row_name]
                next_cols = set(active_cols) - cover
                next_rows = {
                    name
                    for name in active_rows
                    if memberships[name].isdisjoint(cover)
                }

                record(
                    kind="select",
                    active_cols=next_cols,
                    active_rows=next_rows,
                    chosen_rows=chosen_rows,
                    focus_row=row_name,
                    note=f"Select row {row_name}",
                )

                if solve(next_cols, next_rows, chosen_rows):
                    return True

                chosen_rows.pop()
                record(
                    kind="backtrack",
                    active_cols=active_cols,
                    active_rows=active_rows,
                    chosen_rows=chosen_rows,
                    focus_row=row_name,
                    note=f"Backtrack from {row_name}",
                )
            return False

        solve(
            active_cols=set(COLUMNS),
            active_rows=set(row.name for row in rows),
            chosen_rows=[],
        )
        record(
            kind="done",
            active_cols=set(COLUMNS),
            active_rows=set(row.name for row in rows),
            chosen_rows=[],
            note=f"Search complete. Total solutions: {solution_count}",
        )
        return steps

    def taken_map_from_chosen(
        self,
        chosen_rows: Sequence[str],
        row_lookup: Dict[str, RowDef],
    ) -> Dict[str, Tuple[Coord, ...]]:
        taken: Dict[str, Tuple[Coord, ...]] = {}
        for row_name in chosen_rows:
            row = row_lookup[row_name]
            taken[row.piece] = row.orient_cells
        return taken

    def build_matrix_table(
        self,
        columns: Sequence[str],
        rows: Sequence[RowDef],
    ) -> Dict[str, object]:
        label_w = 2.2
        cell_w = 0.42
        cell_h = 0.24

        group = VGroup()
        header = VGroup()
        row_groups = {}
        row_labels = {}
        row_marks: Dict[str, Dict[str, Text]] = {}
        row_memberships: Dict[str, Set[str]] = {}
        col_boxes = {}

        top_left = Rectangle(
            width=label_w,
            height=cell_h,
            stroke_color=WHITE,
            stroke_width=1.2,
        )
        top_left.move_to((0, 0, 0))
        top_txt = Text("row", font_size=12, color=WHITE)
        top_txt.move_to(top_left.get_center())
        header.add(VGroup(top_left, top_txt))

        for col_idx, col in enumerate(columns):
            x = label_w / 2 + cell_w / 2 + col_idx * cell_w
            box = Rectangle(
                width=cell_w,
                height=cell_h,
                stroke_color=WHITE,
                stroke_width=1.0,
            )
            box.move_to((x, 0, 0))
            txt = Text(col, font_size=12, color=WHITE)
            txt.move_to(box.get_center())
            header.add(VGroup(box, txt))
            col_boxes[col] = box

        group.add(header)

        for row_idx, row in enumerate(rows, start=1):
            y = -row_idx * cell_h
            membership = {row.piece, *row.cells}
            row_memberships[row.name] = membership

            label_box = Rectangle(
                width=label_w,
                height=cell_h,
                stroke_color=WHITE,
                stroke_width=0.9,
            )
            label_box.move_to((0, y, 0))
            label_txt = Text(row.name, font_size=11, color=WHITE)
            label_txt.move_to(label_box.get_center())

            cells_group = VGroup()
            marks_group = VGroup()
            marks_map: Dict[str, Text] = {}
            for col_idx, col in enumerate(columns):
                x = label_w / 2 + cell_w / 2 + col_idx * cell_w
                box = Rectangle(
                    width=cell_w,
                    height=cell_h,
                    stroke_color=WHITE,
                    stroke_width=0.6,
                )
                box.move_to((x, y, 0))
                cells_group.add(box)

                mark = Text("1", font_size=12, color=GREEN)
                mark.move_to(box.get_center())
                mark.set_opacity(1.0 if col in membership else 0.0)
                marks_group.add(mark)
                marks_map[col] = mark

            row_group = VGroup(VGroup(label_box, label_txt), cells_group,
                               marks_group)
            row_groups[row.name] = row_group
            row_labels[row.name] = label_box
            row_marks[row.name] = marks_map
            group.add(row_group)

        or_y = -(len(rows) + 1) * cell_h
        or_label_box = Rectangle(
            width=label_w,
            height=cell_h,
            stroke_color=BLUE,
            stroke_width=1.2,
            fill_color=BLUE,
            fill_opacity=0.08,
        )
        or_label_box.move_to((0, or_y, 0))
        or_label_txt = Text("OR", font_size=12, color=BLUE)
        or_label_txt.move_to(or_label_box.get_center())
        or_cells_group = VGroup()
        or_marks: Dict[str, Text] = {}
        for col_idx, col in enumerate(columns):
            x = label_w / 2 + cell_w / 2 + col_idx * cell_w
            box = Rectangle(
                width=cell_w,
                height=cell_h,
                stroke_color=BLUE,
                stroke_width=0.9,
                fill_color=BLUE,
                fill_opacity=0.06,
            )
            box.move_to((x, or_y, 0))
            or_cells_group.add(box)
            mark = Text("1", font_size=12, color=WHITE)
            mark.move_to(box.get_center())
            mark.set_opacity(0.18)
            or_marks[col] = mark

        or_row = VGroup(VGroup(or_label_box, or_label_txt), or_cells_group)
        group.add(or_row, *or_marks.values())

        return {
            "group": group,
            "row_groups": row_groups,
            "row_labels": row_labels,
            "row_marks": row_marks,
            "row_memberships": row_memberships,
            "col_boxes": col_boxes,
            "or_label_box": or_label_box,
            "or_marks": or_marks,
        }

    def build_board(self) -> Dict[str, object]:
        cell = 0.78
        grid = VGroup()
        cell_boxes: Dict[str, Rectangle] = {}

        for r in range(ROWS):
            for c in range(COLS):
                box = Rectangle(
                    width=cell,
                    height=cell,
                    stroke_color=WHITE,
                    stroke_width=1.8,
                    fill_color=BLACK,
                    fill_opacity=0.05,
                )
                x = (c - 0.5) * cell
                y = (1 - r) * cell
                box.move_to((x, y, 0))
                grid.add(box)
                cell_boxes[self.cell_name(r, c)] = box

        labels = VGroup()
        for name, box in cell_boxes.items():
            txt = Text(name, font_size=16, color=WHITE)
            txt.move_to(box.get_center())
            labels.add(txt)

        tile_layer = VGroup()
        board_title = Text("Board", font_size=20, color=WHITE)
        board_title.next_to(grid, UP, buff=0.18)
        group = VGroup(board_title, grid, labels, tile_layer)

        return {
            "group": group,
            "cell_boxes": cell_boxes,
            "tile_layer": tile_layer,
        }

    def build_picker(self) -> Dict[str, object]:
        title = Text("Picker", font_size=20, color=WHITE)
        slots = VGroup()
        slot_content: Dict[str, VGroup] = {}
        slot_frames: Dict[str, Rectangle] = {}

        for idx, piece_name in enumerate(("M", "D", "L")):
            frame = Rectangle(
                width=1.6,
                height=0.7,
                stroke_color="#8a8a8a",
                stroke_width=0.8,
                fill_color=BLACK,
                fill_opacity=0.02,
            )
            frame.move_to((0, -idx * 1.08, 0))
            label = Text(piece_name, font_size=18, color=WHITE)
            label.next_to(frame, LEFT, buff=0.16)

            base_shape = self.make_piece_shape(
                PIECES[piece_name].cells,
                cell=0.24,
                color=PIECES[piece_name].color,
                gray=False,
            )
            base_shape.move_to(frame.get_center())
            slot_content[piece_name] = base_shape
            slot_frames[piece_name] = frame

            slots.add(VGroup(frame, label, base_shape))

        title.next_to(slots, UP, buff=0.12)
        group = VGroup(title, slots)
        return {
            "group": group,
            "slot_content": slot_content,
            "slot_frames": slot_frames,
        }

    def apply_table_state(
        self,
        table: Dict[str, object],
        active_cols: Set[str],
        active_rows: Set[str],
        chosen_rows: Sequence[str],
        focus_col: Optional[str],
        focus_row: Optional[str],
    ) -> AnimationGroup:
        anims = []
        chosen_set = set(chosen_rows)

        for col, box in table["col_boxes"].items():
            if col in active_cols:
                anims.append(box.animate.set_opacity(1.0))
                anims.append(box.animate.set_fill(opacity=0.0))
                width = 2.5 if col == focus_col else 1.0
                color = YELLOW if col == focus_col else WHITE
                anims.append(box.animate.set_stroke(color, width=width))
            else:
                anims.append(box.animate.set_opacity(0.35))
                anims.append(box.animate.set_fill(color=YELLOW, opacity=0.25))
                anims.append(box.animate.set_stroke(WHITE, width=1.0))

        for row_name, row_group in table["row_groups"].items():
            label_box = table["row_labels"][row_name]
            if row_name in chosen_set:
                anims.append(row_group[0].animate.set_opacity(1.0))
                anims.append(row_group[1].animate.set_opacity(1.0))
                for col, mark in table["row_marks"][row_name].items():
                    base = 1.0 if col in table["row_memberships"][row_name] else 0.0
                    anims.append(mark.animate.set_opacity(base))
                anims.append(label_box.animate.set_stroke(GREEN, width=2.6))
            elif row_name in active_rows:
                anims.append(row_group[0].animate.set_opacity(1.0))
                anims.append(row_group[1].animate.set_opacity(1.0))
                for col, mark in table["row_marks"][row_name].items():
                    base = 1.0 if col in table["row_memberships"][row_name] else 0.0
                    anims.append(mark.animate.set_opacity(base))
                if row_name == focus_row:
                    anims.append(
                        label_box.animate.set_stroke(ORANGE, width=2.6)
                    )
                else:
                    anims.append(label_box.animate.set_stroke(WHITE,
                                                              width=0.9))
            else:
                anims.append(row_group[0].animate.set_opacity(0.14))
                anims.append(row_group[1].animate.set_opacity(0.14))
                for col, mark in table["row_marks"][row_name].items():
                    base = 1.0 if col in table["row_memberships"][row_name] else 0.0
                    anims.append(mark.animate.set_opacity(base * 0.14))
                anims.append(label_box.animate.set_stroke(WHITE, width=0.9))

        return AnimationGroup(*anims, lag_ratio=0.0)

    def apply_board_state(
        self,
        board: Dict[str, object],
        chosen: Sequence[RowDef],
        row_lookup: Dict[str, RowDef],
    ) -> AnimationGroup:
        new_layer = VGroup()

        for row in chosen:
            color = PIECES[row.piece].color
            for cell_name in row.cells:
                base_cell = board["cell_boxes"][cell_name]
                tile_cell = Rectangle(
                    width=base_cell.width * 0.9,
                    height=base_cell.height * 0.9,
                    fill_color=color,
                    fill_opacity=0.82,
                    stroke_width=0.0,
                )
                tile_cell.move_to(base_cell.get_center())
                new_layer.add(tile_cell)

        return AnimationGroup(
            board["tile_layer"].animate.become(new_layer),
            lag_ratio=0.0,
        )

    def apply_picker_state(
        self,
        picker: Dict[str, object],
        taken: Dict[str, Tuple[Coord, ...]],
    ) -> AnimationGroup:
        anims = []
        for piece_name in ("M", "D", "L"):
            shape = picker["slot_content"][piece_name]
            is_taken = piece_name in taken
            cells = taken[piece_name] if is_taken else PIECES[piece_name].cells
            new_shape = self.make_piece_shape(
                cells,
                cell=0.24,
                color=PIECES[piece_name].color,
                gray=is_taken,
            )
            frame_center = picker["slot_frames"][piece_name].get_center()
            new_shape.move_to(frame_center)
            anims.append(shape.animate.become(new_shape))

        return AnimationGroup(*anims, lag_ratio=0.0)

    def update_status(
        self,
        status: Text,
        note: str,
        status_anchor,
    ) -> AnimationGroup:
        new_status = Text(note, font_size=16, color=YELLOW)
        new_status.next_to(status_anchor, DOWN, buff=0.18, aligned_edge=LEFT)
        return AnimationGroup(
            status.animate.become(new_status),
            lag_ratio=0.0,
        )

    def make_piece_shape(
        self,
        cells: Sequence[Coord],
        cell: float,
        color: str,
        gray: bool,
    ) -> VGroup:
        norm = self.normalize(cells)
        fill = GREY_B if gray else color
        opacity = 0.42 if gray else 0.84

        squares = VGroup()
        for r, c in norm:
            sq = Rectangle(
                width=cell,
                height=cell,
                fill_color=fill,
                fill_opacity=opacity,
                stroke_color=WHITE if not gray else GREY_B,
                stroke_width=1.0,
            )
            sq.move_to((c * cell, -r * cell, 0))
            squares.add(sq)

        if len(squares) == 0:
            return VGroup()

        center = squares.get_center()
        squares.shift(-center)
        return squares

    def unique_orientations(self, cells: Sequence[Coord]) -> List[Tuple[Coord,
                                                                       ...]]:
        seen: Set[Tuple[Coord, ...]] = set()
        out: List[Tuple[Coord, ...]] = []

        for flip in (False, True):
            for k in range(4):
                transformed = []
                for r, c in cells:
                    x, y = r, c
                    if flip:
                        y = -y
                    for _ in range(k):
                        x, y = y, -x
                    transformed.append((x, y))

                norm = self.normalize(transformed)
                if norm not in seen:
                    seen.add(norm)
                    out.append(norm)

        return out

    @staticmethod
    def normalize(cells: Iterable[Coord]) -> Tuple[Coord, ...]:
        cells = list(cells)
        min_r = min(r for r, _ in cells)
        min_c = min(c for _, c in cells)
        return tuple(sorted((r - min_r, c - min_c) for r, c in cells))

    @staticmethod
    def cell_name(r: int, c: int) -> str:
        return f"c{r}{c}"
