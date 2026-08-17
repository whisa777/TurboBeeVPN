# Собирает тестовый конфиг (mixed-inbound) из Shared/RoutingData.json,
# проверяет его через sing-box check, прогоняет реальную маршрутизацию
# и останавливает ядро. Воспроизводит логику iOS-конфига ConfigBuilder.
# Требуется: sing-box.exe (параметр -SingBoxPath).
# Использование:
#   powershell -ExecutionPolicy Bypass -File .\windows-test-routing.ps1 -SingBoxPath C:\...\sing-box.exe -SrsDir C:\...\WindowsVPN
param(
    [string]$SingBoxPath = "sing-box.exe",
    [string]$SrsDir = $PSScriptRoot,
    [string]$VlessUrl = "vless://REPLACE_WITH_YOUR_KEY@example.com:443?type=ws"
)
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$singBox = $SingBoxPath

$routing = Get-Content -Raw (Join-Path $root "Shared\RoutingData.json") | ConvertFrom-Json
$srsGeoip  = Join-Path $SrsDir "geoip-ru.srs"
$srsGeosite = Join-Path $SrsDir "geosite-ru.srs"
$configPath = Join-Path $env:TEMP "turbobee-test-config.json"
$logOutPath = Join-Path $env:TEMP "turbobee-singbox-out.log"
$logErrPath = Join-Path $env:TEMP "turbobee-singbox-err.log"

if (-not (Test-Path $srsGeoip) -or -not (Test-Path $srsGeosite)) {
    Write-Host "geoip-ru.srs / geosite-ru.srs not found in $SrsDir" -ForegroundColor Yellow
}

$rules = @(
    @{ action = "sniff" },
    @{ protocol = "dns"; action = "hijack-dns" },
    @{ action = "route"; domain = @($routing.alwaysProxy); outbound = "proxy" },
    @{ action = "route"; domain = @($routing.ruWhitelist); outbound = "direct" },
    @{ action = "route"; rule_set = @("geoip-ru", "geosite-ru"); outbound = "direct" }
)
$ruleSet = @(
    @{ type = "local"; tag = "geoip-ru";  format = "binary"; path = $srsGeoip },
    @{ type = "local"; tag = "geosite-ru"; format = "binary"; path = $srsGeosite }
)

# VLESS-ключ передаётся параметром -VlessUrl
if ($VlessUrl -like "*REPLACE_WITH_YOUR_KEY*") {
    Write-Host "Предупреждение: не передан реальный ключ (-VlessUrl), проверка туннеля не сработает" -ForegroundColor Yellow
}
$vless = $VlessUrl
$m = [regex]::Match($vless, "vless://([a-f0-9-]+)@([^:/?#]+):(\d+)([^#]*)")
$proxy = @{
    type = "vless"; tag = "proxy"
    server = $m.Groups[2].Value; server_port = [int]$m.Groups[3].Value; uuid = $m.Groups[1].Value
    transport = @{ type = "ws"; path = "/ws" }
}

$config = @{
    log = @{ level = "info"; timestamp = $true }
    dns = @{ servers = @(@{ type = "local"; tag = "dns-local" }); final = "dns-local"; strategy = "ipv4_only" }
    inbounds = @(@{ type = "mixed"; tag = "mixed-in"; listen = "127.0.0.1"; listen_port = 10808 })
    outbounds = @($proxy, @{ type = "direct"; tag = "direct" }, @{ type = "block"; tag = "block" })
    route = @{ auto_detect_interface = $true; final = "proxy"; rules = $rules; rule_set = $ruleSet }
}
[System.IO.File]::WriteAllText($configPath, ($config | ConvertTo-Json -Depth 10), (New-Object System.Text.UTF8Encoding($false)))

Write-Host "== sing-box check ==" -ForegroundColor Cyan
& $singBox check -c $configPath
if ($LASTEXITCODE -ne 0) { exit 1 }
Write-Host "check OK" -ForegroundColor Green

Write-Host "== starting sing-box ==" -ForegroundColor Cyan
$p = Start-Process -FilePath $singBox -ArgumentList @("run", "-c", $configPath) -WindowStyle Hidden -PassThru -RedirectStandardOutput $logOutPath -RedirectStandardError $logErrPath
Start-Sleep -Seconds 3
try {
    $directIp = (curl.exe -s --max-time 15 https://api.ipify.org)
    Write-Host "LOCAL IP (direct): $directIp"
    $cases = @(
        @{ url = "https://api.ipify.org"; expect = "proxy" },
        @{ url = "https://www.youtube.com"; expect = "proxy" },
        @{ url = "https://ya.ru"; expect = "direct" },
        @{ url = "https://vk.com"; expect = "direct" },
        @{ url = "https://3dnews.ru"; expect = "direct" },
        @{ url = "https://www.google.com"; expect = "proxy" }
    )
    foreach ($c in $cases) {
        if ($c.url -like "*ipify*") {
            $body = (curl.exe -s --max-time 20 --socks5-hostname 127.0.0.1:10808 $c.url) -join ""
            $code = $LASTEXITCODE
            $verdict = if ($code -eq 0 -and $body) { "OK" } else { "FAIL" }
            Write-Host ("{0,-5} {1,-30} http={2} body={3} (expect {4})" -f $verdict, $c.url, $code, $body, $c.expect)
        } else {
            $code = (curl.exe -s -o NUL --max-time 20 --socks5-hostname 127.0.0.1:10808 -w "%{http_code}" $c.url)
            $verdict = if ($code -ne "000") { "OK" } else { "FAIL" }
            Write-Host ("{0,-5} {1,-30} http={2} (expect {3})" -f $verdict, $c.url, $code, $c.expect)
        }
    }
    Write-Host "== route decisions from sing-box log ==" -ForegroundColor Cyan
    Get-Content $logErrPath -ErrorAction SilentlyContinue | Select-String "outbound connection to" | ForEach-Object { ($_ -replace ".*outbound/", "") -replace "\[[0-9a-z]+\].*", "" } | Select-Object -Unique
} finally {
    Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
    Write-Host "sing-box stopped"
}
