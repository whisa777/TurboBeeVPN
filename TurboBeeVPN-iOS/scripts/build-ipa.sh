#!/usr/bin/env bash
# Собирает несвязанный (unsigned) IPA для ручной подписи через
# Sideloadly / AltStore. Расширение пакета остаётся внутри Payload.
set -euo pipefail

SCHEME="${SCHEME:-TurboBeeVPN}"
CONFIGURATION="${CONFIGURATION:-Release}"
BUILD_DIR="${BUILD_DIR:-build}"

rm -rf "${BUILD_DIR}"

echo ">>> xcodebuild archive (${SCHEME} / ${CONFIGURATION})"
xcodebuild \
  -project TurboBeeVPN.xcodeproj \
  -scheme "${SCHEME}" \
  -configuration "${CONFIGURATION}" \
  -destination 'generic/platform=iOS' \
  -derivedDataPath "${BUILD_DIR}/DerivedData" \
  -archivePath "${BUILD_DIR}/TurboBeeVPN.xcarchive" \
  CODE_SIGNING_ALLOWED=NO \
  CODE_SIGNING_REQUIRED=NO \
  CODE_SIGN_IDENTITY="" \
  archive

APP="${BUILD_DIR}/TurboBeeVPN.xcarchive/Products/Applications/TurboBeeVPN.app"
if [ ! -d "${APP}" ]; then
  echo "error: .app not found: ${APP}" >&2
  exit 1
fi

# Ad-hoc подпись с entitlements (Network Extension).
# Sideloadly / AltStore / SideStore читают entitlements из сигнатуры при ре-подписи.
# Без этого capability не переносится, и saveToPreferences() падает с
# NEVPNErrorDomain code 5 "permission denied" (профиль VPN не создаётся).
echo ">>> ad-hoc signing with entitlements (packet-tunnel-provider)"
if [ -d "${APP}/PlugIns/PacketTunnel.appex" ]; then
  codesign --force --sign - \
    --entitlements "${PWD}/PacketTunnel/PacketTunnel.entitlements" \
    "${APP}/PlugIns/PacketTunnel.appex"
fi
codesign --force --sign - \
  --entitlements "${PWD}/TurboBeeVPN/TurboBeeVPN.entitlements" \
  "${APP}"

echo ">>> packing IPA"
mkdir -p "${BUILD_DIR}/Payload"
cp -R "${APP}" "${BUILD_DIR}/Payload/"
cd "${BUILD_DIR}"
zip -qry TurboBeeVPN-unsigned.ipa Payload
cd ..

echo ">>> done: ${BUILD_DIR}/TurboBeeVPN-unsigned.ipa"
