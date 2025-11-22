#!/usr/bin/env bash
set -euo pipefail

red() { printf "\033[31m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
yellow() { printf "\033[33m%s\033[0m\n" "$*"; }

echo "== Checking Poppler (pdfinfo) =="
if command -v pdfinfo >/dev/null 2>&1; then
  green "pdfinfo found: $(pdfinfo -v 2>&1 | head -n1)"
else
  red "pdfinfo (poppler-utils) NOT found. Please install poppler-utils."
fi

echo "\n== Checking Tesseract =="
if command -v tesseract >/dev/null 2>&1; then
  green "tesseract found: $(tesseract --version | head -n1)"
else
  red "tesseract NOT found. Install Tesseract OCR."
fi

echo "\n== Checking Arabic language (ara) =="
if command -v tesseract >/dev/null 2>&1; then
  if tesseract --list-langs 2>/dev/null | grep -q "^ara$"; then
    green "Arabic language (ara) is installed."
  else
    yellow "Arabic 'ara' language not found. Install 'tesseract-ocr-ara' or add ara.traineddata to tessdata."
  fi
fi

echo "\n== Checking Python deps =="
python3 - <<'PY'
import importlib, sys
mods = [
  ('pdf2image', 'pdf2image'),
  ('pytesseract', 'pytesseract'),
  ('PIL', 'Pillow (PIL)'),
  ('pdfplumber', 'pdfplumber'),
  ('fastapi', 'fastapi'),
  ('uvicorn', 'uvicorn'),
]
missing = []
for m,_ in mods:
    try:
        importlib.import_module(m)
        print(f"[OK] {m}")
    except Exception as e:
        print(f"[MISS] {m}: {e}")
        missing.append(m)
print("Missing:", missing)
PY

echo "\n== Done =="