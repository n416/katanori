# 入れる道の当たり検査と動画 — コマンド集

なぜこの形かは [COLLISION-SURVEY.md](COLLISION-SURVEY.md)。ここは**回し方だけ**。

```
case_v6_1.scad          形と道（PATH_*）の出どころ。ここは触らずに使う
  └ tools/_sweep_v61.scad   呼び出し口（動かす物・相手・1 姿勢の交わり・道の一覧）
       ├ tools/sweep_chk.py      距離で道を走り、当たりを出す   → _tmp_sweep/<key>.json
       │    └ sweep_accept.json    了承済みの当たりの台帳
       └ tools/sweep_movie.py    動画を焼く                     → _tmp_sweep/<key>.mp4
            └ tools/_sweep_blender.py   Blender の中で動く側
```

**検査の道は 6 本**: `hub` `rsp` `oled` `bat` `lidmain` `lidflap`
**動画の場面は 5 つ**: `hub` `rsp` `oled` `bat` `lid`

蓋は**たわむので検査は 2 つの剛体**（`lidmain` 天板・`lidflap` 左の板）に分けるが、
🔒 ユーザー 2026-09-18「天板と左壁はつながっています」── **実物は 1 つの部品**なので、
**動画では `lid` という 1 つの場面に 2 つを同時に出す**。左の板だけを飛ばすのは嘘の絵になる。

---

## 1. 検査

6 本とも回す（48 秒ほど）。**新しい当たりがあれば終了コード 1。**

```bash
python hardware/tools/sweep_chk.py
```

1 本だけ。

```bash
python hardware/tools/sweep_chk.py bat
```

読み方:

- `済` … `hardware/sweep_accept.json` の台帳に載っている当たり（前に見て了承した物）
- `新` … 台帳に無い当たり。**見て判断する物はこれだけ**
- `めり込み無し` … 触れているのは同一平面の皮だけ（板が柱の頭に載る面など）
- `最小隙間 0.000` は「当たっている」ではなく「**触れている**」。皮かどうかは厚みで分ける

## 2. 動画

5 場面とも焼く（1 つ 1〜2 分）。

```bash
python hardware/tools/sweep_movie.py
```

1 つだけ（蓋は `lid`）。

```bash
python hardware/tools/sweep_movie.py lid
```

**覗き見**（3 枚だけ焼く・十数秒）。頭 / 座った所 / 交わりだけ、の 3 枚が出る。
⚠ **焼いたら必ずこれで「物が動いているか」を目で見ること**（動かない絵の上で色と数字だけが変わる事故を起こした）。

```bash
python hardware/tools/sweep_movie.py bat --peek
```

絵の読み方:

| 色 | 意味 |
|---|---|
| 青 | **問題なし**（空いている・面で触れているだけ、の両方） |
| 赤 | **めり込んでいる** |

⚠ **色は 2 色しかない。** 皮で触れているだけの所を黄色にしていた頃は、
`lidflap` が道の全域で触れているために最初から最後まで黄色になり、「入らない」と読めてしまった
（🔒 ユーザー 2026-09-18）。触れていることは焼き込みの文字（`touch`）に残す。
交わりを見せるコマでは:

| | |
|---|---|
| 明るい赤の塊 | その姿勢の**交わりそのもの**（OpenSCAD で厳密に取った形） |
| 赤い針金の枠 | いちばん深い塊の場所（小さい当たりを見つけるため） |
| 消えるのは当たっている物だけ | 場面に物が 2 つあるとき、相手（天板など）は残る |

コマの並びは 3 つ:

1. **入れる**（道のとおり動く）
2. 当たりがあれば、**いちばん深い所で止めて動く物を消し、交わりだけ**を見せる（0.8 秒）
3. **組み上がった姿勢に戻して 2.5 秒止める**（🔒 ユーザー 2026-09-18「組み立て完了の状態で数秒維持してほしい」）

焼き込みの文字は `s`（道のどこか）・`gap`（隙間 mm）・`HIT t=…mm V=…mm3`・`>> assembled`。

### 節目のものを残す

`docs/_img/sweep/<日付>/` に動画と README（そのときの判定の表）を残す。

```bash
python hardware/tools/sweep_movie.py --save
```

名前を自分で付けるなら:

```bash
python hardware/tools/sweep_movie.py --save=v61n-発注前
```

⚠ `hardware/_tmp_sweep/` は git に入らない（作業場・焼き直すと上書き・別の PC には行かない）。
**残すと決めた物だけ** `--save` で `docs/_img/sweep/` へ移す。

## 3. 出る物の場所

`hardware/_tmp_sweep/`（git には入れない）

| | |
|---|---|
| `<key>.mp4` | 動画 |
| `<key>.json` | 検査の全部（姿勢ごとの隙間・厳密評価・済/新の分類） |
| `<key>_frames/f*.png` | 動画のコマ |
| `<key>_mover.off` / `_world.off` | 動かす物と相手（OpenSCAD から 1 回だけ出した物） |
| `<key>_hit*.off` | 接触した姿勢の交わりの形 |

残すと決めた物は `docs/_img/sweep/<日付>/`（こちらは git に入る）。

## 4. 新しい当たりが出たとき

1. 動画で見る → `python hardware/tools/sweep_movie.py <場面>`（蓋なら `lid`）
2. 直すなら `case_v6_1.scad` の形か `PATH_*` を直して、1 に戻る
3. 「これでよい」と判じるなら、`sweep_chk.py` が出した雛形に**理由を書いて**
   `hardware/sweep_accept.json` の `accept` に足す

```json
{ "id": "bat-guide-ring-low", "key": "bat",
  "why": "bat_guide_ring を電池が乗り越えるぶん。🔒 ユーザー「電池は膨らみますし、隙間は多少あっても良い」",
  "box": [[14.6, 9.4, 0.0], [18.1, 45.4, 1.7]], "thick": 0.75, "since": "2026-09-17" }
```

`why` の 🔒 は**ユーザーが決めた物**、無印は担当の判断。ここを空のまま足さない。
形を動かして当たりの場所が `box` から出たら、また「新」として鳴る。それが狙い。

## 5. 道を直す・足す

道（通過点）は `case_v6_1.scad` の `PATH_HUB` / `PATH_RSP` / `PATH_OLED` / `PATH_BAT` /
`PATH_LIDMAIN` / `PATH_LIDFLAP`。**ここが唯一の出どころ**で、検査も動画もここを読む。
1 点は `[dx, dy, dz, rx, ry, rz]`（移動 3 つ ＋ 回し 3 つ・度）。

道を 1 本足すには 3 か所:

1. `case_v6_1.scad` に `PATH_<名前>` を書く
2. `tools/_sweep_v61.scad` の `sw_mover()` に「動かす物」、`sw_world()` に「そのとき箱に居る物」を足す
3. 同じファイルの `SW_MODE == "pose"` の並びに `["<名前>", PATH_<名前>, 回す中心, 端までの長さ]` を足す

回す道なら**回す中心 `c` と、中心から端までの長さ `r` を必ず渡す**
（`c` の既定は世界の原点なので、傾けると物が遠くへ飛ぶ。`r` は刻みを出すのに要る）。

たわむ物は **2 つの剛体に分けて別々に当てる**（蓋がその例。`lidmain` と `lidflap`）。

## 6. つまみ

`hardware/tools/sweep_chk.py`

| | 既定 | 何 |
|---|---|---|
| `TOL` | 0.05 | これ以下の隙間は「接触」として扱う（clash tolerance） |
| `SKIN_T` | 0.01 | 厚みがこれ未満なら同一平面の皮 ＝ めり込みではない |
| `EXACT_MOVE` | 0.30 | 接触区間の中で厳密な交わりを取る間隔 mm |
| `EXACT_MAX` | 12 | 1 区間あたりの厳密評価の上限（重くしないため） |
| `MIN_MOVE` | 0.02 | 接触区間で 1 歩に進む距離 mm |

⚠ **刻みの定数は無い。** 空いている距離から自動で出す（Conservative Advancement）。
広い所は 1 歩で飛び、狭い所だけ細かくなる。

`hardware/tools/sweep_movie.py`

| | 既定 | 何 |
|---|---|---|
| `MM_PER_FRAME` | 0.5 | 1 コマで物が動く距離 mm |
| `FPS` | 24 | |
| `HOLD_HIT` | 20 | いちばん深い所で止めるコマ数（ここで動く物を消す） |
| `HOLD_END` | 60 | 組み上がった姿勢で止めるコマ数（2.5 秒）。**動画はここで終わる** |

## 7. 要る物 / 場所が違う PC で

```bash
pip install trimesh python-fcl
```

OpenSCAD・Blender・ffmpeg は入っている物を使う。場所が違う PC では環境変数で上書きする。

bash（Git Bash）なら:

```bash
OPENSCAD="C:/Program Files/OpenSCAD/openscad.exe" python hardware/tools/sweep_chk.py
```

PowerShell なら:

```powershell
$env:OPENSCAD = "C:\Program Files\OpenSCAD\openscad.exe"; python hardware/tools/sweep_chk.py
```

| 環境変数 | 既定 |
|---|---|
| `OPENSCAD` | `C:\Program Files\OpenSCAD (Nightly)\openscad.exe` |
| `BLENDER` | `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe` |
| `FFMPEG` | `ffmpeg`（PATH から） |

## 8. 困ったとき

| 症状 | 見る所 |
|---|---|
| 動画で物が動かない | `matrix_world` に素の配列を入れると列として読まれる。`mathutils.Matrix()` で包む。まず `--peek` で確かめる |
| 動く物が箱の面の裏に消える | EEVEE の半透明どうしは前後関係が壊れる。半透明は箱だけにする |
| 針金の枠が中身の詰まった箱に見える | Wireframe は物を拡大する前に効く。`scale` で大きくしない（頂点を書く） |
| 箱が画面から出る | `ortho_scale` は横に効く。16:9 では縦が先に切れる（外接箱の 8 隅で合わせている） |
| `<key>.json が無い` | 先に `sweep_chk.py <key>` を回す |
| 検査が遅い | 厳密評価の回数（`EXACT_MAX`）を減らす。距離で走る所は 1 本 2〜5 秒しか掛かっていない |

## 9. まだ手を付けていない

🔴 **この道具はナイロン（MJF）しか見ていない。** `-D MAT=` を渡していないので、
`case_v6_1.scad` の既定（`MAT = "nylon"`）のまま回っている。
6 本の道もナイロンの入れ方（左の窓から差して右へ滑らせる／蓋を真上から降ろす）で、
板 6 枚のレジンの組み立てを表していない。

🔒 ユーザー 2026-09-15「レジン版とナイロン版はスイッチできるわけで、それに応じてアラートを分けて」
── `_stl_preflight.py` の `--mat` と `stl_v61n.py` の `--resin-check` はこれに従っているが、
**この道具だけが従っていない**。レジンの道を書くところから要る（2026-09-18 時点で未着手）。

---

**静止の当たり**（組み上がった状態）は別の道具:

```bash
python hardware/tools/stl_v61n.py --check
```
