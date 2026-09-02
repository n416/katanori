# 実機のシリアルを読み続けてログに落とし、コマンドも送れるようにする道具。
#
#   python firmware/serlog.py
#
# ・COM4 を 115200 で開く（ポートが無いあいだは待って、挿さったら勝手に開く）
# ・読んだ行は同じフォルダの serial.log へ時刻付きで追記
# ・同じフォルダに cmd.txt を置くと、その中身を1行送って消す（`s` `creg` `beep` など）
#
# 2026-09-02 の動作チェックで使った。抜き差しの多い作業でも落ちない。
import serial, time, pathlib
D = pathlib.Path(__file__).parent
LOG = D / "serial.log"
CMD = D / "cmd.txt"

def stamp():
    return time.strftime("%H:%M:%S")

with open(LOG, "a", encoding="utf-8", errors="replace", buffering=1) as f:
    while True:
        try:
            ser = serial.Serial()
            ser.port, ser.baudrate, ser.timeout = "COM4", 115200, 0.2
            ser.dtr = False          # 勝手にリセット/書き込みモードにしない
            ser.rts = False
            ser.open()
            ser.dtr = False
            ser.rts = False
        except Exception:
            time.sleep(1.0)
            continue
        f.write("==== %s ポートを開きました ====\n" % stamp())
        buf = b""
        try:
            while True:
                if CMD.exists():
                    c = CMD.read_text(encoding="utf-8").strip()
                    CMD.unlink()
                    ser.write((c + "\n").encode())
                    f.write(">>> %s を送りました\n" % c)
                n = ser.in_waiting
                data = ser.read(n if n else 1)
                if data:
                    buf += data
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        f.write("%s %s\n" % (stamp(), line.decode("utf-8", "replace").rstrip("\r")))
                else:
                    time.sleep(0.05)
        except Exception as e:
            f.write("==== %s 切れました (%s) ====\n" % (stamp(), type(e).__name__))
            try:
                ser.close()
            except Exception:
                pass
            time.sleep(1.0)
