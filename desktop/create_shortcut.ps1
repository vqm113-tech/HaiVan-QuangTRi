# ==========================================
# desktop\create_shortcut.ps1
# Tao shortcut ngoai Desktop, tro toi run_app.bat (cach nhanh, khong can .exe)
# hoac toi HaiVanQuangTri.exe (neu da build) - tu dong chon file nao co san.
#
# Chay: click phai file nay -> "Run with PowerShell"
# (neu bao loi "khong cho phep chay script", mo PowerShell voi quyen Admin
#  roi go: Set-ExecutionPolicy RemoteSigned -Scope CurrentUser)
# ==========================================

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$exePath = Join-Path $scriptDir "dist\HaiVanQuangTri\HaiVanQuangTri.exe"
$batPath = Join-Path $scriptDir "run_app.bat"

if (Test-Path $exePath) {
    $target = $exePath
    Write-Host "Da tim thay file .exe -> tao shortcut toi: $target"
} else {
    $target = $batPath
    Write-Host "Chua build .exe -> tao shortcut toi ban chay nhanh: $target"
    Write-Host "(Xem BUILD_EXE.md neu muon build thanh .exe that su)"
}

$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "He thong Du bao Hai van Quang Tri.lnk"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($shortcutPath)
$Shortcut.TargetPath = $target
$Shortcut.WorkingDirectory = Split-Path $target
$Shortcut.Description = "He thong Du bao Hai van Quang Tri"
$Shortcut.Save()

Write-Host ""
Write-Host "Da tao shortcut ngoai Desktop: $shortcutPath"
