// ============================================================================
// micro-B の L 字アダプタ  オーディオファン「方向変換アダプター L字 B」 Amazon B0CTMHK3BY
//   2026-08-24 ユーザー発見・購入。PowerBoost の micro-B に挿し、90° 曲げて箱の内側へ出す。
//
//   📄 商品図: 16 × 13 × 11 mm・1 g。13 は金属プラグの先から胴の底まで（プラグ軸方向）。
//      16 は肘の方向の胴の長さ。11 は胴の幅（プラグの広い辺と同じ向き）。
//   🔒 **プラグは 5 mm 埋まり、口の面から出るのは 8 mm。確定（2026-08-24 ユーザー）。測り直さない。**
//   ⚠ 首と胴の厚みの内訳（1.5 ＋ 6.5）だけは絵の都合で、合計 8 は動かない。
//
//   ローカル座標:  原点 = レセプタクルの面（口の面）でのプラグ軸の中心
//      +Z … プラグ軸。+Z がレセプタクルの中（挿さる側）、−Z が外
//      +X … プラグの広い面（ツメのある面）が向く側 ＝ 胴が伸びる側（肘の向き）
//      ±Y … プラグの幅方向（胴の幅 11 もこの向き）
// ============================================================================
LA_PLUG_IN  = 5.0;          // 🔒 埋まる長さ（確定）
LA_PLUG_W   = 6.9;          // 📄 micro-B プラグの殻の幅（規格）
LA_PLUG_T   = 1.9;          // 📄 同・厚み（規格）
LA_TOTAL_H  = 13.0;         // 📄 商品図
LA_BODY_L   = 16.0;         // 📄 商品図（肘の方向）
LA_BODY_W   = 11.0;         // 📄 商品図（幅）
LA_OUT      = 8.0;          // 🔒 口の面から外へ出る長さ（確定）
LA_NECK     = 1.5;          // 絵の都合: プラグの根元の黒い首
LA_BODY_T   = LA_OUT - LA_NECK;                    // 6.5  胴の厚み（プラグ軸方向）
LA_TAIL     = 2.3;          // ⚠ 推定: プラグ軸から胴の端（壁側）までの出っ張り
LA_SOCK     = [7.6, 2.6];   // 📄 micro-B メスの開口（幅 × 高さ）

function la_body_box() = [[-LA_TAIL, -LA_BODY_W/2, -LA_NECK - LA_BODY_T], [LA_BODY_L - LA_TAIL, LA_BODY_W/2, -LA_NECK]];
function la_out_len()  = LA_NECK + LA_BODY_T;      // 口の面から外へ出る長さ 8.0
function la_reach()    = LA_BODY_L - LA_TAIL;      // 口の軸から肘の先（ソケットの面）まで 13.7

module usb_l_adapter_plug() {                      // レセプタクルに埋まる部分（当たり検査からは除く）
    color("#c8ccd0") translate([-LA_PLUG_T/2, -LA_PLUG_W/2, 0]) cube([LA_PLUG_T, LA_PLUG_W, LA_PLUG_IN]);
}
module usb_l_adapter_body() {                      // 口の面から外に出る部分（当たり検査はこれ）
    color("#2d3748") translate([-LA_PLUG_T/2 - 0.6, -LA_PLUG_W/2 - 0.6, -LA_NECK]) cube([LA_PLUG_T + 1.2, LA_PLUG_W + 1.2, LA_NECK]);   // 首
    b = la_body_box();
    color("#1a202c") difference() {
        translate(b[0]) cube(b[1] - b[0]);
        // 肘の先のソケット（開口は +X を向く）
        translate([b[1][0] - 6, -LA_SOCK[0]/2, b[0][2] + (LA_BODY_T - LA_SOCK[1])/2]) cube([6.01, LA_SOCK[0], LA_SOCK[1]]);
    }
}
module usb_l_adapter() { usb_l_adapter_plug(); usb_l_adapter_body(); }

// 肘の先に挿すストレートのプラグ（例: B0H5BRM1YG の micro-B 側）の予約。⚠ 頭の寸法は未取得・仮
LA_NEXT_HEAD = [10.0, 9.0, 5.5];                   // 長さ × 幅 × 厚み ⚠ 仮
module usb_l_adapter_next_plug() {
    b = la_body_box(); zc = b[0][2] + LA_BODY_T/2;
    color("#f6ad55", 0.5) translate([b[1][0], -LA_NEXT_HEAD[1]/2, zc - LA_NEXT_HEAD[2]/2]) cube(LA_NEXT_HEAD);
}

// 単体で見る
if ($preview || true) { usb_l_adapter(); %usb_l_adapter_next_plug(); }
