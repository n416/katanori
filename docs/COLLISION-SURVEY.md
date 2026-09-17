# 当たり判定の作り方 — 世の中の手 (2026-09-17 調べ)

## 0. いま何が起きているか

`case_v6_1.scad` の `sweep_pose()` は、**姿勢を n 個置いて `union` し、世界との `intersection` の体積を測る**。
これは CSG のブーリアンなので、姿勢を細かくするほど面数が線形に増え、CGAL / Manifold の計算量はそれ以上に増える。

- `PATH_HUB` の道のり ≒ 100mm。`SWEEP_STEP = 0.25` なら 400 姿勢。
  回しを入れると `hub_r() = 45.7` なので 10° で弧 8mm ＝ さらに 32 姿勢。
- `hub_unit()` は板＋部品で数千面。**400 倍して数百万面**を 1 つのソリッドに合体させようとする。
  → 2026-09-17 夜、PC が固まった。**道具の使い方が世の中と違う**のであって、PC が非力なのではない。

そして刻みを粗くすると、今度は**姿勢と姿勢のあいだを見ていない**（すり抜け＝見落とし）。
「誤報か、重すぎるか」の板挟みは、**この方式を採っている限り原理的に解けない**。

---

## 1. 世の中は「ブーリアンを取らない」

交わりの**体積を作る**のは、CAD の当たり判定では誰もやっていない。標準は次の 3 つ。

### A. 距離クエリ（BVH）— 実務の本命

三角形を BVH（木）に入れて、**2 つの物の最短距離／めり込み深さを mm で返す**。形は作らない。

| ライブラリ | 出来ること | 入手 |
|---|---|---|
| **FCL**（Flexible Collision Library） | 当たり判定・最短距離・連続当たり判定（CCD）。ROS / MoveIt の標準 | `pip install python-fcl` — **cp312 の Windows wheel あり**（0.7.0.11, 2026-04-08） |
| **trimesh** | STL 読み・`CollisionManager`（中身は FCL）・`min_distance_single()` | `pip install trimesh` (5.1.0) |
| **MeshLib** | 厳密ブーリアン・当たり三角形の列挙・SDF | `pip install meshlib` — Windows wheel あり（3.1.4, 2026-09-16） |
| Bullet / Coal(hpp-fcl) | 同上。ゲーム・ロボットの現場 | — |

速さの桁が違う。**1 姿勢 1 ペアあたりミリ秒**なので、450 姿勢 × 数十ペアでも 1 秒程度。
いまの「体積を作る」やり方とは、比べる土俵が違う。

### B. 刻みを決め打ちにしない — Conservative Advancement

CCD の定石。**「いま d mm 空いている。物の最大点速度が v なら、d/v だけ進んでも絶対に当たらない」**
と保証しながら進む。だから:

- 広い所は 1 歩で飛ばす（速い）
- 狭い所だけ勝手に細かくなる（すり抜けない）
- **`SWEEP_STEP` という定数が要らなくなる。**「0.25 か 1.5 か」を人が選ぶ問題が消える

回しがあっても使える。論文は C2A（Tang et al. 2009, ICRA）。速度で 1〜28 倍。

### C. 掃引体そのものを作る — 研究の領域

- Sellán, Aigerman, Jacobson "Swept Volumes via Spacetime Numerical Continuation"（SIGGRAPH 2021）。
  陰関数で 4D 時空に持ち上げて掃引体の等値面を追う。MIT ライセンスのコードあり（ただし Adobe が特許出願中）。
- "Implicit Swept Volume SDF"（2024, arXiv 2405.00362）。
- **どれも「union して hull を取る」より 1 桁速い**と主張している時点で、いまのやり方が土俵外だと分かる。
  設計の検査では**掃引体は作らない**のが普通。

> `hull()` で姿勢を繋ぐと凹みが埋まる（`path_lid` 0.07 → 21327mm³）のは既に踏んだ通り。
> 厳密には Minkowski だが遅すぎる。**これは「掃引体を作ろうとしたから」起きる問題で、A + B なら起きない。**

---

## 2. 誤報を消す実務の手

### (a) しきい値（clash tolerance）を持つ ── 体積でなく**深さ**で判定する

業界のクラッシュ検出は、**0 か非 0 か**では判定しない。

- 0.05mm 程度の penetration threshold を置いて、意図した接触（嵌め合い・パッキン・面接触）を落とす。
  これをやらないと報告が誤報で埋まる、というのが BIM / CAD 双方の定説。
- SolidWorks の干渉認識にも「一致を干渉として扱う」の切り替えがある。

いまの `0 が正` は、この意味で**世の中より厳しい判定**をしている。
体積 5mm³ は「深さ 0.01mm × 面積 500mm²」かもしれないし「深さ 2mm × 面積 2.5mm²」かもしれない。
**前者は誤報、後者は入らない。体積は両者を区別できない。**

### (b) 当たり用の形を、見せる形と分ける（collision proxy）

ゲーム・ロボットの世界では、**表示メッシュで当たりを取らない**のが常識。
凸分解（V-HACD）や箱・カプセルの代理形を持つ。理由は速さと、三角形分割由来の誤報を避けるため。

**OpenSCAD 特有の誤報源**: `circle()` は多角形が円に**内接**する。
つまり `$fn=48` の穴は真円より小さく、柱は真円より細い。
→ ぴったりの嵌め合いが**必ず当たる**（誤報）。
逃げの要る穴は `r / cos(180/$fn)` で外接させるのが定石。
`katanori-spk-fn-and-wedge` で踏んだ薄肉と同じ根っこ。

### (c) 模型の忠実さ

`PCB_PARTS` が 55 個中 9 個しかない件（[katanori-model-fidelity]）は、
**誤報の裏返しの見落とし**。距離クエリに移せば 55 個入れても速さは問題にならない。

---

## 3. 成果物が「動画」なのも、世の中の標準

SolidWorks の Motion Study の *Find Interferences Over Time* は、まさにこの形をしている。

- アニメーションを再生しながら、**フレームごと**に干渉を探す
- 結果は一覧表: **フレーム番号・時刻・当たった部品の組・干渉の体積**
- その行をクリックするとそのフレームへ飛ぶ

Navisworks の Clash Detective も同じ（当たった場所へ視点を飛ばす）。
つまり実務の成果物は「**動画** ＋ **当たった区間の表**」がセットで、
数字だけ・絵だけでは判定しない。ユーザーの直感は業界の作法と一致している。

### 我々の環境で作れる物

| 部品 | 状態 |
|---|---|
| ffmpeg | `C:\ffmpeg\bin\ffmpeg` にあり |
| Blender | 5.2 導入済み（`C:\Program Files\Blender Foundation`） |
| OpenSCAD | `C:\Program Files\OpenSCAD (Nightly)\openscad.exe` |
| Python | 3.12.10 / numpy 1.26.4（trimesh・fcl は未導入） |

- **OpenSCAD の `--animate N`**: `$t` を 0→1 に振って PNG を連番で吐く → ffmpeg で mp4。手軽だが、
  フレームごとに CSG を評価するので、部品数が多いと重い。
- **Blender**: STL を一度だけ出して、姿勢を Python で振る。描画は毎フレーム数十 ms。
  **当たった区間だけ赤く塗る**・めり込み量を字幕に焼く、が自然にできる。こちらが本命。

---

## 4. 作った物（2026-09-17）

形を作るのは OpenSCAD のまま、**判定と動画だけ外に出した**。

| ファイル | 役目 |
|---|---|
| `hardware/tools/_sweep_v61.scad` | 呼び出し口。`SW_MODE="mover"/"world"/"hit"/"pose"`。`case_v6_1.scad` は触らない |
| `hardware/tools/sweep_chk.py` | 距離クエリで道を走り、接触区間の中だけ厳密な交わりを取る |
| `hardware/tools/sweep_movie.py` | Blender で動画を焼く（青＝空き／黄＝接触／赤＝めり込み） |
| `hardware/tools/_sweep_blender.py` | Blender の中で動く側 |

```
python hardware/tools/sweep_chk.py hub rsp oled bat
python hardware/tools/sweep_movie.py bat
```

### 旧検査との突き合わせ（2026-09-17）

| 道 | 旧（OpenSCAD の掃引） | 新（距離＋厳密） | 一致 |
|---|---|---|---|
| `path_hub` | 0.00 mm³ | 厚み 0.000 mm（皮）→ 入る | ✅ |
| `path_rsp` | 0.00 mm³ | 厚み 0.000 mm（皮）→ 入る | ✅ |
| `path_oled` | **0.51 mm³** | 0.512 mm³・厚み 0.400 mm・1.6×0.8×0.4 @ s=0.898 | ✅ |
| `path_bat` | **86.82 mm³** | 86.818 mm³・厚み 2.382 mm・35×6×2.382 @ [15.2, 9.9, 0.5] | ✅ |

体積は小数 3 桁まで同じ。新しい方は**道のどこで・どんな形で**当たっているかまで出る。

### 速さ

| | 旧 | 新 |
|---|---|---|
| `path_hub` 0.25 刻み | **PC が固まる**（400 姿勢 × 28782 面 ＝ 1150 万面） | ── |
| `path_hub` | SWEEP_STEP 1.5 で数十秒 | 距離 188 姿勢 1.8 秒 ＋ 厳密 13 回 ＝ **11 秒** |
| 4 本まとめて | ── | **48 秒** |

刻みは `SWEEP_STEP` のような決め打ちを持たない。空いている距離 d と、その区間で物のどの点も動かない上限 M から
`Δt = (d − 0.05) / M` で出す（Conservative Advancement）。広い所は 1 歩で飛び、狭い所だけ細かくなる。
**刻みより細い物をすり抜ける**という旧方式の穴が原理的に無い。

### 誤報の落とし方

- 隙間 0.05mm 以下を「接触」として扱う（clash tolerance）
- 接触したら厳密な交わりを取り、**主軸で測った厚み**が 0.01mm 未満なら同一平面の皮 ＝ めり込みではない
  （`path_hub` の接触はすべて厚み 0.000 の平面。板の裏が柱の頭に載っているだけ）
- 体積で判定しない。体積 5mm³ は「深さ 0.01 × 面積 500」かもしれず、「深さ 2 × 面積 2.5」かもしれない

### 動画の読み方

`hardware/_tmp_sweep/<key>.mp4`。1 コマで物が 0.5mm 動く（24fps）。

- **箱は灰色の半透明**、動く物は不透明。色は 青＝空いている／黄＝触れているだけ（皮）／**赤＝めり込んでいる**
- **明るい赤の塊**が、その姿勢での**交わりそのもの**（OpenSCAD で厳密に取った形）
- 最後にいちばん深い所で止まり、**動く物を消して交わりだけ**を見せる
- 焼き込みの文字: `s`（道のどこか）・`gap`（隙間 mm）・`HIT t=…mm V=…mm3`

### 動画で踏んだ穴（2026-09-17）

- 🔴 **`obj.matrix_world` に素の配列を入れると「列」として読まれる。** 行で渡したつもりの平行移動が
  行列のいちばん下の行（点の変換に使われない場所）に入り、**まるごと捨てられる**。
  最初に焼いた 3 本は**物が 1mm も動いていなかった**（色と字幕は別経路なので、動かない絵の上で
  色と数字だけが変わる、いちばん質の悪い出方をした。ユーザーの指摘で発覚）。
  ⇒ `mathutils.Matrix([行, 行, 行, 行])` で包む。
  ⚠ **焼いたら必ず 2 コマ以上を開いて、物が動いているかを目で確かめること。**
- EEVEE の半透明どうしは前後関係が壊れる（動く物が箱の面の裏に消えた）。
  半透明は箱だけにして、動く物は不透明のまま扱う。
- `Wireframe` モディファイアは物を拡大する**前**に効く。`scale` で大きくすると線まで太る
  （8.4 倍して針金の箱が中身の詰まった箱に見えた）。⇒ 毎コマ頂点そのものを書く。
- カメラの寄りは外接箱の 8 隅をカメラ座標へ落として合わせる。`ortho_scale` は横に効くので、
  16:9 では**縦が先に切れる**（縦長の場面で箱が枠から出た）。
- 道が「座った姿勢 → 外」の向きで書かれている物がある（`PATH_BAT`）。
  動画は座る姿勢で終わる方が読めるので、その場合はコマ順を逆にする（剛体なので当たりは向きに依らない）。

### まだ手を付けていない

- `path_lid` は蓋がたわむ（`lid_flexed()`）ので、剛体を前提にした新しい道具にまだ載せていない
- `case_v6_1.scad` の `sweep_pose()` / `path_*` はまだ残っている（二重管理）
- STL の壊れた辺（`shell` 6・`hub` 22）。ゼロ面積の面が `shell` に 74 枚ある。
  当たり判定は三角形の集まりとして見るので走るが、内外判定を使う手が採れない

## 参考

- C2A: Controlled Conservative Advancement — http://gamma-web.iacs.umd.edu/papers/documents/articles/2009/tang09.pdf
- Swept Volumes via Spacetime Numerical Continuation — https://www.dgp.toronto.edu/projects/swept-volumes/
- Implicit Swept Volume SDF — https://arxiv.org/pdf/2405.00362
- FCL / python-fcl — https://github.com/BerkeleyAutomation/python-fcl
- trimesh.collision — https://trimesh.org/trimesh.collision.html
- MeshLib — https://meshlib.io/feature/mesh-to-sdf/
- SOLIDWORKS Detecting Interference (Motion) — https://help.solidworks.com/2023/english/SolidWorks/motionstudies/t_detecting_interference_motion.htm
- Clash detection と tolerance — https://www.spatial.com/glossary/what-is-clash-detection
- V-HACD（凸分解） — https://github.com/isabella232/VHACD
- OpenSCAD Animation — https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/Animation
