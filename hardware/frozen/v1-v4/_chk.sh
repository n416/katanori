#!/bin/bash
# $1=W $2=PART_SEL $3..=追加の -D
W="$1"; SEL="$2"; shift 2
rm -f _v2c.stl
ERR=$("/c/Program Files/OpenSCAD (Nightly)/openscad.exe" -o _v2c.stl --backend=manifold --export-format binstl -D "W=\"$W\"" -D "PART_SEL=\"$SEL\"" "$@" _btn_v2_chk.scad 2>&1 | grep -ciE "^ERROR|Assertion")
if [ "$ERR" != "0" ]; then echo -n "ERR "; elif [ -f _v2c.stl ]; then python _vol.py _v2c.stl|awk '{printf "%s ", $2}'; else echo -n "0 "; fi
rm -f _v2c.stl
