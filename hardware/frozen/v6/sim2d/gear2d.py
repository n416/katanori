# -*- coding: utf-8 -*-
"""v6 の歯車 3 枚を **2 次元**の物理で回す。
   🔴 MuJoCo（3 次元）では歯どうしの接触が解けなかった（docs/MECH-V6-REQ.md 末尾）。
      この機構は歯車 3 枚が同じ平面で噛むだけなので、2 次元で足りる。
   歯形は hardware/frozen/v6/_v6_gear.scad と同じ式。歯は**中心線で 2 つに割る**（凸包の太り 0.0000）。
   つまみ = 動かす物（kinematic）／ 中継・読み取り = 押される物（dynamic）。
"""
import math, pymunk, numpy as np, imageio.v2 as iio
from PIL import Image, ImageDraw

M, PA, THIN, ADD, DED, SEG = 0.5, 20.0, 0.12, 0.85, 1.25, 8
KN_C, IDLER, SENS = (24.0, 30.04), (33.003, 21.3684), (38.2, 10.0)
NK, NI = 28, 22
d2r = math.radians
def invd(a): return math.tan(d2r(a))*180/math.pi - a
def rp(z): return M*z/2
def rb(z): return rp(z)*math.cos(d2r(PA))
def ra(z): return rp(z)+M*ADD
def rf(z): return rp(z)-M*DED
def half(z): return (M*math.pi/2-THIN)/(2*rp(z))*180/math.pi + invd(PA)
def flank(z,i):
    r0=max(rb(z),rf(z)); r=r0+(ra(z)-r0)*i/SEG
    a=half(z)-invd(math.degrees(math.acos(rb(z)/r)))
    return (r*math.cos(d2r(a)), r*math.sin(d2r(a)))
def half_tooth(z, side):
    F=[flank(z,i) for i in range(SEG+1)]
    return [(F[0][0],0.0),(F[-1][0],0.0)]+[(x,side*y) for (x,y) in F]
def rot(p,a):
    c,s=math.cos(d2r(a)),math.sin(d2r(a)); return [(x*c-y*s, x*s+y*c) for (x,y) in p]
def mesh_rot(rA,zA,zB,th): return (th+180)-(rA-th)*zA/zB+180.0/zB
TH_KI=math.degrees(math.atan2(IDLER[1]-KN_C[1], IDLER[0]-KN_C[0]))
TH_IS=math.degrees(math.atan2(SENS[1]-IDLER[1], SENS[0]-IDLER[0]))
ROT_K=0.0; ROT_I=mesh_rot(ROT_K,NK,NI,TH_KI); ROT_S=mesh_rot(ROT_I,NI,NK,TH_IS)

sp = pymunk.Space(); sp.gravity=(0,0); sp.iterations=60
def make(c, z, phase, kinematic, ctype):
    m = 0.0003*math.pi*ra(z)**2
    if kinematic:
        b = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    else:
        b = pymunk.Body(m, 0.5*m*ra(z)**2)
    b.position = c; b.angle = 0.0
    shapes=[pymunk.Circle(b, rf(z))]
    for k in range(z):
        a = phase + k*360.0/z
        for side in (+1,-1):
            shapes.append(pymunk.Poly(b, rot(half_tooth(z,side), a)))
    for s in shapes:
        s.friction=0.05; s.elasticity=0.0; s.collision_type=ctype
        s.filter = pymunk.ShapeFilter(categories=1<<ctype, mask=(1<<(ctype-1))|(1<<(ctype+1)))
    sp.add(b, *shapes)
    if not kinematic: sp.add(pymunk.PivotJoint(sp.static_body, b, c))
    return b, shapes
knob, s_k = make(KN_C,  NK, ROT_K, True,  2)
idl,  s_i = make(IDLER, NI, ROT_I, False, 3)
sen,  s_s = make(SENS,  NK, ROT_S, False, 4)
for b in (idl, sen): b.angular_velocity = 0.0

DT = 1/6000.0
SWING = d2r(160.0); T = 1.2
W, H = 660, 700
X0, X1, Y0, Y1 = 8.0, 48.0, -2.0, 48.0
SC = W/(X1-X0)
def px(p): return (int((p[0]-X0)*SC), int(H - (p[1]-Y0)*SC))
frames, log = [], []
def draw(t):
    im = Image.new("RGB", (W, H), (253, 253, 245)); dr = ImageDraw.Draw(im)
    for (b, ss, col) in ((knob, s_k, (63,114,176)), (idl, s_i, (224,128,48)), (sen, s_s, (63,160,85))):
        for s_ in ss:
            if isinstance(s_, pymunk.Circle):
                c = px((b.position.x, b.position.y)); r = int(s_.radius*SC)
                dr.ellipse([c[0]-r, c[1]-r, c[0]+r, c[1]+r], fill=col)
            else:
                pts = [b.local_to_world(v) for v in s_.get_vertices()]
                dr.polygon([px((p.x, p.y)) for p in pts], fill=col)
        a = b.angle
        dr.line([px((b.position.x, b.position.y)),
                 px((b.position.x + ra(NK)*math.cos(a), b.position.y + ra(NK)*math.sin(a)))],
                fill=(208,52,44), width=5)
    dr.text((12, 10), "t=%.2fs   knob %7.1f   idler %7.1f   sensor %7.1f"
            % (t, math.degrees(knob.angle), math.degrees(idl.angle), math.degrees(sen.angle)),
            fill=(30,30,30))
    return __import__("numpy").asarray(im)

n=int(2*T/DT)
for i in range(n):
    t=i*DT
    knob.angular_velocity = (SWING/T) if t<T else -(SWING/T)
    sp.step(DT)
    idl.angular_velocity *= 0.9995; sen.angular_velocity *= 0.9995
    if i % int(0.02/DT) == 0:
        frames.append(draw(t))
        log.append((t, math.degrees(knob.angle), math.degrees(idl.angle), math.degrees(sen.angle)))
iio.mimsave("gear2d.gif", frames, duration=0.05, loop=0)
print("  frames %d -> gear2d.gif" % len(frames))
print("  %-7s %-9s %-10s %-10s %-9s %-9s" % ("t","つまみ","中継","読み取り","中継/つ","読/つ"))
for t,a,b,c in log[::max(1,len(log)//10)]:
    f=lambda v:(v/a) if abs(a)>2 else float('nan')
    print("  %-7.2f %-9.2f %-10.2f %-10.2f %-9.4f %-9.4f" % (t,a,b,c,f(b),f(c)))
pk=max(log,key=lambda l:abs(l[1]))
print("  --- 振り切り: つまみ %.2f / 中継 %.2f / 読み取り %.2f" % (pk[1],pk[2],pk[3]))
print("      比 中継 %.4f（理論 -1.2727）／ 読み取り %.4f（理論 +1.0000）" % (pk[2]/pk[1], pk[3]/pk[1]))
print("  --- 戻り: つまみ %.2f / 読み取り %.2f ⇒ 差 %.3f 度" % (log[-1][1],log[-1][3],log[-1][3]-log[-1][1]))
