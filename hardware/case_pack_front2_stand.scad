// 箱詰めスタディ ── 立てた版
//
// **case_pack_front2.scad の中身をそのまま使い、フラグだけ差し替える。**
// 🔒 コピーしていない。本体を直せばこちらにも反映される。
//
//   openscad hardware/case_pack_front2_stand.scad
//
// ⚠ 本体の既定は S_CORRIDOR=1（行Sの線が全部パネルへ出る＝上限）だが、
//    これまで報告してきた数字はすべて **S_CORRIDOR=0**（下段へ降りる＝下限）で出している。
//    ここで 0 に揃えてある。**行Sの6本をどう逃がすかは未決**なので、
//    決まったら両方の版のここを直すこと。

include <case_pack_front2.scad>

STAND_ALL  = true;    // ← ハブ基板も電池も PowerBoost も立てる
S_CORRIDOR = 0;
