"""カタノリ実機へシリアルコマンドを投げて出力を取る。

`pio device monitor` と違って対話が要らないので、決まった手順を流して結果を
持ち帰るのに使う。行頭に経過秒が付くため、「どの操作の何秒後に何が起きたか」を
後から突き合わせられる（つまみを回しながらコーデックの生死を見る、等）。

  python ser.py <待ち秒> <コマンド...>
  python ser.py 3 knob creg          # 各コマンドの後に3秒ぶん読む
  python ser.py 300                  # コマンド無し = 5分間ただ監視する

ポートは環境変数 KATANORI_PORT で指定する（既定 COM4）。`pio device list` で確認:

  KATANORI_PORT=COM7 python ser.py 3 creg

pyserial が要る。PlatformIO の Python には入っているので、素の python に無ければ
そちらを使う（パスは `pio system info` で分かる）。

DTR/RTS は触らない（触るとESP32がリセットされる。platformio.ini と同じ方針）。
`pio device monitor` と同時には使えない。ポートは同時に1つしか掴めない。
"""
import os
import sys
import time

import serial

PORT = os.environ.get("KATANORI_PORT", "COM4")
BAUD = 115200


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    wait = float(sys.argv[1])
    cmds = sys.argv[2:]

    s = serial.Serial()
    s.port = PORT
    s.baudrate = BAUD
    s.timeout = 0.2
    s.dtr = False
    s.rts = False
    s.open()
    time.sleep(0.3)
    s.reset_input_buffer()

    t0 = time.time()

    def pump(until):
        """経過秒つきで読み流す。行頭に [+12.3s] を付ける。"""
        buf = ""
        while time.time() < until:
            data = s.read(4096)
            if not data:
                continue
            buf += data.decode("utf-8", "replace")
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                print(f"[+{time.time() - t0:5.1f}s] {line.rstrip()}", flush=True)

    if not cmds:
        # コマンド無し = ただの監視モード（配線を触りながらログを見る用）
        pump(t0 + wait)
    else:
        for c in cmds:
            s.write((c + "\n").encode())
            s.flush()
            print(f"===== >>> {c}", flush=True)
            pump(time.time() + wait)
    s.close()


if __name__ == "__main__":
    main()
