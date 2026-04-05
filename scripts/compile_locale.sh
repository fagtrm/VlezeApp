#!/usr/bin/env bash
# Компилировать .po → .mo для всех языков
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCALE_DIR="$SCRIPT_DIR/../locale"

for po_file in "$LOCALE_DIR"/*/LC_MESSAGES/vlezeapp.po; do
    mo_file="${po_file%.po}.mo"
    msgfmt -o "$mo_file" "$po_file"
    lang=$(basename "$(dirname "$(dirname "$po_file")")")
    echo "Compiled: $lang → $(basename "$mo_file")"
done
