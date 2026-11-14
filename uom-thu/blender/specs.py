# Garment specs shared by masks.py (PIL) and garments.py (Blender). Units: cm, y up, top of garment ~ y=0.
# A point is (x, y) smooth or (x, y, 1) sharp corner. Half outlines run from the centre line down the right side.

PX_PER_CM = 6

def mirror(half):
    """Close a right-half outline (starts and ends on x=0) into a full polygon."""
    left = [(-p[0],) + tuple(p[1:]) for p in reversed(half[1:-1])]
    return list(half) + left

def mir_pts(pts):
    return [(-p[0],) + tuple(p[1:]) for p in pts]

def mir_lines(lines):
    return lines + [[(-x, y) for x, y in l] for l in lines]

def leg_crease(hip, hem_out, hem_in, crotch_y):
    # ridge from upper thigh to hem along the leg centre (pressed linen crease)
    top = ((hip[0] * 0.55), crotch_y + 4)
    bot = ((hem_out + hem_in) / 2, None)
    return top, bot

# ---------- colours (name_vi, hex) ----------
LINEN_COLORS = {
    'be-yen-mach': ('Be yến mạch', '#d6c7ab'),
    'trang-nga':   ('Trắng ngà',   '#ece6d9'),
    'xanh-reu':    ('Xanh rêu',    '#8c9a78'),
    'nau-dat':     ('Nâu đất',     '#8a5a3c'),
    'xanh-navy':   ('Xanh navy',   '#2c3a55'),
    'den':         ('Đen',         '#262628'),
}
COAT_COLORS = {
    'camel':     ('Camel',      '#b88a5a'),
    'den':       ('Đen',        '#232325'),
    'xam-tieu':  ('Xám tiêu',   '#86868a'),
    'be-kem':    ('Be kem',     '#d9ccb4'),
    'nau-chocolate': ('Nâu socola', '#57392a'),
}
DRESS_COLORS = {
    'trang-nga':  ('Trắng ngà',  '#efe9dd'),
    'xanh-sage':  ('Xanh sage',  '#a3b19a'),
    'den':        ('Đen',        '#262628'),
    'hong-dat':   ('Hồng đất',   '#c58b7a'),
    'xanh-baby':  ('Xanh baby',  '#a9c1d9'),
}

G = {}

# ---------------- PANTS (quần linen) ----------------
def pants(key, name, waist, hip, length, hem_out, hem_in, crotch, elastic=False, cuff=False):
    w = waist
    half = [(0, 0, 1), (w, 0, 1), (w + 0.6, -5, 0) if elastic else (w + 0.5, -6), (hip, -24),
            (hem_out, -length, 1), (hem_in, -length, 1), (0, -crotch, 1)]
    if elastic:
        half = [(0, 0, 1), (w, 0, 1), (w + 0.4, -5.5, 1), (hip, -26), (hem_out, -length, 1), (hem_in, -length, 1), (0, -crotch, 1)]
    lines = []
    band = 5.5 if elastic else 4.0
    lines.append([(-w - 1, -band), (w + 1, -band)])
    if not elastic:
        lines += mir_lines([[(w - 3, -band), (hip - 2.2, -17)]])            # slant side pockets
        lines.append([(0, -band), (2.6, -band - 1), (2.6, -16), (0, -19.5)])  # fly stitching
        lines += mir_lines([[(x, 0), (x, -band)] for x in (w * 0.55, w - 1.5)])  # belt loops
    else:
        lines += [[(x, -0.6), (x, -band + 0.6)] for x in [i * 1.7 - w + 0.8 for i in range(int(2 * w / 1.7))]]  # elastic gathers
    if cuff:
        lines.append([(hem_in, -length + 4), (hem_out, -length + 4)])
        lines.append([(-hem_in, -length + 4), (-hem_out, -length + 4)])
    # pressed crease along each leg
    cx_top = hip * 0.5
    cx_bot = (hem_out + hem_in) / 2
    ridges = [((cx_top, -crotch + 2), (cx_bot, -length + 1), 0.55, 0.9),
              ((-cx_top, -crotch + 2), (-cx_bot, -length + 1), 0.55, 0.9)]
    slabs = [{'poly': [(-w - 0.3, 0.3, 1), (w + 0.3, 0.3, 1), (w + 0.7 if elastic else w + 0.5, -band, 1), (-w - 0.7 if elastic else -w - 0.5, -band, 1)], 'z': 0.15, 'th': 0.5}]
    if elastic:  # drawstring cords hanging from centre
        slabs.append({'poly': [(-1.2, -2.0, 1), (-0.6, -2.0, 1), (-1.6, -17, 1), (-2.3, -17, 1)], 'z': 0.6, 'th': 0.35})
        slabs.append({'poly': [(0.6, -2.0, 1), (1.2, -2.0, 1), (2.6, -16, 1), (1.9, -16, 1)], 'z': 0.6, 'th': 0.35})
    G[key] = dict(cat='quan', name=name, outline=mirror(half), lines=lines, ridges=ridges, slabs=slabs,
                  dots=[(0, -2.0)] if not elastic else [], dark=[],
                  folds=dict(top=0.45, bottom=1.5, lam=(5.5, 8.5, 13.0)), colors=LINEN_COLORS,
                  vton='Lower-body')

pants('quan-ong-rong', 'Quần linen ống rộng', 19, 25.5, 100, 32, 3.0, 33)
pants('quan-ong-suong', 'Quần linen ống suông', 18.5, 24.5, 100, 25.5, 4.5, 33)
pants('quan-lung-culottes', 'Quần culottes linen', 19, 26, 68, 32, 3.0, 32)
pants('quan-palazzo-lung-chun', 'Quần palazzo lưng chun', 16.5, 26, 104, 36, 2.5, 34, elastic=True)

# ---------------- COATS (áo măng tô) ----------------
def coat(key, name, length, belted=False, double=False):
    hem_w = 27 if length > 100 else 25.5
    half = [(0, -0.5, 1), (5.5, 1.5), (9, 0.6), (19.5, -3, 1), (23.5, -8), (27, -30), (29.5, -64, 1),
            (23.2, -66.5, 1), (23.6, -69, 1), (hem_w, -length, 1), (0, -length - 0.8, 1)]
    lines = []
    lines += mir_lines([[(20.5, -21), (22.2, -45), (23.0, -65.5)]])    # inner sleeve seam
    lines += mir_lines([[(19.3, -3), (21.5, -21)]])                     # armhole seam
    lines += mir_lines([[(23.6, -58), (29.0, -58.8)]])                  # cuff tab line
    lines += mir_lines([[(10.5, -62), (18.5, -60.5)], [(10.5, -62), (10.6, -63.2)], [(18.5, -60.5), (18.7, -61.8)]])  # pocket flaps
    lines.append([(0.0, -39), (0.0, -length)])                          # front closure
    lines.append([(-hem_w + 1, -length + 3), (hem_w - 1, -length + 3)])  # hem stitch
    dots = []
    if double:
        dots += [(6, y) for y in (-44, -56, -68)] + [(-6, y) for y in (-44, -56, -68)]
    elif not belted:
        dots += [(2.4, y) for y in (-46, -60, -74)]
    lapel = [(5.5, 1.5, 1), (8.7, 0.4, 1), (12.8, -8.5, 1), (11.3, -11.2, 1), (15.2, -14, 1), (7.5, -28), (0.6, -40, 1), (0.2, -38.5, 1)]
    if double:
        lapel = [(5.5, 1.5, 1), (8.7, 0.4, 1), (13.3, -9, 1), (11.8, -11.8, 1), (16.5, -14.5, 1), (11, -27), (2.0, -41, 1), (0.2, -38.5, 1)]
    slabs = [{'poly': lapel, 'z': 0.6, 'th': 0.45}, {'poly': mir_pts(lapel), 'z': 0.6, 'th': 0.45}]
    dark = [[(0, -0.5), (5.3, 1.4), (0.2, -38.5), (-5.3, 1.4)]]  # visible inside of the V neckline
    if belted:
        slabs.append({'poly': [(-25, -40, 1), (25, -40, 1), (25.3, -45, 1), (-25.3, -45, 1)], 'z': 0.8, 'th': 0.4})
        slabs.append({'poly': [(-2.5, -39.5, 1), (2.5, -39.5, 1), (3, -46, 1), (-3, -46, 1)], 'z': 1.3, 'th': 0.5})  # knot
        slabs.append({'poly': [(-2.2, -45, 1), (0.6, -45, 1), (-1.5, -78, 1), (-4.6, -77, 1)], 'z': 1.1, 'th': 0.35})  # sash tails
        slabs.append({'poly': [(0.4, -45, 1), (3.0, -45, 1), (4.8, -70, 1), (1.8, -70.5, 1)], 'z': 1.2, 'th': 0.35})
    G[key] = dict(cat='mangto', name=name, outline=mirror(half), lines=lines,
                  ridges=[((0, -40), (0, -length), -0.35, 0.7)], slabs=slabs, dots=dots, dark=dark,
                  folds=dict(top=0.3, bottom=1.1, lam=(6.5, 10.0, 15.0)), colors=COAT_COLORS, vton='Dress')

coat('mangto-dang-dai', 'Măng tô dáng dài', 112)
coat('mangto-dang-lung', 'Măng tô dáng lửng', 86)
coat('mangto-that-dai', 'Măng tô thắt đai', 108, belted=True)
coat('mangto-hai-hang-khuy', 'Măng tô hai hàng khuy', 104, double=True)

# ---------------- DRESSES (đầm linen) ----------------
def dress(key, name, half, lines=(), slabs=(), dots=(), dark=(), folds=None):
    G[key] = dict(cat='dam', name=name, outline=mirror(half), lines=list(lines), ridges=[], slabs=list(slabs),
                  dots=list(dots), dark=list(dark), folds=folds or dict(top=0.35, bottom=1.4, lam=(5.0, 8.0, 12.0)),
                  colors=DRESS_COLORS, vton='Dress')

# slip dress, 2 straps
strap = [(5.6, -11.5, 1), (6.4, -11.5, 1), (7.4, 1.5, 1), (6.6, 1.5, 1)]
dress('dam-hai-day', 'Đầm hai dây linen',
      [(0, -15.5, 1), (6.2, -11, 1), (10.5, -13.5, 1), (12, -25), (11, -38), (14, -62), (17.5, -104, 1), (0, -105, 1)],
      lines=[[(-11, -38), (11, -38)]] + [[(-17, -101), (17, -101)]],
      slabs=[{'poly': strap, 'z': 0.3, 'th': 0.3}, {'poly': mir_pts(strap), 'z': 0.3, 'th': 0.3}])

# shirt dress with collar, short sleeves, button placket and tie belt
collar = [(0.3, -3.5, 1), (4.5, 1.2, 1), (7.8, 0.3, 1), (6.0, -6.5, 1)]
dress('dam-so-mi', 'Đầm sơ mi linen',
      [(0, -3.5, 1), (4.5, 1.0), (8.5, 0.6), (17.5, -3, 1), (24, -9.5), (26.5, -22, 1), (19.8, -24.5, 1), (18.8, -37), (17.6, -42),
       (24.5, -102, 1), (0, -103, 1)],
      lines=[[(-1.6, -3), (-1.6, -102)], [(1.6, -3), (1.6, -102)]] + mir_lines([[(17.6, -3), (19.8, -24)], [(19.6, -19.5), (26.0, -18)]]),
      slabs=[{'poly': collar, 'z': 0.5, 'th': 0.35}, {'poly': mir_pts(collar), 'z': 0.5, 'th': 0.35},
             {'poly': [(-18.3, -39, 1), (18.3, -39, 1), (18.5, -43, 1), (-18.5, -43, 1)], 'z': 0.6, 'th': 0.35},
             {'poly': [(-1.5, -42.5, 1), (1.2, -42.5, 1), (-2.0, -64, 1), (-4.6, -63, 1)], 'z': 0.9, 'th': 0.3},
             {'poly': [(0.8, -42.5, 1), (3.0, -42.5, 1), (5.4, -60, 1), (2.8, -60.5, 1)], 'z': 1.0, 'th': 0.3}],
      dots=[(0, y) for y in (-7, -17, -27, -48, -58, -68, -78, -88)])

# A-line sleeveless, round neck
dress('dam-chu-a', 'Đầm chữ A sát nách',
      [(0, -5, 1), (6, -1, 1), (12.5, -2, 1), (12.2, -9), (15.8, -21, 1), (15.2, -34), (26, -96, 1), (0, -98, 1)],
      lines=[[(-15.2, -34), (15.2, -34)], [(-25.5, -93.5), (25.5, -93.5)]] + mir_lines([[(5.5, -34), (8.5, -96)]]),
      folds=dict(top=0.3, bottom=1.6, lam=(6.0, 9.0, 14.0)))

# babydoll smock: square neck, puff sleeves, tiered skirt
dress('dam-babydoll', 'Đầm babydoll tầng',
      [(0, -6, 1), (8, -6, 1), (9, 0, 1), (14, 0, 1), (21, -3.5), (22.5, -11), (21, -14, 1), (16.5, -14.5, 1), (15.5, -27, 1),
       (19.5, -56, 1), (22.5, -60), (30, -100, 1), (0, -101, 1)],
      lines=[[(-15.5, -27), (15.5, -27)], [(-19.5, -56), (19.5, -56)]] + mir_lines([[(14, -0.5), (16.5, -14)], [(15.6, -12.5), (21.5, -12)]])
            + [[(x, -27.5), (x * 1.1, -31)] for x in [i * 2.2 - 15 for i in range(14)]]
            + [[(x, -56.5), (x * 1.06, -60)] for x in [i * 2.6 - 19 for i in range(15)]],
      folds=dict(top=0.35, bottom=1.5, lam=(3.5, 6.0, 9.0)))
