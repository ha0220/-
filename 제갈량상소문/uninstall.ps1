# 제갈량 상소문 자동 실행 끄기 (폴더와 파일은 지우지 않습니다)
$taskName = 'JegalRyangSosomun'
$lnkPath  = Join-Path ([Environment]::GetFolderPath('Startup')) 'JegalRyangSosomun.lnk'

Write-Host ''
Write-Host '=== 제갈량 상소문 자동 실행 끄기 ===' -ForegroundColor Yellow

if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host '[완료] 오전 7시 자동 실행을 껐습니다.' -ForegroundColor Green
} else {
    Write-Host '오전 7시 자동 실행은 원래 켜져 있지 않았습니다.'
}

if (Test-Path -LiteralPath $lnkPath) {
    Remove-Item -LiteralPath $lnkPath -Force
    Write-Host '[완료] 컴퓨터를 켤 때 자동 실행을 껐습니다.' -ForegroundColor Green
} else {
    Write-Host '컴퓨터를 켤 때 자동 실행은 원래 켜져 있지 않았습니다.'
}
