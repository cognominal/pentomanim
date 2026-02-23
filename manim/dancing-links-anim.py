from manim import (
    BLUE_B,
    Create,
    CurvedArrow,
    Dot,
    DOWN,
    FadeIn,
    FadeOut,
    GRAY,
    Indicate,
    LaggedStart,
    LEFT,
    Rectangle,
    RIGHT,
    Scene,
    Text,
    UP,
    VGroup,
    WHITE,
    Write,
    YELLOW,
)


class DLXNode(VGroup):
    def __init__(self, name="", is_head=False):
        super().__init__()
        box = Rectangle(width=1.4, height=0.55, stroke_width=2)
        mid = Rectangle(
            width=0.28,
            height=0.55,
            stroke_width=0,
            fill_color=GRAY,
            fill_opacity=0.55 if is_head else 0.18,
        )
        left_dot = Dot(point=LEFT * 0.34, radius=0.045)
        right_dot = Dot(point=RIGHT * 0.34, radius=0.045)

        self.box = box
        self.mid = mid
        self.left_dot = left_dot
        self.right_dot = right_dot
        self.name = name

        self.add(box, mid, left_dot, right_dot)

    def lport(self):
        return self.left_dot.get_center()

    def rport(self):
        return self.right_dot.get_center()


def bidir_link(a: DLXNode, b: DLXNode, arc=0.55, color=WHITE):
    """Two directed links between adjacent nodes."""
    fwd = CurvedArrow(
        a.rport(),
        b.lport(),
        angle=-arc,
        color=color,
        stroke_width=2,
        tip_length=0.12,
    )
    back = CurvedArrow(
        b.lport(),
        a.rport(),
        angle=arc,
        color=color,
        stroke_width=2,
        tip_length=0.12,
    )
    return VGroup(fwd, back)


class DancingLinksDemo(Scene):
    def construct(self):
        names = ["H", "1", "2", "3", "4"]
        nodes = [DLXNode(n, is_head=(n == "H")) for n in names]
        row = VGroup(*nodes).arrange(RIGHT, buff=0.75).move_to(UP * 1.2)

        head, n1, n2, n3, n4 = nodes

        title = Text("Dancing Links (remove 3rd, then 2nd)", font_size=34)
        title.to_edge(UP)

        self.play(Write(title), FadeIn(row, shift=UP * 0.2))

        l_h1 = bidir_link(head, n1, arc=0.45)
        l_12 = bidir_link(n1, n2, arc=0.45)
        l_23 = bidir_link(n2, n3, arc=0.45)
        l_34 = bidir_link(n3, n4, arc=0.45)
        l_4h = VGroup(
            CurvedArrow(
                n4.rport(),
                head.lport(),
                angle=-2.25,
                stroke_width=2,
                tip_length=0.12,
            ),
            CurvedArrow(
                head.lport(),
                n4.rport(),
                angle=2.25,
                stroke_width=2,
                tip_length=0.12,
            ),
        )

        links = VGroup(l_h1, l_12, l_23, l_34, l_4h)
        self.play(LaggedStart(*[Create(g) for g in links], lag_ratio=0.08))
        self.wait(0.4)

        t1 = Text("remove(3): 2↔3 and 3↔4 are replaced by 2↔4", font_size=28)
        t1.next_to(row, DOWN, buff=1.0)
        bypass_24 = bidir_link(n2, n4, arc=0.9, color=YELLOW)

        self.play(Indicate(n3, color=YELLOW), Write(t1))
        self.play(
            l_23.animate.set_stroke(opacity=0.15),
            l_34.animate.set_stroke(opacity=0.15),
            run_time=0.3,
        )
        self.play(Create(bypass_24), run_time=0.45)
        self.play(
            FadeOut(l_23),
            FadeOut(l_34),
            n3.animate.set_opacity(0.25),
            run_time=0.3,
        )
        self.wait(0.4)

        t2 = Text("remove(2): 1↔2 and 2↔4 are replaced by 1↔4", font_size=28)
        t2.next_to(t1, DOWN, buff=0.35)
        bypass_14 = bidir_link(n1, n4, arc=1.2, color=BLUE_B)

        self.play(Indicate(n2, color=BLUE_B), Write(t2))
        self.play(
            l_12.animate.set_stroke(opacity=0.15),
            bypass_24.animate.set_stroke(opacity=0.15),
            run_time=0.3,
        )
        self.play(Create(bypass_14), run_time=0.45)
        self.play(
            FadeOut(l_12),
            FadeOut(bypass_24),
            n2.animate.set_opacity(0.25),
            run_time=0.3,
        )
        self.wait(1.2)
