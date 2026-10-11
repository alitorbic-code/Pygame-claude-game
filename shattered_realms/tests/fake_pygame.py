"""Minimal pygame stand-in so the smoke test can run where pygame is not installed.

It only checks that *our* code paths run (no NameError/AttributeError/TypeError); it
cannot validate real pygame behavior. When real pygame is installed it is used instead.
"""
import sys
import types
from collections import defaultdict


class Rect:
    def __init__(self, x=0, y=0, w=0, h=0):
        if hasattr(x, "__iter__"):
            x, y, w, h = tuple(x)
        self.x, self.y, self.w, self.h = x, y, w, h

    width = property(lambda s: s.w, lambda s, v: setattr(s, "w", v))
    height = property(lambda s: s.h, lambda s, v: setattr(s, "h", v))
    left = property(lambda s: s.x, lambda s, v: setattr(s, "x", v))
    top = property(lambda s: s.y, lambda s, v: setattr(s, "y", v))
    right = property(lambda s: s.x + s.w, lambda s, v: setattr(s, "x", v - s.w))
    bottom = property(lambda s: s.y + s.h, lambda s, v: setattr(s, "y", v - s.h))
    centerx = property(lambda s: s.x + s.w / 2)
    centery = property(lambda s: s.y + s.h / 2)
    center = property(lambda s: (s.centerx, s.centery), lambda s, v: s._set(v, 0.5, 0.5))
    topleft = property(lambda s: (s.x, s.y), lambda s, v: s._set(v, 0, 0))
    topright = property(lambda s: (s.right, s.y), lambda s, v: s._set(v, 1, 0))
    bottomleft = property(lambda s: (s.x, s.bottom), lambda s, v: s._set(v, 0, 1))
    bottomright = property(lambda s: (s.right, s.bottom), lambda s, v: s._set(v, 1, 1))
    midleft = property(lambda s: (s.x, s.centery), lambda s, v: s._set(v, 0, 0.5))
    midright = property(lambda s: (s.right, s.centery), lambda s, v: s._set(v, 1, 0.5))

    def _set(self, pos, fx, fy):
        self.x, self.y = pos[0] - self.w * fx, pos[1] - self.h * fy

    def inflate(self, dx, dy):
        return Rect(self.x - dx / 2, self.y - dy / 2, self.w + dx, self.h + dy)

    def move(self, dx, dy):
        return Rect(self.x + dx, self.y + dy, self.w, self.h)

    def copy(self):
        return Rect(self.x, self.y, self.w, self.h)

    def clip(self, other):
        x, y = max(self.x, other.x), max(self.y, other.y)
        r, b = min(self.right, other.right), min(self.bottom, other.bottom)
        return Rect(x, y, max(0, r - x), max(0, b - y))

    def collidepoint(self, *pos):
        px, py = pos[0] if len(pos) == 1 else pos
        return self.x <= px < self.right and self.y <= py < self.bottom


class Surface:
    def __init__(self, size=(0, 0), flags=0):
        self.size = tuple(size)

    def get_size(self):
        return self.size

    def get_rect(self, **kw):
        rect = Rect(0, 0, *self.size)
        for key, value in kw.items():
            setattr(rect, key, value)
        return rect

    def blit(self, *a, **k): return Rect()
    def fill(self, *a, **k): return Rect()
    def set_alpha(self, *a): pass
    def set_at(self, *a): pass
    def copy(self): return Surface(self.size)
    def convert(self): return self


class Font:
    def __init__(self, name, size):
        self.size = size

    def render(self, text, aa, color):
        return Surface((int(len(text) * self.size * 0.45), self.size))


class Event:
    def __init__(self, type, dict=None, **kw):
        self.type = type
        self.dict = dict or kw
        self.__dict__.update(self.dict)


class Clock:
    def tick(self, fps=0): return 16
    def get_fps(self): return 60.0


def install():
    pg = types.ModuleType("pygame")
    pg.error = type("error", (Exception,), {})
    names = ["QUIT", "KEYDOWN", "KEYUP", "MOUSEMOTION", "MOUSEBUTTONDOWN", "MOUSEBUTTONUP", "WINDOWFOCUSLOST"]
    for i, name in enumerate(names):
        setattr(pg, name, 100 + i)
    keys = {"UP": 1, "DOWN": 2, "LEFT": 3, "RIGHT": 4, "w": 5, "a": 6, "s": 7, "d": 8, "RETURN": 9,
            "KP_ENTER": 10, "SPACE": 11, "ESCAPE": 12, "F3": 13, "F11": 14, "UNKNOWN": 0, "j": 15,
            "k": 16, "e": 17, "TAB": 18, "LSHIFT": 19}
    for name, value in keys.items():
        setattr(pg, "K_" + name, value)
    pg.KMOD_ALT = 256
    pg.SRCALPHA, pg.FULLSCREEN, pg.RESIZABLE = 1, 2, 4
    pg.Rect, pg.Surface, pg.Vector2 = Rect, Surface, tuple
    pg.init = pg.quit = lambda *a: None
    pg.mixer = types.SimpleNamespace(pre_init=lambda *a: None, init=lambda *a: None, get_init=lambda: None,
                                     quit=lambda: None, music=types.SimpleNamespace(), Sound=lambda **k: None)
    window = Surface((1280, 720))
    pg.display = types.SimpleNamespace(set_caption=lambda *a: None, set_mode=lambda *a, **k: window,
                                       get_surface=lambda: window, flip=lambda: None)
    pg.font = types.SimpleNamespace(Font=Font)
    pg.draw = types.SimpleNamespace(**{n: (lambda *a, **k: None) for n in ("rect", "circle", "line", "polygon", "ellipse")})
    pg.transform = types.SimpleNamespace(scale=lambda s, size: Surface(size))
    pg.time = types.SimpleNamespace(Clock=Clock)
    queue = []
    pg.event = types.SimpleNamespace(
        Event=Event, post=queue.append,
        get=lambda: [queue.pop(0) for _ in range(len(queue))])
    code_for = {"a": 6, "d": 8, "w": 5, "s": 7, "space": 11, "left shift": 19, "j": 15, "k": 16, "e": 17,
                "tab": 18, "escape": 12}

    def key_code(name):
        if name in code_for:
            return code_for[name]
        raise ValueError(name)

    pg.key = types.SimpleNamespace(key_code=key_code, name=lambda k: str(k), get_pressed=lambda: defaultdict(bool))
    sys.modules["pygame"] = pg
    return pg
