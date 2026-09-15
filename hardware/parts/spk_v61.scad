include <mat.scad>   // 材料のスイッチ（case と同じ 1 行を読む）
function spk_mat() = mat_name();
// スピーカー v6.1 ── parts/spk_v5.scad の写し（2026-09-14）。
//   🔒 ユーザー「コピーして使って」: v5 の形を変えないために分けた。
//   🔒 ユーザー 2026-09-14「スピーカーのケースはもう分けたままで良いです」:
//     いまは中身が spk_v5.scad と同じ（S_NUT_ANG を 20 にしたが 57 へ戻したため）。
//     **同じでも畳まない。**v6.1 がスピーカーを触るときは必ずこちらを直す。
//   ⚠ v5 側を直したら、ここへ手で持って来ること（2 つを自動で揃える仕掛けは無い）。
// スピーカー v5 ── 座・縁・ハニカムのグリル・吊り（板 2 枚＋足）・バスタブ 3（2026-09-08 に case_v5 から分離。ユーザー「部品完全に分けた方がいい。ボタンもつまみもそうしてる」）
//   原点 = スピーカーの中心・z0 = 天板の外面（btn_v3 / knob_v5 と同じ約束）。case_v5 は at_spk() で SPK_AT へ置く
//
//   openscad -o spktest.stl -D 'part="print_deck"' hardware/parts/spk_v5.scad   // 試し刷り: 天板の切れ端＋座＋縁＋板＋足（天面を下・支柱無し・足は庇 6.0 のまま）
//   openscad -o spktub.stl  -D 'part="print_tub"'  hardware/parts/spk_v5.scad   // バスタブ 3（板を下）
//   （part 未指定なら分解図。part="deck" で天板だけ・"look" で組み立て図・"check" で当たり）
//   ⚠ モジュール名は全部 spk_ で始める。case_v5 が knob_v5 / btn_v3 と一緒に use するので、assembly / exploded / print_tub のような名前は後勝ちで上書きしてしまう（🔴 2026-09-08 つまみがスピーカーになった）
//
// 🔒 ユーザー 2026-09-08 案: 左右（±X）の天井から薄い板を下ろし、スピーカーの下端の高さで内側へ曲げて足にする。足は厚くして中に縦のナット。
//   バスタブ 3 は足の下の板＋±X の壁。壁の外から横に M2×6 を入れて足の中の**縦の六角**のナットへ（🔒 ユーザー 2026-09-08「六角ポケットを縦にして、横からねじ止め」: 縦ねじ＋ザグリは廃止）。板の中央の台が胴の裏に当たり、座との間に挟む（クランプ）
// 🔒 入れ方（2026-09-08 私が決めた。足がスピーカーの下に入るので下からは入らない）: 天板を裏返して机に置き、スピーカーを**前（−Y）から横に滑り込ませて**足に乗せる。
//   そのために 前の縁は無し（縁は後ろ半分だけ）・座と振動板の逃げは前の縁まで溝で開く・バスタブ 3 に前の止めの壁。左右は板、後ろはつまみの台座と縁が止める。
// 空き（case_v5 で 2026-09-08 測定・世界座標）: 右は右の壁 84.35 まで 8.15、左は OLED の後ろの縁 48.62 まで 4.3（y 10.04 より後ろ。前は ReSpeaker の押さえ x 50〜52.4）、
//   後ろはつまみの台座 25.1 まで 0.3、下は ReSpeaker 36.5 まで 9.1。OLED の腕は x 73.1〜76.5・y 〜9.5。この数字は下の S_NOTCH / S_LIP_X1 に局所で写してある

// ✅ 実物で確認（2026-09-09 ユーザー・ターム 2026-09-09-0340 を刷って組んだ）:
//   ① スピーカーが小判の座に綺麗に嵌る（逃げ 0.3・後ろ半分の縁が位置を出す・真下から真っすぐ）
//   ② M2 ナットが手の中へ板の下端の溝から入る（天板を裏返した状態で口は上向き）
//   ③ M2×4 が壁の外から入り、中央の台が磁石の面に当たって座との間に挟める
//   ⇒ 倒した手（S_NUT_ANG 57°）・ポケット・台の高さは、ここまでは実物で通っている

use <parts.scad>   // speaker_112495() / spk_l() / spk_w() / spk_th() / spk_dia()

part = "explode";

S_DECK_T = 2.5;                 // 天板の厚み（case_v5 の TOP_T と同じ値。ここは形だけ）
Z_IN = -S_DECK_T;               // 天板の内面 −2.5
S_LIFT = 0.9; S_CL = 0.3;       // 座の深さ（内面から）・座の逃げ（片側）
S_REL = 0.4 + S_LIFT;           // 振動板の逃げの深さ 1.3（振動板の上の空気 0.4 ＋ 座の 0.9）。天板の残り 1.2
S_HEX_AF = 2.2; S_HEX_WALL = 0.6;   // ハニカム: 六角の二面幅 2.2・穴どうしの肉 0.6（2026-09-05）
S_RIM_H = 3.0; S_RIM_T = 1.5;   // 位置出しの縁（後ろ半分だけ）。高さ 0.8 → 3.0（🔒 ユーザー 2026-09-08「出力面がわずかに小さいので 0.8 ではガイドにならない」）・肉 0.6 → 1.5（「薄すぎて割れないか」）
                                // ⚠ 模型のスピーカーは側面が真っすぐ 23 × 15・逃げ 0.3。裏の面が片側 0.3 を超えて大きければ入らない
Z_BODY_B = Z_IN + S_LIFT - spk_th();         // スピーカーの一番下（磁石の先）−7.1（枠の裏は −5.6）。全厚 5.5（✅ 2026-09-08）。面は座の天井 −1.6 に着く（🔴 2026-09-08 それまで v4 の「振動板の上に 0.2」を写して −5.8 にしていて、クランプの台で押しても面が天井に着くまで 0.2 動けた＝挟めていなかった。ユーザー「座標ミス？」）。case_v5 の at_spk は局所座標で置くので一緒に動く
Z_BODY_T = Z_BODY_B + spk_th();              // 面 −1.6
// ---- 吊り ----
S_PLATE_T = 1.8 + 1.0; S_PLAY = 0.2;         // 板の厚み 2.8 ＝ ナット 1.8 ＋ 外の肉 1.0（🔒 ユーザー 2026-09-09「ポケットの内壁は縁と一体化して無くして」）（🔒 ユーザー 2026-09-08「天板からの手を内側に曲げるのをやめる」: 足は無し、ナットは板の中）
// ナットは板の中で、天板の直下に置く（板は外にあるので高さは自由。全厚 5.5 になって板とバスタブ 3 が下がり、ReSpeaker に 1.05 入ったので上げた・2026-09-08）
// 🔴 この行は代入が 4 つ並ぶ。行末にコメントを足すと後ろの 3 つが飲まれて undef になる（2026-09-15 に再発）
// ナイロンは 呼び 4.0 ＋ 0.5（MJF は穴の公差 ±0.3）。レジンは実績の +0.3
S_NUT_AF = nylon() ? 4.5 : 4.3; S_NUT_T = 1.8; S_SKIN = 0.7; S_SCR_D = 2.5;
S_NUT_SKIN_X = 0;                            // ポケットの内側の肉は無し。ポケットは縁（x 11.8〜13.3）と同じ所に入る
S_Y = [-spk_w() / 2, spk_w() / 2];           // 板・足・バスタブ 3 の Y ＝ スピーカーの幅 ±7.5
S_SEAT_CX = spk_l() / 2 - spk_w() / 2; S_SEAT_R = spk_w() / 2 + S_CL;   // 座の小判: 端の半円の芯 x ±4.0・半径 7.8
S_NUT_ANG = 57;                              // 🔒 ユーザー 2026-09-14（v6.1）: いったん 20 にしたが **57 のまま**が正。ナットの道が ReSpeaker の板の頭に 8.49mm³ 入るのは、天板とスピーカーを先に机で組んでから箱へ載せるので塞がらない（組む順で解く・部品は動かさない）。点対称は S_HANDS が持つので角度だけで保たれる   // 🔒 ユーザー 2026-09-09「手は小判の同心円みたいな形になっていい」→「やっておくか」: 手・ナット・ねじ・壁を、端の半円の芯（x ±S_SEAT_CX）から S_NUT_ANG 度倒した放射方向に置く。0 なら真横（前の形）。57 は OLED の板の後ろの縁（世界 y 4.40）にねじの頭が 0.40 で並ぶ角度（60 だと 0.12 しか空かない）
S_HANDS = [[-1, 1], [1, -1]];                // 点対称: −X 側は +y へ、+X 側は −y へ（世界の左の前は壁の柱と前板が居るので前へ出せない）
S_R_I = S_SEAT_R;                            // 板の内の面までの半径 7.8 ＝ 座の輪郭（小判に接する）
S_R_O = S_R_I + S_PLATE_T;                   // 板の外の面 10.6
S_R_NUT = S_R_I + S_NUT_SKIN_X + S_NUT_T / 2;   // ナットの芯 8.7（ポケット 7.8〜9.6）
S_ARM_W = S_NUT_AF / cos(30) + 2 * S_SKIN;   // 手の幅（接線方向）6.37 ＝ 六角の対角 4.97 ＋ 肉 0.7 × 2
S_ARM_R0 = 5.0;                              // バスタブの腕が中央の板に食い込む半径
S_LEAD = spk_lead_xy();                      // 線が外形から出る所（parts.scad から。+X の端の三日月の上側のはんだの x・前の縁）
// 線の穴は無し（2026-09-08 写真: 線は裏面からではなく、前の側面の基板から長辺に沿って出る。前の壁の窓から外へ）
Z_NUT_C = Z_IN - S_SKIN - S_NUT_AF / 2;      // 六角の中心 −5.35（上の角は天板の内面から 0.7 下）＝ 横ねじの高さ。⚠ 局所 z0 は天板の外面 ＝ 世界 52.95（Z_TOP 50.45 ＋ TOP_T 2.5）
// 🔒 2026-09-08 OLED のピンヘッダ（世界 x ≤ 48.13・y 10.3〜20.9・z 45.2〜47.8）: 一度ねじを −10.5 まで下げて避けたら、バスタブ 3 の底が電流計に当たった（ユーザー「今度は電流計に当たってる」）。
//   下げるのをやめ、**左の壁とねじをヘッダの後ろ（世界 y > 20.9 ＝ 局所 y > 3.6）に寄せる**。左の壁は局所 y 3.9〜7.5 の短い壁、左のねじは y 5.5
Z_FOOT_T = Z_BODY_B - S_PLAY;                // （足は無い。記録用: 磁石の先の 0.2 下 −7.3）
Z_FOOT_B = Z_NUT_C - S_NUT_AF / 2 - S_SKIN;  // 板の下端 −8.2（六角の下から肉 0.7）
S_TUB_T = 2.0; Z_TUB_T = Z_FOOT_B; Z_TUB_B = Z_TUB_T - S_TUB_T;   // バスタブ 3 の板 −8.2〜−10.2（底は世界 42.75）
S_WALL_T = 1.5; S_R_W0 = S_R_O + S_PLAY; S_R_W1 = S_R_W0 + S_WALL_T;   // バスタブ 3 の壁 半径 10.8〜12.3（手と同じ向き・同じ幅）
Z_WALL_T = Z_NUT_C + 2.2;                    // 壁の上端 −3.15（ねじの頭 φ4 の上 −3.35 を覆う）

S_LIP_T = 1.5; S_LIP_X1 = 2.0; Z_LIP_T = Z_BODY_B + 1.5 + 2.0;   // 前の止めの壁: y −9.3〜−7.8・x −13.3〜8.1（OLED の腕の手前）・上端 −3.6（枠の側面の半分）。線の切り欠き S_LIP_WIRE
S_PAD_X = spk_mag()[0] / 2; S_PAD_Y = spk_mag()[1] / 2; Z_PAD_T = Z_BODY_B;   // クランプの台（🔒 ユーザー 2026-09-08「クランプみたいにすればいいのに」）: 磁石＋パッキンの当たり面 16 × 10.5 と同じ ±8.0 × ±5.25・上面 −7.1。手を倒したので前の ±8.68 × ±7.5 では角が手に入る
S_SCR_LEN = 4.0;                             // 横ねじ M2×4（私が 6.0 から変えた・2026-09-09。ポケットが内側へ寄って、6 だと先が 10.3 でスピーカーの胴に 1.2 入る）。頭は壁の外 16.3、壁 1.5 → 隙間 0.2 → 外の肉 1.0 → ナット（13.6〜11.8）。先は 12.3 でナットに 1.3 かかる
S_HEAD_D = 4.0; S_HEAD_T = 1.3; S_NUT_AF_REAL = 4.0; S_NUT_T_REAL = 1.6;
// 試し刷りの天板の切れ端（世界 x 47〜82・y 8.2〜24.8 を局所に写した物）: x ±17.5・y −9.1〜7.5。前は OLED の腕（y 〜8.0）を入れない
S_DECK = [[-15.0, -13.2], [15.0, 13.2]];   // 後ろは縁（y 7.8〜9.3）まで入れる（🔴 2026-09-08 7.5 で切っていて look に縁が出ず、天板と形が違って見えた）

// 手の座標系: 端の半円の芯を原点に、+X = 外向き（放射）・+Y = 接線。h = [sx, sy]
module spk_at_hand(h) translate([h[0] * S_SEAT_CX, 0, 0]) rotate([0, 0, h[0] > 0 ? h[1] * S_NUT_ANG : 180 - h[1] * S_NUT_ANG]) children();
module spk_obr2d(l, w) hull() for (sx = [w / 2, l - w / 2]) translate([sx, w / 2]) circle(d = w, $fn = 48);
module spk_obr(l, w, h) hull() for (sx = [w / 2, l - w / 2]) translate([sx, w / 2, 0]) cylinder(d = w, h = h, $fn = 48);
// ハニカムの穴: 振動板 14 × 8 の範囲に六角を千鳥で並べる（偶数段 nx+1 個・奇数段は 1 個少ない）。平らな辺が左右
module spk_grille() { pitch = S_HEX_AF + S_HEX_WALL; w = spk_dia()[0]; d = spk_dia()[1]; rh = pitch * 0.866;
    nx = floor(w / pitch + 1e-6); nxo = max(0, floor((w - pitch) / pitch + 1e-6)); ny = floor(d / rh + 1e-6);
    for (j = [0 : ny]) { n = (j % 2) ? nxo : nx;
        for (i = [0 : n]) translate([-n * pitch / 2 + i * pitch, -ny * rh / 2 + j * rh, Z_IN - 1]) rotate([0, 0, 30]) cylinder(d = S_HEX_AF / cos(30), h = S_DECK_T + 2, $fn = 6); } }
module spk_rim_full() translate([-spk_l() / 2 - S_CL - S_RIM_T, -spk_w() / 2 - S_CL - S_RIM_T, Z_IN - S_RIM_H]) difference() {
    spk_obr(spk_l() + 2 * (S_CL + S_RIM_T), spk_w() + 2 * (S_CL + S_RIM_T), S_RIM_H + 0.01);
    translate([S_RIM_T, S_RIM_T, -1]) spk_obr(spk_l() + 2 * S_CL, spk_w() + 2 * S_CL, S_RIM_H + 3);
}
module spk_rim() intersection() { translate([-100, 0, -100]) cube([200, 100, 200]); spk_rim_full(); }   // 後ろ半分だけ
// 🔒 ユーザー 2026-09-09「形は変えず配線で逃がす」: スピーカーの 2 本目の線（前の縁から局所 x 9.44・φ0.9）は +X の手（内の面 8.98）の真下を通るので、内へ寄せてから前の壁の切り欠き（x 5.44〜8.1）へ抜く。
//   parts.scad の切り株は 1.2 に短くし（まっすぐ描くと手を突き抜けたため）、道は case_v5 の w_phout が描く。spk_check は 0
module spk_hang_arms() for (h = S_HANDS) spk_at_hand(h) translate([S_R_I, -S_ARM_W / 2, Z_FOOT_B]) cube([S_PLATE_T, S_ARM_W, Z_IN - Z_FOOT_B + 0.01]);   // まっすぐな板を放射方向に置く（内の面は小判に接する）
module spk_hang_cut() for (h = S_HANDS) spk_at_hand(h) translate([S_R_NUT, 0, Z_NUT_C]) {
    rotate([30, 0, 0]) rotate([0, 90, 0]) cylinder(d = S_NUT_AF / cos(30), h = S_NUT_T, center = true, $fn = 6);   // 六角（軸は放射方向・平面が上下）
    translate([-S_NUT_T / 2, -S_NUT_AF / 2, Z_FOOT_B - Z_NUT_C - 1]) cube([S_NUT_T, S_NUT_AF, (Z_NUT_C - Z_FOOT_B) + 1]);   // 板の下端へ開く溝。ナットは下から差す（組む時は天板が裏返しなので口は上向き・組んだ後はバスタブ 3 の板が塞ぐ）
    rotate([0, 90, 0]) cylinder(d = S_SCR_D, h = 12, $fn = 24);   // 横ねじの通し（外へ）
}
module spk_driver_probe(d = 6.0, len = 45) for (h = S_HANDS) spk_at_hand(h) translate([S_R_W1, 0, Z_NUT_C]) rotate([0, 90, 0]) cylinder(d = d, h = len, $fn = 24);   // ドライバーの軸が要る空間（壁の外の面から外へ）
module spk_nut_path(len) for (h = S_HANDS) spk_at_hand(h) translate([S_R_NUT - S_NUT_T / 2 - 0.15, -S_NUT_AF / 2 - 0.15, Z_FOOT_B - len]) cube([S_NUT_T + 0.3, S_NUT_AF + 0.3, len]);   // ナットが入る道（case_v5 の nutpath が呼ぶ）
// ---- 天板側（case_v5 が at_spk() で呼ぶ）----
module spk_station_add() { spk_rim(); spk_hang_arms(); }   // 後ろの角の R（spk_gussets）は 2026-09-08 に消した: 足 15 のうち 1.1 しか持たず意味が無い（ユーザー）
// 座の壁とナットのポケットの間に残る楔を出さない（🔴 2026-09-14 刷る向きの検算: 厚さ 0.018〜0.213mm の刃が
//   天板に残っていた。実績の下限 0.42 割れ＝刷れば折れて中に落ちる）。両方の空から S_THIN 届く所＝肉が 0.5 以下の所を削る
S_THIN = 0.50;
module spk_seat2d() translate([-spk_l() / 2 - S_CL, -spk_w() / 2 - S_CL]) spk_obr2d(spk_l() + 2 * S_CL, spk_w() + 2 * S_CL);
module spk_nutpocket2d() for (h = S_HANDS) spk_at_hand(h)
    translate([S_R_NUT - S_NUT_T / 2, -S_NUT_AF / cos(30) / 2]) square([S_NUT_T, S_NUT_AF / cos(30)]);
module spk_thin_trim() translate([0, 0, Z_FOOT_B - 0.01]) linear_extrude(Z_IN - Z_FOOT_B + 0.02)
    for (h = S_HANDS) hull() intersection() {   // 手ごとに hull（2 つを一緒に hull すると間の肉まで消える）
        offset(r = S_THIN) spk_seat2d();
        offset(r = S_THIN) spk_at_hand(h) translate([S_R_NUT - S_NUT_T / 2, -S_NUT_AF / cos(30) / 2]) square([S_NUT_T, S_NUT_AF / cos(30)]);
    }
module spk_station_cut() {
    spk_thin_trim();
    translate([-spk_l() / 2 - S_CL, -spk_w() / 2 - S_CL, Z_IN - 0.01]) spk_obr(spk_l() + 2 * S_CL, spk_w() + 2 * S_CL, S_LIFT + 0.01);           // 座（内面から 0.9）
    translate([-(spk_dia()[0] + 1) / 2, -(spk_dia()[1] + 1) / 2, Z_IN - 0.01]) spk_obr(spk_dia()[0] + 1, spk_dia()[1] + 1, S_REL + 0.01);   // 振動板の逃げ（小判 15 × 9・内面から 1.3）
    // 前へ開く溝は 2026-09-09 に廃止（私の判断）: 手を倒してスピーカーは真下から真っすぐ入るようになり、溝は要らなくなった。
    //   残しておくと、倒した手の内側の角が溝の空の上に 6.00mm 張り出して刷る（_stl_preflight の 🔴）
    spk_keepout();
}
module spk_keepout() { spk_grille(); spk_hang_cut(); }
function spk_wire_z() = Z_BODY_B + spk_mag()[2] - 0.8 - 0.2;   // 線の芯の高さ −6.6（枠の裏 −5.6 → 基板 0.8 → パッドの上の線 φ0.9 の芯。parts.scad の切り株と同じ）。線の下端 −7.05 は磁石の面 −7.1 の内側なので台の逃げは要らない
function spk_pad_xy(i) = let (q = spk_solder_xy(spk_solder_ang()[i])) [q[0] - spk_l() / 2, q[1] - spk_w() / 2];   // 線が付くパッド i（0: 上側・1: その次）の局所 xy
function spk_plate_bottom() = Z_FOOT_B;   // 板の下端（口の高さ）   // 天板の keepout（支柱を立てない体積）にも入れる物
// ---- 部品 ----
module spk_body() translate([-spk_l() / 2, -spk_w() / 2, Z_BODY_B]) speaker_112495();
// バスタブ 3 の板の 2D（局所 xy）。壁の外まで、y −7.8（前の壁の裏）〜7.5。左の壁の無い所（y < 3.9）は板の外（x < −16.1）を持たない。前左の角は ReSpeaker の押さえの逃げ
module spk_tub_floor2d() union() {
    translate([-(spk_l() / 2 + S_CL + S_LIP_T), -(spk_w() / 2 + S_CL + S_LIP_T)]) spk_obr2d(spk_l() + 2 * (S_CL + S_LIP_T), spk_w() + 2 * (S_CL + S_LIP_T));   // 中央（スピーカーの下）は小判なり 26.6 × 18.6 ＝ 止めの壁の外の面と同じ輪郭（🔒 ユーザー 2026-09-09「この角も同心円上にあわせると統一感出ます」）
    for (h = S_HANDS) translate([h[0] * S_SEAT_CX, 0]) rotate(h[0] > 0 ? h[1] * S_NUT_ANG : 180 - h[1] * S_NUT_ANG) translate([S_ARM_R0, -S_ARM_W / 2]) square([S_R_W1 - S_ARM_R0, S_ARM_W]);   // 壁の下の腕（放射方向・点対称）
}

// バスタブ 3（別部品）: 板 ＋ ±X の壁（板の上に立つ）＋ 前の止めの壁（板の前・板の底から）＋ クランプの台（板の上）。横ねじの穴・前の壁の線の切り欠き。
//   🔒 2026-09-08 面が重ならないように組む（ユーザー「ちゃんと図形をつくらずブーリアンでやってる？表示がガビガビ」）: 壁と台は板の上面から、前の壁は板の前の面から始める
// 前の止めの壁: 内の面が座の輪郭・肉 S_LIP_T の帯を小判に沿わせ、前半分（y ≤ 0）かつ x ≤ S_LIP_X1 で切る（右端は倒した手と線の道の手前）
module spk_lip() intersection() {
    translate([0, 0, Z_TUB_B]) difference() {
        translate([-(spk_l() / 2 + S_CL + S_LIP_T), -(spk_w() / 2 + S_CL + S_LIP_T), 0]) spk_obr(spk_l() + 2 * (S_CL + S_LIP_T), spk_w() + 2 * (S_CL + S_LIP_T), Z_LIP_T - Z_TUB_B);
        translate([-(spk_l() / 2 + S_CL), -(spk_w() / 2 + S_CL), -1]) spk_obr(spk_l() + 2 * S_CL, spk_w() + 2 * S_CL, Z_LIP_T - Z_TUB_B + 2);
    }
    translate([-60, -60, -60]) cube([60 + S_LIP_X1, 60, 120]);
}
module spk_tub() color("#e0a040") difference() {
    union() {
        translate([0, 0, Z_TUB_B]) linear_extrude(S_TUB_T) spk_tub_floor2d();
        for (h = S_HANDS) spk_at_hand(h) translate([S_R_W0, -S_ARM_W / 2, Z_TUB_T]) cube([S_WALL_T, S_ARM_W, Z_WALL_T - Z_TUB_T]);   // 壁（手と同じ向き・同じ幅）
        spk_lip();   // 前の止めの壁（🔒 ユーザー 2026-09-09「この板も小判状に沿わせた方が良いのでは」）
        translate([-S_PAD_X, -S_PAD_Y, Z_TUB_T]) cube([2 * S_PAD_X, 2 * S_PAD_Y, Z_PAD_T - Z_TUB_T]);   // クランプの台（磁石＋パッキンの面に当たる）
    }
    for (h = S_HANDS) spk_at_hand(h) translate([S_R_W0 - 1, 0, Z_NUT_C]) rotate([0, 90, 0]) cylinder(d = S_SCR_D, h = S_WALL_T + 2, $fn = 24);   // 横ねじの通し
}
module spk_tub_screws() color("#b8b8b8") for (h = S_HANDS) spk_at_hand(h) translate([S_R_W1, 0, Z_NUT_C]) rotate([0, -90, 0]) { mirror([0, 0, 1]) cylinder(d = S_HEAD_D, h = S_HEAD_T, $fn = 24); cylinder(d = 2.0, h = S_SCR_LEN, $fn = 16); }   // M2×4。頭は壁の外、軸は壁 → 隙間 → 外の肉 → ナット
module spk_tub_nuts() color("#b8b8b8") for (h = S_HANDS) spk_at_hand(h) translate([S_R_NUT, 0, Z_NUT_C]) rotate([30, 0, 0]) rotate([0, 90, 0]) cylinder(d = S_NUT_AF_REAL / cos(30), h = S_NUT_T_REAL, center = true, $fn = 6);
module spk_tub_all() { spk_tub(); spk_tub_screws(); spk_tub_nuts(); }
// ---- 天板の切れ端（絵と試し刷り）----
module spk_deck_test() intersection() {
    difference() {
        union() { translate([S_DECK[0][0], S_DECK[0][1], Z_IN]) cube([S_DECK[1][0] - S_DECK[0][0], S_DECK[1][1] - S_DECK[0][1], S_DECK_T]); spk_station_add(); }
        spk_station_cut();
    }
    translate([S_DECK[0][0], S_DECK[0][1], -50]) cube([S_DECK[1][0] - S_DECK[0][0], S_DECK[1][1] - S_DECK[0][1], 50]);   // 縁の後ろ半分も y 7.5 で切る（刷る面を平らに）
}
// 刷る向きは**天面を下**（実物の天板と同じ。🔒 ユーザー 2026-09-08「出力面が下。天板下で印刷するんだからそれに合わせて。失敗するならそれはそれ」）
//   足は内向きの庇 6.0 × 3.5（実績: 4.0 は無事・6.83 は失敗）。🔴 2026-09-08 足の下に支柱を 4 回立て直したが、板・足・天板に囲まれた袋の中でニッパーが入らない（ユーザー「柱剥がせないよこんなの」）。支柱は無し。
//   足の後ろの角だけの R も試したが、足 15 のうち 1.1 しか持たないので消した。**足は庇 6.0 のまま**（実績: 4.0 は無事・6.83 は失敗）
module spk_print_deck() rotate([180, 0, 0]) spk_deck_test();   // 天面を下（z 0）・支柱無し
module spk_print_tub()  translate([0, 0, -Z_TUB_B]) spk_tub();                               // 板を下・壁と前の壁と台が立つ
// ---- 絵 ----
module spk_assembly() { color("#c9d0d8") spk_deck_test(); spk_body(); spk_tub_all(); }
module spk_exploded() { color("#c9d0d8") spk_deck_test(); translate([0, -22, 0]) spk_body(); translate([0, 0, -14]) spk_tub_all(); }   // スピーカーは前へ（入れる向き）・バスタブ 3 は下へ
module spk_check() { intersection() { spk_deck_test(); spk_body(); } intersection() { spk_tub(); spk_body(); } intersection() { spk_tub(); translate([0, 0, 0.01]) spk_deck_test(); } }   // 部品ごとに見るなら _tmp_v5/_spk3.scad（part="none" で include）   // 0 が正（板の上面と足の下面は面で接するので 0.01 離す）

if      (part == "look")       spk_assembly();
else if (part == "print_deck") spk_print_deck();
else if (part == "print_tub")  spk_print_tub();
else if (part == "deck")       spk_deck_test();   // 天板のスピーカーの所だけ（座・縁・グリル・手。バスタブもスピーカーも出さない）
else if (part == "check")      spk_check();
else if (part == "none")       {}   // 何も描かない（検査ファイルが include して使う）
else                           spk_exploded();
