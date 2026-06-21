"""
Pencil Insurance — "How it works" explainer (Manim Community Edition).

Renders the brand-matched 3-step flow (Lose it → Claim it → Get it back) as an
mp4 to embed on the landing page (#watch section auto-detects it).

────────────────────────────────────────────────────────────────────────────
RENDER (one command — needs `pip install manim` + ffmpeg; NO LaTeX required):

    manim -qh --format=mp4 -o how_it_works.mp4 manim_scenes/how_it_works.py HowItWorks

Then copy the output into static/ so the site picks it up:

    cp media/videos/how_it_works/1080p60/how_it_works.mp4 static/how_it_works.mp4

(Quality flags: -ql draft, -qm medium, -qh 1080p, -qk 4k. Use -qh for the site.)
────────────────────────────────────────────────────────────────────────────
"""
from manim import *

# Brand tokens (mirror static/themes.css Void Gold)
VOID = "#07080A"
GOLD = "#F0B429"
GOLD_WHITE = "#FFD97A"
GOLD_DIM = "#A87020"
TEXT = "#ECEFFE"
MUTED = "#8B93B4"
SURFACE = "#12151F"

config.background_color = VOID


def pencil(scale=1.0):
    """A simple gold pencil built from primitives."""
    body = Rectangle(width=0.5, height=2.4, fill_color=GOLD, fill_opacity=1, stroke_width=0)
    tip = Triangle(fill_color="#D4A05A", fill_opacity=1, stroke_width=0).scale(0.32)
    tip.next_to(body, UP, buff=0).stretch(0.9, 0)
    lead = Triangle(fill_color="#1a1a1a", fill_opacity=1, stroke_width=0).scale(0.1)
    lead.next_to(tip, UP, buff=-0.12)
    eraser = Rectangle(width=0.5, height=0.28, fill_color="#9B5D6A", fill_opacity=1, stroke_width=0)
    eraser.next_to(body, DOWN, buff=0)
    return VGroup(eraser, body, tip, lead).scale(scale)


def chip(label, emoji_color=GOLD):
    dot = Circle(radius=0.32, fill_color=GOLD, fill_opacity=0.12, stroke_color=GOLD_DIM, stroke_width=1.5)
    t = Text(label, font="Inter", weight=BOLD, color=TEXT).scale(0.5)
    t.next_to(dot, RIGHT, buff=0.3)
    return VGroup(dot, t)


class HowItWorks(Scene):
    def construct(self):
        # ── Intro wordmark ──
        mark = Text("Pencil Insurance", font="Inter", weight=BOLD, color=TEXT).scale(0.9)
        tagline = Text("school stationery, insured", font="JetBrains Mono", color=MUTED).scale(0.4)
        tagline.next_to(mark, DOWN, buff=0.3)
        intro = VGroup(mark, tagline).move_to(ORIGIN)
        self.play(Write(mark, run_time=1.1))
        self.play(FadeIn(tagline, shift=UP * 0.2))
        self.wait(0.6)
        self.play(FadeOut(intro, shift=UP * 0.3))

        # ── Step 1: Lose it ──
        p = pencil(0.9).move_to(UP * 0.6)
        label1 = Text("Lose it.", font="Inter", weight=BOLD, color=TEXT).scale(1.1).next_to(p, DOWN, buff=0.7)
        sub1 = Text("pencil gone — right before the exam", font="JetBrains Mono", color=MUTED).scale(0.4)
        sub1.next_to(label1, DOWN, buff=0.25)
        self.play(FadeIn(p, shift=DOWN * 0.3), Write(label1))
        self.play(FadeIn(sub1))
        # snap the pencil + drop
        top = p[1:]  # body+tip+lead
        self.play(Rotate(top, angle=-0.5, about_point=p.get_center()), p.animate.shift(DOWN * 0.2), run_time=0.5)
        self.play(p.animate.shift(DOWN * 4).set_opacity(0.0), run_time=0.7)
        self.play(FadeOut(label1), FadeOut(sub1))

        # ── Step 2: Claim it ──
        phone = RoundedRectangle(width=1.8, height=3.4, corner_radius=0.25,
                                 fill_color=SURFACE, fill_opacity=1, stroke_color=GOLD_DIM, stroke_width=1.5)
        screen_line = Line(phone.get_top() + DOWN * 0.45 + LEFT * 0.6,
                           phone.get_top() + DOWN * 0.45 + RIGHT * 0.6, color=MUTED, stroke_width=2)
        btn = RoundedRectangle(width=1.3, height=0.5, corner_radius=0.12, fill_color=GOLD, fill_opacity=1, stroke_width=0)
        btn.move_to(phone.get_bottom() + UP * 0.7)
        btn_t = Text("File claim", font="Inter", weight=BOLD, color=VOID).scale(0.32).move_to(btn)
        phone_grp = VGroup(phone, screen_line, btn, btn_t).move_to(UP * 0.3)
        label2 = Text("Claim it.", font="Inter", weight=BOLD, color=TEXT).scale(1.1).to_edge(DOWN, buff=1.2)
        sub2 = Text("two taps from your dashboard", font="JetBrains Mono", color=MUTED).scale(0.4)
        sub2.next_to(label2, DOWN, buff=0.25)
        self.play(FadeIn(phone_grp, shift=UP * 0.3), Write(label2))
        self.play(FadeIn(sub2))
        # tap pulse
        for _ in range(2):
            self.play(btn.animate.scale(0.92).set_fill(GOLD_WHITE), run_time=0.16)
            self.play(btn.animate.scale(1/0.92).set_fill(GOLD), run_time=0.16)
        self.play(FadeOut(phone_grp), FadeOut(label2), FadeOut(sub2))

        # ── Step 3: Get it back ──
        bag = RoundedRectangle(width=2.0, height=2.2, corner_radius=0.3,
                               fill_color=SURFACE, fill_opacity=1, stroke_color=GOLD_DIM, stroke_width=1.5)
        strap = Arc(radius=0.6, start_angle=0, angle=PI, color=GOLD_DIM, stroke_width=4).next_to(bag, UP, buff=-0.25)
        check = Text("✓", font="Inter", weight=BOLD, color=GOLD).scale(1.4).move_to(bag)
        bag_grp = VGroup(bag, strap, check).move_to(UP * 0.4)
        label3 = Text("Get it back.", font="Inter", weight=BOLD, color=GOLD_WHITE).scale(1.1).next_to(bag_grp, DOWN, buff=0.7)
        sub3 = Text("delivered to OWIS — same school day", font="JetBrains Mono", color=MUTED).scale(0.4)
        sub3.next_to(label3, DOWN, buff=0.25)
        self.play(FadeIn(bag_grp, shift=DOWN * 0.3), Write(label3))
        self.play(FadeIn(sub3))
        self.play(Flash(check, color=GOLD, line_length=0.4, num_lines=14, flash_radius=1.0))
        self.wait(0.5)
        self.play(FadeOut(bag_grp), FadeOut(label3), FadeOut(sub3))

        # ── Outro ──
        out1 = Text("Launching July 1 at OWIS", font="Inter", weight=BOLD, color=TEXT).scale(0.85)
        out2 = Text("from ₹60 / month  ·  built by Arsh & Daksh", font="JetBrains Mono", color=MUTED).scale(0.42)
        out2.next_to(out1, DOWN, buff=0.35)
        outro = VGroup(out1, out2).move_to(ORIGIN)
        self.play(Write(out1))
        self.play(FadeIn(out2, shift=UP * 0.2))
        self.wait(1.3)
        self.play(FadeOut(outro))
