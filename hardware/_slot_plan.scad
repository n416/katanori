// 帯 B を溝の高さ（Z 33.0〜34.3）で水平に切った図（2026-08-25）。
//   PowerBoost の前 2 穴は、六角の穴から帯の後ろの面まで幅 4.3 の通路が抜けている＝ナットは横から差す。
//   電流計の後穴（左）は板が低いぶん溝も低い（Z 29.75〜31.45）ので、この高さでは丸い通し穴しか見えない。
include <case_v4.scad>
part = "none";
color("#cbd5e0") intersection() { straps_v4(); translate([12, 32.5, 33.0]) cube([42, 11, 1.3]); }
color("#4a5568") intersection() { seat_hw();   translate([12, 32.5, 33.0]) cube([42, 11, 1.3]); }
