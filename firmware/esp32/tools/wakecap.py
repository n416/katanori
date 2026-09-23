"""機体（COM5）の ch1（呼び名の聞き分けに渡している音）を、倍率を掛ける前の音で取り出して WAV にする。

  python wakecap.py <出力.wav> <秒数（30 まで）>

手順: 今の倍率を読む → wakegain 1（16 倍する前の音にする）→ 秒数だけ待つ（この間に呼ぶ）
→ wakedump でその区間だけを取り出す → 倍率を元に戻す。
DTR/RTS は触らない（触ると機体がリセットされ、スピーカーが轟音を出す）。
"""
import os, re, sys, time, wave
import numpy as np, serial

out, length = sys.argv[1], min(float(sys.argv[2]), 29.0)
s = serial.Serial(); s.port = "COM5"; s.baudrate = 115200; s.timeout = 0.2; s.dtr = False; s.rts = False
s.open(); time.sleep(0.3); s.reset_input_buffer()

def cmd(c, until=None, wait=1.5):
    s.write((c + "\n").encode()); t = time.time(); buf = b""; lines = []
    while time.time() - t < wait or (until and not any(until in l for l in lines)):
        d = s.read(65536)
        if d:
            buf += d
            *done, buf = buf.split(b"\n"); lines += [x.decode("utf-8", "replace").strip() for x in done]
        if until and any(until in l for l in lines): break
        if time.time() - t > 120: break
    return lines

g = [l for l in cmd("wakegain") if "[WAKE]" in l]
orig = int(re.search(r"(\d+) 倍", g[-1]).group(1)) if g else 16
print("今の倍率:", orig)
try:
    print([l for l in cmd("wakegain 1") if "[WAKE]" in l])
    # 倍率を 1 にした後の音だけを取る（控えには 16 倍した前の音も残っている）
    print(f"\n>>> 今から {length:g} 秒の間に、機体に向かって「ワラビモチ」と普段どおり 4 回呼んでください（間を 3〜4 秒あける）\n", flush=True)
    t1 = time.time()
    while time.time() - t1 < length:
        left = length - (time.time() - t1)
        print(f"   残り {left:4.0f} 秒", flush=True); time.sleep(min(5, max(0.1, left)))
    print(">>> おしまい。取り出します", flush=True)
    t0 = time.time()
    lines = cmd(f"wakedump {length:g} {length:g}", until="WD END", wait=0)
    print(f"吐き出し {time.time()-t0:.1f} 秒")
finally:
    print([l for l in cmd(f"wakegain {orig}") if "[WAKE]" in l])
    s.close()

rows = {}
for l in lines:
    m = re.match(r"WD (\d{5}) ([0-9a-f]+)$", l)
    if m:
        h = m.group(2); rows[int(m.group(1))] = [int(h[i:i+4], 16) for i in range(0, len(h), 4)]
end = [l for l in lines if l.startswith("WD END")]
n_exp = int(end[0].split()[2]) if end else None
missing = [i for i in range(n_exp or 0) if i not in rows]
a = np.array([v for i in sorted(rows) for v in rows[i]], dtype=np.uint16).view(np.int16)
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
with wave.open(out, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(a.tobytes())
print(f"{len(rows)}/{n_exp} 行・欠け {len(missing)} 行 → {len(a)/16000:.2f} 秒・ピーク {np.abs(a.astype(int)).max()}・RMS {np.sqrt((a.astype(float)**2).mean()):.1f} → {out}")
