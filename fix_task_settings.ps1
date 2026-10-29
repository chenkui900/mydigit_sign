$ErrorActionPreference = 'Stop'
try {
    $t = Get-ScheduledTask -TaskName '数码之家自动签到'
    $s = $t.Settings
    $s.StopIfGoingOnBatteries = $false
    $s.IdleSettings.StopOnIdleEnd = $false
    Set-ScheduledTask -TaskName '数码之家自动签到' -Settings $s | Out-Null
    Write-Host '[成功] 已修改：电脑从空闲转为使用中时不再终止任务；电池模式不停止。' -ForegroundColor Green
    $t2 = Get-ScheduledTask -TaskName '数码之家自动签到'
    Write-Host ('StopOnIdleEnd          = ' + $t2.Settings.IdleSettings.StopOnIdleEnd)
    Write-Host ('StopIfGoingOnBatteries = ' + $t2.Settings.StopIfGoingOnBatteries)
} catch {
    Write-Host '[提示] 需要管理员权限，正在弹出 UAC 窗口，请在弹窗中点"是"……' -ForegroundColor Yellow
    Start-Process powershell -Verb RunAs -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File', $PSCommandPath)
    exit
}
Read-Host '按回车退出'
