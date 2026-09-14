# v6（2026-09-12〜13）

筐体 v6 はユーザーの判断で**失敗**として閉じた（2026-09-13）。
ここに置いてあるのは、次の版で使い回せる物と、v6 を読み解くのに要る物である。
`hardware/` 直下の作業場（v5）には置かない。

## 使い回せる物

| 場所 | 中身 |
|---|---|
| `_v6_gear.scad` | つまみの歯車の機構（歯形・ロータ・ブラケット・当たり検査 chk_*）。組む順は冒頭 |
| `_v6_knob_hold.scad` `_v6_gear_probe.scad` | 歯車の保持と探りの道具。`_v6_gear.scad` を include して読む |
| `_tmp_gearbox_proposal.scad` | ギアボックスの提案（未実装）。要求は docs/MECH-V6-REQ.md |
| `pcb/` | KiCad の板 `hub_power/`（ハブ＋電源の 1 枚パネル）と、回路図・基板・自動配線・製造ファイルを作るスクリプト。読み方は docs/POWER.md |
| `pcb/freerouting/` | 自動配線の実行ファイル（展開しただけ・git には入れない）。`route.py` がこの場所を読む |
| `tools/` | 電池の座の探索（_v6_bat*）・歯車の当たり検査（_v6_gear_chk / _v6_gear_sweep）・柱の隙間（_v6_post_gap） |
| `sim2d/` | 歯車を 2D で回した MuJoCo 模型 |

## v6 そのもの

| 場所 | 中身 |
|---|---|
| `_v6_portrait.scad` | v6 の形の正（縦置き）。`_v6_shape.scad` `_v6_form.scad` `_v6_flat.scad` はその派生 |
| `case_v6.scad` | 口の座標を板に合わせた版 |
| `_tmp_v6b_stack.scad` | 積み方の提案（本体には入っていない） |
| `chk/` | 当たり検査の出力 STL と echo |
| `pcb_tmp/` | 電源板の大きさを決めた当たり取り（pbfit*.scad）と PowerBoost の箱 |
| `renders/` | レポート用の絵（リポジトリ直下に散っていた物） |

## 動かし方

.scad は `parts/` を `../../parts/` で読む。スクリプトはリポジトリの根から回す。

```
"C:/Program Files/OpenSCAD (Nightly)/openscad.exe" --backend=manifold -o x.echo -D "part=\"p_khub\"" hardware/frozen/v6/_v6_gear.scad
python hardware/frozen/v6/tools/_v6_gear_chk.py
python hardware/frozen/v6/pcb/gen_sch.py && python hardware/frozen/v6/pcb/gen_pcb.py && python hardware/frozen/v6/pcb/route.py
```

文書は docs/CASE-V6-PLAN.md・MECH-V6-REQ.md・MECH-V6-HANDOFF.md・MEDIATOR-V6-HANDOFF.md・HUB-V6-PARTS.md。
