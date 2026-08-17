#!/usr/bin/env bash
# Собирает Libbox.xcframework из исходников sing-box (ветка testing).
# Нужен Go и Xcode (macOS runner).
set -euo pipefail

SING_BOX_VERSION="${SING_BOX_VERSION:-testing}"
GOMOBILE_VERSION="v0.1.13"
OUT_DIR="${1:-Frameworks}"

echo ">>> installing gomobile/gobind (${GOMOBILE_VERSION})"
go install "github.com/sagernet/gomobile/cmd/gomobile@${GOMOBILE_VERSION}"
go install "github.com/sagernet/gomobile/cmd/gobind@${GOMOBILE_VERSION}"
export PATH="$(go env GOPATH)/bin:${PATH}"

WORK="$(mktemp -d)/sing-box-src"
echo ">>> cloning sing-box@${SING_BOX_VERSION} into ${WORK}"
git clone --depth 1 --branch "${SING_BOX_VERSION}" https://github.com/SagerNet/sing-box.git "${WORK}"

echo ">>> building Libbox.xcframework (target: apple, platform: ios,iossimulator)"
cd "${WORK}"
go run ./cmd/internal/build_libbox -target apple -platform ios,iossimulator

mkdir -p "${OUT_DIR}"
rm -rf "${OUT_DIR}/Libbox.xcframework"
cp -R Libbox.xcframework "${OUT_DIR}/"
echo ">>> done: ${OUT_DIR}/Libbox.xcframework"
