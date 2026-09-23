"""機体の ch1（呼び名の聞き分けに渡している音）を流しっぱなしで受けて wav に残す。
誤爆した瞬間の音を後から切り出すための道具。

  python tools/wakestream.py rec <秒> <出力フォルダ> [--dry]
      機体に wakestream on を送り、届いた音を <出力フォルダ>/full.wav（16kHz・16bit・モノラル）へ
      受けた端から書き足す。0.5 秒ごとに wav の長さも書き直すので、強制終了されても
      そこまでの音が残る（消えるのは最後の 0.5 秒だけ）。機体のログは log.txt に 1 行ずつ。
      越えた 5 秒後に wake<N>_<時刻>.wav をその場で切る（終了を待たない）。
      --dry を付けると wakedry on も送る。越えても機体は喋らず、サーバーにも繋がない
      （記録だけ残して見張りへ戻る）。流しっぱなしで誤爆を溜めるときはこれ。終わりに切る。

  python tools/wakestream.py stop <出力フォルダ>
      裏で回している rec を止める。強制終了しない止め方（rec は 0.3 秒以内に気づく）。

  python tools/wakestream.py cut <出力フォルダ> <時刻>... [--pm 5]
      full.wav から時刻（mm:ss か 秒）の前後 --pm 秒を切り出す。録っている最中でも切れる。

ポートは環境変数 KATANORI_PORT（既定 COM5）。DTR/RTS は触らない。
届かなかった行は行番号から分かるので、その部分は無音で埋めて時刻がずれないようにする。
"""
import os
import re
import signal
import struct
import sys
import time
import wave
from pathlib import Path

import numpy as np

RATE = 16000
ROW = 64  # 1 行のサンプル数（AudioIo::pumpWakeStream）
PORT = os.environ.get("KATANORI_PORT", "COM5")
PM = 5.0  # 起きた時刻の前後、何秒を切り出すか
WAKE_LINE = re.compile(r"\[WAKE\] [★☆]")  # 越えた 1 回につき 1 行だけ出る印
SYNC = 0.5  # 何秒ごとに wav の長さを書き直すか


def fmt(sec: float) -> str:
    return f"{int(sec // 60):02d}:{sec % 60:04.1f}"


def parse_time(s: str) -> float:
    if ":" in s:
        m, sec = s.split(":", 1)
        return int(m) * 60 + float(sec)
    return float(s)


class WavSink:
    """受けた端から書き足す wav。長さを定期的に書き直すので、途中で殺されても読める。

    書き直す長さは必ず本体をディスクに出した後の値にする。header が本体より長いと
    読み手が壊れた扱いにするので、ずれるなら短い側に倒す。
    """

    def __init__(self, path: Path, rate: int = RATE) -> None:
        self.f = open(path, "wb")
        self.rate = rate
        self.nbytes = 0  # 書き足した音のバイト数
        self.f.write(self._header(0))
        self.f.flush()

    def _header(self, n: int) -> bytes:
        return (b"RIFF" + struct.pack("<I", 36 + n) + b"WAVEfmt "
                + struct.pack("<IHHIIHH", 16, 1, 1, self.rate, self.rate * 2, 2, 16)
                + b"data" + struct.pack("<I", n))

    def write(self, a: np.ndarray) -> None:
        self.f.write(a.astype("<i2").tobytes())
        self.nbytes += len(a) * 2

    def sync(self) -> None:
        self.f.flush()  # 先に本体を出してから長さを書く
        end = self.f.tell()
        self.f.seek(0)
        self.f.write(self._header(self.nbytes))
        self.f.flush()
        self.f.seek(end)

    def close(self) -> None:
        self.sync()
        self.f.close()

    @property
    def seconds(self) -> float:
        return self.nbytes / 2 / self.rate


def write_wav(path: Path, a: np.ndarray) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(a.astype("<i2").tobytes())


def cut_one(out: Path, t: float, pm: float, i: int) -> Path:
    with wave.open(str(out / "full.wav")) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")
    s0 = max(0, int((t - pm) * RATE))
    s1 = min(len(a), int((t + pm) * RATE))
    f = out / f"wake{i}_{fmt(t).replace(':', 'm')}s.wav"
    write_wav(f, a[s0:s1])
    print(f"{f.name}  {fmt(s0 / RATE)}〜{fmt(s1 / RATE)}", flush=True)
    return f


def cut(out: Path, times: list[float], pm: float) -> None:
    for i, t in enumerate(times, 1):
        cut_one(out, t, pm, i)


def rec(seconds: float, out: Path, dry: bool = False) -> None:
    import serial

    out.mkdir(parents=True, exist_ok=True)
    stopFile = out / "STOP"
    if stopFile.exists():
        stopFile.unlink()

    stopped = {"v": False}

    def onSignal(sig, frame):  # Ctrl+C・taskkill（/F なし）でも綺麗に閉じる
        stopped["v"] = True

    for name in ("SIGINT", "SIGTERM", "SIGBREAK"):
        if hasattr(signal, name):
            try:
                signal.signal(getattr(signal, name), onSignal)
            except (ValueError, OSError):
                pass

    s = serial.Serial()
    s.port = PORT
    s.baudrate = 115200
    s.dtr = False
    s.rts = False
    s.timeout = 0.2
    s.open()
    time.sleep(0.2)
    s.reset_input_buffer()  # 開く前に溜まっていた古い行を捨てる（越えた行が混じると偽の切り出しになる）

    sink = WavSink(out / "full.wav")
    log = open(out / "log.txt", "w", encoding="utf-8")
    row0 = None
    nextRow = None
    dropped = 0
    wakes: list[float] = []
    pendingCut: list[float] = []
    t0 = time.time()
    lastShown = 0.0
    lastSync = 0.0
    lastStop = 0.0

    def pos_sec() -> float:
        return sink.seconds

    def flush_cuts(force: bool = False) -> None:
        for t in list(pendingCut):
            if force or sink.seconds >= t + PM:  # 後ろ 5 秒が溜まったら、その場で切る
                sink.sync()
                cut_one(out, t, PM, wakes.index(t) + 1)
                pendingCut.remove(t)

    if dry:
        s.write(b"wakedry on\n")  # 越えても会話へ進ませない（機体の main.cpp wakeDryRun）
        time.sleep(0.3)
    s.write(b"wakestream on\n")
    try:
        buf = b""
        lines: list[bytes] = []
        while time.time() - t0 < seconds and not stopped["v"]:
            now = time.time()
            if now - lastStop >= 0.3:  # 裏で回していても止められるように
                lastStop = now
                if stopFile.exists():
                    break
            if now - lastSync >= SYNC:
                lastSync = now
                sink.sync()
                flush_cuts()
            if not lines:
                # 1 バイトずつ読むと 250 行/秒に追いつかない（Windows）。まとめて読んで行に割る
                chunk = s.read(max(1, s.in_waiting))
                if not chunk:
                    continue
                buf += chunk
                parts = buf.split(b"\n")
                buf = parts.pop()
                lines = parts
                continue
            raw = lines.pop(0)
            line = raw.decode("utf-8", errors="replace").rstrip()
            m = re.match(r"WD (\d+) ([0-9a-f]{256})$", line)  # 壊れた行（欠け・つながり）は無視して穴にする
            if m:
                row = int(m.group(1))
                if row0 is None:
                    row0 = row
                    nextRow = row
                if row > nextRow:  # 届かなかった行は無音で埋める
                    dropped += row - nextRow
                    sink.write(np.zeros((row - nextRow) * ROW, dtype="<i2"))
                    nextRow = row
                if row == nextRow:
                    sink.write(np.frombuffer(bytes.fromhex(m.group(2)), dtype=">i2").astype("<i2"))
                    nextRow = row + 1
                continue
            print(f"[{fmt(pos_sec())}] {line}", file=log, flush=True)
            if line.startswith("WD SKIP"):
                continue
            # ★呼ばれました（ふだん）と ☆試し 越えました（wakedry 入）の両方。
            # 「眠っている間に呼ばれました」など、同じ 1 回に付いてくる他の行は拾わない
            if WAKE_LINE.match(line):
                t = pos_sec()
                wakes.append(t)
                pendingCut.append(t)
                print(f"  ★ {fmt(t)} 起きた（{line[line.find('確からしさ'):][:24]}）", flush=True)
            if now - lastShown >= 10:
                lastShown = now
                print(f"  録った {fmt(pos_sec())} / 実時間 {fmt(now - t0)}  行の欠け {dropped}", flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            s.write(b"wakestream off\n")
            time.sleep(0.3)
            if dry:
                s.write(b"wakedry off\n")  # 喋る機体に戻す（機体の再起動でも戻る）
                time.sleep(0.3)
        finally:
            s.close()
        flush_cuts(force=True)
        sink.close()
        log.close()
        if stopFile.exists():
            stopFile.unlink()
    print(f"full.wav {fmt(sink.seconds)} / 実時間 {fmt(time.time() - t0)}  行の欠け {dropped}"
          f"（1 行 {ROW / RATE * 1000:.0f}ms）  起きた {len(wakes)} 回")


def stop(out: Path) -> None:
    (out / "STOP").write_text("stop", encoding="utf-8")
    print("STOP を置きました。rec は 0.3 秒以内に止まります")


def main() -> None:
    try:  # ★ や 〜 を出すので、cp932 の窓・裏で回したときに落ちないようにする
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if len(sys.argv) < 3:
        print(__doc__)
        return
    if sys.argv[1] == "rec":
        args = sys.argv[2:]
        dry = "--dry" in args
        if dry:
            args.remove("--dry")
        rec(float(args[0]), Path(args[1]), dry)
    elif sys.argv[1] == "stop":
        stop(Path(sys.argv[2]))
    elif sys.argv[1] == "cut":
        args = sys.argv[3:]
        pm = PM
        if "--pm" in args:
            i = args.index("--pm")
            pm = float(args[i + 1])
            del args[i:i + 2]
        cut(Path(sys.argv[2]), [parse_time(t) for t in args], pm)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
