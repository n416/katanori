"""満充電から電池が切れるまで、機体の電池ログを Wi-Fi 越しに取り続ける（稼働時間の実測）。

  python batrun.py <出力.log> [間隔秒（既定 10）]

katanori.local の 23 番（Console.h）に繋ぎ、合言葉を送って `batreset`・`batlog <間隔>` を打ち、
流れてくる行すべてに PC の時刻を付けて書く。切れたら 5 秒おきに繋ぎ直す。
電池が切れると機体は戻らないので、ログの最後の [BAT] 行の時刻が終わりの時刻になる。
Ctrl+C で止める。機体の設定は変えない（眠らないようにするのは機体のメニューで）。
"""
import socket, sys, time, datetime
sys.stdout.reconfigure(encoding="utf-8")

HOST, PORT, PASS = "katanori.local", 23, "katanori"   # 合言葉は platformio.ini の --auth と同じ
out = sys.argv[1]
every = int(sys.argv[2]) if len(sys.argv) > 2 else 10
first = True

def stamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

with open(out, "a", encoding="utf-8") as f:
    def note(msg):
        line = f"{stamp()} {msg}"
        print(line, flush=True); f.write(line + "\n"); f.flush()

    note(f"# 開始 間隔 {every} 秒")
    while True:
        try:
            s = socket.create_connection((HOST, PORT), timeout=10)
            s.settimeout(120)   # 間隔の 10 倍以上なにも来なければ切れたとみなす
            s.sendall((PASS + "\n").encode())
            time.sleep(1)
            if first:
                s.sendall(b"batreset\n")   # 積算 mAh を 0 から
                first = False
            s.sendall(f"batlog {every}\nbat\ncfg\n".encode())   # cfg: 眠るまでの時間を控えに残す
            note("# 繋がった")
            buf = b""
            while True:
                d = s.recv(4096)
                if not d:
                    raise ConnectionError("相手が閉じた")
                buf += d.replace(b"\xff", b"")
                *lines, buf = buf.split(b"\n")
                for l in lines:
                    t = l.decode("utf-8", "replace").strip()
                    if t:
                        note(t)
        except KeyboardInterrupt:
            note("# 止めた")
            break
        except Exception as e:
            note(f"# 切れた: {e}")
            time.sleep(5)
