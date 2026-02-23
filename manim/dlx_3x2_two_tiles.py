from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence

from manim import (
    AnimationGroup,
    BLACK,
    BLUE,
    Create,
    DOWN,
    FadeIn,
    FadeOut,
    GREEN,
    LEFT,
    ORANGE,
    Rectangle,
    RIGHT,
    Scene,
    Text,
    UP,
    VGroup,
    WHITE,
    YELLOW,
)


@dataclass(frozen=True)
class RowDef:
    name: str
    tile: str
    cells: tuple[str, ...]


COLUMNS: List[str] = [
    "D",
    "Q",
    "c00",
    "c01",
    "c10",
    "c11",
    "c20",
    "c21",
]

ROWS: List[RowDef] = [
    RowDef("D_h_r0", "D", ("c00", "c01")),
    RowDef("D_h_r1", "D", ("c10", "c11")),
    RowDef("D_h_r2", "D", ("c20", "c21")),
    RowDef("D_v_c0_r0", "D", ("c00", "c10")),
    RowDef("D_v_c1_r0", "D", ("c01", "c11")),
    RowDef("D_v_c0_r1", "D", ("c10", "c20")),
    RowDef("D_v_c1_r1", "D", ("c11", "c21")),
    RowDef("Q_r0", "Q", ("c00", "c01", "c10", "c11")),
    RowDef("Q_r1", "Q", ("c10", "c11", "c20", "c21")),
]

TILE_COLORS: Dict[str, str] = {
    "D": BLUE,
    "Q": ORANGE,
}

ROW_LOOKUP: Dict[str, RowDef] = {row.name: row for row in ROWS}


def row_membership(row: RowDef) -> set[str]:
    return {row.tile, *row.cells}


class DLXBoard3x2TwoTiles(Scene):
    def construct(self) -> None:
        title = Text(
            "Algorithm X / DLX: 3x2 board, tiles 1x2 (D) + 2x2 (Q)",
            font_size=28,
            color=WHITE,
        )
        title.to_edge(UP, buff=0.35)
        subtitle = Text(
            "Columns: tile-use + board cells. Rows: valid placements.",
            font_size=22,
            color=WHITE,
        )
        subtitle.next_to(title, DOWN, buff=0.18)

        table = self.build_matrix_table(COLUMNS, ROWS)
        table.scale(0.72)
        table.to_edge(LEFT, buff=0.35)
        table.shift(DOWN * 0.35)

        board = self.build_board()
        board.scale(0.9)
        board.to_edge(RIGHT, buff=0.7)
        board.shift(DOWN * 0.2)

        legend = self.build_legend()
        legend.next_to(board, DOWN, buff=0.3)

        self.play(FadeIn(title), FadeIn(subtitle), run_time=1.0)
        self.play(Create(table), FadeIn(board), FadeIn(legend), run_time=1.4)

        self.wait(0.3)

        status = Text("", font_size=24, color=YELLOW)
        status.next_to(subtitle, DOWN, buff=0.2)
        self.add(status)

        # Solution path 1: choose Q, then Q_r0, then D_h_r2.
        status.become(Text("Choose column Q (smallest size = 2)",
                           font_size=24, color=YELLOW))
        status.next_to(subtitle, DOWN, buff=0.2)
        self.play(self.highlight_column(table, "Q", YELLOW), run_time=0.8)

        self.play(self.highlight_row(table, "Q_r0", ORANGE), run_time=0.8)
        status.become(Text("Pick row Q_r0, cover Q + its board columns",
                           font_size=24, color=YELLOW))
        status.next_to(subtitle, DOWN, buff=0.2)
        self.play(
            self.cover_columns(table, ["Q", "c00", "c01", "c10", "c11"]),
            self.place_tile_on_board(board, "Q_r0"),
            run_time=1.5,
        )

        status.become(Text("Remaining forced row: D_h_r2", font_size=24,
                           color=YELLOW))
        status.next_to(subtitle, DOWN, buff=0.2)
        self.play(self.highlight_row(table, "D_h_r2", BLUE), run_time=0.8)
        self.play(
            self.cover_columns(table, ["D", "c20", "c21"]),
            self.place_tile_on_board(board, "D_h_r2"),
            run_time=1.4,
        )
        status.become(Text("Solution 1 found", font_size=24, color=GREEN))
        status.next_to(subtitle, DOWN, buff=0.2)
        self.play(FadeIn(status), run_time=0.5)
        self.wait(0.8)

        # Backtrack and second branch.
        status.become(Text("Backtrack to Q and try next row Q_r1",
                           font_size=24, color=YELLOW))
        status.next_to(subtitle, DOWN, buff=0.2)
        self.play(
            self.reset_table(table),
            self.clear_board_tiles(board),
            run_time=1.2,
        )

        self.play(self.highlight_column(table, "Q", YELLOW), run_time=0.6)
        self.play(self.highlight_row(table, "Q_r1", ORANGE), run_time=0.8)
        self.play(
            self.cover_columns(table, ["Q", "c10", "c11", "c20", "c21"]),
            self.place_tile_on_board(board, "Q_r1"),
            run_time=1.4,
        )

        status.become(Text("Remaining forced row: D_h_r0", font_size=24,
                           color=YELLOW))
        status.next_to(subtitle, DOWN, buff=0.2)
        self.play(self.highlight_row(table, "D_h_r0", BLUE), run_time=0.8)
        self.play(
            self.cover_columns(table, ["D", "c00", "c01"]),
            self.place_tile_on_board(board, "D_h_r0"),
            run_time=1.2,
        )

        status.become(Text("Solution 2 found. Search complete.",
                           font_size=24, color=GREEN))
        status.next_to(subtitle, DOWN, buff=0.2)
        self.play(FadeIn(status), run_time=0.5)
        self.wait(1.5)

    def build_matrix_table(
        self,
        columns: Sequence[str],
        rows: Sequence[RowDef],
    ) -> VGroup:
        cell_w = 0.58
        cell_h = 0.42
        label_w = 2.15

        grid = VGroup()
        header_cells = VGroup()
        row_labels = VGroup()
        row_cells = VGroup()
        markers = VGroup()

        total_cols = len(columns)

        header_box = Rectangle(
            width=label_w,
            height=cell_h,
            stroke_color=WHITE,
            stroke_width=1.5,
        )
        header_box.move_to((0, 0, 0))
        header_txt = Text("rows", font_size=20)
        header_txt.move_to(header_box.get_center())
        header_cells.add(VGroup(header_box, header_txt))

        for col_idx, col in enumerate(columns):
            x = label_w / 2 + cell_w / 2 + col_idx * cell_w
            box = Rectangle(
                width=cell_w,
                height=cell_h,
                stroke_color=WHITE,
                stroke_width=1.3,
            )
            box.move_to((x, 0, 0))
            txt = Text(col, font_size=18)
            txt.move_to(box.get_center())
            header_cells.add(VGroup(box, txt))

        for row_idx, row in enumerate(rows, start=1):
            y = -row_idx * cell_h

            label_box = Rectangle(
                width=label_w,
                height=cell_h,
                stroke_color=WHITE,
                stroke_width=1.1,
            )
            label_box.move_to((0, y, 0))
            label_txt = Text(row.name, font_size=16)
            label_txt.move_to(label_box.get_center())
            row_group = VGroup(label_box, label_txt)
            row_group.set_z_index(1)
            row_labels.add(row_group)

            membership = row_membership(row)
            row_cells_for_row = VGroup()
            marker_row = VGroup()
            for col_idx, col in enumerate(columns):
                x = label_w / 2 + cell_w / 2 + col_idx * cell_w
                box = Rectangle(
                    width=cell_w,
                    height=cell_h,
                    stroke_color=WHITE,
                    stroke_width=1.0,
                )
                box.move_to((x, y, 0))
                row_cells_for_row.add(box)

                marker = Text("1", font_size=20, color=GREEN)
                marker.move_to(box.get_center())
                marker.set_opacity(1.0 if col in membership else 0.0)
                marker_row.add(marker)

            row_cells.add(row_cells_for_row)
            markers.add(marker_row)

        grid.add(header_cells, row_labels, row_cells, markers)

        # Attach named subgroups for step animations.
        grid.column_boxes = {
            columns[i]: header_cells[i + 1][0] for i in range(total_cols)
        }
        grid.row_groups = {
            rows[i].name: VGroup(row_labels[i], row_cells[i], markers[i])
            for i in range(len(rows))
        }
        grid.row_label_boxes = {
            rows[i].name: row_labels[i][0] for i in range(len(rows))
        }

        return grid

    def build_board(self) -> VGroup:
        cell = 0.9
        rows = 3
        cols = 2
        grid = VGroup()
        for r in range(rows):
            for c in range(cols):
                box = Rectangle(
                    width=cell,
                    height=cell,
                    stroke_color=WHITE,
                    stroke_width=2.0,
                    fill_color=BLACK,
                    fill_opacity=0.05,
                )
                x = (c - 0.5) * cell
                y = (1 - r) * cell
                box.move_to((x, y, 0))
                grid.add(box)

        labels = VGroup()
        idx = 0
        for r in range(rows):
            for c in range(cols):
                txt = Text(f"c{r}{c}", font_size=18, color=WHITE)
                txt.move_to(grid[idx].get_center())
                labels.add(txt)
                idx += 1

        tile_layer = VGroup()
        board = VGroup(grid, labels, tile_layer)
        board.tile_layer = tile_layer
        board.grid_cells = {
            "c00": grid[0],
            "c01": grid[1],
            "c10": grid[2],
            "c11": grid[3],
            "c20": grid[4],
            "c21": grid[5],
        }
        return board

    def build_legend(self) -> VGroup:
        d_swatch = Rectangle(
            width=0.4,
            height=0.25,
            fill_color=BLUE,
            fill_opacity=0.8,
            stroke_width=0.0,
        )
        d_txt = Text("D: 1x2 tile", font_size=18)
        d = VGroup(d_swatch, d_txt).arrange(RIGHT, buff=0.14)

        q_swatch = Rectangle(
            width=0.4,
            height=0.25,
            fill_color=ORANGE,
            fill_opacity=0.8,
            stroke_width=0.0,
        )
        q_txt = Text("Q: 2x2 tile", font_size=18)
        q = VGroup(q_swatch, q_txt).arrange(RIGHT, buff=0.14)

        return VGroup(d, q).arrange(DOWN, aligned_edge=LEFT, buff=0.15)

    def highlight_column(self, table: VGroup, col: str, color: str):
        return table.column_boxes[col].animate.set_stroke(color, width=4.0)

    def highlight_row(self, table: VGroup, row_name: str, color: str):
        return table.row_label_boxes[row_name].animate.set_stroke(
            color,
            width=3.5,
        )

    def cover_columns(self, table: VGroup, cols: Iterable[str]):
        anims = []
        covered = set(cols)
        for col in covered:
            anims.append(table.column_boxes[col].animate.set_fill(
                color=YELLOW,
                opacity=0.28,
            ))

        for row_name, row_group in table.row_groups.items():
            row = ROW_LOOKUP[row_name]
            if row_membership(row) & covered:
                anims.append(row_group.animate.set_opacity(0.2))

        return AnimationGroup(*anims, lag_ratio=0.0)

    def place_tile_on_board(self, board: VGroup, row_name: str):
        row = ROW_LOOKUP[row_name]
        color = TILE_COLORS[row.tile]
        placed = VGroup()
        for cell_name in row.cells:
            base_cell = board.grid_cells[cell_name]
            tile_cell = Rectangle(
                width=base_cell.width * 0.92,
                height=base_cell.height * 0.92,
                fill_color=color,
                fill_opacity=0.8,
                stroke_width=0.0,
            )
            tile_cell.move_to(base_cell.get_center())
            placed.add(tile_cell)

        placed.set_z_index(2)
        board.tile_layer.add(placed)
        return FadeIn(placed)

    def clear_board_tiles(self, board: VGroup):
        to_remove = VGroup(*board.tile_layer)
        board.tile_layer.remove(*list(board.tile_layer))
        return FadeOut(to_remove)

    def reset_table(self, table: VGroup):
        anims = []
        for box in table.column_boxes.values():
            anims.append(box.animate.set_stroke(WHITE, width=1.3))
            anims.append(box.animate.set_fill(opacity=0.0))
        for row_group in table.row_groups.values():
            anims.append(row_group.animate.set_opacity(1.0))
        for label_box in table.row_label_boxes.values():
            anims.append(label_box.animate.set_stroke(WHITE, width=1.1))
        return AnimationGroup(*anims, lag_ratio=0.0)
