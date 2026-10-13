#!/bin/sh
# Render first page of each demo PDF to PNG and copy phone photos into public/docs.
set -e
SRC=../data/generated/inbox
OUT=public/docs
mkdir -p "$OUT"
for f in "$SRC"/*.pdf; do
  b=$(basename "$f" .pdf)
  pdftoppm -png -r 110 -f 1 -l 1 -singlefile "$f" "$OUT/$b"
done
cp "$SRC"/IMG_*.png "$OUT"/
