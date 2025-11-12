from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import turtle
import random
from typing import Dict, List

# -----------------------------
# Data classes
# -----------------------------

#Reads an L-System configuration from a text file. e.g., Axiom, Rules, Angle, Step, etc.
@dataclass
class LSystemConfig:
    axiom: str
    rules: Dict[str, str]
    angle: float
    iterations: int
    step: float
    random_length: bool = False

    @classmethod
    def from_file(cls, filename: Path) -> "LSystemConfig":
        # initialize the default value of parameters
        axiom = ""
        rules: Dict[str, str] = {}
        angle = 25.0
        iterations = 4
        step = 5.0
        random_length = False
        # open and read the config
        with open(filename, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip() #remove space
                #skip empty line and conments
                if not line or line.startswith("#"):
                    continue
                    #parse config parameters
                if line.startswith("Axiom:"):
                    axiom = line.split(":", 1)[1].strip()
                elif "->" in line:
                    left, right = line.split("->", 1)
                    rules[left.strip()] = right.strip()
                elif line.startswith("Angle:"):
                    angle = float(line.split(":", 1)[1])
                elif line.startswith("Iterations:"):
                    iterations = int(line.split(":", 1)[1])
                elif line.startswith("Step:"):
                    step = float(line.split(":", 1)[1])
                elif line.lower().startswith("random_length"):
                    val = line.split(":", 1)[1].strip().lower()
                    random_length = val in ("true", "1", "yes", "y", "on")
        #return a LsystemConfig objmethod
        return cls(axiom=axiom, rules=rules, angle=angle,
                   iterations=iterations, step=step,
                   random_length=random_length)


# Expands an axiom string using a set of production rules to generate the full L-System string representation.
@dataclass
class LSystemGenerator:
    @staticmethod
    def _pick_production(prod_str: str) -> str:
        # Selects one production from a rule string
        choices = [p.strip() for p in prod_str.split("|")]
        if len(choices) == 1:
            return choices[0]

        alts: List[str] = []
        weights: List[float] = []
        has_weight = False
        # Parse each alternative and extract optional weights
        for c in choices:
            if ":" in c:
                rhs, wt = c.rsplit(":", 1)
                try:
                    w = float(wt.strip())
                    alts.append(rhs.strip()); weights.append(w)
                    has_weight = True
                except ValueError:
                    alts.append(c)
            else:
                alts.append(c)
        # if valid weight exist, the probability based on weight
        if has_weight and len(weights) == len(alts):
            total = sum(weights)
            if total <= 0:
                return random.choice(alts)
            r = random.random() * total
            acc = 0.0
            for alt, w in zip(alts, weights):
                acc += w
                if r <= acc:
                    return alt
            return alts[-1]
        else:
            return random.choice(alts)

    # Rewrites the axiom using the given rules to produce the full L-system string.
    def generate(self, cfg: LSystemConfig) -> str:
        s = cfg.axiom
        for _ in range(cfg.iterations):
            nxt = []
            for ch in s:
                if ch in cfg.rules:
                    nxt.append(self._pick_production(cfg.rules[ch]))
                else:
                    nxt.append(ch)
            s = "".join(nxt)
        return s

#Interprets the generated L-System string and draws it.
@dataclass
class TurtleRenderer:
    screen: turtle.Screen
    pen: turtle.Turtle

    def draw(self, cfg: LSystemConfig, instr: str) -> None:
        t = self.pen
        scr = self.screen

        # clear previous draw
        t.clear()
        t.penup(); t.home(); t.goto(0, -200); t.setheading(90); t.pendown()

        stack: List[tuple] = []
        depth = 0
        base_width = 3

        for cmd in instr:
            width = max(1, base_width * (0.8 ** depth))
            t.pensize(width)
            t.pencolor("black")

            if cmd == "F":
                dist = cfg.step * (random.uniform(0.1, 1.9) if cfg.random_length else 1.0)
                t.forward(dist)

            elif cmd == "+":
                t.left(cfg.angle)

            elif cmd == "-":
                t.right(cfg.angle)

            elif cmd == "[":
                depth += 1
                stack.append((t.position(), t.heading()))

            elif cmd == "]":
                if stack:
                    pos, head = stack.pop()
                    t.penup(); t.goto(pos); t.setheading(head); t.pendown()
                    depth -= 1

            elif cmd == "L":
                # when depth>3, generate leaves
                if depth > 3:
                    self._draw_leaf(t)

            elif cmd == "R":
                # random fruits
                if random.random() < 0.25:
                    self._draw_fruit(t)

            elif cmd == "f":
                t.penup(); t.forward(cfg.step); t.pendown()
        ts = t.getscreen()
        ts.getcanvas().postscript(file="tree_output.eps")
        scr.title(f"L-System | Angle={cfg.angle:.1f}° | Iter={cfg.iterations} | Step={cfg.step} | RandomLength={'ON' if cfg.random_length else 'OFF'}")
        scr.update()


    def _draw_leaf(self, t: turtle.Turtle) -> None:
        t.pencolor(0.0, 0.6, 0.2)
        t.fillcolor(0.0, 0.8, 0.2)

        pos = t.position()
        heading = t.heading()

        tilt = random.uniform(-30, 30)
        a = random.uniform(8.0, 12.0)  # 长轴
        b = random.uniform(3.0, 5.0)   # 短轴

        t.begin_fill()
        t.right(tilt)
        for _ in range(2):
            t.circle(a, 90)
            t.circle(b, 90)
        t.end_fill()

        t.penup(); t.setheading(heading); t.goto(pos); t.pendown()

    def _draw_fruit(self, t: turtle.Turtle) -> None:
        fruit_colors = ["#FF4D4D", "#FF884D", "#FFD24D", "#FF66B2", "#A64DFF"]
        t.pencolor(random.choice(fruit_colors))
        t.fillcolor(t.pencolor())
        radius = random.uniform(2, 5)
        t.begin_fill(); t.circle(radius); t.end_fill()


# -----------------------------
# bind hotkeys
# -----------------------------
#The main interactive application. Handles configuration loading, hotkeys, and dynamic redrawing.
class LSystemApp:
    def __init__(self):
        self.screen = turtle.Screen()
        self.pen = turtle.Turtle()
        self.screen.tracer(0, 0)
        self.pen.hideturtle()
        self.pen.speed(0)
        self.pen.pensize(3)

        self.cfg: LSystemConfig = LSystemConfig(
            axiom="F",
            rules={"F": "F"},
            angle=25.0,
            iterations=3,
            step=8.0,
            random_length=False,
        )
        self.gen = LSystemGenerator()
        self.renderer = TurtleRenderer(self.screen, self.pen)

        self._bind_hotkeys()


    def load_config(self, idx: int) -> None:
        path = Path(f"configs/tree{idx}.txt")
        if not path.exists():
            print(f"config not found: {path}")
            return
        self.cfg = LSystemConfig.from_file(path)
        print(f"Loaded {path}")
        self.redraw()

    def redraw(self) -> None:
        instr = self.gen.generate(self.cfg)
        self.renderer.draw(self.cfg, instr)

    # -hotkeys settings
    def _bind_hotkeys(self) -> None:
        for i in range(1, 10):
            self.screen.onkey(lambda i=i: self.load_config(i), str(i))

        self.screen.onkey(self.inc_angle, "Up")
        self.screen.onkey(self.dec_angle, "Down")
        self.screen.onkey(self.inc_iter, "Right")
        self.screen.onkey(self.dec_iter, "Left")
        self.screen.onkey(self.inc_step, "W")
        self.screen.onkey(self.dec_step, "S")
        self.screen.onkey(self.toggle_random, "R")
        #hotkey "a" for configure10
        self.screen.onkey(lambda: self.load_config(10), "A")

    def inc_angle(self) -> None:
        self.cfg.angle += 5
        self.redraw()

    def dec_angle(self) -> None:
        self.cfg.angle -= 5
        self.redraw()

    def inc_iter(self) -> None:
        self.cfg.iterations += 1
        self.redraw()

    def dec_iter(self) -> None:
        if self.cfg.iterations > 0:
            self.cfg.iterations -= 1
        self.redraw()

    def inc_step(self) -> None:
        self.cfg.step += 1
        self.redraw()

    def dec_step(self) -> None:
        if self.cfg.step > 1:
            self.cfg.step -= 1
        self.redraw()

    def toggle_random(self) -> None:
        self.cfg.random_length = not self.cfg.random_length
        print(f"Random length mode {'ON' if self.cfg.random_length else 'OFF'}")
        self.redraw()


    def run(self, initial_config: Path | None = None) -> None:
        if initial_config and initial_config.exists():
            self.cfg = LSystemConfig.from_file(initial_config)
        self.redraw()
        self.screen.listen()
        turtle.done()


# -----------------------------
# main
# -----------------------------
if __name__ == "__main__":
    app = LSystemApp()
    # use one configuration by default
    app.run(initial_config=Path("configs/tree1.txt"))
    # save the canvas, if saved, print saved to debug
    print("saved")

