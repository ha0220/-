# 제갈량 상소문 창 열기
#   open.ps1          : 눌렀을 때 항상 열기
#   open.ps1 -Daily   : "오늘 이미 열었으면 건너뛰기" (자동 실행용. 아침 7시 + 컴퓨터 켤 때 두 번 열리는 것을 막음)
param([switch]$Daily)

$dir    = Split-Path -Parent $MyInvocation.MyCommand.Path
$html   = Join-Path $dir 'sosomun.html'
$marker = Join-Path $dir 'last_shown.txt'
$today  = (Get-Date).ToString('yyyy-MM-dd')

if (-not (Test-Path -LiteralPath $html)) { exit 1 }

if ($Daily) {
    if (Test-Path -LiteralPath $marker) {
        $last = (Get-Content -LiteralPath $marker -ErrorAction SilentlyContinue | Select-Object -First 1)
        if ($last -eq $today) { exit 0 }
    }
    Set-Content -LiteralPath $marker -Value $today -Encoding ASCII -ErrorAction SilentlyContinue
}

# 한글·띄어쓰기가 들어간 경로도 안전하게 file:// 주소로 바꿉니다
$uri = $null
try { $uri = ([System.Uri]::new($html, [System.UriKind]::Absolute)).AbsoluteUri } catch { }
if (-not $uri) { $uri = 'file:///' + (($html -replace '\\', '/') -replace ' ', '%20') }
$opened = $false

# 1순위: 주소창 없는 "앱 창"으로 (엣지는 윈도우에 기본 설치되어 있음), 2순위: 크롬
foreach ($browser in @('msedge', 'chrome')) {
    try {
        Start-Process -FilePath $browser -ArgumentList @("--app=$uri", '--window-size=980,900') -ErrorAction Stop
        $opened = $true
        break
    } catch { }
}

# 3순위: 평소 쓰는 브라우저로 열기
if (-not $opened) {
    Start-Process -FilePath $html
}
