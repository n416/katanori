// ハブ基板 PU52X74 のモック（実装込み）
//
// 🔒 **穴の位置も部品の位置も、relay_board.html の initialLayout() から生成している。**
//    手で転記していない。穴割りを直したら `python hardware/gen_hub_board.py` を流す。
//
//   use <hub_board.scad>
//   hub_board();                 // 板＋部品＋口
//   hub_corridors();             // 🟪 線が出て曲がるのに要る空間（向きごと）
//   hub_stack_h()                // 板の下面から実装の頂点までの高さ [mm]
//
// ---- 座標系 ----
//   X 0〜74 … 列1〜27（列1が X 小）／ Y 0〜52 … 行A〜S（行A が Y 小）
//   Z 0 が板の下面。+Z が部品面。
//
// ---- 🔴 これを作って分かったこと（2026-08-15）----
// **最高点は「ヘッダの向き」で入れ替わる。裸のヘッダ寸法(8.5mm)で比べてはいけない。**
//   立てる … 口が 25mm（ハウジング＋線が曲がり切るまで）で、**口が断然の最高点**。層 28.6mm
//   横出し … 口は寝て ⚠約6mm。**リレーの 10mm が最高点**になり、層 13.6mm
// 🔴 **13.6mm のうち 10mm はリレーで、ヘッダを寝かせても減らない。** 横出しの効果はここで頭打ち。
//
// ⚠ AI はこの節に一度「最高点はヘッダ(8.5mm)ではなくリレー(10mm)」と書いた。
//    **8.5 は裸のヘッダで、ハウジングを忘れている**（ユーザー指摘）。同じ忘れ方を
//    このファイルの中で2回している（HUB_RA_HOUSING の注記も参照）。
//    🔒 **口の高さを語るときは、必ずハウジングが挿さった状態で数える。**

include <hub_board_parts.scad>

$fn = 32;

// 🔒 コネクタ1個が要する空間 ✅約25mm（ユーザー・2026-08-15）
//    ハウジング＋線が出て断線しない曲げで向きを変え切るまで。**向きを変えても同じ。**
HUB_CONN = 25.0;

HUB_SOLDER = 2.0;    // ⚠ 半田面に出る足の長さ（切った後）

// 横出し（ライトアングル）にするか。false なら立てる
HUB_RA = true;

// ---- 高さ ----
// 部品面の頂点。
//   🔒 口の高さは「ヘッダ単体8.5mm」ではなく **HUB_CONN(25mm)** で数える。
//      ハウジングが挿さり、線が出て曲がり切るまでが要る空間だから
//      （docs/DIMENSIONS.md 1.5）。**ヘッダの寸法だけ数えるのは過小評価。**
//   横出しなら口は寝るので HUB_RA_HOUSING で済み、代わりに hub_corridors() が横に出る。
// ⚠ 横出しにしても**ハウジングは消えない。寝るだけ**。板の上に出る高さは
//    ハウジングの断面のぶん残る。⬜ 実測が無いので推定。
//    🔴 AI は当初ここに 2.5（＝横出しヘッダの樹脂だけ）を置いていた。**またハウジングを
//       忘れていた**（2026-08-15・ユーザー指摘。裸のヘッダ8.5mmで比較したのと同じ誤り）。
HUB_RA_HOUSING = 6.0;   // ⚠ 2.54mm ハウジングを寝かせた断面の高さ（未実測）

function hub_part_h(p, ra) =
    (p[2] != "header") ? p[7] : (ra ? HUB_RA_HOUSING : HUB_CONN);

function hub_top(ra = HUB_RA) =
    max([ for (p = HUB_PARTS) hub_part_h(p, ra) ]);

function hub_stack_h(ra = HUB_RA) = HUB_T + hub_top(ra) + HUB_SOLDER;

// 🔴 `use <hub_board.scad>` は**モジュールと関数しか取り込まない。変数は取り込まない。**
//    呼ぶ側から HUB_SOLDER などを直に参照すると undef になり、translate が丸ごと
//    無視されて**部品が原点に置かれる**（2026-08-15、箱詰めスタディで実際に起きた。
//    OpenSCAD は WARNING を出していたが、AI が grep で ERROR だけ拾って捨てていた）。
//    🔒 **外に出す値は必ず関数にする。**
function hub_solder() = HUB_SOLDER;
function hub_size()   = [HUB_L, HUB_W, HUB_T];

// 口が出る向き → 単位ベクトル
// 🔒 exit は relay_board.html の**画面の方向**で書かれている（up = 画面の上 = 行A側）。
//    🔴 2026-08-19、穴割りの鏡像を直して**行A が Y 大**になったので、up/down を
//       入れ替えた。ここを直さないと、口の向きだけが古い鏡像のまま残る。
// 🔒 板は筐体へ **180度 回して**載る（HUB_ROT180・生成器がその向きで座標を出す）。
//    回れば口の向きも回る。**座標だけ回して向きを回さないと、口の向きだけが嘘になる。**
function hub_screen_dir(e) =
      (e == "up")    ? [ 0,  1]
    : (e == "down")  ? [ 0, -1]
    : (e == "right") ? [ 1,  0]
    :                  [-1,  0];
function hub_dir(e) = (HUB_ROT180 ? -1 : 1) * hub_screen_dir(e);

// ---- 描画 ----
module hub_board(ra = HUB_RA) {
    // 板
    color("#1a5c2a") difference() {
        cube([HUB_L, HUB_W, HUB_T]);
        for (sx = [-1, 1], sy = [-1, 1])
            translate([HUB_L / 2 + sx * HUB_MOUNT[0] / 2,
                       HUB_W / 2 + sy * HUB_MOUNT[1] / 2, -1])
                cylinder(d = HUB_MOUNT_D, h = HUB_T + 2);
    }
    // 半田面（足の逃げの予約）。取付穴の周り φ7.5 は床の柱（case_v3 HUB_POST_D 7.0）が座る所で足は無い。
    //    2026-08-24: ここを抜いていなかったので chk_floor が v3 の最初から 215mm³ 出ていた（柱 ↔ この予約）
    color("#888", 0.35) difference() {
        translate([0, 0, -HUB_SOLDER]) cube([HUB_L, HUB_W, HUB_SOLDER]);
        for (sx = [-1, 1], sy = [-1, 1])
            translate([HUB_L / 2 + sx * HUB_MOUNT[0] / 2, HUB_W / 2 + sy * HUB_MOUNT[1] / 2, -HUB_SOLDER - 1])
                cylinder(d = 7.5, h = HUB_SOLDER + 2, $fn = 32);
    }

    // 部品
    for (p = HUB_PARTS) {
        k = p[2];
        h = p[7];
        c = (k == "relay")  ? "#222"
          : (k == "button") ? "#c0392b"
          : (k == "header") ? "#c93"
          : (k == "ph")     ? "#eee" : "#555";
        if (k == "header" && ra) {
            // 🔒 横出し: ハウジングごと板の上に寝る（消えるのではなく寝るだけ）
            translate([p[3], p[4], HUB_T]) color(c)
                cube([p[5] - p[3], p[6] - p[4], HUB_RA_HOUSING]);
        } else {
            translate([p[3], p[4], HUB_T]) color(c)
                cube([p[5] - p[3], p[6] - p[4], h]);
        }
    }
}

// 🟪 線が出て曲がるのに要る空間。**部品も壁も置けない。**
//    横出し → 板の面から真横へ HUB_CONN
//    立てる → 口の真上へ HUB_CONN
module hub_corridors(ra = HUB_RA, skip = undef) {
    for (h = HUB_HEADERS) {
        if (skip == undef || skip != h[2]) {
            d  = hub_dir(h[2]);
            w  = max(h[6] - h[4], 6);   // 口の幅
            l  = max(h[7] - h[5], 6);
            cx = (h[4] + h[6]) / 2;
            cy = (h[5] + h[7]) / 2;
            color("#8e44ad", 0.18)
            if (ra) {
                if (d[0] != 0)
                    translate([d[0] > 0 ? HUB_L : -HUB_CONN, cy - l / 2, 0])
                        cube([HUB_CONN, l, 12]);
                else
                    translate([cx - w / 2, d[1] > 0 ? HUB_W : -HUB_CONN, 0])
                        cube([w, HUB_CONN, 12]);
            } else {
                translate([cx - w / 2, cy - l / 2, HUB_T])
                    cube([w, l, HUB_CONN]);
            }
        }
    }
}

// 単体で開いたときだけ
if ($preview && is_undef(HUB_EMBEDDED)) {
    hub_board();
    hub_corridors();
    echo(str("実装の頂点 ", hub_top(), "mm / 層の総高 ", hub_stack_h(), "mm",
             "  (横出し=", HUB_RA, ")"));
    echo(str("立てた場合: 頂点 ", hub_top(false),
             "mm / 層 ", hub_stack_h(false), "mm"));
}
