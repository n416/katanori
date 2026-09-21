"""機体のシリアルを読み続け、<接頭辞>.flag ができたら直近 40 秒の音を受け取る。
  python session.py <接頭辞>
機体の判定の行は <接頭辞>.log に、音は <接頭辞>_<入れ方>.wav に置く。

機体は d で「ためるのを止めて全行を送る」。行は "L <ch> <番号> <base64>"。
USB シリアルは行を黙って落とすので、欠けた・壊れた行は g <ch> <番号> で取り直す。
最後に u で機体を元に戻す。
"""
import base64, os, sys, time, wave
import serial

prefix = sys.argv[1]
flag = prefix + '.flag'
if os.path.exists(flag):
    os.remove(flag)
s = serial.Serial(); s.port = 'COM5'; s.baudrate = 115200; s.dtr = False; s.rts = False; s.timeout = 0.2
s.open()
log = open(prefix + '.log', 'w', encoding='utf-8')


def lines_iter(deadline):
    buf = b''
    while time.time() < deadline:
        raw = s.readline()
        if not raw:
            yield None
            continue
        buf += raw
        if not buf.endswith(b'\n'):
            continue
        yield buf.decode('utf-8', 'replace').strip()
        buf = b''


def take(line, got, nlines):
    parts = line.split(' ', 3)
    if len(parts) != 4 or parts[0] != 'L':
        return
    try:
        c, i = int(parts[1]), int(parts[2])
        pcm = base64.b64decode(parts[3], validate=True)
    except Exception:
        return
    # 最後の行以外は 1,500 サンプルちょうどのはず
    if i < nlines - 1 and len(pcm) != 3000:
        return
    got[(c, i)] = pcm


# 合図を待ちながら、機体の判定の行を残す
for line in lines_iter(time.time() + 3600):
    if line:
        log.write(time.strftime('%H:%M:%S ') + line + '\n'); log.flush()
    if os.path.exists(flag):
        break
s.write(b'd\n')

n = nlines = 0
rate = 16000
names, got = [], {}
for line in lines_iter(time.time() + 400):
    if line is None:
        continue
    if line.startswith('CAP '):
        _, n, nlines, rate, a, b = line.split()
        n, nlines, rate, names = int(n), int(nlines), int(rate), [a, b]
    elif line == 'CAPEND':
        break
    elif nlines:
        take(line, got, nlines)

missing = [(c, i) for c in range(2) for i in range(nlines) if (c, i) not in got]
first_missing = len(missing)
for attempt in range(5):
    if not missing:
        break
    for c, i in missing:
        s.write(f'g {c} {i}\n'.encode())
        for line in lines_iter(time.time() + 3):
            if line and line.startswith(f'L {c} {i} '):
                take(line, got, nlines)
                break
    missing = [(c, i) for c in range(2) for i in range(nlines) if (c, i) not in got]

s.write(b'u\n')
s.close()
log.close()
for c, nm in enumerate(names):
    pcm = b''.join(got.get((c, i), b'\0' * 3000) for i in range(nlines))
    with wave.open(f'{prefix}_{nm}.wav', 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(pcm)
print(f'done {n / rate:.1f}秒 {rate}Hz {nlines}行×2  欠けて取り直した {first_missing}  最後まで欠けた {len(missing)}')
