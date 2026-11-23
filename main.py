import math, os, random
from kivy.app import App
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.core.window import Window 
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line 
from kivy.graphics.texture import Texture
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button 
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label 
from kivy.uix.widget import Widget

IMAGE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "painting.jpg")
LEVELS = [("Easy 3x3", 3, 60), ("Medium 4x4", 4, 120), ("Hard 5x5", 5, 180)]
CYAN = (.45, .85, 1, 1)
PURPLE = (.72, .55, 1, 1)
RED = (1, .4, .45, 1)


def clamp(v):
    return max(0, min(255, int(v)))
    
    
def make_painting(size=240):
    """Procedural sunset painting. Rows are written bottom-up (GL order)."""
    buf = bytearray()
    for row in range(size):
        v = 1 - row / size 
        for col in range(size):
            u = col / size 
            if v < 0.62:
                t = v / 0.62
                r, g, b = 50 + 205 * t, 30 + 140 * t * t, 130 - 70 * t
                d = math.hypot(u - 0.5, v - 0.40)
                if d < 0.13:
                    r, g, b = 255, 235, 130
                elif d < 0.28:
                    k = (0.28 - d) /0.15
                    r += (255 - r) * k * 0.6
                    g += (180 - g) * k * 0.5
                ridge = 0.50 + 0.07 * math.sin(u * 9) + 0.04 * math.sin(u * 23 + 1)
                if v > ridge:
                    s = (v - ridge) * 3
                    r, g, b = 60 - 30 * s, 30 + 40 * s, 70 + 20 * s
            else:
                t = (v - 0.62) / 0.38
                wave = math.sin(v * 90 + math.sin(u * 14) * 2)
                r, g, b = 20 + 40 * t, 70 + 50 * t + wave * 15, 140 - 30 * t + wave * 20
                if abs(u - 0.5) < 0.10 * (1 - t * 0.5) and wave > -0.3:
                    r, g, b = 255, 200 + wave * 30, 100
            buf += bytes((clamp(r), clamp(g), clamp(b), 255))
    return buf, size, size 
    
    
def to_gray(px):
    out = bytearray(px)
    for i in range(0, len(px), 4):
        g = (px[i] * 30 + px[i + 1] * 59 + px[i + 2] * 11) // 100
        out[i] = out[i + 1] = out[i + 2] = g
    return out
    
    
def tex_from(buf, w, h):
    t = Texture.create(size=(w, h), colorfmt="rgba")
    t.blit_buffer(bytes(buf), colorfmt="rgba", bufferfmt="ubyte")
    return t
    
    
def make_glow(n=64):
    """Soft radial blob used for the background glow."""
    buf = bytearray()
    for j in range(n):
        for i in range(n):
            d = math.hypot(i - n / 2 + .5, j - n / 2 + .5) / (n / 2)
            a = max(0, 1 - d) ** 2
            buf += bytes((255, 255, 255, int(255 * a)))
    return tex_from(buf, n, n)
    
    
def load_art():
    buf = None
    if os.path.exists(IMAGE_PATH):
        try:
            t = CoreImage(IMAGE_PATH).texture
            buf, w, h = bytearray(t.pixels), t.width, t.height
        except Exception:
            buf = None
    if buf is None:
        buf, w, h = make_painting()
    return tex_from(buf, w, h), tex_from(to_gray(buf), w, h), w / h
    
    
def slice_tiles(tex, n):
    w, h = tex.size 
    tw, th = int(w) // n, int(h) // n
    return [tex.get_region((i % n) * tw, int(h) - (i // n + 1) * th, tw, th)
            for i in range(n * n)]
            
            
def glass(x, y, w, h, r, fill=.08, border=.22, tint=(1, 1, 1)):
    """Draw one frosted-glass panel: tinted fill, soft edge, bright top rim."""
    r = min(r, w / 2, h / 2)
    Color(tint[0], tint[1], tint[2], fill)
    RoundedRectangle(pos=(x, y), size=(w, h), radius=[r])
    Color(1, 1, 1, border)
    Line(rounded_rectangle=(x, y, w, h, r), width=1.1)
    Color(1, 1, 1, min(1, border + .25))
    Line(points=[x + r, y + h - .5, x + w - r, y + h - .5], width=1.2)
    
    
class Backdrop(FloatLayout):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.grad = Texture.create(size=(1, 2), colorfmt="rgba")
        self.grad.blit_buffer(bytes([8, 10, 24, 255, 28, 14, 48, 255]),
                              colorfmt="rgba", bufferfmt="ubyte")
        self.grad.mag_filter = "linear"
        self.glow = make_glow()
        self.bind(pos=self.redraw, size=self.redraw)
        
    def redraw(self, *a):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(1, 1, 1, 1)
            Rectangle(texture=self.grad, pos=self.pos, size=self.size)
            w, h = self.size 
            blobs = ((.10, .88, 1.1, (.55, .30, 1, .55)),
                     (.95, .12, 1.2, (.10, .70, 1, .45)),
                     (.85, .62, .7, (1, .30, .70, .28)))
            for fx, fy, s, col in blobs:
                d = w * s
                Color(*col)
                Rectangle(texture=self.glow, size=(d, d),
                          pos=(self.x + w * fx - d / 2, self.y + h * fy - d / 2))
                          
                          
class Stat(BoxLayout):
    def __init__(self, title, **kw):
        super().__init__(orientation="vertical", padding=(dp(6), dp(6)), **kw)
        self.frac, self.accent = None, CYAN
        self.cap = Label(text=title, font_size="11sp", color=(1, 1, 1, .55),
                         size_hint_y=.35)
        self.val = Label(text="-", font_size="20sp", bold=True, size_hint_y=.65)
        self.add_widget(self.cap)
        self.add_widget(self.val)
        self.bind(pos=self.redraw, size=self.redraw)
        
    def set(self, text, frac=None, accent=CYAN):
        self.val.text, self.val.color = text, accent
        self.frac, self.accent = frac, accent
        self.redraw()
        
    def redraw(self, *a):
        self.canvas.before.clear()
        with self.canvas.before:
            glass(self.x, self.y, self.width, self.height, dp(16))
            if self.frac is not None:
                bw = self.width - dp(28)
                x, y = self.x + dp(14), self.y + dp(7)
                Color(1, 1, 1, .12)
                RoundedRectangle(pos=(x, y), size=(bw, dp(4)), radius=[dp(2)])
                Color(*self.accent)
                RoundedRectangle(pos=(x, y), size=(max(dp(4), bw * self.frac), dp(4)),
                                 radius=[dp(2)])


class GlassButton(Button):
    def __init__(self, **kw):
        super().__init__(background_normal="", background_down="",
                         background_color=(0, 0, 0, 0), bold=True,
                         font_size="15sp", **kw)
        self.bind(pos=self.redraw, size=self.redraw, state=self.redraw)
        
    def redraw(self, *a):
        down = self.state == "down"
        self.canvas.before.clear()
        with self.canvas.before:
            glass(self.x, self.y, self.width, self.height, dp(18),
                  fill=.22 if down else .09, border=.38 if down else .22,
                  tint=(.6, .8, 1) if down else (1, 1, 1))
                  
                  
class Game(Widget):
    def __init__(self, stats, **kw):
        super().__init__(**kw)
        self.stats = stats
        self.level = 0
        self.on_level = None
        self.ctex, self.gtex, self.aspect = load_art()
        self.msg = Label(text="", markup=True, halign="center", valign="middle",
                         size_hint=(None, None), font_size="16sp")
        self.add_widget(self.msg)
        self.new_game()
        Clock.schedule_interval(self.tick, 1 / 30)
        
    def new_game(self):
        _, self.n, self.limit = LEVELS[self.level]
        self.ctiles = slice_tiles(self.ctex, self.n)
        self.gtiles = slice_tiles(self.gtex, self.n)
        self.perm = list(range(self.n * self.n))
        while self.solved():
            random.shuffle(self.perm)
        self.sel, self.moves, self.time_left = None, 0, float(self.limit)
        self.state, self.t_end, self.flash = "play", 0.0, 0.0
        self.conf = []
        self.msg.text = ""
        if self.on_level:
            self.on_level()
            
    def solved(self):
        return all(t == p for p, t in enumerate(self.perm))
        
    def board(self):
        m = dp(18)
        aw, ah = self.width - 2 * m, self.height - 2 * m
        bw = min(aw, ah * self.aspect)
        bh = bw / self.aspect
        return self.x + (self.width - bw) / 2, self.y + (self.height - bh) / 2, bw, bh
        
    def on_touch_down(self, t):
        if not self.collide_point(*t.pos):
            return False
        if self.state != "play":
            if self.t_end > 1.5:                     # avoid accidental taps
                if self.state == "won":
                    self.level = (self.level + 1) % len(LEVELS)
                self.new_game()
            return True
        bx, by, bw, bh = self.board()
        n = self.n
        c = int((t.x - bx) // (bw / n))
        r = int((by + bh - t.y) // (bh / n))
        if 0 <= c < n and 0 <= r < n:
            p = r * n + c
            if self.sel is None:
                self.sel = p
            elif self.sel == p:
                self.sel = None
            else:
                a = self.sel
                self.perm[a], self.perm[p]= self.perm[p], self.perm[a]
                self.sel, self.moves = None, self.moves + 1
                if self.solved():
                    self.win()
        return True
        
    def win(self):
        self.state, self.t_end, self.flash = "won", 0.0, 1.0
        self.msg.text = ("[size=32sp][b]SOLVED![/b][/size]\n%d moves  |  %ds left\n"
                         "[color=8fdcff]Tap for next level[/color]"
                         % (self.moves, self.time_left))
        cx, cy = self.center 
        for _ in range(180):                          # burst from the centre
            a, s = random.uniform(0, 6.283), random.uniform(250, 750)
            self.conf.append([cx, cy, math.cos(a) * s, math.sin(a) * s + 200,
                              self.rcolor(), random.uniform(6, 14)])
                              
    @staticmethod
    def rcolor():
        return (random.random() * .6 + .4, random.random() * .6 + .4,
                random.random() * .6 + .4, 1)
                
    def tick(self, dt):
        if self.state == "play":
            self.time_left -= dt
            if self.time_left <= 0:
                self.time_left, self.state, self.t_end = 0, "lost", 0.0
                self.msg.text = ("[size=30sp][b]TIME'S UP[/b][/size]\n"
                                 "[color=8fdcff]Tap to retry[/color]")
        else:
            self.t_end += dt
        if self.state == "won" and self.t_end < 3.5:  # confetti rain
            for _ in range(4):
                self.conf.append([self.x + random.random() * self.width, self.top,
                                  random.uniform(-60, 60), random.uniform(-250, -80),
                                  self.rcolor(), random.uniform(6, 14)])
        for q in self.conf:
            q[3] -= 500 * dt
            q[0] += q[2] * dt
            q[1] += q[3] * dt
        self.conf = [q for q in self.conf if q[1] > -30]
        self.flash = max(0, self.flash - dt * 1.5)
        
        total = len(self.perm)
        good = sum(1 for p, t in enumerate(self.perm) if p == t)
        s_col, s_mov, s_time = self.stats
        s_col.set("%d/%d" % (good, total), good / total, PURPLE)
        s_mov.set(str(self.moves))
        low = self.time_left < 10
        s_time.set("%d s" % math.ceil(self.time_left),
                   self.time_left / self.limit, RED if low else CYAN)
        self.draw()
        
    def draw(self):
        n = self.n
        self.canvas.before.clear()
        with self.canvas.before:
            bx, by, bw, bh = self.board()
            pad = dp(8)
            glass(bx - pad, by - pad, bw + 2 * pad, bh + 2 * pad, dp(22), fill=.07)
            tw, th = bw / n, bh / n
            won = self.state == "won"
            gap = 0 if won else 1.5
            for p, tid in enumerate(self.perm):
                x = bx + (p % n) * tw
                y = by + bh - (p // n + 1) * th
                tex = self.ctiles[tid] if (won or tid == p) else self.gtiles[tid]
                Color(1, 1, 1, 1)
                Rectangle(texture=tex, pos=(x + gap, y + gap),
                          size=(tw - 2 * gap, th - 2 * gap))
            if self.sel is not None and not won:
                x = bx + (self.sel % n) * tw
                y = by + bh - (self.sel // n + 1) * th
                Color(1, 1, 1, .18)
                Rectangle(pos=(x + 2, y + 2), size=(tw - 4, th - 4))
                Color(*CYAN)
                Line(rectangle=(x + 2, y + 2, tw - 4, th - 4), width=2.5)
            if self.state != "play":
                if self.state == "lost":
                    Color(0, 0, 0, .55)
                    RoundedRectangle(pos=(bx - pad, by - pad),
                                     size=(bw + 2 * pad, bh + 2 * pad), radius=[dp(22)])
                pw, ph = min(self.width * .85, dp(300)), dp(170)
                px, py = self.center_x - pw / 2, self.center_y - ph / 2
                Color(.03, .03, .07, .55)
                RoundedRectangle(pos=(px, py), size=(pw, ph), radius=[dp(24)])
                glass(px, py, pw, ph, dp(24), fill=.10, border=.30, tint=(.7, .8, 1))
                self.msg.pos, self.msg.size = (px, py), (pw, ph)
                self.msg.text_size = (pw, ph)
            for q in self.conf:
                Color(*q[4])
                Rectangle(pos=(q[0], q[1]), size=(q[5], q[5]))
            if self.flash > 0:
                Color(1, 1, 1, self.flash)
                Rectangle(pos=self.pos, size=self.size)
                
                
class PuzzleApp(App):
    def build(self):
        Window.clearcolor = (.03, .03, .06, 1)
        root = Backdrop()
        col = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        
        row = BoxLayout(size_hint_y=None, height=dp(62), spacing=dp(10))
        stats = [Stat("COLOUR"), Stat("MOVES"), Stat("TIME")]
        for s in stats:
            row.add_widget(s)
            
        game = Game(stats)
        
        bar = BoxLayout(size_hint_y=None, height=dp(54), spacing=dp(10))
        btn_new = GlassButton(text="New game")
        btn_lvl = GlassButton(text=LEVELS[0][0])
        
        def cycle(*_):
            game.level = (game.level + 1) % len(LEVELS)
            game.new_game()
            
        game.on_level = lambda: setattr(btn_lvl, "text", LEVELS[game.level][0])
        btn_new.bind(on_release=lambda *_: game.new_game())
        btn_lvl.bind(on_release=cycle)
        bar.add_widget(btn_new)
        bar.add_widget(btn_lvl)
        
        col.add_widget(row)
        col.add_widget(game)
        col.add_widget(bar)
        root.add_widget(col)
        return root
        
        
PuzzleApp().run()
                                 
                    
