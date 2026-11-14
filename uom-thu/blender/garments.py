# Blender script: build linen garments procedurally and render flat-lay product shots.
# Usage: blender -b -P garments.py -- MASKDIR OUTDIR [key[:color] ...]
import bpy, sys, os, math, json
import numpy as np
from mathutils import Vector, noise

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from specs import G, PX_PER_CM as P

argv = sys.argv[sys.argv.index('--') + 1:]
MASKDIR, OUT = argv[0], argv[1]
WANT = argv[2:]
os.makedirs(OUT, exist_ok=True)


def srgb_to_lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_lin(h):
    h = h.lstrip('#')
    return tuple(srgb_to_lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4)) + (1.0,)


def chaikin(poly, it=3):
    pts = [(p[0], p[1], len(p) > 2 and p[2] == 1) for p in poly]
    for _ in range(it):
        n = len(pts); new = []
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            if a[2]:
                new.append(a)
            else:
                pa = pts[i - 1]
                # replace smooth vertex a by two points toward its neighbours
                new.append((0.25 * pa[0] + 0.75 * a[0], 0.25 * pa[1] + 0.75 * a[1], False))
                new.append((0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1], False))
        pts = new
    return [(p[0], p[1]) for p in pts]


def slab_mesh(name, poly, extrude, bevel, voxel):
    cu = bpy.data.curves.new(name + '_cu', 'CURVE')
    cu.dimensions = '2D'; cu.fill_mode = 'BOTH'
    cu.extrude = extrude; cu.bevel_depth = bevel; cu.bevel_resolution = 3
    sp = cu.splines.new('POLY')
    pts = chaikin(poly)
    sp.points.add(len(pts) - 1)
    for i, (x, y) in enumerate(pts):
        sp.points[i].co = (x, y, 0, 1)
    sp.use_cyclic_u = True
    co = bpy.data.objects.new(name + '_c', cu); bpy.context.scene.collection.objects.link(co)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(co.evaluated_get(dg))
    bpy.data.objects.remove(co); bpy.data.curves.remove(cu)
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    rm = ob.modifiers.new('rm', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = voxel; rm.adaptivity = 0
    dg = bpy.context.evaluated_depsgraph_get()
    me2 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    ob.modifiers.clear(); old = ob.data; ob.data = me2; bpy.data.meshes.remove(old)
    return ob


def seg_dist(px, py, a, b):
    ax, ay = a; bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy)), t


def build(key, g):
    for o in list(bpy.data.objects):
        if o.type == 'MESH' and o.name != 'catcher':
            bpy.data.objects.remove(o)
    info = json.load(open(os.path.join(MASKDIR, key + '.json')))
    x0, y0, x1, y1 = info['bbox']
    img = bpy.data.images.load(os.path.join(MASKDIR, key + '.png'), check_existing=False)
    img.colorspace_settings.name = 'Non-Color'
    W, H = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(H, W, 4)

    def mask(x, y):
        c = int((x - x0) * P); r = int((y - y0) * P)
        if 0 <= c < W and 0 <= r < H:
            return px[r, c]
        return (0, 0, 0, 0)

    ys = [p[1] for p in g['outline']]
    top, bot = max(ys), min(ys)
    F = g['folds']; lam = F['lam']
    seed = sum(map(ord, key)) * 0.37

    def disp(X, Y):
        t = np.clip((top - Y) / (top - bot), 0, 1)
        amp = F['top'] + (F['bottom'] - F['top']) * t ** 1.3
        S = np.zeros_like(X)
        for k, l in enumerate(lam):
            warp = 1.3 * np.sin(Y * 0.07 + seed * (k + 1)) + 0.9 * np.sin(Y * 0.023 + X * 0.05 + k * 2.1) + 0.6 * np.sin(X * 0.11 - Y * 0.04 + seed)
            S += np.sin(2 * np.pi * X / l + warp + k * 1.7 + seed) / (k + 1)
        D = amp * S * 0.6
        D += 0.3 * np.sin(X * 0.13 + Y * 0.05 + seed) * np.sin(Y * 0.09 - seed)
        for a, b, h, w in g['ridges']:
            ax, ay = a; bx, by = b; dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy
            tt = np.clip(((X - ax) * dx + (Y - ay) * dy) / L2, 0, 1)
            dist = np.hypot(X - (ax + tt * dx), Y - (ay + tt * dy))
            fade = np.minimum(1.0, np.minimum(tt * 6, (1 - tt) * 6))
            D += h * np.exp(-(dist / w) ** 2) * fade
        c = np.clip(((X - x0) * P).astype(int), 0, W - 1); r = np.clip(((Y - y0) * P).astype(int), 0, H - 1)
        m = px[r, c]
        D += -0.32 * m[:, 0] + 0.6 * m[:, 2]
        return D

    def apply_disp(ob, base_z):
        me = ob.data; n = len(me.vertices)
        co = np.zeros(n * 3, dtype=np.float32); me.vertices.foreach_get('co', co); co = co.reshape(n, 3)
        nm = np.zeros(n * 3, dtype=np.float32); me.vertices.foreach_get('normal', nm); nm = nm.reshape(n, 3)
        wgt = np.clip(nm[:, 2] * 1.6, 0, 1) * (nm[:, 2] > 0.05)
        co[:, 2] += base_z + disp(co[:, 0], co[:, 1]) * wgt
        me.vertices.foreach_set('co', co.ravel()); me.update(); me.shade_smooth()

    body = slab_mesh(key, g['outline'], 0.45, 0.55, 0.32)
    apply_disp(body, 0.0)
    obs = [body]
    for i, s in enumerate(g['slabs']):
        sl = slab_mesh(f'{key}_s{i}', s['poly'], s['th'] * 0.5, s['th'] * 0.5, 0.18)
        apply_disp(sl, 1.0 + s['z'])
        obs.append(sl)

    mat = make_material(img, (x0, y0, x1, y1))
    for o in obs:
        o.data.materials.append(mat)

    # camera framing
    h = top - bot
    xs = [p[0] for p in g['outline']]
    w = max(xs) - min(xs)
    cam = bpy.data.objects['cam']
    cam.location = (0, (top + bot) / 2, 300)
    cam.data.ortho_scale = max(h * 1.14, w * 1.14 * 4 / 3)
    return mat


def make_material(img, bbox):
    x0, y0, x1, y1 = bbox
    m = bpy.data.materials.new('linen'); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    bsdf = N['Principled BSDF']
    bsdf.inputs['Roughness'].default_value = 0.86
    bsdf.inputs['Sheen Weight'].default_value = 0.35
    bsdf.inputs['Sheen Roughness'].default_value = 0.6
    tc = N.new('ShaderNodeTexCoord')
    sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sep.inputs[0])
    def lin(inp, a, b):
        mr = N.new('ShaderNodeMapRange'); mr.clamp = False
        mr.inputs['From Min'].default_value = a; mr.inputs['From Max'].default_value = b
        L.new(inp, mr.inputs['Value']); return mr.outputs['Result']
    comb = N.new('ShaderNodeCombineXYZ')
    L.new(lin(sep.outputs['X'], x0, x1), comb.inputs['X'])
    L.new(lin(sep.outputs['Y'], y0, y1), comb.inputs['Y'])
    it = N.new('ShaderNodeTexImage'); it.image = img; it.extension = 'CLIP'
    L.new(comb.outputs[0], it.inputs['Vector'])
    sc = N.new('ShaderNodeSeparateColor'); L.new(it.outputs['Color'], sc.inputs[0])

    base = N.new('ShaderNodeRGB'); base.name = 'BASE'
    # linen slubs: horizontal + vertical streaky noise
    def streak(sx, sy, sc_):
        mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (sx, sy, 1)
        L.new(tc.outputs['Object'], mp.inputs['Vector'])
        nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = sc_; nz.inputs['Detail'].default_value = 4
        L.new(mp.outputs[0], nz.inputs['Vector']); return nz.outputs['Fac']
    sh = streak(0.08, 3.0, 2.0); sv = streak(3.0, 0.08, 2.0)
    mx = N.new('ShaderNodeMath'); mx.operation = 'ADD'; L.new(sh, mx.inputs[0]); L.new(sv, mx.inputs[1])
    var = N.new('ShaderNodeMapRange'); var.inputs['From Min'].default_value = 0.6; var.inputs['From Max'].default_value = 1.4
    var.inputs['To Min'].default_value = 0.9; var.inputs['To Max'].default_value = 1.08
    L.new(mx.outputs[0], var.inputs['Value'])
    c1 = N.new('ShaderNodeMix'); c1.data_type = 'RGBA'; c1.blend_type = 'MULTIPLY'; c1.inputs['Factor'].default_value = 1
    L.new(base.outputs[0], c1.inputs[6]); L.new(var.outputs['Result'], c1.inputs[7])
    # seams darken
    def darken(col_out, fac_out, amt):
        mm = N.new('ShaderNodeMath'); mm.operation = 'MULTIPLY'; mm.inputs[1].default_value = amt
        L.new(fac_out, mm.inputs[0])
        mi = N.new('ShaderNodeMix'); mi.data_type = 'RGBA'; mi.blend_type = 'MIX'
        L.new(mm.outputs[0], mi.inputs['Factor']); L.new(col_out, mi.inputs[6])
        mi.inputs[7].default_value = (0, 0, 0, 1); return mi.outputs[2]
    c2 = darken(c1.outputs[2], sc.outputs['Red'], 0.30)
    c3 = darken(c2, sc.outputs['Green'], 0.55)
    c4 = darken(c3, sc.outputs['Blue'], 0.35)
    L.new(c4, bsdf.inputs['Base Color'])
    # fine weave bump
    nzf = N.new('ShaderNodeTexNoise'); nzf.inputs['Scale'].default_value = 6.0; nzf.inputs['Detail'].default_value = 8
    L.new(tc.outputs['Object'], nzf.inputs['Vector'])
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.18; bump.inputs['Distance'].default_value = 0.05
    L.new(nzf.outputs['Fac'], bump.inputs['Height']); L.new(bump.outputs[0], bsdf.inputs['Normal'])
    return m


def scene_setup():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
    sc.cycles.samples = 28; sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = 768, 1024
    sc.render.film_transparent = True
    sc.view_settings.view_transform = 'Standard'
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Color'].default_value = (1, 1, 1, 1)
    w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.42
    sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 3.0; sun.angle = math.radians(18)
    so = bpy.data.objects.new('sun', sun); sc.collection.objects.link(so)
    so.rotation_euler = (math.radians(-40), math.radians(-22), 0)
    cd = bpy.data.cameras.new('cam'); cd.type = 'ORTHO'; cd.clip_end = 1000
    cam = bpy.data.objects.new('cam', cd); sc.collection.objects.link(cam); sc.camera = cam
    bpy.ops.mesh.primitive_plane_add(size=2000, location=(0, 0, -1.3))
    pl = bpy.context.active_object; pl.name = 'catcher'; pl.is_shadow_catcher = True


scene_setup()
for key, g in G.items():
    sel = [w for w in WANT if w.split(':')[0] == key]
    if WANT and not sel:
        continue
    colors = [w.split(':')[1] for w in sel if ':' in w] or list(g['colors'].keys())
    mat = build(key, g)
    for c in colors:
        mat.node_tree.nodes['BASE'].outputs[0].default_value = hex_lin(g['colors'][c][1])
        bpy.context.scene.render.filepath = os.path.join(OUT, f'{key}__{c}.png')
        bpy.ops.render.render(write_still=True)
        print('RENDERED', key, c, flush=True)
