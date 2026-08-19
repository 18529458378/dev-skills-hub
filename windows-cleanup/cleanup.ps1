<#
.SYNOPSIS
    Windows 系统清理工具 - 清理临时文件、缓存、浏览器数据等
.DESCRIPTION
    安全清理 Windows 系统中的各种垃圾文件，释放磁盘空间
.NOTES
    版本: 2.0.0
    需要: 管理员权限
#>

[CmdletBinding()]
param(
    [switch]$Quick,        # 快速模式：仅清理临时文件
    [switch]$Auto,         # 自动确认所有操作
    [switch]$DryRun,       # 模拟运行，不实际删除
    [switch]$IncludeDownloads,  # 包含下载目录（超过30天的文件）
    [switch]$Deep          # 深度清理：包含系统文件、休眠文件等
)

#Requires -RunAsAdministrator

$ErrorActionPreference = "SilentlyContinue"
$totalFreed = 0
$logEntries = @()

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $entry = "[$timestamp] [$Level] $Message"
    $script:logEntries += $entry
    switch ($Level) {
        "INFO"    { Write-Host $entry -ForegroundColor Cyan }
        "SUCCESS" { Write-Host $entry -ForegroundColor Green }
        "WARN"    { Write-Host $entry -ForegroundColor Yellow }
        "ERROR"   { Write-Host $entry -ForegroundColor Red }
    }
}

function Get-FolderSize {
    param([string]$Path)
    if (Test-Path $Path) {
        return (Get-ChildItem $Path -Recurse -Force -ErrorAction SilentlyContinue |
                Measure-Object -Property Length -Sum).Sum
    }
    return 0
}

function Remove-FilesSafe {
    param(
        [string]$Path,
        [string]$Description,
        [string]$Filter = "*",
        [int]$OlderThanDays = 0
    )

    if (-not (Test-Path $Path)) {
        Write-Log "跳过（不存在）: $Description"
        return
    }

    $beforeSize = Get-FolderSize $Path

    if ($DryRun) {
        Write-Log "[模拟] 将清理: $Description ($([math]::Round($beforeSize/1MB, 2)) MB)"
        $script:totalFreed += $beforeSize
        return
    }

    try {
        $items = Get-ChildItem $Path -Filter $Filter -Recurse -Force -ErrorAction SilentlyContinue
        if ($OlderThanDays -gt 0) {
            $cutoff = (Get-Date).AddDays(-$OlderThanDays)
            $items = $items | Where-Object { $_.LastWriteTime -lt $cutoff }
        }

        $items | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue
        $afterSize = Get-FolderSize $Path
        $freed = $beforeSize - $afterSize
        $script:totalFreed += $freed

        if ($freed -gt 0) {
            Write-Log "已清理: $Description (释放 $([math]::Round($freed/1MB, 2)) MB)" "SUCCESS"
        } else {
            Write-Log "无需清理: $Description"
        }
    } catch {
        Write-Log "清理失败: $Description - $_" "ERROR"
    }
}

function Confirm-Action {
    param([string]$Message)
    if ($Auto) { return $true }
    $response = Read-Host "$Message (Y/N)"
    return ($response -eq "Y" -or $response -eq "y")
}

# ========== 主程序 ==========

Write-Host "`n========================================" -ForegroundColor Blue
Write-Host "  Windows 系统清理工具 v2.0" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Blue

if ($DryRun) {
    Write-Host "*** 模拟运行模式 - 不会实际删除文件 ***`n" -ForegroundColor Yellow
}

# 1. 用户临时文件
Write-Log "开始清理临时文件..."
Remove-FilesSafe -Path $env:TEMP -Description "用户临时文件"
Remove-FilesSafe -Path "C:\Windows\Temp" -Description "系统临时文件"
Remove-FilesSafe -Path "C:\Windows\Prefetch" -Description "预读取文件" -Filter "*.pf"

# 2. 浏览器缓存（快速模式也执行）
Write-Log "清理浏览器缓存..."
$browserPaths = @(
    @{Path = "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\Cache"; Desc = "Chrome 缓存"},
    @{Path = "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\Code Cache"; Desc = "Chrome 代码缓存"},
    @{Path = "$env:LOCALAPPDATA\Microsoft\Edge\User Data\Default\Cache"; Desc = "Edge 缓存"},
    @{Path = "$env:LOCALAPPDATA\Mozilla\Firefox\Profiles"; Desc = "Firefox 缓存"},
    @{Path = "$env:APPDATA\Mozilla\Firefox\Profiles"; Desc = "Firefox 配置缓存"}
)
foreach ($b in $browserPaths) {
    Remove-FilesSafe -Path $b.Path -Description $b.Desc
}

if (-not $Quick) {
    # 3. 系统缓存
    Write-Log "清理系统缓存..."
    Remove-FilesSafe -Path "C:\Windows\SoftwareDistribution\Download" -Description "Windows Update 缓存"
    Remove-FilesSafe -Path "$env:LOCALAPPDATA\Microsoft\Windows\Explorer" -Description "缩略图缓存" -Filter "thumbcache_*.db"
    Remove-FilesSafe -Path "C:\ProgramData\Microsoft\Windows\WER" -Description "错误报告"
    Remove-FilesSafe -Path "$env:LOCALAPPDATA\CrashDumps" -Description "崩溃转储"

    # 4. 应用缓存
    Write-Log "清理应用缓存..."
    Remove-FilesSafe -Path "$env:LOCALAPPDATA\npm-cache" -Description "npm 缓存"
    Remove-FilesSafe -Path "$env:LOCALAPPDATA\pip\Cache" -Description "pip 缓存"
    Remove-FilesSafe -Path "$env:APPDATA\Code\Cache" -Description "VS Code 缓存"
    Remove-FilesSafe -Path "$env:APPDATA\Code\CachedData" -Description "VS Code 缓存数据"
    Remove-FilesSafe -Path "$env:LOCALAPPDATA\Temp" -Description "本地临时文件"

    # 5. 日志文件
    Write-Log "清理日志文件..."
    Remove-FilesSafe -Path "C:\Windows\Logs" -Description "系统日志" -OlderThanDays 7
    Remove-FilesSafe -Path "$env:WINDIR\Panther" -Description "安装日志" -OlderThanDays 30

    # 6. 回收站
    if (Confirm-Action "是否清空回收站?") {
        try {
            $recycleSize = (Get-ChildItem 'C:\$Recycle.Bin' -Recurse -Force -ErrorAction SilentlyContinue |
                           Measure-Object -Property Length -Sum).Sum
            Clear-RecycleBin -Force -ErrorAction SilentlyContinue
            $script:totalFreed += $recycleSize
            Write-Log "已清空回收站 (释放 $([math]::Round($recycleSize/1MB, 2)) MB)" "SUCCESS"
        } catch {
            Write-Log "清空回收站失败: $_" "ERROR"
        }
    }

    # 7. 下载目录（可选）
    if ($IncludeDownloads -and (Confirm-Action "是否清理下载目录中超过30天的文件?")) {
        Remove-FilesSafe -Path "$env:USERPROFILE\Downloads" -Description "下载目录(30天前)" -OlderThanDays 30
    }

    # 8. 深度清理
    if ($Deep) {
        Write-Log "执行深度清理..."

        # Windows.old
        if (Test-Path "C:\Windows.old") {
            if (Confirm-Action "是否删除 C:\Windows.old (删除后无法回退到旧系统)?") {
                $oldSize = Get-FolderSize "C:\Windows.old"
                Remove-Item "C:\Windows.old" -Recurse -Force -ErrorAction SilentlyContinue
                $script:totalFreed += $oldSize
                Write-Log "已删除 Windows.old (释放 $([math]::Round($oldSize/1MB, 2)) MB)" "SUCCESS"
            }
        }

        # 休眠文件
        if (Confirm-Action "是否禁用休眠并删除 hiberfil.sys (释放约内存大小的空间)?") {
            powercfg /h off
            Write-Log "已禁用休眠功能" "SUCCESS"
        }

        # 系统还原点
        if (Confirm-Action "是否清理所有系统还原点?") {
            vssadmin delete shadows /all /quiet
            Write-Log "已清理系统还原点" "SUCCESS"
        }
    }
}

# ========== 清理完成 ==========
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  清理完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "总释放空间: $([math]::Round($totalFreed/1MB, 2)) MB ($([math]::Round($totalFreed/1GB, 2)) GB)" -ForegroundColor Cyan
Write-Host "日志条目数: $($logEntries.Count)`n" -ForegroundColor Gray

# 保存日志
$logPath = "$env:USERPROFILE\Desktop\cleanup-log-$(Get-Date -Format 'yyyyMMdd-HHmmss').txt"
$logEntries | Out-File $logPath -Encoding UTF8
Write-Host "日志已保存到: $logPath`n" -ForegroundColor Gray
