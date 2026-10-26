import random, math
from functools import lru_cache
import cv2
import numpy as np
import pygame

# KONTROL
#   Geser sarung tangan   -> gerakin wizard
#   Ngepal                -> mulai ngecas spell
#   Buka tangan           -> lepas spell 
#   O = kalibrasi tangan terbuka, F = kalibrasi kepalan (tekan saat gesturenya ditahan)
#   Keyboard cadangan: panah kiri/kanan + SPACE (tahan lalu lepas)
#   R restart | Q / ESC keluar

CAMERA_INDEX = 0
LOWER_PURPLE = np.array([120, 40, 30], dtype=np.uint8)
UPPER_PURPLE = np.array([165, 255, 255], dtype=np.uint8)
MIN_AREA = 1200
WIDTH, HEIGHT = 1000, 700
FPS = 60
START_LIVES = 3
PLAYER_Y = HEIGHT - 120
MEGA_TIME = 0.6
MAX_CHARGE = 1.0


FIST_SOL, OPEN_SOL = 0.90, 0.74

WHITE = (245, 247, 255)
PURPLE = (150, 95, 235)
LAVENDER = (210, 185, 255)
CYAN = (90, 220, 255)
GOLD = (255, 205, 90)
RED = (255, 85, 105)
GREEN = (100, 235, 165)
MUTED = (150, 160, 195)
PINK = (255, 95, 170)


_fonts = {}
def text(surf, msg, size, color, x, y, center=True):
    if size not in _fonts:
        _fonts[size] = pygame.font.SysFont("arial", size, bold=True)
    img = _fonts[size].render(msg, True, color)
    rect = img.get_rect(center=(x, y)) if center else img.get_rect(topleft=(x, y))
    surf.blit(img, rect)


@lru_cache(maxsize=256)
def glow(radius, color):
    s = pygame.Surface((radius * 2, radius * 2))
    for r in range(radius, 0, -2):
        k = (1 - r / radius) ** 2
        pygame.draw.circle(s, tuple(int(c * k) for c in color), (radius, radius), r)
    return s


def add_glow(surf, x, y, radius, color):
    radius = max(4, int(radius))
    surf.blit(glow(radius, color), (int(x) - radius, int(y) - radius),
              special_flags=pygame.BLEND_RGB_ADD)


def lerp(a, b, t):
    return a + (b - a) * t


def clamp01(v):
    return max(0.0, min(1.0, v))


def make_background():
    bg = pygame.Surface((WIDTH, HEIGHT))
    top, bot = (6, 6, 24), (46, 20, 78)
    for y in range(HEIGHT):
        t = y / HEIGHT
        pygame.draw.line(bg, tuple(int(lerp(top[i], bot[i], t)) for i in range(3)), (0, y), (WIDTH, y))
    for x, y, r, c in [(220, 190, 320, (55, 20, 95)), (800, 330, 380, (15, 45, 100)),
                       (520, 560, 340, (80, 25, 90))]:
        add_glow(bg, x, y, r, c)
   
    gy = PLAYER_Y + 50
    pygame.draw.rect(bg, (14, 10, 34), (0, gy, WIDTH, HEIGHT - gy))
    pygame.draw.line(bg, (150, 95, 235), (0, gy), (WIDTH, gy), 3)
    add_glow(bg, WIDTH // 2, gy, 420, (35, 18, 70))
    return bg


class Gesture:
    """Deteksi ngepal sama buka dari bentuk kontur (solidity + luas)."""
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


# game state
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


def start_charge(g, src):
    if g["game_over"] or g["charge"] is not None:
        return
    g["charge"], g["src"] = 0.0, src


def release_charge(g):
    c = g["charge"]
    g["charge"], g["src"] = None, None
    if c is None or g["game_over"] or g["cooldown"] > 0:
        return
    mega = c >= MEGA_TIME
    g["cooldown"] = .1
    if mega:
        g["bolts"].append(dict(x=g["x"], y=PLAYER_Y - 60, vy=-760, r=30, pierce=True))
        g["shake"] = .25
        burst(g["particles"], g["x"], PLAYER_Y - 60, GOLD, 30, (80, 320))
    else:
        g["bolts"].append(dict(x=g["x"], y=PLAYER_Y - 60, vy=-620, r=11, pierce=False))
        burst(g["particles"], g["x"], PLAYER_Y - 60, CYAN, 8)


# drawing
def draw_wizard(surf, x, y, charge, t):
    bob = math.sin(t * 3) * 3
    y = int(y + bob)
    # bayangan
    pygame.draw.ellipse(surf, (8, 5, 20), (x - 34, PLAYER_Y + 40, 68, 14))
    # jubah
    pygame.draw.polygon(surf, (90, 55, 175), [(x - 30, y + 38), (x - 20, y - 10), (x + 20, y - 10), (x + 30, y + 38)])
    pygame.draw.polygon(surf, (120, 80, 215), [(x - 12, y + 38), (x - 8, y - 10), (x + 8, y - 10), (x + 12, y + 38)])
    pygame.draw.line(surf, GOLD, (x - 20, y + 4), (x + 20, y + 4), 4)
    # kepala + janggut
    pygame.draw.circle(surf, (255, 214, 178), (x, y - 20), 15)
    pygame.draw.polygon(surf, (235, 235, 250), [(x - 13, y - 14), (x + 13, y - 14), (x, y + 10)])
    pygame.draw.circle(surf, (30, 20, 50), (x - 5, y - 23), 2)
    pygame.draw.circle(surf, (30, 20, 50), (x + 5, y - 23), 2)
    # topi
    pygame.draw.polygon(surf, (70, 40, 150), [(x - 26, y - 30), (x + 4, y - 78), (x + 26, y - 30)])
    pygame.draw.ellipse(surf, (95, 60, 185), (x - 32, y - 38, 64, 14))
    pygame.draw.circle(surf, GOLD, (x + 4, y - 56), 4)
    # tongkat + orb
    pygame.draw.line(surf, (120, 80, 50), (x + 30, y + 36), (x + 36, y - 30), 5)
    c = 0 if charge is None else min(charge, MAX_CHARGE)
    mega = c >= MEGA_TIME
    col = GOLD if mega else CYAN
    orb_r = 8 + c * 8
    add_glow(surf, x + 36, y - 34, 30 + c * 45, tuple(int(v * .8) for v in col))
    pygame.draw.circle(surf, col, (x + 36, y - 34), int(orb_r))
    pygame.draw.circle(surf, WHITE, (x + 36, y - 34), int(orb_r * .45))
    if charge is not None:
        ang = t * 6
        for i in range(3):
            a = ang + i * math.tau / 3
            pygame.draw.circle(surf, col, (int(x + 36 + math.cos(a) * (orb_r + 12)),
                                           int(y - 34 + math.sin(a) * (orb_r + 12))), 3)


def draw_enemy(surf, e, t):
    x, y, r = int(e["x"]), int(e["y"]), e["r"]
    col = e["col"]
    add_glow(surf, x, y, r * 2.6, tuple(int(c * .35) for c in col))
    dark = tuple(int(c * .6) for c in col)
    wob = math.sin(t * 8 + e["ph"]) * 3
    pygame.draw.circle(surf, dark, (x, y - 2), r + 3)
    pygame.draw.circle(surf, col, (x, y - 2), r)
    # rok bergelombang
    pts = [(x - r, y - 2)]
    n = 4
    for i in range(n + 1):
        px = x - r + i * (2 * r) / n
        py = y + r * .75 + (wob if i % 2 else -wob)
        pts.append((px, py))
    pts.append((x + r, y - 2))
    pygame.draw.polygon(surf, col, pts)
    # mata
    for dx in (-r * .35, r * .35):
        pygame.draw.circle(surf, WHITE, (int(x + dx), int(y - r * .15)), max(4, r // 4))
        pygame.draw.circle(surf, (30, 10, 40), (int(x + dx), int(y - r * .1)), max(2, r // 8))
    pygame.draw.line(surf, (30, 10, 40), (x - r * .6, y - r * .55), (x - r * .15, y - r * .35), 3)
    pygame.draw.line(surf, (30, 10, 40), (x + r * .6, y - r * .55), (x + r * .15, y - r * .35), 3)


def draw_bolt(surf, b, t):
    x, y, r = int(b["x"]), int(b["y"]), b["r"]
    col = GOLD if b["pierce"] else CYAN
    add_glow(surf, x, y, r * 3.2, col)
    for i in range(1, 5):
        pygame.draw.circle(surf, tuple(int(c * (1 - i * .2)) for c in col), (x, y + i * r * .8), max(2, int(r * (1 - i * .18))))
    pygame.draw.circle(surf, col, (x, y), r)
    pygame.draw.circle(surf, WHITE, (x, y), max(3, int(r * .5)))


def panel(surf, rect, alpha=150):
    s = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
    pygame.draw.rect(s, (14, 12, 36, alpha), s.get_rect(), border_radius=14)
    pygame.draw.rect(s, (150, 95, 235, 160), s.get_rect(), 2, border_radius=14)
    surf.blit(s, (rect[0], rect[1]))


#  main
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Magic Hands: Elemental Battle")
    clock = pygame.time.Clock()
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        pygame.quit()
        raise SystemExit("Webcam tidak bisa dibuka. Tutup aplikasi lain yang memakai kamera atau coba CAMERA_INDEX = 1.")

    bg = make_background()
    world = pygame.Surface((WIDTH, HEIGHT))
    stars = [[random.randrange(WIDTH), random.randrange(PLAYER_Y + 40), random.uniform(6, 28),
              random.choice((1, 1, 2, 3)), random.random() * 6] for _ in range(110)]

    g = new_game()
    gesture = Gesture()
    smooth_x = None
    lost_timer = 0.0
    cam_surf = None
    t = 0.0
    running = True

    try:
        while running:
            dt = min(clock.tick(FPS) / 1000, .04)
            t += dt
            g["cooldown"] = max(0, g["cooldown"] - dt)
            g["shake"] = max(0, g["shake"] - dt)
            g["flash"] = max(0, g["flash"] - dt)

            # webcam + HSV
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
                        # wizard tetap bisa digeser walau lagi ngepal/ngecas
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
                small = cv2.resize(frame, (210, 158))
                rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
                cam_surf = pygame.image.frombuffer(rgb.tobytes(), (210, 158), "RGB")

            # events
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False
                elif ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_q, pygame.K_ESCAPE):
                        running = False
                    elif ev.key == pygame.K_SPACE:
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

            #update
            if g["charge"] is not None:
                g["charge"] = min(MAX_CHARGE, g["charge"] + dt)
                if random.random() < .5:
                    a = random.random() * math.tau
                    px, py = g["x"] + 36, PLAYER_Y - 34
                    g["particles"].append([px + math.cos(a) * 40, py + math.sin(a) * 40,
                                           -math.cos(a) * 90, -math.sin(a) * 90, .4,
                                           GOLD if g["charge"] >= MEGA_TIME else CYAN, 3])

            if not g["game_over"]:
                g["spawn"] += dt
                interval = max(.55, 1.5 - g["score"] * .012)
                if g["spawn"] >= interval:
                    g["spawn"] = 0
                    r = random.randint(18, 26)
                    g["enemies"].append(dict(
                        x=random.randint(r, WIDTH - r), y=-r, r=r,
                        vy=random.randint(50, 90) + min(g["score"], 60),
                        ph=random.random() * math.tau,
                        col=random.choice([(235, 80, 140), (240, 130, 70), (150, 90, 235)])))

                player_rect = pygame.Rect(g["x"] - 24, PLAYER_Y - 30, 48, 70)
                for b in g["bolts"][:]:
                    b["y"] += b["vy"] * dt
                    if random.random() < .6:
                        col = GOLD if b["pierce"] else CYAN
                        g["particles"].append([b["x"] + random.uniform(-b["r"], b["r"]) * .6, b["y"] + b["r"],
                                               random.uniform(-20, 20), random.uniform(30, 90), .3, col, 2])
                    if b["y"] < -50:
                        g["bolts"].remove(b)

                for e in g["enemies"][:]:
                    e["y"] += e["vy"] * dt
                    e["x"] += math.sin(e["y"] / 35 + e["ph"]) * 25 * dt
                    hit = False
                    for b in g["bolts"][:]:
                        if math.hypot(e["x"] - b["x"], e["y"] - b["y"]) < e["r"] + b["r"]:
                            if not b["pierce"]:
                                g["bolts"].remove(b)
                            g["enemies"].remove(e)
                            g["score"] += 1
                            burst(g["particles"], e["x"], e["y"], random.choice([PURPLE, CYAN, GOLD, e["col"]]), 18)
                            hit = True
                            break
                    if hit:
                        continue
                    er = pygame.Rect(int(e["x"] - e["r"]), int(e["y"] - e["r"]), e["r"] * 2, e["r"] * 2)
                    if player_rect.colliderect(er):
                        g["enemies"].remove(e)
                        g["lives"] -= 1
                        g["shake"] = .3
                        g["flash"] = .25
                        burst(g["particles"], e["x"], e["y"], RED, 22)
                        if g["lives"] <= 0:
                            g["game_over"] = True
                            g["charge"] = None
                    elif e["y"] - e["r"] > HEIGHT:
                        g["enemies"].remove(e)

            for p in g["particles"][:]:
                p[0] += p[2] * dt
                p[1] += p[3] * dt
                p[4] -= dt
                if p[4] <= 0:
                    g["particles"].remove(p)

            #  draw (ke surface 'world' dulu supaya bisa shake)
            world.blit(bg, (0, 0))
            for s in stars:
                s[1] += s[2] * dt
                if s[1] > PLAYER_Y + 45:
                    s[0], s[1] = random.randrange(WIDTH), -5
                br = int(70 + 90 * (.5 + .5 * math.sin(t * 2 + s[4])))
                pygame.draw.circle(world, (br, br, min(255, br + 40)), (int(s[0]), int(s[1])), s[3])

            for b in g["bolts"]:
                draw_bolt(world, b, t)
            for e in g["enemies"]:
                draw_enemy(world, e, t)
            draw_wizard(world, int(g["x"]), PLAYER_Y, g["charge"], t)
            for p in g["particles"]:
                radius = max(1, int(p[6] * min(1, p[4] / .5)))
                add_glow(world, p[0], p[1], radius * 3, tuple(int(c * .5) for c in p[5]))
                pygame.draw.circle(world, p[5], (int(p[0]), int(p[1])), radius)

            ox = oy = 0
            if g["shake"] > 0:
                ox, oy = random.randint(-6, 6), random.randint(-6, 6)
            screen.fill((0, 0, 0))
            screen.blit(world, (ox, oy))

            #  HUD (tidak ikut shake)
            panel(screen, (18, 16, WIDTH - 36, 62))
            text(screen, "MAGIC HANDS", 26, LAVENDER, 150, 47)
            text(screen, f"SCORE  {g['score']}", 24, GOLD, WIDTH // 2, 47)
            text(screen, f"WAVE {1 + g['score'] // 8}", 18, CYAN, WIDTH - 285, 47)
            for i in range(START_LIVES):
                col = RED if i < g["lives"] else (70, 74, 95)
                hx, hy = WIDTH - 125 + i * 32, 45
                pygame.draw.circle(screen, col, (hx - 5, hy - 2), 8)
                pygame.draw.circle(screen, col, (hx + 5, hy - 2), 8)
                pygame.draw.polygon(screen, col, [(hx - 13, hy), (hx + 13, hy), (hx, hy + 15)])

            # bar power
            bw, bx, by = 300, WIDTH // 2 - 150, HEIGHT - 52
            pygame.draw.rect(screen, (20, 18, 45), (bx, by, bw, 16), border_radius=8)
            ch = 0 if g["charge"] is None else g["charge"] / MAX_CHARGE
            if ch > 0:
                col = GOLD if g["charge"] >= MEGA_TIME else CYAN
                pygame.draw.rect(screen, col, (bx, by, int(bw * ch), 16), border_radius=8)
            pygame.draw.line(screen, WHITE, (bx + int(bw * MEGA_TIME / MAX_CHARGE), by - 2),
                             (bx + int(bw * MEGA_TIME / MAX_CHARGE), by + 18), 2)
            pygame.draw.rect(screen, (150, 95, 235), (bx, by, bw, 16), 2, border_radius=8)
            text(screen, "MEGA!" if (g["charge"] or 0) >= MEGA_TIME else "POWER", 14,
                 GOLD if (g["charge"] or 0) >= MEGA_TIME else MUTED, WIDTH // 2, by - 14)

            status = ("GLOVE: FIST (charging)" if gesture.fist else "GLOVE: OPEN") if glove_found \
                else "SHOW YOUR PURPLE GLOVE TO CAMERA"
            text(screen, status, 15, GREEN if glove_found else MUTED, WIDTH // 2, HEIGHT - 18)
            text(screen, "Ngepal = cas | Buka tangan = tembak | O/F = kalibrasi", 13, MUTED, 190, HEIGHT - 18)

            # preview webcam
            if cam_surf:
                px, py = WIDTH - 232, HEIGHT - 180
                screen.blit(cam_surf, (px, py))
                pygame.draw.rect(screen, (150, 95, 235), (px, py, 210, 158), 2, border_radius=4)

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

            pygame.display.flip()
    finally:
        cap.release()
        cv2.destroyAllWindows()
        pygame.quit()


if __name__ == "__main__":
    main()