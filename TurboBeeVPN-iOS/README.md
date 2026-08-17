# TurboBee VPN (iOS)

iOS-клиент TurboBee VPN: туннель sing-box + NEPacketTunnelProvider + SwiftUI.
Тот же принцип сплит-роутинга, что и в Android-версии:

- **Всегда через VPN** (YouTube, WhatsApp/Meta, OpenAI и др.) — `alwaysProxy`;
- **Белый список RU** (банки, госуслуги, маркетплейсы, операторы и т.д.) — напрямую;
- **geoip-ru + geosite-ru** (если включён переключатель «Bypass RU») — напрямую;
- всё остальное — через VLESS-сервер.

## Структура

```
TurboBeeVPN-iOS/
├── TurboBeeVPN/            # SwiftUI-приложение
│   ├── TurboBeeVPNApp.swift
│   ├── ContentView.swift   # поле vless-ссылки, переключатель, кнопки
│   ├── VPNManager.swift    # NETunnelProviderManager
│   ├── Profile.swift       # модель профиля
│   ├── VlessLinkParser.swift
│   ├── ProfileStore.swift
│   ├── Info.plist
│   └── TurboBeeVPN.entitlements
├── PacketTunnel/           # NEPacketTunnelProvider-расширение
│   ├── PacketTunnelProvider.swift  # запуск sing-box (CommandServer)
│   ├── PlatformInterface.swift     # openTun + протоколы Libbox
│   ├── ConfigBuilder.swift         # JSON-конфиг sing-box из RoutingData.json
│   ├── Resources/geoip-ru.srs      # rule-set (из WindowsVPN)
│   ├── Resources/geosite-ru.srs
│   ├── Info.plist
│   └── PacketTunnel.entitlements
├── Shared/RoutingData.json # единый источник списков alwaysProxy / ruWhitelist
├── Frameworks/             # Libbox.xcframework (собирается CI-скриптом)
├── scripts/                # build-libbox.sh, generate-project.sh, build-ipa.sh,
│                           # windows-test-routing.ps1
├── project.yml             # xcodegen
├── .github/workflows/build.yml
└── codemagic.yaml
```

## Сборка

Проект нельзя собрать на Windows — нужен macOS-раннер. Рабочий цикл:

1. Залить репозиторий на GitHub (или подключить Codemagic).
2. Сборка запускается через GitHub Actions (`workflow_dispatch`/push) или Codemagic:
   - `scripts/build-libbox.sh` — клонирует `SagerNet/sing-box` (ветка `testing`),
     собирает `Libbox.xcframework` через `go run ./cmd/internal/build_libbox -target apple -platform ios,iossimulator`;
   - `scripts/generate-project.sh` — `xcodegen generate`;
   - `scripts/build-ipa.sh` — `xcodebuild archive` без подписи → unsigned IPA.
3. Артефакт `TurboBeeVPN-unsigned.ipa` скачивается и подписывается.

### Локальная сборка на Mac

```bash
brew install xcodegen
go install github.com/sagernet/gomobile/cmd/gomobile@v0.1.13
go install github.com/sagernet/gomobile/cmd/gobind@v0.1.13

bash scripts/build-libbox.sh     # -> Frameworks/Libbox.xcframework
xcodegen generate
bash scripts/build-ipa.sh        # -> build/TurboBeeVPN-unsigned.ipa
```

## Установка (без платного Apple-аккаунта)

1. Скачать `TurboBeeVPN-unsigned.ipa` из артефактов CI.
2. Подписать и установить через **Sideloadly** (или AltStore):
   - Apple ID (бесплатный, можно с привязанным iPhone) + пароль приложения;
   - entitlements приложения включают только `packet-tunnel-provider`,
     App Groups не используются — профиль передаётся через
     `NETunnelProviderProtocol.providerConfiguration`;
3. В приложении вставить vless-ссылку (по умолчанию подставлена рабочая),
   при необходимости включить «Обход российских сайтов» и нажать «Подключить».
4. Первый запуск: iOS спросит разрешение «Разрешить VPN-конфигурации».

Free-аккаунт требует переподписывания раз в 7 дней (Sideloadly это делает автоматически).

## Проверка маршрутизации на Windows (без iOS)

Логика конфига воспроизводится локально на Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows-test-routing.ps1 `
  -SingBoxPath C:\...\sing-box.exe -SrsDir C:\...\WindowsVPN
```

Скрипт собирает тестовый конфиг (mixed-inbound) из `Shared/RoutingData.json`,
прогоняет `sing-box check`, стартует ядро и проверяет реальные маршруты
(youtube→proxy, ya.ru/vk→direct, 3dnews.ru→direct через rule-set, google→proxy),
после чего останавливает ядро.

## Изменение списков доменов

Правки вносятся только в `Shared/RoutingData.json` (используется и Android-версией,
и iOS). Повторно собрать конфиг не нужно — списки читаются из бандла при каждом
запуске туннеля.

## Конфигурация sing-box (что внутри)

- Inbound: `tun` (10.10.0.1/30, mtu 1500, `stack: gvisor`, `auto_redirect: false`).
- DNS: `dns-local`, hijack через правило `hijack-dns`, `strategy: ipv4_only`.
- Правила роутинга: `sniff` → `hijack-dns` → alwaysProxy→proxy →
  ruWhitelist→direct → (rule_set geoip-ru+geosite-ru→direct) → `final: proxy`.
- Outbounds: vless (ws) / direct / block.