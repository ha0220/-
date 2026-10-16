# 제갈량 상소문 자동 실행 설치
#   1) 컴퓨터를 켜고 로그인할 때마다  : 시작프로그램 바로가기
#   2) 매일 오전 7시                  : 작업 스케줄러 (그 시각에 컴퓨터가 꺼져 있었다면 켜질 때 한 번 실행)
#   두 방법이 겹쳐도 하루에 한 번만 열립니다.

$ErrorActionPreference = 'Stop'
$dir      = Split-Path -Parent $MyInvocation.MyCommand.Path
$open     = Join-Path $dir 'open.ps1'
$psExe    = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$psArgs   = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$open`" -Daily"
$taskName = 'JegalRyangSosomun'
$okStartup = $false
$okTask    = $false

Write-Host ''
Write-Host '=== 제갈량 상소문 자동 실행 설치 ===' -ForegroundColor Yellow
Write-Host "설치 위치: $dir"
Write-Host ''

if (-not (Test-Path -LiteralPath $open)) {
    Write-Host '[실패] open.ps1 파일을 찾지 못했습니다. 폴더 전체를 옮겼는지 확인하십시오.' -ForegroundColor Red
    exit 1
}

# 1) 시작프로그램 바로가기 (컴퓨터 켤 때)
try {
    $startupDir = [Environment]::GetFolderPath('Startup')
    $lnkPath    = Join-Path $startupDir 'JegalRyangSosomun.lnk'
    $shell      = New-Object -ComObject WScript.Shell
    $lnk        = $shell.CreateShortcut($lnkPath)
    $lnk.TargetPath       = $psExe
    $lnk.Arguments        = $psArgs
    $lnk.WorkingDirectory = $dir
    $lnk.WindowStyle      = 7
    $lnk.Description      = '제갈량 상소문 (컴퓨터를 켤 때 하루 한 번)'
    $lnk.Save()
    if (Test-Path -LiteralPath $lnkPath) { $okStartup = $true }
} catch {
    Write-Host "[실패] 시작프로그램 등록: $($_.Exception.Message)" -ForegroundColor Red
}
if ($okStartup) { Write-Host '[완료] 컴퓨터를 켜고 로그인할 때마다 상소문이 열립니다.' -ForegroundColor Green }

# 2) 작업 스케줄러 (매일 오전 7시)
try {
    $action   = New-ScheduledTaskAction -Execute $psExe -Argument $psArgs -WorkingDirectory $dir
    $trigger  = New-ScheduledTaskTrigger -Daily -At '07:00'
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description '제갈량 상소문: 매일 오전 7시' -Force | Out-Null
    $info = Get-ScheduledTask -TaskName $taskName | Get-ScheduledTaskInfo
    $okTask = $true
    Write-Host '[완료] 매일 오전 7시에 상소문이 열리도록 등록했습니다.' -ForegroundColor Green
    Write-Host "       다음 실행 예정: $($info.NextRunTime)"
} catch {
    Write-Host "[실패] 오전 7시 등록: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ''
if ($okStartup -and $okTask) {
    Write-Host '모두 설치되었습니다.' -ForegroundColor Green
} elseif ($okStartup -or $okTask) {
    Write-Host '일부만 설치되었습니다. 위의 [실패] 줄을 사진 찍어 알려 주십시오. 그래도 [완료]된 방법은 작동합니다.' -ForegroundColor Yellow
} else {
    Write-Host '설치되지 않았습니다. 위의 [실패] 줄을 사진 찍어 알려 주십시오. (먼저읽어보세요.txt 의 "손으로 하는 방법"을 쓰셔도 됩니다.)' -ForegroundColor Red
}

# 지금 한 번 열어서 눈으로 확인
Write-Host ''
Write-Host '지금 상소문 창을 한 번 열어 봅니다...'
& $psExe -NoProfile -ExecutionPolicy Bypass -File $open
