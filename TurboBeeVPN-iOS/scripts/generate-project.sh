#!/usr/bin/env bash
# Генерирует TurboBeeVPN.xcodeproj из project.yml (нужен xcodegen).
set -euo pipefail

if ! command -v xcodegen >/dev/null 2>&1; then
  echo ">>> installing xcodegen"
  brew install xcodegen
fi

xcodegen generate
echo ">>> generated TurboBeeVPN.xcodeproj"
