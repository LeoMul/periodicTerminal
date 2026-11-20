#!/usr/bin/env python3
"""periodic - a vim-style periodic table for your terminal.

Usage:  periodic [element]        e.g.  periodic Fe   |   periodic 26   |   periodic iron
Keys:   ? for help.  Enter on an element queries NIST ASD energy levels.
        :q / :wq / ZZ quit.  The grid scales to the terminal size.
Mouse:  click selects, double-click / right-click opens levels, wheel scrolls (:set nomouse to turn off)
Env:    PERIODIC_LEVELS_DIR=dir  look there first for levels_cm_<El>+<charge>.txt files
        PERIODIC_OPACITY=10..100  cell opacity (default 70)   PERIODIC_NO_MOUSE=1
        PERIODIC_ASPECT=2.0       font height:width ratio, for square cells
        PERIODIC_SPACING=0        no gaps between cells
        PERIODIC_CACHE_MB=500     cap on ~/.cache/periodic (oldest files removed first)
        PERIODIC_LITE=1           start in lite mode (L toggles)
"""
import csv
import curses
import io
import math
import os
import re
import sys
import time

os.environ.setdefault("ESCDELAY", "25")

# symbol name mass  (integer mass = most stable isotope, shown as [mass])
RAW = """H Hydrogen 1.008
He Helium 4.0026
Li Lithium 6.94
Be Beryllium 9.0122
B Boron 10.81
C Carbon 12.011
N Nitrogen 14.007
O Oxygen 15.999
F Fluorine 18.998
Ne Neon 20.180
Na Sodium 22.990
Mg Magnesium 24.305
Al Aluminium 26.982
Si Silicon 28.085
P Phosphorus 30.974
S Sulfur 32.06
Cl Chlorine 35.45
Ar Argon 39.948
K Potassium 39.098
Ca Calcium 40.078
Sc Scandium 44.956
Ti Titanium 47.867
V Vanadium 50.942
Cr Chromium 51.996
Mn Manganese 54.938
Fe Iron 55.845
Co Cobalt 58.933
Ni Nickel 58.693
Cu Copper 63.546
Zn Zinc 65.38
Ga Gallium 69.723
Ge Germanium 72.630
As Arsenic 74.922
Se Selenium 78.971
Br Bromine 79.904
Kr Krypton 83.798
Rb Rubidium 85.468
Sr Strontium 87.62
Y Yttrium 88.906
Zr Zirconium 91.224
Nb Niobium 92.906
Mo Molybdenum 95.95
Tc Technetium 98
Ru Ruthenium 101.07
Rh Rhodium 102.91
Pd Palladium 106.42
Ag Silver 107.87
Cd Cadmium 112.41
In Indium 114.82
Sn Tin 118.71
Sb Antimony 121.76
Te Tellurium 127.60
I Iodine 126.90
Xe Xenon 131.29
Cs Caesium 132.91
Ba Barium 137.33
La Lanthanum 138.91
Ce Cerium 140.12
Pr Praseodymium 140.91
Nd Neodymium 144.24
Pm Promethium 145
Sm Samarium 150.36
Eu Europium 151.96
Gd Gadolinium 157.25
Tb Terbium 158.93
Dy Dysprosium 162.50
Ho Holmium 164.93
Er Erbium 167.26
Tm Thulium 168.93
Yb Ytterbium 173.05
Lu Lutetium 174.97
Hf Hafnium 178.49
Ta Tantalum 180.95
W Tungsten 183.84
Re Rhenium 186.21
Os Osmium 190.23
Ir Iridium 192.22
Pt Platinum 195.08
Au Gold 196.97
Hg Mercury 200.59
Tl Thallium 204.38
Pb Lead 207.2
Bi Bismuth 208.98
Po Polonium 209
At Astatine 210
Rn Radon 222
Fr Francium 223
Ra Radium 226
Ac Actinium 227
Th Thorium 232.04
Pa Protactinium 231.04
U Uranium 238.03
Np Neptunium 237
Pu Plutonium 244
Am Americium 243
Cm Curium 247
Bk Berkelium 247
Cf Californium 251
Es Einsteinium 252
Fm Fermium 257
Md Mendelevium 258
No Nobelium 259
Lr Lawrencium 266
Rf Rutherfordium 267
Db Dubnium 268
Sg Seaborgium 269
Bh Bohrium 270
Hs Hassium 277
Mt Meitnerium 278
Ds Darmstadtium 281
Rg Roentgenium 282
Cn Copernicium 285
Nh Nihonium 286
Fl Flerovium 289
Mc Moscovium 290
Lv Livermorium 293
Ts Tennessine 294
Og Oganesson 294"""

ELEMS = {}  # Z -> (symbol, name, mass)
for i, line in enumerate(RAW.splitlines(), start=1):
    s, n, m = line.split()
    ELEMS[i] = (s, n, m)
NZ = len(ELEMS)

# ---------------------------------------------------------------- layout
POS = {}  # Z -> (row, col)


def _build():
    def put(z, r, c):
        POS[z] = (r, c)
    put(1, 1, 1); put(2, 1, 18)
    for z in (3, 4): put(z, 2, z - 2)
    for z in range(5, 11): put(z, 2, z + 8)
    for z in (11, 12): put(z, 3, z - 10)
    for z in range(13, 19): put(z, 3, z)
    for z in range(19, 37): put(z, 4, z - 18)
    for z in range(37, 55): put(z, 5, z - 36)
    for z in (55, 56): put(z, 6, z - 54)
    for z in range(72, 87): put(z, 6, z - 68)
    for z in (87, 88): put(z, 7, z - 86)
    for z in range(104, 119): put(z, 7, z - 100)
    for z in range(57, 72): put(z, 9, z - 54)    # lanthanides
    for z in range(89, 104): put(z, 10, z - 86)  # actinides


_build()
GRID = {rc: z for z, rc in POS.items()}
assert len(POS) == NZ

# ------------------------------------------------------------- categories
CATS = ["alkali metal", "alkaline earth", "transition metal", "post-transition metal",
        "metalloid", "nonmetal", "halogen", "noble gas", "lanthanide", "actinide"]
C256 = [203, 215, 75, 145, 114, 120, 80, 177, 218, 211]
C8 = [curses.COLOR_RED, curses.COLOR_YELLOW, curses.COLOR_BLUE, curses.COLOR_WHITE,
      curses.COLOR_GREEN, curses.COLOR_GREEN, curses.COLOR_CYAN, curses.COLOR_MAGENTA,
      curses.COLOR_MAGENTA, curses.COLOR_RED]


def category(z):
    if z in (3, 11, 19, 37, 55, 87): return 0
    if z in (4, 12, 20, 38, 56, 88): return 1
    if z in (2, 10, 18, 36, 54, 86, 118): return 7
    if z in (9, 17, 35, 53, 85, 117): return 6
    if z in (5, 14, 32, 33, 51, 52): return 4
    if z in (1, 6, 7, 8, 15, 16, 34): return 5
    if 57 <= z <= 71: return 8
    if 89 <= z <= 103: return 9
    if z in (13, 31, 49, 50, 81, 82, 83, 84, 113, 114, 115, 116): return 3
    return 2


CAT_OF = {z: category(z) for z in ELEMS}

# ------------------------------------------------------ electron configuration
ORDER = ["1s", "2s", "2p", "3s", "3p", "4s", "3d", "4p", "5s", "4d", "5p",
         "6s", "4f", "5d", "6p", "7s", "5f", "6d", "7p"]
CAP = {"s": 2, "p": 6, "d": 10, "f": 14}
NOBLE = [(86, "[Rn]"), (54, "[Xe]"), (36, "[Kr]"), (18, "[Ar]"), (10, "[Ne]"), (2, "[He]")]
EXC = {
    24: "[Ar] 3d5 4s1", 29: "[Ar] 3d10 4s1",
    41: "[Kr] 4d4 5s1", 42: "[Kr] 4d5 5s1", 44: "[Kr] 4d7 5s1", 45: "[Kr] 4d8 5s1",
    46: "[Kr] 4d10", 47: "[Kr] 4d10 5s1",
    57: "[Xe] 5d1 6s2", 58: "[Xe] 4f1 5d1 6s2", 64: "[Xe] 4f7 5d1 6s2",
    78: "[Xe] 4f14 5d9 6s1", 79: "[Xe] 4f14 5d10 6s1",
    89: "[Rn] 6d1 7s2", 90: "[Rn] 6d2 7s2", 91: "[Rn] 5f2 6d1 7s2",
    92: "[Rn] 5f3 6d1 7s2", 93: "[Rn] 5f4 6d1 7s2", 96: "[Rn] 5f7 6d1 7s2",
    103: "[Rn] 5f14 7s2 7p1",
}


def _fill(z):
    occ = {}
    for sub in ORDER:
        if z <= 0:
            break
        n = min(z, CAP[sub[1]])
        occ[sub] = n
        z -= n
    return occ


def config(z):
    if z in EXC:
        return EXC[z]
    occ, core = _fill(z), ""
    for nz, sym in NOBLE:
        if nz < z:
            core = sym
            for s, n in _fill(nz).items():
                occ[s] -= n
            break
    key = lambda kv: (int(kv[0][0]), "spdf".index(kv[0][1]))
    parts = [f"{s}{n}" for s, n in sorted(occ.items(), key=key) if n > 0]
    return " ".join(([core] if core else []) + parts)


def info(z):
    r, c = POS[z]
    period = r if r <= 7 else r - 3
    if r >= 9: block, group = "f", "-"
    elif z in (1, 2) or c <= 2: block, group = "s", str(c)
    elif c >= 13: block, group = "p", str(c)
    else: block, group = "d", str(c)
    sym, name, mass = ELEMS[z]
    mass = mass if "." in mass else f"[{mass}]"
    return sym, name, mass, period, group, block


# -------------------------------------------------------------- navigation
def move_h(z, d):
    r, c = POS[z]
    cols = [cc for (rr, cc) in GRID if rr == r and (cc > c if d > 0 else cc < c)]
    if not cols:
        return z
    return GRID[(r, min(cols) if d > 0 else max(cols))]


def move_v(z, d):
    r, c = POS[z]
    rows = {rr for (rr, _) in GRID if (rr > r if d > 0 else rr < r)}
    if not rows:
        return z
    nr = min(rows) if d > 0 else max(rows)
    cols = [cc for (rr, cc) in GRID if rr == nr]
    return GRID[(nr, min(cols, key=lambda cc: (abs(cc - c), -cc)))]


def row_edge(z, last):
    r, _ = POS[z]
    cols = [cc for (rr, cc) in GRID if rr == r]
    return GRID[(r, max(cols) if last else min(cols))]


def find(q):
    q = q.strip().lower()
    if not q:
        return []
    if q.isdigit():
        return [int(q)] if 1 <= int(q) <= NZ else []
    exact = [z for z, (s, n, _) in ELEMS.items() if q in (s.lower(), n.lower())]
    if exact:
        return exact
    pre = [z for z, (_, n, _) in ELEMS.items() if n.lower().startswith(q)]
    sub = [z for z, (_, n, _) in ELEMS.items() if q in n.lower() and z not in pre]
    return sorted(pre + sub)


# ------------------------------------------------------------------ drawing
def put(win, y, x, s, attr=0):
    h, w = win.getmaxyx()
    if y < 0 or y >= h or x < 0 or x >= w - 1:
        return
    s = s[: w - x - 1]
    if not s:
        return
    try:
        win.addstr(y, x, s, attr)
    except curses.error:
        pass


def isdig(c):
    return c != "" and c in "0123456789"


MIN_H, MIN_W = 16, 56

# ---- mouse (PRESSED events only; double-click timing is done here, so it works everywhere)
_B1 = getattr(curses, "BUTTON1_PRESSED", 0)
_B3 = getattr(curses, "BUTTON3_PRESSED", 0)
_UP = getattr(curses, "BUTTON4_PRESSED", 0)
_DN = getattr(curses, "BUTTON5_PRESSED", 0)
MOUSE_MASK = _B1 | _B3 | _UP | _DN


def read_mouse():
    """Consume one pending mouse event -> ('left'|'right'|'up'|'down', x, y) or None."""
    try:
        _, mx, my, _, b = curses.getmouse()
    except curses.error:
        return None
    if _UP and b & _UP: return ("up", mx, my)
    if _DN and b & _DN: return ("down", mx, my)
    if _B3 and b & _B3: return ("right", mx, my)
    if _B1 and b & _B1: return ("left", mx, my)
    return None


class Clicker:
    """Detects a second click on the same target within 0.5 s."""
    def __init__(self):
        self.t, self.key = 0.0, None

    def double(self, key):
        now = time.monotonic()
        dbl = key == self.key and now - self.t < 0.5
        self.t, self.key = now, (None if dbl else key)
        return dbl
FILL_BASE = 10  # colour pairs 11..20: white text on a solid category colour


# Base colours for the cell fills (cube-aligned so blending stays vivid, not muddy grey)
FILL_RGB = [(255, 0, 0), (255, 135, 0), (0, 135, 255), (135, 135, 175), (175, 215, 0),
            (0, 255, 0), (0, 215, 215), (135, 0, 255), (255, 0, 135), (255, 95, 95)]


def xterm_rgb(i):
    if i >= 232:
        v = 8 + 10 * (i - 232)
        return (v, v, v)
    i -= 16
    lv = (0, 95, 135, 175, 215, 255)
    return (lv[i // 36], lv[(i // 6) % 6], lv[i % 6])


def nearest_xterm(rgb):
    best, bi = None, 16
    for i in range(16, 256):
        r, g, b = xterm_rgb(i)
        d = (r - rgb[0]) ** 2 + (g - rgb[1]) ** 2 + (b - rgb[2]) ** 2
        if best is None or d < best:
            best, bi = d, i
    return bi


def _env_int(name, default):
    try:
        return max(10, min(100, int(os.environ.get(name, default))))
    except ValueError:
        return default


def detect_light():
    v = os.environ.get("COLORFGBG", "")           # set by some terminals as "fg;bg"
    return v.split(";")[-1] in ("7", "15") if v else False


def _env_float(name, default, lo, hi):
    try:
        return max(lo, min(hi, float(os.environ.get(name, default))))
    except ValueError:
        return default


OPT = {"opacity": _env_int("PERIODIC_OPACITY", 70), "light": detect_light(),
       "aspect": _env_float("PERIODIC_ASPECT", 2.0, 1.0, 3.0),
       "space": os.environ.get("PERIODIC_SPACING", "1") not in ("0", "off", "no"),
       "lite": os.environ.get("PERIODIC_LITE", "0") not in ("0", "", "off", "no"),
       "cut": {"M1": 0, "E1": 3}, "m1air": False}


def input_pending(win):
    """True if another key/mouse event is already queued (held key, wheel flood)."""
    win.nodelay(True)
    try:
        c = win.getch()
    finally:
        win.nodelay(False)
    if c == -1:
        return False
    curses.ungetch(c)
    return True


class Throttle:
    """Skip redraws while input is queued, but never for longer than max_wait seconds."""
    def __init__(self, max_wait=0.06):
        self.max_wait, self.last = max_wait, 0.0

    def should_draw(self, win):
        now = time.monotonic()
        if now - self.last >= self.max_wait or not input_pending(win):
            self.last = now
            return True
        return False


def init_fills():
    """Cells are drawn as the category colour blended over the terminal background.
    A terminal cell can't be truly transparent, so opacity is emulated by blending."""
    a = OPT["opacity"] / 100.0
    bgc = 255.0 if OPT["light"] else 0.0
    for i, rgb in enumerate(FILL_RGB):
        mix = tuple(c * a + bgc * (1 - a) for c in rgb)
        lum = 0.2126 * mix[0] + 0.7152 * mix[1] + 0.0722 * mix[2]
        curses.init_pair(FILL_BASE + i + 1, 231 if lum < 150 else 16, nearest_xterm(mix))


def layout(h, w):
    """Square cells: a terminal character is ~OPT['aspect'] times taller than wide, so a cell
    rh lines tall is drawn fw = rh * aspect columns wide. Gaps follow the same rule: one blank
    line between periods = aspect blank columns between groups.
    -> dict(fw, rh, gh, gv, cw, x0, T) or None if the terminal is too small."""
    a = OPT["aspect"]
    for gv in ((1, 0) if OPT["space"] else (0,)):        # keep the gaps if at all possible
        gh = max(1, int(round(gv * a))) if gv else 1
        for rh in (5, 4, 3, 2, 1):
            fw = max(2, int(round(rh * a)))
            cw = fw + gh
            gw = 18 * cw - gh                             # grid width
            T = 9 * rh + 8 * gv + 1                       # grid height (7 periods + f-block + spacer)
            if gw <= w - 2 and 1 + T + 1 + 2 + 1 <= h:    # header, grid, divider, 2-line info, status
                return {"fw": fw, "rh": rh, "gh": gh, "gv": gv, "cw": cw, "T": T,
                        "x0": max(1, (w - gw) // 2)}
    return None


def cell_y(r, top, L):
    rh, gv = L["rh"], L["gv"]
    if r <= 7:
        return top + (r - 1) * (rh + gv)
    return top + 7 * (rh + gv) + 1 + (r - 9) * (rh + gv)  # extra spacer line above the f-block


def hit_cell(win, mx, my):
    h, w = win.getmaxyx()
    L = layout(h, w) if h >= MIN_H and w >= MIN_W else None
    if not L:
        return None
    for z, (r, c) in POS.items():
        y, x = cell_y(r, 1, L), L["x0"] + (c - 1) * L["cw"]
        if y <= my < y + L["rh"] + L["gv"] and x <= mx < x + L["cw"]:   # gaps count too
            return z
    return None


def cell_lines(z, fw, rh):
    """Text lines for one cell, vertically centred in rh lines -> [(text, kind)]."""
    sym, name, mass = ELEMS[z]
    if "." in mass:
        ms = mass if len(mass) <= fw else ("%.1f" % float(mass))
    else:
        ms = "[" + mass + "]"
    nm = name if len(name) <= fw else name[: fw - 1] + "."
    if rh == 1:
        body = [(sym, "sym")]
    elif rh == 2:
        body = [(str(z), "q"), (sym, "sym")]
    elif rh == 3:
        body = [(str(z), "q"), (sym, "sym"), (ms[:fw], "q")]
    else:
        body = [(str(z), "q"), (sym, "sym"), (nm, "q"), (ms[:fw], "q")]
    pad = (rh - len(body) + 1) // 2
    out = [("", "q")] * pad + body
    return out + [("", "q")] * (rh - len(out))


def draw(win, st):
    h, w = win.getmaxyx()
    win.erase()
    L = layout(h, w) if h >= MIN_H and w >= MIN_W else None
    if not L:
        put(win, 0, 0, "terminal too small (need %dx%d)" % (MIN_W, MIN_H))
        win.refresh()
        return
    fw, rh, cw, x0, T = L["fw"], L["rh"], L["cw"], L["x0"], L["T"]
    top = 1
    title = "PERIODIC" + (" [lite]" if OPT["lite"] else "")
    put(win, 0, x0, title, curses.A_BOLD)
    put(win, 0, x0 + len(title) + 2, "? help  :q quit  hjkl w/b  / search  Enter levels  c colour  L lite",
        curses.A_DIM)

    for z, (r, c) in POS.items():
        cat = CAT_OF[z]
        base = curses.color_pair(cat + 1)
        sel = z == st["cur"]
        if sel:
            attr = base | curses.A_REVERSE | curses.A_BOLD
        elif st["hl"] is not None and cat != st["hl"]:
            attr = base | curses.A_DIM                      # receded: colour text only
        elif OPT["lite"]:
            attr = base | curses.A_BOLD                     # lite: coloured text, no fill
        else:
            attr = curses.color_pair(FILL_BASE + cat + 1) | curses.A_BOLD   # solid block
        if z in st["matches"] and not sel:
            attr = (attr & ~curses.A_DIM) | curses.A_UNDERLINE | curses.A_BOLD
        quiet = attr if sel else (attr & ~curses.A_BOLD) | curses.A_DIM
        y, x = cell_y(r, top, L), x0 + (c - 1) * cw
        for i, (t, kind) in enumerate(cell_lines(z, fw, rh)):   # paint every line: full block
            if t or sel or not OPT["lite"]:
                put(win, y + i, x, t.center(fw), (attr | curses.A_BOLD) if kind == "sym" else quiet)

    for (r, c, s_) in ((6, 3, "*"), (7, 3, "**"), (9, 2, "*"), (10, 2, "**")):
        put(win, cell_y(r, top, L) + rh // 2, x0 + (c - 1) * cw, s_.center(fw), curses.A_DIM)

    sy = top + T
    put(win, sy, x0, "-" * min(w - 2 - x0, 18 * cw - L["gh"]), curses.A_DIM)
    z = st["cur"]
    sym, name, mass, period, group, block = info(z)
    col = curses.color_pair(CAT_OF[z] + 1)
    extra = []
    if st["hl"] is not None:
        extra.append("highlighting: %s (c/C, Esc)" % CATS[st["hl"]])
    if st["matches"]:
        extra.append("%d match(es) n/N Esc" % len(st["matches"]))
    if h >= sy + 6 + len(extra):                            # roomy: four-line panel
        put(win, sy + 1, x0, "%s (%s)" % (name, sym), col | curses.A_BOLD)
        put(win, sy + 2, x0, "Z = %d   mass = %s   period %s   group %s   %s-block" % (z, mass, period, group, block))
        put(win, sy + 3, x0, "category: ")
        put(win, sy + 3, x0 + 10, CATS[CAT_OF[z]], col)
        put(win, sy + 4, x0, "config:   " + config(z))
        for i, e in enumerate(extra):
            put(win, sy + 5 + i, x0, e, curses.A_DIM)
    else:                                                   # short terminal: two-line panel
        head = "%s (%s)" % (name, sym)
        put(win, sy + 1, x0, head, col | curses.A_BOLD)
        put(win, sy + 1, x0 + len(head) + 2,
            "Z=%d  mass %s  period %s  group %s  %s-block" % (z, mass, period, group, block))
        cat = CATS[CAT_OF[z]]
        put(win, sy + 2, x0, cat, col)
        put(win, sy + 2, x0 + len(cat) + 2, "config: " + config(z))
        if extra and sy + 3 < h - 1:
            put(win, sy + 3, x0, "   ".join(extra), curses.A_DIM)

    put(win, h - 1, 1, st["msg"][: w - 14])
    put(win, h - 1, w - 10, st["count"] + st["pend"], curses.A_BOLD)
    win.refresh()


def prompt(win, label):
    h, w = win.getmaxyx()
    buf = ""
    try:
        curses.curs_set(1)
    except curses.error:
        pass
    while True:
        win.move(h - 1, 0)
        win.clrtoeol()
        put(win, h - 1, 0, (label + buf)[: w - 2])
        win.refresh()
        ch = win.getch()
        if ch == curses.KEY_MOUSE:
            read_mouse()
            continue
        if ch in (10, 13, curses.KEY_ENTER):
            break
        if ch == 27:
            buf = None
            break
        if ch in (curses.KEY_BACKSPACE, 127, 8):
            if buf:
                buf = buf[:-1]
            else:
                buf = None
                break
        elif 32 <= ch < 127:
            buf += chr(ch)
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    return buf


# --------------------------------------------------------------------- help
HELP = [
    "h j k l / arrows   move (accepts a count: 5l)",
    "w / b              next / previous element by atomic number",
    "0 / $   gg / G     row start / end, hydrogen / oganesson (26G -> Z=26)",
    "Enter              pick an ionization stage, query energy levels",
    "/  n  N            search symbol, name or number; next / previous",
    "c / C              cycle category highlight          Esc  clear",
    "mouse              click select, double/right-click levels, wheel scroll",
    ":q :q! :wq :x :qa  quit             ZZ / ZQ   quit",
    ":26  :Fe  :iron    jump to an element",
    ":levels [stage]    e.g.  :levels II    :e Fe III",
    ":set [no]mouse     mouse on / off       :set [no]spacing   gaps between cells",
    "L  or  :set [no]lite   lite mode: no cell fills / level colours (for slow terminals)",
    ":set aspect=2.0    font height/width ratio; raise if cells look tall, lower if wide",
    ":set opacity=70    cell opacity 10-100   :set background=light|dark",
    ":noh   :help       clear matches / this help       q  quit",
]

VHELP = [
    "j k / arrows       move (accepts a count)",
    "Ctrl-d / Ctrl-u    half page down / up",
    "Ctrl-f / Ctrl-b    page down / up",
    "gg / G             top / bottom   (12G -> row 12)",
    "/  n  N            search configuration or term, next, previous",
    "u                  cycle units: cm-1 / eV / Ry / Eh",
    "c                  colour on / off: configuration by outer subshell (s p d f),",
    "                   term by parity (even / odd*), energy red (low) -> blue (high)",
    "f                  cycle line tags: M1 (in-term dJ=1, empirical A) -> E1 allowed -> off",
    "                   E1: one-electron LS-allowed lines, hydrogenic f (dn0 / Kramers, capped)",
    "                   method tag: dn0 same-shell, kram Kramers, cap / f=1 capped, ? penetrating",
    "F                  full list for the current mode, strongest first (Enter -> upper level)",
    "t / a              cycle minimum A shown / air vs vacuum wavelengths",
    "o                  toggle energy-sorted / NIST order",
    "r                  refetch from NIST (skip the cache)",
    "click row / header (header cycles units), wheel scrolls",
    "q  Esc  :q  ZZ     back",
    ":qa                quit the program",
]


def show_lines(win, title, lines):
    win.erase()
    put(win, 1, 2, title, curses.A_BOLD)
    for i, line in enumerate(lines):
        put(win, 3 + i, 2, line)
    put(win, 4 + len(lines), 2, "press any key", curses.A_DIM)
    win.refresh()
    if win.getch() == curses.KEY_MOUSE:
        read_mouse()


QUIT_ALL = {"qa", "qa!", "qall", "qall!", "xa", "wqa", "cq", "cq!"}
CLOSE = {"q", "q!", "quit", "x", "xit", "exit", "wq", "wq!", "close", "clo"}

# ---------------------------------------------------- ionization stage helpers
_ROM = ((100, "C"), (90, "XC"), (50, "L"), (40, "XL"), (10, "X"), (9, "IX"),
        (5, "V"), (4, "IV"), (1, "I"))


def roman(n):
    out = ""
    for v, s in _ROM:
        while n >= v:
            out += s
            n -= v
    return out


def unroman(s):
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
    s = s.upper()
    if not s or any(ch not in vals for ch in s):
        return None
    tot = 0
    for i, ch in enumerate(s):
        v = vals[ch]
        tot += -v if i + 1 < len(s) and vals[s[i + 1]] > v else v
    return tot if roman(tot) == s else None


def parse_stage(s, z=None):
    """'II' or '2' -> stage 2 (Fe II = Fe+).  '2+' -> charge 2 -> stage 3."""
    s = s.strip()
    if not s:
        return None
    if s.endswith("+") and s[:-1].isdigit():
        v = int(s[:-1]) + 1
    elif s.isdigit():
        v = int(s)
    else:
        v = unroman(s)
    if v is None or v < 1 or (z is not None and v > z):
        return None
    return v


def ion_label(sym, stage):
    q = stage - 1
    return sym + ("" if q == 0 else "+" if q == 1 else "%d+" % q)


# ------------------------------------------------------- NIST energy levels
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "periodic")
try:
    CACHE_MAX = max(1, int(os.environ.get("PERIODIC_CACHE_MB", "500"))) * 1024 * 1024
except ValueError:
    CACHE_MAX = 500 * 1024 * 1024


def prune_cache(keep=None, limit=None):
    """Keep CACHE_DIR under the size cap by deleting the files with the oldest
    modification times first (reads refresh the time, so this is least-recently-used).
    Only CACHE_DIR is touched, never PERIODIC_LEVELS_DIR. -> bytes removed."""
    limit = CACHE_MAX if limit is None else limit
    try:
        files = []
        for e in os.scandir(CACHE_DIR):
            if e.is_file(follow_symlinks=False):
                stt = e.stat(follow_symlinks=False)
                files.append((stt.st_mtime, stt.st_size, e.path))
    except OSError:
        return 0
    total = sum(f[1] for f in files)
    removed = 0
    for _, size, path in sorted(files):
        if total <= limit:
            break
        if keep and os.path.abspath(path) == os.path.abspath(keep):
            continue
        try:
            os.remove(path)
        except OSError:
            continue
        total -= size
        removed += size
    return removed
LOCAL_DIR = os.environ.get("PERIODIC_LEVELS_DIR", "")
UNITS = [
    ("cm-1", 1.0),
    ("eV", 1.0 / 8065.543937),
    ("Ry", 1.0 / 109737.31568),
    ("Eh", 1.0 / 219474.6313632),
]


def levels_url(sym, stage):
    # NIST takes the ionization *charge* here: "Fe+0" = neutral = Fe I
    return ("https://physics.nist.gov/cgi-bin/ASD/energy1.pl?de=0&spectrum=%s+%d"
            "&submit=Retrieve+Data&units=0&format=3&output=0&page_size=15"
            "&multiplet_ordered=1&conf_out=on&term_out=on&level_out=on&unc_out=1"
            "&j_out=on&lande_out=on&perc_out=on&biblio=on&temp=" % (sym, stage - 1))


def _parse_levels(text):
    """Parse NIST tab-delimited level output -> [(conf, term, J, E_cm1, flag)]."""
    rows, cols = [], None
    prev_conf = prev_term = ""
    for rec in csv.reader(io.StringIO(text.lstrip("\ufeff")), delimiter="\t", quotechar='"'):
        rec = [re.sub(r"<[^>]+>", "", x).strip() for x in rec]
        if cols is None:
            low = [x.lower() for x in rec]
            if len(rec) >= 2 and any(x.startswith("level") for x in low):
                def col(p, low=low):
                    return next((i for i, x in enumerate(low) if x.startswith(p)), None)
                cols = {k: col(p) for k, p in (("conf", "configuration"), ("term", "term"),
                                              ("j", "j"), ("pre", "prefix"), ("lev", "level"))}
            continue
        if len(rec) < 2 or cols["lev"] is None:
            continue
        get = lambda k: rec[cols[k]] if cols[k] is not None and cols[k] < len(rec) else ""
        lev = get("lev")
        m = re.search(r"[0-9]+(?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)?", lev)
        if not m:
            continue
        pre = get("pre")
        flag = pre[:1] if pre[:1] in ("[", "(") else (lev[:1] if lev[:1] in ("[", "(") else "")
        conf, term = get("conf"), get("term")
        blank_conf = not conf
        if blank_conf:
            conf = prev_conf          # grouped output leaves repeats blank
            if not term:
                term = prev_term
        prev_conf, prev_term = conf, term
        rows.append((conf, term, get("j"), float(m.group()), flag))
    return rows


def _read_rows(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return _parse_levels(f.read())
    except OSError:
        return []


def _ssl_context():
    import ssl
    try:
        import certifi  # fixes CERTIFICATE_VERIFY_FAILED on some macOS pythons
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:  # noqa: BLE001
        return None


def get_levels(sym, stage, force=False):
    """-> (rows, source, error). Order: local dir, cache, NIST. Cache: ~/.cache/periodic."""
    cache = os.path.join(CACHE_DIR, "levels_%s_%d.tsv" % (sym, stage))
    if not force:
        if LOCAL_DIR:
            local = os.path.join(os.path.expanduser(LOCAL_DIR), "levels_cm_%s+%d.txt" % (sym, stage - 1))
            rows = _read_rows(local)
            if rows:
                return rows, "local file", None
        rows = _read_rows(cache)
        if rows:
            try:
                os.utime(cache)            # mark as recently used
            except OSError:
                pass
            return rows, "cache", None
    url = levels_url(sym, stage)
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (periodic-tui)"})
        with urllib.request.urlopen(req, timeout=25, context=_ssl_context()) as r:
            text = r.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001 - show any network problem to the user
        return [], "none", "network error: %s   url: %s" % (e, url)
    rows = _parse_levels(text)
    if not rows:
        dump = os.path.join(CACHE_DIR, "last_reply.txt")
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            with open(dump, "w", encoding="utf-8") as f:
                f.write(text)
            prune_cache(keep=dump)
        except OSError:
            dump = "(could not save)"
        lines = [ln for ln in text.splitlines() if ln.strip()][:4]
        snip = " // ".join(re.sub(r"<[^>]+>", " ", ln).replace("\t", " | ")[:110] for ln in lines)
        return [], "none", ("no levels parsed for %s %s (charge %d). reply starts: %s   "
                            "full reply saved to %s   url: %s" % (sym, roman(stage), stage - 1, snip, dump, url))
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(cache, "w", encoding="utf-8") as f:
            f.write(text)
        prune_cache(keep=cache)
    except OSError:
        pass
    return rows, "NIST ASD", None


# ---- colour coding for the level table
LV_BASE = 40                       # pairs 41.. : subshell l, parity, limit, energy ramp
LV_L = "spdfg"                     # outermost subshell -> pairs 41..45
LV_EVEN, LV_ODD, LV_LIMIT = 46, 47, 48
LV_RAMP = 50                       # pairs 50..59: energy, low (red) -> high (blue), like photon colour
LV256 = {"l": [203, 114, 75, 177, 215], "even": 117, "odd": 216, "limit": 226,
         "ramp": [196, 208, 214, 220, 154, 84, 49, 44, 39, 33]}


def init_level_pairs(big):
    try:
        if big:
            for i, c in enumerate(LV256["l"]):
                curses.init_pair(LV_BASE + 1 + i, c, -1)
            curses.init_pair(LV_EVEN, LV256["even"], -1)
            curses.init_pair(LV_ODD, LV256["odd"], -1)
            curses.init_pair(LV_LIMIT, LV256["limit"], -1)
            for i, c in enumerate(LV256["ramp"]):
                curses.init_pair(LV_RAMP + i, c, -1)
        else:
            C = curses
            for i, c in enumerate((C.COLOR_RED, C.COLOR_GREEN, C.COLOR_BLUE, C.COLOR_MAGENTA, C.COLOR_YELLOW)):
                curses.init_pair(LV_BASE + 1 + i, c, -1)
            curses.init_pair(LV_EVEN, C.COLOR_CYAN, -1)
            curses.init_pair(LV_ODD, C.COLOR_YELLOW, -1)
            curses.init_pair(LV_LIMIT, C.COLOR_YELLOW, -1)
            ramp = (C.COLOR_RED,) * 2 + (C.COLOR_YELLOW,) * 2 + (C.COLOR_GREEN,) * 2 + \
                   (C.COLOR_CYAN,) * 2 + (C.COLOR_BLUE,) * 2
            for i, c in enumerate(ramp):
                curses.init_pair(LV_RAMP + i, c, -1)
    except curses.error:
        pass


_SUBSHELL = re.compile(r"\d+([spdfghik])\d*")


def outer_l(conf):
    """'3d6.(5D).4s' -> 's' (the last open subshell written); '' if none."""
    m = _SUBSHELL.findall(conf)
    return m[-1] if m else ""


def is_odd(term):
    return term.rstrip().endswith(("*", "°"))


def is_limit(conf, term):
    return term.strip().lower() == "limit" or "limit" in conf.lower()


# ---- M1 fine-structure lines: empirical A-values
# A_ul = 1.3 s^-1 (lambda_ul / 4 um)^-3 f(J, L, S), for lines between levels of the same
# LS term (same configuration and term) with J_u = J_l +- 1; J below is J_u. Pure-LS estimate.
_LETTERS = "SPDFGHIKLMNOQRTUVWXYZ"
_TERM_LS = re.compile(r"(\d+)\s*([SPDFGHIKLMNOQRTUVWXYZ])\d*\s*[*°]?\s*$")


def term_LS(term):
    """'a 6D' / 'z 4F*' / '3P' -> (L, S); None for jK, jj or unparsable terms."""
    t = term.strip()
    if not t or "[" in t or "(" in t or "," in t:
        return None
    m = _TERM_LS.search(t)
    if not m:
        return None
    return float(_LETTERS.index(m.group(2))), (int(m.group(1)) - 1) / 2.0


def parse_J(j):
    j = j.strip()
    try:
        if "/" in j:
            a, b = j.split("/")
            return int(a) / int(b)
        return float(int(j))
    except ValueError:
        return None


def m1_f(Ju, Jl, L, S):
    """Algebraic factor f(J, L, S) with J = J_u; 0 if the line is not allowed."""
    J = Ju
    if abs(Ju - (Jl + 1)) < 1e-9:
        if J <= 0:
            return 0.0
        v = (J * J - (L - S) ** 2) * ((L + S + 1) ** 2 - J * J) / (12 * J * (2 * J + 1))
    elif abs(Ju - (Jl - 1)) < 1e-9:
        v = ((J + 1) ** 2 - (L - S) ** 2) * ((L + S + 1) ** 2 - (J + 1) ** 2) / (12 * (J + 1) * (2 * J + 1))
    else:
        return 0.0
    return max(0.0, v)


def m1_A(lam_A, f):
    """Empirical A (s^-1) for vacuum wavelength lam_A (angstrom)."""
    return 1.3 * (lam_A / 4.0e4) ** -3 * f


def vac_to_air(lam):
    """Vacuum -> air wavelength (angstrom), Morton (2000); unchanged below 2000 A."""
    if lam < 2000.0:
        return lam
    s2 = (1.0e4 / lam) ** 2
    n = 1 + 8.34254e-5 + 2.406147e-2 / (130 - s2) + 1.5998e-4 / (38.9 - s2)
    return lam / n


def m1_lines(rows):
    """All in-term dJ = +-1 M1 lines -> list of (A, lam_vac_A, upper, lower, Ju, Jl, f),
    strongest first."""
    groups = {}
    for r in rows:
        conf, term, j, e, flag = r
        if is_limit(conf, term):
            continue
        LS, J = term_LS(term), parse_J(j)
        if LS is None or J is None:
            continue
        groups.setdefault((conf.strip(), term.strip()), []).append((r, J, LS))
    out = []
    for members in groups.values():
        for i in range(len(members)):
            for k in range(i + 1, len(members)):
                (r1, J1, (L, S)), (r2, J2, _) = members[i], members[k]
                if abs(abs(J1 - J2) - 1) > 1e-9 or r1[3] == r2[3]:
                    continue
                (up, Ju), (lo, Jl) = ((r1, J1), (r2, J2)) if r1[3] > r2[3] else ((r2, J2), (r1, J1))
                f = m1_f(Ju, Jl, L, S)
                if f <= 0:
                    continue
                lam = 1.0e8 / (up[3] - lo[3])
                out.append((m1_A(lam, f), lam, up, lo, Ju, Jl, f))
    out.sort(key=lambda t: -t[0])
    return out


def fmt_J(J):
    return ("%d" % J) if abs(J - round(J)) < 1e-9 else ("%d/2" % round(2 * J))


def fmt_lam(lam, air):
    if air:
        lam = vac_to_air(lam)
    if lam < 1.0e4:
        return "%.2f Å" % lam
    if lam < 1.0e8:
        return "%.4f µm" % (lam / 1.0e4)
    return "%.2f cm" % (lam / 1.0e8)


def lam_attr(lam):
    """Colour a wavelength like the photon: red ... violet across the visible."""
    if lam > 7500:
        return curses.color_pair(LV_RAMP) | curses.A_DIM          # infrared
    if lam < 3800:
        return curses.color_pair(LV_RAMP + 9) | curses.A_DIM      # ultraviolet
    return curses.color_pair(LV_RAMP + min(9, max(0, int((7500 - lam) / 370.0))))


def method_attr(tag):
    """dn0/kram: hydrogenic formula used; cap/f=1: limited; '?': penetrating orbital."""
    if "?" in tag:
        return curses.color_pair(LV_BASE + 1)                  # red-ish: treat with care
    if tag.startswith(("dn0", "kram")):
        return curses.color_pair(LV_BASE + 2)                  # green
    return curses.color_pair(LV_LIMIT)                         # yellow: capped / f = 1


def a_attr(A, mode="M1"):
    if A >= MODES[mode]["strong"]:
        return curses.color_pair(LV_LIMIT) | curses.A_BOLD          # strong
    if A >= MODES[mode]["moderate"]:
        return curses.color_pair(LV_BASE + 2)                      # moderate
    return curses.A_DIM                                            # weak


# ---- E1 (allowed) lines: hydrogenic estimates of the oscillator strength
#
#   Candidates: parity changes, |dJ| <= 1 (no 0-0), LS-allowed when both terms are LS
#   (dS = 0, |dL| <= 1, no S-S), and one electron jumps n_a l_a <- n_b l_b with |dl| = 1.
#   One-electron absorption f for a -> b, with n* = zeta sqrt(Ry/(E_limit - E)), zeta = stage:
#     dn = 0 : f0 = (dE/Ry)/3 * l_>/(2l_a+1) * sigma^2,  sigma = 3/2 (n*/zeta) sqrt(n*^2 - l_>^2)
#     dn != 0: fK = 0.8 * 32/(3 pi sqrt3) / (n_lo^5 n_hi^3) / (1/n_lo^2 - 1/n_hi^2)^3   (Kramers,
#              integer n from the configuration), used as f = min(fK, f0, 1)
#     no ionization limit in the list: f = min(fK, 1) for dn != 0, f = 1 for dn = 0
#   Then for each upper level, the array's decay is shared over the allowed lower levels of
#   that lower configuration in proportion to (2J_l+1), and scaled by occupancy:
#     A_line = 6.670e15 (2l_a+1)/(2l_b+1) f / lambda[A]^2 * N_b * vac_a/(2(2l_a+1)) * w_line
#   Method tags: dn0, kram (Kramers), cap (f0 smaller than Kramers), f=1; '?' marks a d/f
#   orbital with n*^2 <= l(l+1), where the hydrogenic picture is poor.
RY_CM = 109737.31568
_ORB = re.compile(r"(\d+)([spdfghik])(\d*)")
_LL = "spdfghik"


def conf_occ(conf):
    """'3d6.(5D).4s' -> {(3,2): 6, (4,0): 1}  (parent terms ignored)."""
    occ = {}
    for n, l, q in _ORB.findall(re.sub(r"\([^)]*\)", " ", conf)):
        k = (int(n), _LL.index(l))
        occ[k] = occ.get(k, 0) + (int(q) if q else 1)
    return occ


def one_jump(o1, o2):
    """If configurations 1 and 2 differ by one electron moving with |dl| = 1, return
    (orbital with the extra electron in 2, orbital with the extra electron in 1), else None.
    A closed shell written in only one of them is ignored."""
    diff = {}
    for k in set(o1) | set(o2):
        a, b = o1.get(k, 0), o2.get(k, 0)
        cap = 2 * (2 * k[1] + 1)
        if a != b and ((a == 0 and b == cap) or (b == 0 and a == cap)):
            continue
        if a != b:
            diff[k] = a - b
    if len(diff) != 2 or sorted(diff.values()) != [-1, 1]:
        return None
    k1, k2 = list(diff)
    in1, in2 = (k1, k2) if diff[k1] == 1 else (k2, k1)
    return (in2, in1) if abs(in1[1] - in2[1]) == 1 else None


_KRAMERS = 0.8 * 32.0 / (3 * math.pi * math.sqrt(3))


def f_hydrogenic(ka, kb, E_lo, E_up, elim, zeta):
    """One-electron absorption f for a -> b -> (f, method tag)."""
    (na, la), (nb, lb) = ka, kb
    lg = max(la, lb)
    fK = None
    if na != nb:
        n_lo, n_hi = min(na, nb), max(na, nb)
        fK = _KRAMERS / (n_lo ** 5 * n_hi ** 3) / (1.0 / n_lo ** 2 - 1.0 / n_hi ** 2) ** 3
    if elim is None or E_up >= elim:
        return (min(fK, 1.0), "kram" if fK < 1 else "f=1") if fK is not None else (1.0, "f=1")
    nsa = zeta * math.sqrt(RY_CM / (elim - E_lo))
    nsb = zeta * math.sqrt(RY_CM / (elim - E_up))
    nbar = 0.5 * (nsa + nsb)
    sig = 1.5 * nbar / zeta * math.sqrt(max(nbar * nbar - lg * lg, 0.25))
    f0 = (E_up - E_lo) / RY_CM / 3.0 * lg / (2 * la + 1) * sig * sig
    pen = any(l >= 2 and ns * ns <= l * (l + 1) for l, ns in ((la, nsa), (lb, nsb)))
    q = "?" if pen else ""
    if fK is None:
        return (min(f0, 1.0), ("dn0" if f0 < 1 else "f=1") + q)
    f = min(fK, f0, 1.0)
    return f, ("kram" if f == fK else "cap" if f == f0 else "f=1") + q


def e1_A(lam_A, Ju, Jl, f=1.0):
    """Plain f -> A conversion for a single line (kept for reference)."""
    return 6.670e15 * (2 * Jl + 1) / (2 * Ju + 1) * f / lam_A ** 2


def e1_lines(rows, stage=1):
    """Candidate strong E1 lines -> list of (A, lam_vac_A, upper, lower, Ju, Jl, tag),
    strongest first."""
    limits = [r[3] for r in rows if is_limit(r[0], r[1])]
    elim, zeta = (min(limits) if limits else None), float(stage or 1)
    terms = {}
    for r in rows:
        conf, term, j, e, flag = r
        if is_limit(conf, term) or not conf.strip():
            continue
        J = parse_J(j)
        if J is None:
            continue
        key = (conf.strip(), term.strip())
        if key not in terms:
            terms[key] = {"LS": term_LS(term), "odd": is_odd(term), "occ": conf_occ(conf), "levels": []}
        terms[key]["levels"].append((r, J))
    keys, jump_cache, cand = list(terms), {}, []
    for i in range(len(keys)):
        for k in range(i + 1, len(keys)):
            t1, t2 = terms[keys[i]], terms[keys[k]]
            if t1["odd"] == t2["odd"]:
                continue
            note = ""
            if t1["LS"] and t2["LS"]:
                (L1, S1), (L2, S2) = t1["LS"], t2["LS"]
                if abs(S1 - S2) > 1e-9 or abs(L1 - L2) > 1 + 1e-9 or (L1 == 0 and L2 == 0):
                    continue
            else:
                note = " jj"
            ck = (keys[i][0], keys[k][0])
            if ck not in jump_cache:
                jump_cache[ck] = one_jump(t1["occ"], t2["occ"])
            jp = jump_cache[ck]
            if jp is None:
                continue
            extra_in_2, extra_in_1 = jp
            for r1, J1 in t1["levels"]:
                for r2, J2 in t2["levels"]:
                    if abs(J1 - J2) > 1 + 1e-9 or (J1 == 0 and J2 == 0) or r1[3] == r2[3]:
                        continue
                    if r1[3] > r2[3]:     # upper in term 1: the electron sits in extra_in_1
                        cand.append((r1, J1, t1, r2, J2, keys[k][0], extra_in_2, extra_in_1, note))
                    else:
                        cand.append((r2, J2, t2, r1, J1, keys[i][0], extra_in_1, extra_in_2, note))
    # (2J_l+1) sharing: per upper level and lower configuration
    wsum = {}
    for up, Ju, tu, lo, Jl, lconf, ka, kb, note in cand:
        key = (id(up), lconf)
        wsum[key] = wsum.get(key, 0.0) + 2 * Jl + 1
    out = []
    for up, Ju, tu, lo, Jl, lconf, ka, kb, note in cand:
        f, tag = f_hydrogenic(ka, kb, lo[3], up[3], elim, zeta)
        cap_a = 2 * (2 * ka[1] + 1)
        occ = tu["occ"].get(kb, 1) * max(0, cap_a - tu["occ"].get(ka, 0)) / cap_a
        if occ <= 0 or f <= 0:
            continue
        w = (2 * Jl + 1) / wsum[(id(up), lconf)]
        lam = 1.0e8 / (up[3] - lo[3])
        A = 6.670e15 * (2 * ka[1] + 1) / (2 * kb[1] + 1) * f / lam ** 2 * occ * w
        out.append((A, lam, up, lo, Ju, Jl, tag + note))
    out.sort(key=lambda t: -t[0])
    return out


MODES = {
    "M1": {"cuts": [0.0, 1e-4, 1e-3, 1e-2, 0.1, 1.0, 10.0], "strong": 1.0, "moderate": 1e-2,
           "title": "M1 lines within LS terms (dJ = ±1)",
           "formula": "A = 1.3 s⁻¹ (λ/4 µm)⁻³ f(J,L,S)   empirical, pure-LS estimate"},
    "E1": {"cuts": [0.0, 1e4, 1e5, 1e6, 1e7, 1e8, 1e9], "strong": 1e8, "moderate": 1e6,
           "title": "LS-allowed E1 lines (one-electron jumps)",
           "formula": "hydrogenic f (dn0: same-shell formula, kram: Kramers, capped), "
                      "shared by (2J_l+1), x occupancy; ? = penetrating d/f orbital"},
}
A_CUTS = MODES["M1"]["cuts"]


def fmt_e(e, unit_i, flag):
    s = ("%.3f" if unit_i == 0 else "%.6f") % (e * UNITS[unit_i][1])
    return "[" + s + "]" if flag == "[" else "(" + s + ")" if flag == "(" else s


# -------------------------------------------------------- list-style layers
def list_nav(st, ch, c, n, page):
    """Shared vim motions for list screens. True if the key was consumed."""
    if st["pend"] == "g":
        st["pend"] = ""
        if c == "g":
            st["cur"] = int(st["count"]) - 1 if st["count"] else 0
        st["count"] = ""
        st["cur"] = max(0, min(st["cur"], n - 1))
        return True
    if isdig(c) and (c != "0" or st["count"]):
        st["count"] += c
        return True
    cnt = int(st["count"]) if st["count"] else 1
    had = bool(st["count"])
    if c == "g":
        st["pend"] = "g"
        return True
    if c == "j" or ch == curses.KEY_DOWN:
        st["cur"] += cnt
    elif c == "k" or ch == curses.KEY_UP:
        st["cur"] -= cnt
    elif ch == 4:
        st["cur"] += max(1, page // 2)
    elif ch == 21:
        st["cur"] -= max(1, page // 2)
    elif ch in (6, curses.KEY_NPAGE):
        st["cur"] += page
    elif ch in (2, curses.KEY_PPAGE):
        st["cur"] -= page
    elif c == "G":
        st["cur"] = cnt - 1 if had else n - 1
    else:
        return False
    st["count"] = ""
    st["cur"] = max(0, min(st["cur"], n - 1))
    return True


def stage_picker(win, z):
    """Choose an ionization stage. -> stage int, None (cancel) or 'quit'."""
    sym, name, _ = ELEMS[z]
    st = {"cur": 0, "count": "", "pend": ""}
    col = curses.color_pair(CAT_OF[z] + 1)
    top, msg = 0, ""
    clicker = Clicker()
    while True:
        h, w = win.getmaxyx()
        page = max(1, h - 4)
        if st["cur"] < top:
            top = st["cur"]
        if st["cur"] >= top + page:
            top = st["cur"] - page + 1
        win.erase()
        put(win, 0, 1, "energy levels: %s (%s)" % (name, sym), col | curses.A_BOLD)
        put(win, 1, 1, "Enter query  j/k move  3<Enter> stage III  q cancel", curses.A_DIM)
        for i in range(page):
            k = top + i
            if k >= z:
                break
            stage, ne = k + 1, z - k
            line = "%-10s %-8s %3d e-   %s-like" % (sym + " " + roman(stage), ion_label(sym, stage), ne, ELEMS[ne][0])
            on = k == st["cur"]
            put(win, 2 + i, 1, ("> " if on else "  ") + line, curses.A_REVERSE if on else 0)
        put(win, h - 2, 1, "[%d/%d]" % (st["cur"] + 1, z), curses.A_DIM)
        put(win, h - 1, 1, msg)
        put(win, h - 1, w - 10, st["count"] + st["pend"], curses.A_BOLD)
        win.refresh()

        ch = win.getch()
        msg = ""
        if ch == curses.KEY_RESIZE:
            win.clear()
            continue
        if ch == curses.KEY_MOUSE:
            ev = read_mouse()
            if ev:
                kind, mx, my = ev
                if kind == "up":
                    st["cur"] = max(0, st["cur"] - 3)
                elif kind == "down":
                    st["cur"] = min(z - 1, st["cur"] + 3)
                else:
                    k = top + my - 2
                    if 0 <= my - 2 < page and 0 <= k < z:
                        st["cur"] = k
                        if kind == "right" or clicker.double(k):
                            return k + 1
            continue
        c = chr(ch) if 0 <= ch < 256 else ""
        if st["pend"] == "Z":
            st["pend"] = ""
            if c in ("Z", "Q"):
                return None
            continue
        if ch in (10, 13, curses.KEY_ENTER):
            if st["count"]:
                v, st["count"] = int(st["count"]), ""
                if 1 <= v <= z:
                    return v
                msg = "no such stage"
                continue
            return st["cur"] + 1
        if ch == 27:
            if st["count"] or st["pend"]:
                st["count"] = st["pend"] = ""
                continue
            return None
        if list_nav(st, ch, c, z, page):
            continue
        st["count"] = ""
        if c == "q":
            return None
        elif c == "Z":
            st["pend"] = "Z"
        elif c == ":":
            q = prompt(win, ":")
            if q is None:
                continue
            word = q.strip()
            if word in CLOSE:
                return None
            if word in QUIT_ALL:
                return "quit"
            v = parse_stage(word, z)
            if v:
                return v
            if word:
                msg = "E492: Not an editor command: " + word


def levels_view(win, sym, stage, rows, source, err):
    """Scrollable level table. -> 'close', 'quit' or 'refresh'."""
    st = {"cur": 0, "count": "", "pend": "", "msg": "", "unit": 0, "sort": True, "q": "",
          "col": not OPT["lite"], "mode": None}
    linecache, upcache = {}, {}

    def lines_all(mode):
        if mode not in linecache:
            linecache[mode] = m1_lines(rows) if mode == "M1" else e1_lines(rows, stage)
        return linecache[mode]

    def by_upper(mode):
        """id(upper level) -> lines from it above the A cut, strongest first."""
        key = (mode, OPT["cut"][mode])
        if key not in upcache:
            d, cut = {}, MODES[mode]["cuts"][OPT["cut"][mode]]
            for t in lines_all(mode):
                if t[0] >= cut:
                    d.setdefault(id(t[2]), []).append(t)
            upcache[key] = d
        return upcache[key]
    throttle = Throttle()
    emax = max((r[3] for r in rows), default=0.0) or 1.0
    attr_cache = {}

    def row_attrs(r):
        """(conf, term, energy) colour attrs, or 'limit'; computed once per row."""
        a = attr_cache.get(id(r))
        if a is None:
            conf, term, _, e, flag = r
            if is_limit(conf, term):
                a = "limit"
            else:
                ol = outer_l(conf)
                ca = curses.color_pair(LV_BASE + 1 + LV_L.index(ol)) if ol in LV_L else (
                    curses.color_pair(LV_BASE + 5) if ol else 0)
                ta = curses.color_pair(LV_ODD if is_odd(term) else LV_EVEN) if term else 0
                ea = curses.color_pair(LV_RAMP + min(9, max(0, int(10 * e / emax))))
                a = (ca, ta, ea | (curses.A_DIM if flag else 0))
            attr_cache[id(r)] = a
        return a
    view = sorted(rows, key=lambda r: r[3])
    top = 0

    def hit(r):
        return bool(st["q"]) and st["q"] in (r[0] + " " + r[1]).lower()

    def jump(d):
        n, k = len(view), st["cur"]
        for _ in range(n):
            k = (k + d) % n
            if hit(view[k]):
                st["cur"] = k
                return True
        return False

    while True:
        h, w = win.getmaxyx()
        page = max(1, h - 4)
        n = len(view)
        st["cur"] = max(0, min(st["cur"], n - 1)) if n else 0
        if st["cur"] < top:
            top = st["cur"]
        if st["cur"] >= top + page:
            top = st["cur"] - page + 1
        uname = UNITS[st["unit"]][0]
        mode = st["mode"]
        annw = (45 if mode == "E1" else 34) if mode else 0
        narrow = bool(mode) and w < 43 + annw + 12          # tags on, little room: hide the configuration
        termw, ew = (9, 12) if narrow else (12, 14)
        confw = 0 if narrow else max(10, min(60, w - 43 - annw))
        m1map = by_upper(mode) if mode else {}
        vidx = {id(r_): i_ for i_, r_ in enumerate(view)} if mode == "E1" else {}

        if throttle.should_draw(win):
            win.erase()
            put(win, 0, 1, "%s %s  (%s)  energy levels" % (sym, roman(stage), ion_label(sym, stage)), curses.A_BOLD)
            put(win, 1, 1, "%5s %s%-*s %-6s %*s" % ("#", ("%-*s " % (confw, "configuration")) if confw else "",
                                                    termw, "term", "J", ew, "E / " + uname)
                + ("  %-40s" % ("%s →%s  λ_%s  A/s⁻¹" % (
                    mode, "J_l" if mode == "M1" else "#lev", "air" if OPT["m1air"] else "vac")
                    + ("  method" if mode == "E1" else ""))
                   if mode else ""), curses.A_DIM | curses.A_UNDERLINE)
            if st["col"] and n:
                lx = 1 + len("%s %s  (%s)  energy levels" % (sym, roman(stage), ion_label(sym, stage))) + 3
                for txt, a in ([("outer:", curses.A_DIM)] +
                               [(l_, curses.color_pair(LV_BASE + 1 + i_)) for i_, l_ in enumerate("spdf")] +
                               [("  parity:", curses.A_DIM), ("even", curses.color_pair(LV_EVEN)),
                                ("odd*", curses.color_pair(LV_ODD)), ("  E:", curses.A_DIM)] +
                               [("█", curses.color_pair(LV_RAMP + i_)) for i_ in range(10)]):
                    put(win, 0, lx, txt, a)
                    lx += len(txt) + (0 if txt == "█" else 1)
            for i in range(page):
                k = top + i
                if k >= n:
                    break
                conf, term, j, e, flag = view[k]
                cells = ["%5d " % (k + 1), ("%-*s " % (confw, conf[:confw])) if confw else "",
                         "%-*s " % (termw, term[:termw]), "%-6s " % j[:6], "%*s" % (ew, fmt_e(e, st["unit"], flag))]
                y = 2 + i
                lines_here = m1map.get(id(view[k])) if mode else None
                if lines_here:
                    A_, lam_, _, lo_, _, Jl_, _ = lines_here[0]
                    ax = 1 + len("".join(cells)) + 2
                    more = " +%d" % (len(lines_here) - 1) if len(lines_here) > 1 else ""
                    on = k == st["cur"]
                    tgt = fmt_J(Jl_) if mode == "M1" else "#%d" % (vidx.get(id(lo_), -1) + 1)
                    put(win, y, ax, "→%-5s" % tgt, curses.A_REVERSE if on else curses.A_BOLD)
                    put(win, y, ax + 7, "%-13s" % fmt_lam(lam_, OPT["m1air"]),
                        curses.A_REVERSE if on else lam_attr(lam_))
                    put(win, y, ax + 21, "%-9.3g" % A_, curses.A_REVERSE if on else a_attr(A_, mode))
                    tail = (" %-7s" % lines_here[0][6] if mode == "E1" else "") + more
                    put(win, y, ax + 30, tail, curses.A_REVERSE if on else
                        (method_attr(lines_here[0][6]) if mode == "E1" else 0))
                if k == st["cur"] or not st["col"]:
                    attr = curses.A_REVERSE if k == st["cur"] else (curses.A_BOLD if hit(view[k]) else 0)
                    put(win, y, 1, "".join(cells), attr)
                    continue
                extra = curses.A_BOLD | curses.A_UNDERLINE if hit(view[k]) else 0
                ra = row_attrs(view[k])
                if ra == "limit":
                    put(win, y, 1, "".join(cells), curses.color_pair(LV_LIMIT) | curses.A_BOLD | extra)
                    continue
                ca, ta, ea = ra
                x = 1
                for txt, a in zip(cells, (curses.A_DIM, ca, ta, 0, ea)):
                    put(win, y, x, txt, a | extra)
                    x += len(txt)
            if n == 0:
                msg = err or "no data"
                width = max(10, w - 4)
                for i in range(0, len(msg), width):
                    put(win, 3 + i // width, 2, msg[i:i + width])
            put(win, h - 2, 1, "%d levels  [%d/%d]  units: %s  sort: %s  src: %s" % (
                n, st["cur"] + 1 if n else 0, n, uname, "energy" if st["sort"] else "NIST order", source)
                + ("   %s: %d lines, A ≥ %g  (f next  F list  t cut  a air/vac)" % (
                    mode, sum(len(v) for v in m1map.values()), MODES[mode]["cuts"][OPT["cut"][mode]])
                   if mode else ""),
                curses.A_DIM)
            put(win, h - 1, 1, st["msg"])
            put(win, h - 1, w - 10, st["count"] + st["pend"], curses.A_BOLD)
            win.refresh()

        ch = win.getch()
        st["msg"] = ""
        if ch == curses.KEY_RESIZE:
            win.clear()
            continue
        if ch == curses.KEY_MOUSE:
            ev = read_mouse()
            if ev and n:
                kind, mx, my = ev
                if kind == "up":
                    st["cur"] = max(0, st["cur"] - 3)
                elif kind == "down":
                    st["cur"] = min(n - 1, st["cur"] + 3)
                elif my == 1:
                    st["unit"] = (st["unit"] + 1) % len(UNITS)
                elif 0 <= my - 2 < page and top + my - 2 < n:
                    st["cur"] = top + my - 2
            continue
        c = chr(ch) if 0 <= ch < 256 else ""
        if st["pend"] == "Z":
            st["pend"] = ""
            if c in ("Z", "Q"):
                return "close"
            continue
        if ch == 27:
            if st["count"] or st["pend"] or st["q"]:
                st["count"] = st["pend"] = st["q"] = ""
                continue
            return "close"
        if list_nav(st, ch, c, n, page):
            continue
        st["count"] = ""
        if c == "q":
            return "close"
        elif c == "Z":
            st["pend"] = "Z"
        elif c == "?":
            show_lines(win, "levels - keys", VHELP)
        elif c == "u":
            st["unit"] = (st["unit"] + 1) % len(UNITS)
        elif c in ("c", "C"):
            st["col"] = not st["col"]
            st["msg"] = "colour " + ("on" if st["col"] else "off")
        elif c == "f":
            st["mode"] = {None: "M1", "M1": "E1", "E1": None}[st["mode"]]
            if st["mode"] == "M1":
                nl = len(lines_all("M1"))
                st["msg"] = ("M1: %d in-term lines (empirical A, pure LS)  f again: allowed lines" % nl) if nl \
                    else "M1: no same-term levels with dJ = 1 and parsable LS terms  (f again: allowed lines)"
            elif st["mode"] == "E1":
                nl = len(lines_all("E1"))
                st["msg"] = "E1: %d candidate allowed lines, hydrogenic f estimates  F list  t cut" % nl
            else:
                st["msg"] = "line tags off"
        elif c == "F":
            res = lines_view(win, sym, stage, lines_all(st["mode"] or "M1"), st["mode"] or "M1")
            if res == "quit":
                return "quit"
            if isinstance(res, tuple) and res[1] in view:
                st["cur"] = view.index(res[1])
                st["mode"] = res[2]
            win.clear()
        elif c == "t" and st["mode"]:
            md = st["mode"]
            OPT["cut"][md] = (OPT["cut"][md] + 1) % len(MODES[md]["cuts"])
            st["msg"] = "%s lines shown with A ≥ %g s^-1" % (md, MODES[md]["cuts"][OPT["cut"][md]])
        elif c == "a" and st["mode"]:
            OPT["m1air"] = not OPT["m1air"]
            st["msg"] = "wavelengths: " + ("air (above 2000 Å)" if OPT["m1air"] else "vacuum")
        elif c == "r":
            return "refresh"
        elif c == "o":
            keep = view[st["cur"]] if view else None
            st["sort"] = not st["sort"]
            view = sorted(rows, key=lambda r: r[3]) if st["sort"] else list(rows)
            if keep in view:
                st["cur"] = view.index(keep)
        elif c == "/":
            q = prompt(win, "/")
            if q is not None:
                st["q"] = q.strip().lower()
                if st["q"] and not jump(1):
                    st["msg"] = "pattern not found: " + q
        elif c in ("n", "N") and st["q"]:
            if not jump(1 if c == "n" else -1):
                st["msg"] = "pattern not found"
        elif c == ":":
            q = prompt(win, ":")
            if q is None:
                continue
            word = q.strip()
            if word in CLOSE:
                return "close"
            if word in QUIT_ALL:
                return "quit"
            if word.isdigit():
                st["cur"] = max(0, min(n - 1, int(word) - 1))
            elif word:
                st["msg"] = "E492: Not an editor command: " + word


def lines_view(win, sym, stage, lines, mode):
    """Full line list, strongest first. -> 'close', 'quit' or ('goto', upper, mode)."""
    st = {"cur": 0, "count": "", "pend": "", "msg": "", "bylam": False}
    throttle = Throttle()
    top = 0
    M = MODES[mode]

    def visible():
        cut = M["cuts"][OPT["cut"][mode]]
        v_ = [t for t in lines if t[0] >= cut]
        return sorted(v_, key=lambda t: t[1]) if st["bylam"] else v_

    v = visible()
    while True:
        h, w = win.getmaxyx()
        page = max(1, h - 5)
        n = len(v)
        st["cur"] = max(0, min(st["cur"], n - 1)) if n else 0
        if st["cur"] < top:
            top = st["cur"]
        if st["cur"] >= top + page:
            top = st["cur"] - page + 1
        lamh = "λ_" + ("air" if OPT["m1air"] else "vac")
        if throttle.should_draw(win):
            win.erase()
            put(win, 0, 1, "%s %s  %s" % (sym, roman(stage), M["title"]), curses.A_BOLD)
            put(win, 1, 1, M["formula"] + ";  Enter jumps to the upper level", curses.A_DIM)
            if mode == "M1":
                confw = max(8, min(40, w - 93))
                put(win, 2, 1, "%4s %-*s %-10s %-11s %12s %12s  %-14s %10s %6s" % (
                    "#", confw, "configuration", "term", "J_u → J_l", "E_u/cm⁻¹",
                    "E_l/cm⁻¹", lamh, "A/s⁻¹", "f"), curses.A_DIM | curses.A_UNDERLINE)
            else:
                confw = max(0, min(30, (w - 76) // 2))
                put(win, 2, 1, ("%4s %-8s %-5s   %-8s %-5s %-14s %10s %-7s" % (
                    "#", "upper", "J", "lower", "J", lamh, "A/s⁻¹", "method"))
                    + ((" %-*s %-*s" % (confw, "upper conf", confw, "lower conf")) if confw >= 6 else ""),
                    curses.A_DIM | curses.A_UNDERLINE)
            for i in range(page):
                k = top + i
                if k >= n:
                    break
                A, lam, up, lo, Ju, Jl, extra = v[k]
                y, on = 3 + i, k == st["cur"]
                if mode == "M1":
                    cells = [("%4d " % (k + 1), curses.A_DIM), ("%-*s " % (confw, up[0][:confw]), 0),
                             ("%-10s " % up[1][:10], 0), ("%-11s " % ("%s → %s" % (fmt_J(Ju), fmt_J(Jl))), 0),
                             ("%12s " % fmt_e(up[3], 0, up[4]), 0), ("%12s  " % fmt_e(lo[3], 0, lo[4]), 0),
                             ("%-14s " % fmt_lam(lam, OPT["m1air"]), lam_attr(lam)),
                             ("%10.3g " % A, a_attr(A, mode)), ("%6.3f" % extra, curses.A_DIM)]
                else:
                    cells = [("%4d " % (k + 1), curses.A_DIM),
                             ("%-8s " % up[1][:8], 0), ("%-5s → " % fmt_J(Ju), 0),
                             ("%-8s " % lo[1][:8], 0), ("%-5s " % fmt_J(Jl), 0),
                             ("%-14s " % fmt_lam(lam, OPT["m1air"]), lam_attr(lam)),
                             ("%10.3g " % A, a_attr(A, mode)), ("%-7s " % extra, method_attr(extra))]
                    if confw >= 6:
                        cells += [("%-*s " % (confw, up[0][:confw]), curses.A_DIM),
                                  ("%-*s" % (confw, lo[0][:confw]), curses.A_DIM)]
                x = 1
                for txt, a in cells:
                    put(win, y, x, txt, curses.A_REVERSE if on else a)
                    x += len(txt)
            if n == 0:
                cut = M["cuts"][OPT["cut"][mode]]
                why = (" above A = %g s^-1 (t to change)" % cut) if cut else (
                    ": needs two levels of the same configuration and LS term with J differing by 1"
                    if mode == "M1" else
                    ": needs opposite-parity terms whose configurations differ by one electron")
                put(win, 4, 2, "no %s lines%s" % (mode, why))
            put(win, h - 2, 1, "%d lines  [%d/%d]  A ≥ %g  sort: %s   t cut  s sort  a air/vac  "
                "Enter goto  q back" % (n, st["cur"] + 1 if n else 0, n, M["cuts"][OPT["cut"][mode]],
                                         "λ" if st["bylam"] else "A")
                + ("   method: dn0 same-shell, kram Kramers, cap/f=1 capped, ? penetrating"
                   if mode == "E1" else ""), curses.A_DIM)
            put(win, h - 1, 1, st["msg"])
            put(win, h - 1, w - 10, st["count"] + st["pend"], curses.A_BOLD)
            win.refresh()

        ch = win.getch()
        st["msg"] = ""
        if ch == curses.KEY_RESIZE:
            win.clear()
            continue
        if ch == curses.KEY_MOUSE:
            ev = read_mouse()
            if ev and n:
                kind, mx, my = ev
                if kind == "up":
                    st["cur"] = max(0, st["cur"] - 3)
                elif kind == "down":
                    st["cur"] = min(n - 1, st["cur"] + 3)
                elif 0 <= my - 3 < page and top + my - 3 < n:
                    st["cur"] = top + my - 3
            continue
        c = chr(ch) if 0 <= ch < 256 else ""
        if st["pend"] == "Z":
            st["pend"] = ""
            if c in ("Z", "Q"):
                return "close"
            continue
        if ch == 27:
            if st["count"] or st["pend"]:
                st["count"] = st["pend"] = ""
                continue
            return "close"
        if ch in (10, 13, curses.KEY_ENTER) and n:
            return ("goto", v[st["cur"]][2], mode)
        if list_nav(st, ch, c, n, page):
            continue
        st["count"] = ""
        if c in ("q", "F", "f"):
            return "close"
        elif c == "Z":
            st["pend"] = "Z"
        elif c == "t":
            OPT["cut"][mode] = (OPT["cut"][mode] + 1) % len(M["cuts"])
            v = visible()
        elif c == "s":
            st["bylam"] = not st["bylam"]
            v = visible()
        elif c == "a":
            OPT["m1air"] = not OPT["m1air"]
        elif c == ":":
            q = prompt(win, ":")
            if q is None:
                continue
            word = q.strip()
            if word in CLOSE:
                return "close"
            if word in QUIT_ALL:
                return "quit"
            if word.isdigit():
                st["cur"] = max(0, min(n - 1, int(word) - 1))
            elif word:
                st["msg"] = "E492: Not an editor command: " + word


# --------------------------------------------------------------------- main
def run(win, start):
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    try:
        curses.start_color()
        curses.use_default_colors()
        big = curses.COLORS >= 256
        pal = C256 if big else C8
        for i, fg in enumerate(pal):
            curses.init_pair(i + 1, fg, -1)
            if not big:
                dark_bg = C8[i] in (curses.COLOR_RED, curses.COLOR_BLUE, curses.COLOR_MAGENTA)
                curses.init_pair(FILL_BASE + i + 1, curses.COLOR_WHITE if dark_bg else curses.COLOR_BLACK, C8[i])
        if big:
            init_fills()
        init_level_pairs(big)
    except curses.error:
        pass  # monochrome terminal: attributes only
    prune_cache()

    st = {"cur": 1, "matches": [], "hl": None, "msg": "", "count": "", "pend": ""}
    clicker = Clicker()
    if MOUSE_MASK and not os.environ.get("PERIODIC_NO_MOUSE"):
        curses.mouseinterval(0)
        curses.mousemask(MOUSE_MASK)
    if start:
        hits = find(start)
        if hits:
            st["cur"], st["matches"] = hits[0], hits

    def search(q):
        hits = find(q or "")
        st["matches"] = hits
        if not hits:
            st["msg"] = "no match: %s" % q
            return
        after = [z for z in hits if z > st["cur"]]
        st["cur"] = after[0] if after else hits[0]

    def open_levels(z, stage=None):
        """Stage picker -> NIST query -> level viewer. Returns 'quit' or None."""
        sym = ELEMS[z][0]
        preset, force = stage is not None, False
        while True:
            if stage is None:
                stage = stage_picker(win, z)
                if stage is None:
                    return None
                if stage == "quit":
                    return "quit"
            win.erase()
            put(win, 1, 2, "querying NIST ASD for %s %s ..." % (sym, roman(stage)))
            win.refresh()
            rows, src, err = get_levels(sym, stage, force)
            force = False
            res = levels_view(win, sym, stage, rows, src, err)
            if res == "quit":
                return "quit"
            if res == "refresh":
                force = True
                continue
            if preset:
                return None
            stage = None

    def set_mouse(on):
        if not on or not MOUSE_MASK:
            curses.mousemask(0)
            st["msg"] = "mouse off" if not on else "mouse not supported by this curses"
            return
        curses.mouseinterval(0)
        curses.mousemask(MOUSE_MASK)
        st["msg"] = "mouse on: click select, double-click opens levels, wheel scrolls"

    def ex_set(opt):
        opt = opt.strip()
        if opt in ("mouse", "mouse=a"):
            set_mouse(True)
        elif opt in ("nomouse", "mouse="):
            set_mouse(False)
        elif opt.startswith("opacity="):
            try:
                v = int(opt.split("=", 1)[1])
            except ValueError:
                v = 0
            if not 10 <= v <= 100:
                st["msg"] = "E474: opacity must be 10-100"
            elif curses.COLORS < 256:
                st["msg"] = "opacity needs a 256-colour terminal"
            else:
                OPT["opacity"] = v
                init_fills()
                st["msg"] = "opacity %d%%" % v
        elif opt in ("background=light", "background=dark", "bg=light", "bg=dark"):
            OPT["light"] = opt.endswith("light")
            if curses.COLORS >= 256:
                init_fills()
            st["msg"] = "background=" + ("light" if OPT["light"] else "dark")
        elif opt in ("lite", "nolite"):
            OPT["lite"] = opt == "lite"
            st["msg"] = "lite mode " + ("on" if OPT["lite"] else "off")
            win.clear()
        elif opt in ("spacing", "nospacing"):
            OPT["space"] = opt == "spacing"
            st["msg"] = "spacing " + ("on" if OPT["space"] else "off")
        elif opt.startswith("aspect="):
            try:
                v = float(opt.split("=", 1)[1])
            except ValueError:
                v = 0.0
            if not 1.0 <= v <= 3.0:
                st["msg"] = "E474: aspect must be 1.0-3.0 (font height / width)"
            else:
                OPT["aspect"] = v
                st["msg"] = "aspect %.2f" % v
        elif opt in ("opacity", "opacity?"):
            st["msg"] = "opacity=%d  background=%s  aspect=%.2f  %sspacing" % (
                OPT["opacity"], "light" if OPT["light"] else "dark", OPT["aspect"], "" if OPT["space"] else "no")
        else:
            st["msg"] = "E518: Unknown option: " + opt

    def ex(cmd):
        cmd = cmd.strip()
        if not cmd:
            return None
        word, _, arg = cmd.partition(" ")
        arg = arg.strip()
        if word in CLOSE or word in QUIT_ALL:
            return "quit"
        if word in ("h", "help"):
            show_lines(win, "PERIODIC - keys", HELP)
            return None
        if word in ("noh", "nohlsearch"):
            st["matches"] = []
            return None
        if word in ("w", "write"):
            st["msg"] = "nothing to write"
            return None
        if word in ("set", "se"):
            ex_set(arg)
            return None
        if re.fullmatch(r"[0-9]+", word):
            v = int(word)
            if 1 <= v <= NZ:
                st["cur"] = v
            else:
                st["msg"] = "E16: Invalid range"
            return None
        if word in ("lev", "levels", "e", "edit"):
            toks, z, stage = arg.split(), st["cur"], None
            if len(toks) == 2:
                hits = find(toks[0])
                if not hits:
                    st["msg"] = "no such element: " + toks[0]
                    return None
                z = st["cur"] = hits[0]
            if toks:
                stage = parse_stage(toks[-1], z)
                if stage is None and len(toks) == 1 and find(toks[0]):
                    z = st["cur"] = find(toks[0])[0]
                elif stage is None:
                    st["msg"] = "bad ionization stage: " + toks[-1]
                    return None
            return open_levels(z, stage)
        hits = find(cmd)
        if hits:
            st["matches"] = hits
            st["cur"] = hits[0]
        else:
            st["msg"] = "E492: Not an editor command: " + cmd
        return None

    throttle = Throttle()
    while True:
        if throttle.should_draw(win):
            draw(win, st)
        ch = win.getch()
        st["msg"] = ""
        if ch == curses.KEY_RESIZE:
            try:
                curses.update_lines_cols()
            except AttributeError:
                pass
            win.erase()
            win.touchwin()
            continue
        if ch == curses.KEY_MOUSE:
            ev = read_mouse()
            if ev:
                kind, mx, my = ev
                if kind in ("up", "down"):
                    st["cur"] = move_v(st["cur"], -1 if kind == "up" else 1)
                else:
                    zc = hit_cell(win, mx, my)
                    if zc:
                        st["cur"] = zc
                        if (kind == "right" or clicker.double(zc)) and open_levels(zc) == "quit":
                            return
            continue
        c = chr(ch) if 0 <= ch < 256 else ""

        if ch == 27:
            st.update(matches=[], hl=None, count="", pend="")
            continue
        if isdig(c) and (c != "0" or st["count"]):
            st["count"] += c
            continue

        n = int(st["count"]) if st["count"] else 1
        had_count = bool(st["count"])
        st["count"] = ""
        z = st["cur"]

        if st["pend"] == "g":
            st["pend"] = ""
            if c == "g":
                st["cur"] = n if had_count and 1 <= n <= NZ else 1
            continue
        if st["pend"] == "Z":
            st["pend"] = ""
            if c in ("Z", "Q"):
                return
            continue

        if c == "q":
            return
        elif c == "?":
            show_lines(win, "PERIODIC - keys", HELP)
        elif ch in (10, 13, curses.KEY_ENTER):
            if open_levels(z) == "quit":
                return
        elif c == "h" or ch == curses.KEY_LEFT:
            for _ in range(n): z = move_h(z, -1)
        elif c == "l" or ch == curses.KEY_RIGHT:
            for _ in range(n): z = move_h(z, +1)
        elif c == "k" or ch == curses.KEY_UP:
            for _ in range(n): z = move_v(z, -1)
        elif c == "j" or ch == curses.KEY_DOWN:
            for _ in range(n): z = move_v(z, +1)
        elif c == "w":
            z = min(NZ, z + n)
        elif c == "b":
            z = max(1, z - n)
        elif c in ("0", "^"):
            z = row_edge(z, False)
        elif c == "$":
            z = row_edge(z, True)
        elif c == "g":
            st["pend"] = "g"
        elif c == "Z":
            st["pend"] = "Z"
        elif c == "G":
            z = n if had_count and 1 <= n <= NZ else NZ
        elif c == "/":
            q = prompt(win, "/")
            if q is not None:
                search(q)
                z = st["cur"]
        elif c == ":":
            q = prompt(win, ":")
            if q is not None and ex(q) == "quit":
                return
            z = st["cur"]
        elif c in ("n", "N") and st["matches"]:
            ms = sorted(st["matches"])
            i = ms.index(z) if z in ms else -1
            i = (i + (1 if c == "n" else -1)) % len(ms)
            z = ms[i]
        elif c == "c":
            st["hl"] = 0 if st["hl"] is None else (st["hl"] + 1) % len(CATS)
        elif c == "C":
            st["hl"] = len(CATS) - 1 if st["hl"] is None else (st["hl"] - 1) % len(CATS)
        elif c == "L":
            OPT["lite"] = not OPT["lite"]
            st["msg"] = "lite mode " + ("on: no cell fills, plain level lists" if OPT["lite"] else "off")
            win.clear()
        st["cur"] = z


def main():
    start = " ".join(sys.argv[1:]) or None
    try:
        curses.wrapper(run, start)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()