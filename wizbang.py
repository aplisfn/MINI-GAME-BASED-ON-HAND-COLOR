import random, math
from functools import lru_cache
from types import SimpleNamespace
import cv2
import numpy as np
import pygame

CAMERA_INDEX = 0
LOWER_PURPLE = np.array([120, 40, 30], dtype=np.uint8)
UPPER_PURPLE = np.array([165, 255, 255], dtype=np.uint8)
MIN_AREA = 1200
WIDTH, HEIGHT = 1000, 700
FPS = 60
START_LIVES = 3
PLAYER_Y = HEIGHT - 120
GY = PLAYER_Y + 50          
MEGA_TIME = 0.6
MAX_CHARGE = 1.0
AUTO_PAUSE = True      
PAUSE_DELAY = 0.4     

FIST_SOL, OPEN_SOL = 0.90, 0.74

WHITE = (245, 247, 255)
PURPLE = (150, 95, 235)
LAVENDER = (210, 185, 255)
CYAN = (90, 220, 255)
GOLD = (255, 205, 90)
RED = (255, 85, 105)
GREEN = (100, 235, 165)
MUTED = (160, 170, 205)
SKIN = (255, 214, 178)


#  helpers
_fonts = {}
def text(surf, msg, size, color, x, y, shadow=True):
    if size not in _fonts:
        _fonts[size] = pygame.font.SysFont("arial", size, bold=True)
    img = _fonts[size].render(msg, True, color)
    rect = img.get_rect(center=(x, y))
    if shadow:
        sh = _fonts[size].render(msg, True, (8, 5, 22))
        surf.blit(sh, rect.move(2, 2))
    surf.blit(img, rect)


@lru_cache(maxsize=512)
def glow(radius, color):
    s = pygame.Surface((radius * 2, radius * 2))
    for r in range(radius, 0, -2):
        k = (1 - r / radius) ** 2
        pygame.draw.circle(s, tuple(int(c * k) for c in color), (radius, radius), r)
    return s


def add_glow(surf, x, y, radius, color):
    radius = max(4, int(radius))
    surf.blit(glow(radius, tuple(int(c) for c in color)), (int(x) - radius, int(y) - radius),
              special_flags=pygame.BLEND_RGB_ADD)


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_col(c1, c2, t):
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))


def clamp01(v):
    return max(0.0, min(1.0, v))

def sprite(w, h, fn, ss=4):
    big = pygame.Surface((w * ss, h * ss), pygame.SRCALPHA)
    fn(big, ss)
    return pygame.transform.smoothscale(big, (w, h))


def poly(s, S, col, pts):
    pygame.draw.polygon(s, col, [(x * S, y * S) for x, y in pts])


def circ(s, S, col, c, r):
    pygame.draw.circle(s, col, (int(c[0] * S), int(c[1] * S)), int(r * S))


def ell(s, S, col, x, y, w, h, width=0):
    pygame.draw.ellipse(s, col, (x * S, y * S, w * S, h * S), int(width * S) if width else 0)


def line(s, S, col, a, b, w):
    pygame.draw.line(s, col, (a[0] * S, a[1] * S), (b[0] * S, b[1] * S), max(1, int(w * S)))


def flashed(spr):
    f = spr.copy()
    f.fill((150, 150, 150, 0), special_flags=pygame.BLEND_RGB_ADD)
    return f


# karakter 
def wizard_frame(sway):
    def d(s, S):
        robe, robe_l, robe_d = (70, 42, 150), (100, 66, 192), (52, 30, 118)
        # jubah
        poly(s, S, robe, [(30 + sway, 150), (42, 82), (88, 82), (100 + sway, 150)])
        poly(s, S, robe_l, [(30 + sway, 150), (42, 82), (64, 82), (60, 150)])
        poly(s, S, robe_d, [(100 + sway, 150), (88, 82), (72, 82), (78, 150)])
        line(s, S, GOLD, (30 + sway, 147), (100 + sway, 147), 4)
        for i in range(7):  
            px = 36 + sway + i * 10
            poly(s, S, (255, 225, 140), [(px, 147), (px + 3, 141), (px + 6, 147)])
        # sabuk
        line(s, S, (255, 190, 70), (44, 106), (86, 106), 5)
        poly(s, S, (255, 235, 150), [(62, 102), (68, 102), (68, 110), (62, 110)])
        # lengan belakang
        poly(s, S, (86, 54, 172), [(42, 86), (30, 114), (41, 120), (54, 94)])
        circ(s, S, SKIN, (35, 120), 5.5)
        # tongkat
        line(s, S, (112, 72, 40), (98, 160), (100, 36), 5.5)
        line(s, S, (172, 122, 76), (97, 160), (99, 36), 1.6)
        line(s, S, (200, 160, 90), (100, 42), (92, 28), 3)
        line(s, S, (200, 160, 90), (100, 42), (108, 28), 3)
        # lengan depan
        poly(s, S, (104, 70, 198), [(84, 86), (100, 104), (95, 116), (76, 98)])
        circ(s, S, SKIN, (98, 110), 6)
        # kepala
        circ(s, S, (240, 190, 155), (51, 65), 3.5)   # telinga
        circ(s, S, (240, 190, 155), (79, 65), 3.5)
        circ(s, S, SKIN, (65, 64), 14.5)
        # janggut
        poly(s, S, (236, 236, 250), [(50, 66), (80, 66), (75, 98), (65, 118), (55, 98)])
        poly(s, S, (200, 200, 228), [(65, 72), (80, 66), (75, 98), (65, 118)])
        line(s, S, (190, 190, 220), (65, 80), (65, 112), 1.2)
        circ(s, S, (240, 188, 150), (65, 69), 4)    # hidung
        # mata + alis
        circ(s, S, (35, 25, 60), (59, 62), 2)
        circ(s, S, (35, 25, 60), (71, 62), 2)
        circ(s, S, WHITE, (59.6, 61.4), .7)
        circ(s, S, WHITE, (71.6, 61.4), .7)
        line(s, S, (240, 240, 255), (54, 56), (62, 58), 2.4)
        line(s, S, (240, 240, 255), (68, 58), (76, 56), 2.4)
        # topi
        ell(s, S, (52, 30, 118), 34, 46, 62, 16)
        ell(s, S, (92, 58, 178), 34, 44, 62, 14)
        poly(s, S, (76, 46, 164), [(44, 52), (63, 6), (68, 2), (90, 52)])
        poly(s, S, (56, 32, 124), [(66, 6), (68, 2), (90, 52), (72, 52)])
        poly(s, S, (76, 46, 164), [(68, 2), (79, 4), (75, 11), (66, 8)])  # ujung topi menekuk
        poly(s, S, (255, 205, 90), [(45, 47), (89, 47), (90, 52), (44, 52)])
        # bintang di topi
        poly(s, S, (255, 232, 140), [(66, 22), (68, 28), (74, 30), (68, 32), (66, 38),
                                     (64, 32), (58, 30), (64, 28)])
    return sprite(130, 170, d)


def ghost_frame(f):
    def d(s, S):
        o = 2 if f else -2
        body = (214, 232, 255)
        circ(s, S, (170, 195, 240), (42, 40), 28)       
        poly(s, S, (170, 195, 240), [(13, 40), (71, 40), (71, 80), (13, 80)])
        circ(s, S, body, (42, 40), 26)
        poly(s, S, body, [(16, 40), (68, 40), (68, 80), (16, 80)])
        for i, cx in enumerate((22, 36, 50, 64)):        
            cy = 80 + (o if i % 2 else -o)
            circ(s, S, body, (cx, cy), 7.5)
        ell(s, S, (234, 244, 255), 28, 28, 26, 38)       
        # lengan
        circ(s, S, body, (13, 56 + o), 6)
        circ(s, S, body, (71, 56 - o), 6)
        # wajah
        ell(s, S, (45, 32, 90), 27, 30, 10, 16)
        ell(s, S, (45, 32, 90), 47, 30, 10, 16)
        circ(s, S, WHITE, (31, 34), 2.4)
        circ(s, S, WHITE, (51, 34), 2.4)
        ell(s, S, (45, 32, 90), 36, 52, 12, 14)
        circ(s, S, (255, 170, 205), (24, 50), 4)
        circ(s, S, (255, 170, 205), (60, 50), 4)
        line(s, S, (45, 32, 90), (24, 25), (35, 29), 2.4)
        line(s, S, (45, 32, 90), (60, 25), (49, 29), 2.4)
    return sprite(84, 96, d)


def bat_frame(f):
    def d(s, S):
        wing, wing_in = (66, 30, 108), (110, 56, 160)
        if f == 0:
            lw = [(42, 38), (6, 6), (14, 28), (6, 42), (22, 40), (20, 56), (38, 50)]
            li = [(40, 38), (14, 14), (20, 32), (14, 42), (26, 42), (30, 48)]
        else:
            lw = [(42, 40), (4, 50), (16, 54), (10, 66), (26, 60), (28, 70), (40, 52)]
            li = [(40, 42), (12, 52), (22, 56), (18, 62), (30, 58), (36, 52)]
        mir = lambda pts: [(100 - x, y) for x, y in pts]
        poly(s, S, wing, lw);  poly(s, S, wing, mir(lw))
        poly(s, S, wing_in, li); poly(s, S, wing_in, mir(li))
        ell(s, S, (54, 24, 90), 36, 22, 28, 36)            # badan
        poly(s, S, (54, 24, 90), [(40, 22), (41, 4), (50, 17)])  # telinga
        poly(s, S, (54, 24, 90), [(60, 22), (59, 4), (50, 17)])
        poly(s, S, (255, 150, 190), [(42, 19), (43, 9), (48, 17)])
        poly(s, S, (255, 150, 190), [(58, 19), (57, 9), (52, 17)])
        circ(s, S, (70, 34, 112), (50, 28), 13)            # kepala
        circ(s, S, (255, 70, 90), (44, 27), 3.6)           # mata merah
        circ(s, S, (255, 70, 90), (56, 27), 3.6)
        circ(s, S, WHITE, (44.8, 26.2), 1.2)
        circ(s, S, WHITE, (56.8, 26.2), 1.2)
        poly(s, S, WHITE, [(45, 35), (47.5, 42), (50, 35)])  # taring
        poly(s, S, WHITE, [(50, 35), (52.5, 42), (55, 35)])
        line(s, S, (30, 14, 50), (39, 21), (47, 24), 2)
        line(s, S, (30, 14, 50), (61, 21), (53, 24), 2)
    return sprite(100, 74, d)


def pumpkin_frame(f):
    def d(s, S):
        o = 1 if f else 0
        # batang + daun
        poly(s, S, (60, 140, 55), [(40, 20), (51, 20), (55, 6 - o), (46, 2 - o)])
        poly(s, S, (88, 175, 70), [(51, 12), (66, 8 - o), (60, 18)])
        # badan (3 lobus)
        ell(s, S, (150, 62, 14), 4, 17, 44, 62)
        ell(s, S, (150, 62, 14), 42, 17, 44, 62)
        ell(s, S, (214, 96, 24), 6, 19, 40, 58)
        ell(s, S, (214, 96, 24), 44, 19, 40, 58)
        ell(s, S, (150, 62, 14), 22, 13, 46, 70)
        ell(s, S, (244, 128, 36), 24, 15, 42, 66)
        ell(s, S, (255, 168, 80), 29, 20, 12, 22)        # highlight
        for x in (24, 45, 66):                            
            pygame.draw.arc(s, (150, 62, 14), (int((x - 12) * S), int(16 * S), int(24 * S), int(66 * S)),
                            math.pi * .55, math.pi * 1.45, int(1.5 * S))

        face = (255, 232, 100)
        poly(s, S, face, [(23, 40), (35, 40), (29, 29)])
        poly(s, S, face, [(55, 40), (67, 40), (61, 29)])
        poly(s, S, face, [(20, 52), (28, 57), (34, 50), (40, 59), (45, 51), (50, 59), (56, 50),
                          (62, 57), (70, 52), (65, 68), (25, 68)])
        poly(s, S, (255, 190, 60), [(28, 60), (34, 56), (40, 63), (36, 66), (30, 66)])
    return sprite(90, 84, d)


def bolt_sprite():
    def d(s, S):
        poly(s, S, (180, 240, 255), [(18, 0), (21, 15), (36, 18), (21, 21), (18, 36), (15, 21), (0, 18), (15, 15)])
        circ(s, S, (60, 180, 255), (18, 18), 13)
        circ(s, S, CYAN, (18, 18), 10.5)
        circ(s, S, (200, 245, 255), (18, 18), 6.5)
        circ(s, S, WHITE, (18, 18), 3.5)
    return sprite(36, 36, d)


def mega_sprite():
    def d(s, S):
        c = 50
        for i in range(8):
            a = i * math.tau / 8
            a1, a2 = a - .22, a + .22
            R = 49 if i % 2 == 0 else 38
            poly(s, S, (255, 150, 40), [(c, c), (c + math.cos(a1) * 22, c + math.sin(a1) * 22),
                                        (c + math.cos(a) * R, c + math.sin(a) * R),
                                        (c + math.cos(a2) * 22, c + math.sin(a2) * 22)])
        circ(s, S, (255, 120, 30), (c, c), 30)
        circ(s, S, (255, 175, 55), (c, c), 24)
        circ(s, S, (255, 230, 130), (c, c), 16)
        circ(s, S, WHITE, (c, c), 8)
    return sprite(100, 100, d)


def heart_sprite(full):
    def d(s, S):
        def shape(col, g):
            circ(s, S, col, (11, 12), 9 + g)
            circ(s, S, col, (25, 12), 9 + g)
            poly(s, S, col, [(2 - g, 15), (34 + g, 15), (18, 33 + g)])
        if full:
            shape((150, 25, 60), 1.5)
            shape((255, 85, 115), 0)
            circ(s, S, (255, 160, 180), (9, 9), 3.2)
        else:
            shape((40, 40, 62), 1.5)
            shape((66, 66, 92), 0)
    return sprite(36, 36, d)


def cloud_sprite(seed):
    rnd = random.Random(seed)
    small = pygame.Surface((70, 24), pygame.SRCALPHA)
    for _ in range(7):
        pygame.draw.circle(small, (150, 110, 220, 60), (rnd.randint(14, 56), rnd.randint(8, 16)), rnd.randint(5, 9))
    tiny = pygame.transform.smoothscale(small, (35, 12))
    return pygame.transform.smoothscale(tiny, (280, 96))


def rounded_panel(w, h, radius=16):
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(h):
        col = lerp_col((30, 22, 68), (12, 9, 34), y / h)
        pygame.draw.line(surf, col + (225,), (0, y), (w, y))
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, w, h), border_radius=radius)
    surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    pygame.draw.rect(surf, (160, 105, 245, 210), (0, 0, w, h), 2, border_radius=radius)
    pygame.draw.line(surf, (255, 255, 255, 40), (radius, 3), (w - radius, 3))
    return surf


@lru_cache(maxsize=8)
def rune_ring(level):
    k = .30 + level * .17
    s = pygame.Surface((300, 72))
    c1 = tuple(int(v * k) for v in (150, 95, 235))
    c2 = tuple(int(v * k) for v in (90, 220, 255))
    pygame.draw.ellipse(s, c1, (4, 4, 292, 64), 3)
    pygame.draw.ellipse(s, c2, (28, 12, 244, 48), 2)
    pygame.draw.ellipse(s, c1, (60, 20, 180, 32), 1)
    for i in range(12):
        a = i * math.tau / 12
        x1, y1 = 150 + math.cos(a) * 122, 36 + math.sin(a) * 24
        x2, y2 = 150 + math.cos(a) * 146, 36 + math.sin(a) * 31
        pygame.draw.line(s, c2, (x1, y1), (x2, y2), 2)
    return s


# background
def ridge_y(base, amp, seed, x):
    rnd = random.Random(seed)
    p = [rnd.uniform(0, 6.28) for _ in range(3)]
    return base - amp * (.5 * math.sin(x * .006 + p[0]) + .3 * math.sin(x * .015 + p[1])
                         + .2 * math.sin(x * .041 + p[2]))


def draw_ridge(bg, base, amp, seed, color):
    pts = [(0, GY)] + [(x, ridge_y(base, amp, seed, x)) for x in range(0, WIDTH + 21, 20)] + [(WIDTH, GY)]
    pygame.draw.polygon(bg, color, pts)


def draw_castle(bg, cx, base_y):
    col = (20, 12, 44)
    parts = [(cx - 44, 70, 22), (cx + 22, 70, 22), (cx - 11, 100, 22)]
    pygame.draw.rect(bg, col, (cx - 38, base_y - 48, 76, 70))
    wins = []
    for x, h, w in parts:
        pygame.draw.rect(bg, col, (x, base_y - h, w, h + 20))
        pygame.draw.polygon(bg, (30, 16, 62), [(x - 4, base_y - h), (x + w + 4, base_y - h), (x + w // 2, base_y - h - 30)])
        wins.append((x + w // 2, base_y - h + 18))
        wins.append((x + w // 2, base_y - h + 40))
    wins += [(cx - 20, base_y - 20), (cx + 20, base_y - 20), (cx, base_y - 8)]
    for wx, wy in wins:
        add_glow(bg, wx, wy, 14, (90, 60, 18))
        pygame.draw.rect(bg, (255, 208, 110), (wx - 3, wy - 5, 6, 10))


def make_background():
    bg = pygame.Surface((WIDTH, HEIGHT))
    top, bot = (4, 4, 20), (70, 30, 108)
    for y in range(GY + 1):
        pygame.draw.line(bg, lerp_col(top, bot, (y / GY) ** 1.4), (0, y), (WIDTH, y))
    # bulan
    add_glow(bg, 800, 125, 190, (46, 46, 84))
    pygame.draw.circle(bg, (246, 242, 218), (800, 125), 52)
    for cx, cy, r in [(784, 108, 11), (816, 140, 9), (800, 154, 6), (822, 106, 5), (780, 138, 5)]:
        pygame.draw.circle(bg, (222, 218, 190), (cx, cy), r)
    pygame.draw.circle(bg, (255, 252, 235), (788, 112), 6)
    # nebula
    for x, y, r, c in [(200, 190, 300, (46, 16, 86)), (600, 330, 340, (14, 38, 90)), (880, 380, 240, (70, 20, 80))]:
        add_glow(bg, x, y, r, c)
    # gunung 
    draw_ridge(bg, GY - 205, 95, 11, (44, 26, 86))
    cxc = 170
    draw_castle(bg, cxc, int(ridge_y(GY - 205, 95, 11, cxc)) + 10)
    add_glow(bg, WIDTH // 2, GY - 40, 520, (34, 18, 70))
    draw_ridge(bg, GY - 115, 64, 23, (30, 17, 62))
    draw_ridge(bg, GY - 52, 34, 37, (18, 11, 40))
    # tanah batu
    for y in range(GY, HEIGHT):
        pygame.draw.line(bg, lerp_col((44, 30, 84), (10, 6, 26), (y - GY) / (HEIGHT - GY)), (0, y), (WIDTH, y))
    row = 0
    for y in range(GY + 16, HEIGHT, 18):
        pygame.draw.line(bg, (22, 14, 48), (0, y), (WIDTH, y))
        for x in range(-30 + (row % 2) * 28, WIDTH, 56):
            pygame.draw.line(bg, (22, 14, 48), (x, y), (x, y + 18))
        row += 1
    pygame.draw.line(bg, (170, 118, 255), (0, GY), (WIDTH, GY), 3)
    pygame.draw.line(bg, (90, 60, 170), (0, GY + 3), (WIDTH, GY + 3), 2)
    return bg


def build_assets():
    A = SimpleNamespace()
    A.bg = make_background()
    A.wizard = [wizard_frame(sw) for sw in (-3, 0, 3, 0)]
    A.enemy = {}
    for kind, fn, glow_col in (("ghost", ghost_frame, (60, 80, 140)),
                               ("bat", bat_frame, (110, 30, 70)),
                               ("pumpkin", pumpkin_frame, (130, 60, 10))):
        frames = [fn(0), fn(1)]
        A.enemy[kind] = dict(frames=frames, flash=[flashed(f) for f in frames], glow=glow_col)
    A.bolt, A.mega = bolt_sprite(), mega_sprite()
    A.heart_full, A.heart_empty = heart_sprite(True), heart_sprite(False)
    A.panel = rounded_panel(WIDTH - 36, 62)
    A.clouds = [[cloud_sprite(s), random.uniform(0, WIDTH), random.randint(110, 330), random.uniform(6, 16)]
                for s in (1, 2, 3, 4)]
    A.stars = [[random.randrange(WIDTH), random.randrange(GY - 250), random.choice((1, 1, 2, 2, 3)),
                random.random() * 6] for _ in range(120)]
    A.flies = [[random.uniform(0, WIDTH), random.uniform(GY - 300, GY + 30), random.uniform(-12, 12),
                random.uniform(-10, 4), random.random() * 6, random.choice([CYAN, GOLD, (200, 140, 255)])]
               for _ in range(26)]
    return A

class Gesture:
    """Deteksi ngepal vs buka dari bentuk kontur (solidity + luas)."""
    def __init__(self):
        self.sol = None
        self.area = None
        self.openness = 1.0
        self.fist = False
        self.fist_sol, self.open_sol = FIST_SOL, OPEN_SOL
        self.fist_area = self.open_area = None

    def reset(self):
        self.sol = self.area = None
        self.fist = False
        self.openness = 1.0

    def update(self, contour):
        area = cv2.contourArea(contour)
        hull_area = cv2.contourArea(cv2.convexHull(contour)) or 1
        sol = area / hull_area
        self.sol = sol if self.sol is None else .7 * sol + .3 * self.sol
        self.area = area if self.area is None else .7 * area + .3 * self.area

        o_sol = clamp01((self.fist_sol - self.sol) / max(.02, self.fist_sol - self.open_sol))
        if self.fist_area and self.open_area and self.open_area > self.fist_area * 1.1:
            o_area = clamp01((self.area - self.fist_area) / (self.open_area - self.fist_area))
            self.openness = .65 * o_sol + .35 * o_area
        else:
            self.openness = o_sol

        event = None
        if not self.fist and self.openness < .42:
            self.fist, event = True, "close"
        elif self.fist and self.openness > .58:
            self.fist, event = False, "open"
        return event

    def calibrate(self, which):
        if self.sol is None:
            return
        if which == "open":
            self.open_sol, self.open_area = self.sol, self.area
        else:
            self.fist_sol, self.fist_area = self.sol, self.area


ENEMY_SPEC = {"ghost": dict(r=28, hp=1, score=1), "bat": dict(r=26, hp=1, score=1),
              "pumpkin": dict(r=32, hp=2, score=2)}
ENEMY_COLORS = {"ghost": (150, 190, 255), "bat": (255, 80, 130), "pumpkin": (255, 150, 40)}


def new_game():
    return dict(x=WIDTH // 2, bolts=[], enemies=[], particles=[], score=0,
                lives=START_LIVES, spawn=0, charge=None, src=None,
                cooldown=0, shake=0, game_over=False, flash=0)


def burst(particles, x, y, color, n=14, speed=(60, 220)):
    for _ in range(n):
        a = random.random() * math.tau
        s = random.uniform(*speed)
        particles.append([x, y, math.cos(a) * s, math.sin(a) * s,
                          random.uniform(.25, .65), color, random.randint(2, 5)])


ORB_DX, ORB_DY = 35, -72   


def start_charge(g, src):
    if g["game_over"] or g["charge"] is not None:
        return
    g["charge"], g["src"] = 0.0, src


def release_charge(g):
    c = g["charge"]
    g["charge"], g["src"] = None, None
    if c is None or g["game_over"] or g["cooldown"] > 0:
        return
    ox, oy = g["x"] + ORB_DX, PLAYER_Y + ORB_DY
    g["cooldown"] = .1
    if c >= MEGA_TIME:
        g["bolts"].append(dict(x=ox, y=oy, vy=-760, r=34, pierce=True, ang=0))
        g["shake"] = .25
        burst(g["particles"], ox, oy, GOLD, 30, (80, 320))
    else:
        g["bolts"].append(dict(x=ox, y=oy, vy=-640, r=14, pierce=False, ang=0))
        burst(g["particles"], ox, oy, CYAN, 8)


def spawn_enemy(g):
    kind = random.choices(["ghost", "bat", "pumpkin"], [5, 3, 3])[0]
    spec = ENEMY_SPEC[kind]
    base = random.randint(32, 52) + min(g["score"] * .8, 40)
    vy = base * {"ghost": 1.0, "bat": 1.3, "pumpkin": .8}[kind]
    r = spec["r"]
    g["enemies"].append(dict(kind=kind, x=random.randint(r, WIDTH - r), y=-r, r=r, vy=vy,
                             ph=random.random() * math.tau, hp=spec["hp"], flash=0))


#  drawing
def draw_scene(world, A, g, t, dt):
    world.blit(A.bg, (0, 0))

    # bintang berkedip 
    for sx, sy, sz, ph in A.stars:
        br = int(90 + 150 * (.5 + .5 * math.sin(t * 2 + ph)))
        pygame.draw.circle(world, (br, br, min(255, br + 30)), (sx, sy), sz)

    
    for c in A.clouds:
        c[1] += c[3] * dt
        if c[1] > WIDTH + 20:
            c[1] = -300
        world.blit(c[0], (int(c[1]), c[2]))

    # kunang-kunang
    for f in A.flies:
        f[0] += (f[2] + math.sin(t + f[4]) * 14) * dt
        f[1] += (f[3] + math.cos(t * .8 + f[4]) * 10) * dt
        if f[0] < -10: f[0] = WIDTH + 10
        if f[0] > WIDTH + 10: f[0] = -10
        if f[1] < GY - 320: f[1] = GY + 20
        if f[1] > GY + 40: f[1] = GY - 300
        k = .35 + .65 * (.5 + .5 * math.sin(t * 3 + f[4]))
        add_glow(world, f[0], f[1], 11, tuple(int(c * k * .8) for c in f[5]))
        pygame.draw.circle(world, tuple(int(c * k) for c in f[5]), (int(f[0]), int(f[1])), 2)

    charge = g["charge"]
    cval = 0 if charge is None else min(1.0, charge / MAX_CHARGE)
    lvl = int(round(cval * 4)) if charge is not None else 1
    world.blit(rune_ring(lvl), (int(g["x"]) - 150, GY - 4), special_flags=pygame.BLEND_RGB_ADD)
    for i in range(3):
        a = t * (2.2 + cval * 4) + i * math.tau / 3
        rx, ry = g["x"] + math.cos(a) * 140, GY + 32 + math.sin(a) * 28
        add_glow(world, rx, ry, 12, (GOLD if cval >= 1 * MEGA_TIME / MAX_CHARGE else CYAN))

    # peluru
    for b in g["bolts"]:
        x, y = b["x"], b["y"]
        mega = b["pierce"]
        col = (255, 170, 50) if mega else CYAN
        for i in range(1, 6):
            add_glow(world, x, y + i * b["r"] * .9, b["r"] * (2.4 - i * .3),
                     tuple(int(c * (1 - i * .15)) for c in col))
        add_glow(world, x, y, b["r"] * 3.4, col)
        if mega:
            b["ang"] += 240 * dt
            spr = pygame.transform.rotozoom(A.mega, b["ang"], 1)
        else:
            b["ang"] += 120 * dt
            spr = pygame.transform.rotozoom(A.bolt, b["ang"], 1)
        world.blit(spr, spr.get_rect(center=(int(x), int(y))))

    # musuh
    for e in g["enemies"]:
        spec = A.enemy[e["kind"]]
        idx = int(t * 6 + e["ph"]) % 2
        spr = spec["flash"][idx] if e["flash"] > 0 else spec["frames"][idx]
        bob = math.sin(t * 3 + e["ph"]) * 3
        add_glow(world, e["x"], e["y"] + bob, e["r"] * 2.4, spec["glow"])
        world.blit(spr, spr.get_rect(center=(int(e["x"]), int(e["y"] + bob))))

    # wizard
    x = int(g["x"])
    bob = math.sin(t * 3) * 3
    pygame.draw.ellipse(world, (6, 3, 16), (x - 36, GY - 6, 72, 14))
    frame = A.wizard[int(t * 6) % 4]
    top = PLAYER_Y + 42 - 150 + bob
    world.blit(frame, (x - 65, top))
    ox, oy = x + ORB_DX, top + 36
    c = 0 if charge is None else min(charge, MAX_CHARGE)
    mega_ready = charge is not None and charge >= MEGA_TIME
    col = GOLD if mega_ready else CYAN
    orb_r = 6 + c * 10
    add_glow(world, ox, oy, 28 + c * 50, tuple(int(v * (.45 if charge is None else .85)) for v in col))
    pygame.draw.circle(world, col, (int(ox), int(oy)), int(orb_r))
    pygame.draw.circle(world, WHITE, (int(ox), int(oy)), max(2, int(orb_r * .45)))
    if charge is not None:
        for i in range(3):
            a = t * 7 + i * math.tau / 3
            pygame.draw.circle(world, col, (int(ox + math.cos(a) * (orb_r + 13)),
                                            int(oy + math.sin(a) * (orb_r + 13))), 3)

  
    for p in g["particles"]:
        radius = max(1, int(p[6] * min(1, p[4] / .5)))
        add_glow(world, p[0], p[1], radius * 3, tuple(int(v * .5) for v in p[5]))
        pygame.draw.circle(world, p[5], (int(p[0]), int(p[1])), radius)


def draw_hud(screen, A, g, gesture, glove_found, cam_surf, paused=False):
    screen.blit(A.panel, (18, 16))
    text(screen, "WIZBANG", 26, LAVENDER, 150, 47)
    text(screen, f"SCORE  {g['score']}", 24, GOLD, WIDTH // 2, 47)
    text(screen, f"WAVE {1 + g['score'] // 8}", 18, CYAN, WIDTH - 290, 47)
    for i in range(START_LIVES):
        spr = A.heart_full if i < g["lives"] else A.heart_empty
        screen.blit(spr, (WIDTH - 148 + i * 40, 30))

    # bar power
    bw, bx, by = 300, WIDTH // 2 - 150, HEIGHT - 50
    pygame.draw.rect(screen, (16, 12, 40), (bx - 3, by - 3, bw + 6, 22), border_radius=10)
    charge = g["charge"]
    if charge:
        frac = min(1, charge / MAX_CHARGE)
        c1, c2 = ((255, 150, 40), (255, 235, 130)) if charge >= MEGA_TIME else ((50, 140, 255), CYAN)
        n = int(bw * frac)
        for i in range(n):
            pygame.draw.line(screen, lerp_col(c1, c2, i / bw), (bx + i, by), (bx + i, by + 15))
        pygame.draw.line(screen, (255, 255, 255), (bx + 4, by + 3), (bx + max(4, n - 4), by + 3))
    mx = bx + int(bw * MEGA_TIME / MAX_CHARGE)
    pygame.draw.line(screen, WHITE, (mx, by - 5), (mx, by + 20), 2)
    pygame.draw.rect(screen, (160, 105, 245), (bx - 3, by - 3, bw + 6, 22), 2, border_radius=10)
    ready = bool(charge and charge >= MEGA_TIME)
    text(screen, "MEGA BLAST!" if ready else "POWER", 14, GOLD if ready else MUTED, WIDTH // 2, by - 16)

    status = ("GLOVE: FIST (charging)" if gesture.fist else "GLOVE: OPEN") if glove_found \
        else "SHOW YOUR PURPLE GLOVE TO CAMERA"
    text(screen, status, 15, GREEN if glove_found else MUTED, WIDTH // 2, HEIGHT - 16)
    text(screen, "Ngepal = charge | Buka = tembak | Jangan biarkan musuh mendarat!", 13, MUTED, 195, HEIGHT - 16)

    if paused:
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((6, 4, 20, 180))
        screen.blit(shade, (0, 0))
        pulse = .5 + .5 * math.sin(pygame.time.get_ticks() / 300)
        text(screen, "PAUSED", 58, GOLD, WIDTH // 2, HEIGHT // 2 - 55)
        text(screen, "Sarung tangan tidak terdeteksi", 26, WHITE, WIDTH // 2, HEIGHT // 2 + 5)
        text(screen, "Tunjukkan sarung tangan ungu ke kamera, game akan lanjut secara otomatis",
             18, lerp_col(MUTED, CYAN, pulse), WIDTH // 2, HEIGHT // 2 + 48)

    if cam_surf:
        px, py = WIDTH - 202, HEIGHT - 168
        screen.blit(cam_surf, (px, py))
        pygame.draw.rect(screen, (160, 105, 245), (px - 1, py - 1, 182, 137), 2, border_radius=4)

    if g["flash"] > 0:
        fl = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        fl.fill((255, 40, 70, int(110 * g["flash"] / .25)))
        screen.blit(fl, (0, 0))

    if g["game_over"]:
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((4, 5, 15, 210))
        screen.blit(shade, (0, 0))
        text(screen, "GAME OVER", 58, RED, WIDTH // 2, HEIGHT // 2 - 60)
        text(screen, f"Final score: {g['score']}", 30, WHITE, WIDTH // 2, HEIGHT // 2)
        text(screen, "Press R to restart | Q to quit", 21, LAVENDER, WIDTH // 2, HEIGHT // 2 + 48)


# main
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Wizbang")
    clock = pygame.time.Clock()
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        pygame.quit()
        raise SystemExit("Webcam tidak bisa dibuka. Tutup aplikasi lain yang memakai kamera atau coba CAMERA_INDEX = 1.")

    A = build_assets()
    world = pygame.Surface((WIDTH, HEIGHT))

    g = new_game()
    gesture = Gesture()
    smooth_x = None
    lost_timer = 0.0
    cam_surf = None
    glove_ever = False
    paused = False
    t = 0.0
    running = True

    try:
        while running:
            dt = min(clock.tick(FPS) / 1000, .04)
            g["cooldown"] = max(0, g["cooldown"] - dt)
            g["shake"] = max(0, g["shake"] - dt)
            g["flash"] = max(0, g["flash"] - dt)

            # ---------- webcam + HSV
            glove_found = False
            ret, frame = cap.read()
            if ret:
                frame = cv2.flip(frame, 1)
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                mask = cv2.inRange(hsv, LOWER_PURPLE, UPPER_PURPLE)
                kernel = np.ones((5, 5), np.uint8)
                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                contours = [c for c in contours if cv2.contourArea(c) >= MIN_AREA]
                if contours:
                    glove_found = True
                    lost_timer = 0.0
                    c = max(contours, key=cv2.contourArea)
                    m = cv2.moments(c)
                    if m["m00"]:
                        cx, cy = int(m["m10"] / m["m00"]), int(m["m01"] / m["m00"])
                        event = gesture.update(c)
                        smooth_x = cx if smooth_x is None else .4 * cx + .6 * smooth_x
                        g["x"] = max(35, min(WIDTH - 35, int(smooth_x / frame.shape[1] * WIDTH)))
                        if event == "close":
                            start_charge(g, "glove")
                        elif event == "open" and g["src"] == "glove":
                            release_charge(g)
                        hull = cv2.convexHull(c)
                        cv2.drawContours(frame, [hull], -1, (255, 200, 0), 2)
                        cv2.drawContours(frame, [c], -1, (0, 255, 0), 2)
                        cv2.circle(frame, (cx, cy), 7, (0, 255, 255), -1)
                        label = "FIST" if gesture.fist else "OPEN"
                        cv2.putText(frame, f"{label} open={gesture.openness:.2f} sol={gesture.sol:.2f}",
                                    (10, 28), cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 255, 0), 2)
                else:
                    lost_timer += dt
                    cv2.putText(frame, "Show purple glove to camera", (10, 28),
                                cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 0, 255), 2)
                    if lost_timer > .4:
                        gesture.reset()
                        smooth_x = None
                        if g["src"] == "glove":
                            g["charge"], g["src"] = None, None
                cv2.imshow("HSV Mask", mask)
                cv2.waitKey(1)
                small = cv2.resize(frame, (180, 135))
                rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
                cam_surf = pygame.image.frombuffer(rgb.tobytes(), (180, 135), "RGB")
                cam_surf.set_alpha(225)

           
            if glove_found:
                glove_ever = True
            paused = (AUTO_PAUSE and glove_ever and not glove_found
                      and lost_timer > PAUSE_DELAY and not g["game_over"])
            if paused:
                dt = 0.0
            t += dt

            
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False
                elif ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_q, pygame.K_ESCAPE):
                        running = False
                    elif ev.key == pygame.K_SPACE and not paused:
                        start_charge(g, "key")
                    elif ev.key == pygame.K_o:
                        gesture.calibrate("open")
                    elif ev.key == pygame.K_f:
                        gesture.calibrate("fist")
                    elif ev.key == pygame.K_r and g["game_over"]:
                        g = new_game()
                elif ev.type == pygame.KEYUP and ev.key == pygame.K_SPACE and g["src"] == "key":
                    release_charge(g)

            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT]:
                g["x"] -= int(420 * dt)
            if keys[pygame.K_RIGHT]:
                g["x"] += int(420 * dt)
            g["x"] = max(35, min(WIDTH - 35, g["x"]))

            #  update
            if g["charge"] is not None:
                g["charge"] = min(MAX_CHARGE, g["charge"] + dt)
                if random.random() < .6:
                    a = random.random() * math.tau
                    px, py = g["x"] + ORB_DX, PLAYER_Y + ORB_DY
                    g["particles"].append([px + math.cos(a) * 46, py + math.sin(a) * 46,
                                           -math.cos(a) * 100, -math.sin(a) * 100, .4,
                                           GOLD if g["charge"] >= MEGA_TIME else CYAN, 3])

            if not g["game_over"]:
                g["spawn"] += dt
                interval = max(.9, 2.0 - g["score"] * .015)
                if g["spawn"] >= interval:
                    g["spawn"] = 0
                    spawn_enemy(g)

                player_rect = pygame.Rect(g["x"] - 26, PLAYER_Y - 60, 52, 100)
                for b in g["bolts"][:]:
                    b["y"] += b["vy"] * dt
                    if random.random() < .7:
                        col = GOLD if b["pierce"] else CYAN
                        g["particles"].append([b["x"] + random.uniform(-b["r"], b["r"]) * .6, b["y"] + b["r"],
                                               random.uniform(-20, 20), random.uniform(30, 90), .3, col, 2])
                    if b["y"] < -60:
                        g["bolts"].remove(b)

                for e in g["enemies"][:]:
                    e["flash"] = max(0, e["flash"] - dt)
                    e["y"] += e["vy"] * dt
                    sway = {"ghost": 25, "bat": 85, "pumpkin": 12}[e["kind"]]
                    freq = {"ghost": 35, "bat": 22, "pumpkin": 50}[e["kind"]]
                    e["x"] += math.sin(e["y"] / freq + e["ph"]) * sway * dt
                    e["x"] = max(e["r"], min(WIDTH - e["r"], e["x"]))

                    killed = False
                    for b in g["bolts"][:]:
                        if math.hypot(e["x"] - b["x"], e["y"] - b["y"]) < e["r"] + b["r"]:
                            if b["pierce"]:
                                e["hp"] = 0
                            else:
                                e["hp"] -= 1
                                g["bolts"].remove(b)
                            if e["hp"] <= 0:
                                g["enemies"].remove(e)
                                g["score"] += ENEMY_SPEC[e["kind"]]["score"]
                                burst(g["particles"], e["x"], e["y"],
                                      random.choice([ENEMY_COLORS[e["kind"]], CYAN, GOLD]), 20)
                                killed = True
                            else:
                                e["flash"] = .12
                                burst(g["particles"], e["x"], e["y"], WHITE, 6)
                            break
                    if killed:
                        continue
                    er = pygame.Rect(int(e["x"] - e["r"] * .8), int(e["y"] - e["r"] * .8),
                                     int(e["r"] * 1.6), int(e["r"] * 1.6))
                    if player_rect.colliderect(er):
                        g["enemies"].remove(e)
                        g["lives"] -= 1
                        g["shake"] = .3
                        g["flash"] = .25
                        burst(g["particles"], e["x"], e["y"], RED, 22)
                        if g["lives"] <= 0:
                            g["game_over"] = True
                            g["charge"], g["src"] = None, None
                    elif e["y"] + e["r"] * .8 >= GY:
                        # jika musuh mendarat di tanah maka nyawa berkurang
                        g["enemies"].remove(e)
                        g["lives"] -= 1
                        g["shake"] = .3
                        g["flash"] = .25
                        burst(g["particles"], e["x"], GY - 6, RED, 24, (80, 260))
                        burst(g["particles"], e["x"], GY - 6, ENEMY_COLORS[e["kind"]], 12)
                        if g["lives"] <= 0:
                            g["game_over"] = True
                            g["charge"], g["src"] = None, None

            for p in g["particles"][:]:
                p[0] += p[2] * dt
                p[1] += p[3] * dt
                p[4] -= dt
                if p[4] <= 0:
                    g["particles"].remove(p)

            #  draw
            draw_scene(world, A, g, t, dt)
            ox = oy = 0
            if g["shake"] > 0:
                ox, oy = random.randint(-6, 6), random.randint(-6, 6)
            screen.fill((0, 0, 0))
            screen.blit(world, (ox, oy))
            draw_hud(screen, A, g, gesture, glove_found, cam_surf, paused)
            pygame.display.flip()
    finally:
        cap.release()
        cv2.destroyAllWindows()
        pygame.quit()


if __name__ == "__main__":
    main()