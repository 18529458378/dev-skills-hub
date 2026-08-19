<#
.SYNOPSIS
    Windows 系统优化工具 - 性能优化、隐私保护、启动项管理
.DESCRIPTION
    通过修改注册表、服务、启动项等方式优化 Windows 系统性能和隐私
.NOTES
    版本: 2.0.0
    需要: 管理员权限
    建议: 运行前创建系统还原点
#>

[CmdletBinding()]
param(
    [switch]$PrivacyOnly,     # 仅优化隐私
    [switch]$PerformanceOnly, # 仅优化性能
    [switch]$Restore,         # 恢复默认设置
    [switch]$Auto,            # 自动确认
    [switch]$Backup           # 仅备份当前设置
)

#Requires -RunAsAdministrator

$ErrorActionPreference = "SilentlyContinue"
$backupDir = "$env:USERPROFILE\Desktop\WindowsOptimize-Backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
$changes = @()

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "HH:mm:ss"
    switch ($Level) {
        "INFO"    { Write-Host "[$timestamp] $Message" -ForegroundColor Cyan }
        "SUCCESS" { Write-Host "[$timestamp] ✓ $Message" -ForegroundColor Green }
        "WARN"    { Write-Host "[$timestamp] ⚠ $Message" -ForegroundColor Yellow }
        "ERROR"   { Write-Host "[$timestamp] ✗ $Message" -ForegroundColor Red }
    }
    $script:changes += "[$timestamp] $Message"
}

function Backup-RegistryKey {
    param([string]$KeyPath, [string]$FileName)
    $safeName = $FileName -replace '[\\/:*?"<>|]', '_'
    $backupFile = Join-Path $script:backupDir "$safeName.reg"
    reg export $KeyPath $backupFile /y | Out-Null
    Write-Log "已备份注册表: $KeyPath"
}

function Set-RegistryValue {
    param(
        [string]$Path,
        [string]$Name,
        $Value,
        [string]$Type = "DWord",
        [string]$Description
    )

    if ($Restore) { return }

    if (-not (Test-Path $Path)) {
        New-Item -Path $Path -Force | Out-Null
    }

    $oldValue = (Get-ItemProperty -Path $Path -Name $Name -ErrorAction SilentlyContinue).$Name
    Set-ItemProperty -Path $Path -Name $Name -Value $Value -Type $Type -Force

    if ($Description) {
        Write-Log "$Description (旧值: $oldValue → 新值: $Value)" "SUCCESS"
    }
}

function Disable-ServiceSafe {
    param([string]$ServiceName, [string]$Description)
    if ($Restore) { return }
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($service) {
        Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
        Set-Service -Name $ServiceName -StartupType Disabled -ErrorAction SilentlyContinue
        Write-Log "已禁用服务: $Description ($ServiceName)" "SUCCESS"
    }
}

function Confirm-Action {
    param([string]$Message)
    if ($Auto) { return $true }
    $response = Read-Host "`n$Message (Y/N)"
    return ($response -eq "Y" -or $response -eq "y")
}

# ========== 主程序 ==========

Write-Host "`n========================================" -ForegroundColor Blue
Write-Host "  Windows 系统优化工具 v2.0" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Blue

# 创建备份目录
if (-not $Restore) {
    New-Item -Path $backupDir -ItemType Directory -Force | Out-Null
    Write-Log "备份目录: $backupDir"
}

if ($Backup) {
    Write-Host "`n*** 仅备份模式 ***" -ForegroundColor Yellow
    # 备份关键注册表
    Backup-RegistryKey "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" "Explorer-Advanced"
    Backup-RegistryKey "HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection" "DataCollection"
    Backup-RegistryKey "HKCU:\Software\Microsoft\Windows\CurrentVersion\Search" "Search"
    Write-Log "备份完成！" "SUCCESS"
    exit 0
}

if ($Restore) {
    Write-Host "`n*** 恢复模式 ***" -ForegroundColor Yellow
    Write-Log "请从备份目录手动导入注册表文件: $backupDir" "WARN"
    Write-Log "或重新运行 Windows 安装程序修复" "WARN"
    exit 0
}

# ========== 隐私优化 ==========
if (-not $PerformanceOnly) {
    Write-Host "`n--- 隐私优化 ---" -ForegroundColor Magenta

    if (Confirm-Action "是否应用隐私优化设置?") {
        # 禁用遥测和数据收集
        Set-RegistryValue -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection" `
            -Name "AllowTelemetry" -Value 0 -Description "禁用遥测数据收集"

        Set-RegistryValue -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\System" `
            -Name "AllowActivityFeed" -Value 0 -Description "禁用活动历史记录"

        # 禁用广告ID
        Set-RegistryValue -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo" `
            -Name "Enabled" -Value 0 -Description "禁用广告ID"

        # 禁用位置追踪
        Set-RegistryValue -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location" `
            -Name "Value" -Value "Deny" -Type "String" -Description "禁用位置追踪"

        # 禁用Cortana
        Set-RegistryValue -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Search" `
            -Name "CortanaEnabled" -Value 0 -Description "禁用Cortana"

        Set-RegistryValue -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\Windows Search" `
            -Name "AllowCortana" -Value 0 -Description "策略禁用Cortana"

        # 禁用开始菜单推荐/广告
        Set-RegistryValue -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager" `
            -Name "SystemPaneSuggestionsEnabled" -Value 0 -Description "禁用系统建议"

        Set-RegistryValue -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager" `
            -Name "SoftLandingEnabled" -Value 0 -Description "禁用软着陆推荐"

        Set-RegistryValue -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager" `
            -Name "SubscribedContent-338388Enabled" -Value 0 -Description "禁用开始菜单广告"

        # 禁用诊断数据
        Set-RegistryValue -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Diagnostics\DiagTrack" `
            -Name "ShowedToastAtLevel" -Value 0 -Description "禁用诊断提示"

        # 禁用墨迹/打字数据收集
        Set-RegistryValue -Path "HKCU:\Software\Microsoft\Input\TIPC" `
            -Name "Enabled" -Value 0 -Description "禁用打字数据收集"

        Write-Log "隐私优化完成" "SUCCESS"
    }
}

# ========== 性能优化 ==========
if (-not $PrivacyOnly) {
    Write-Host "`n--- 性能优化 ---" -ForegroundColor Magenta

    if (Confirm-Action "是否应用性能优化设置?") {
        # 禁用视觉效果
        Set-RegistryValue -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects" `
            -Name "VisualFXSetting" -Value 2 -Description "设置视觉效果为最佳性能"

        # 禁用透明效果
        Set-RegistryValue -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize" `
            -Name "EnableTransparency" -Value 0 -Description "禁用透明效果"

        # 禁用动画
        Set-RegistryValue -Path "HKCU:\Control Panel\Desktop" `
            -Name "UserPreferencesMask" -Value ([byte[]](0x90,0x12,0x03,0x80,0x10,0x00,0x00,0x00)) `
            -Type "Binary" -Description "禁用窗口动画"

        # 加快菜单显示
        Set-RegistryValue -Path "HKCU:\Control Panel\Desktop" `
            -Name "MenuShowDelay" -Value "100" -Type "String" -Description "加快菜单显示速度"

        # 禁用启动延迟
        Set-RegistryValue -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Serialize" `
            -Name "StartupDelayInMSec" -Value 0 -Description "禁用启动延迟"

        # 禁用Windows搜索索引（可选，SSD推荐）
        if (Confirm-Action "是否禁用Windows搜索索引服务（SSD推荐，HDD不建议）?") {
            Disable-ServiceSafe -ServiceName "WSearch" -Description "Windows搜索索引"
        }

        # 禁用SysMain（Superfetch，SSD推荐）
        if (Confirm-Action "是否禁用SysMain/Superfetch（SSD推荐）?") {
            Disable-ServiceSafe -ServiceName "SysMain" -Description "SysMain/Superfetch"
        }

        # 禁用不必要的服务
        $disableServices = @(
            @{Name = "DiagTrack"; Desc = "连接用户体验和遥测"},
            @{Name = "dmwappushservice"; Desc = "WAP推送消息服务"},
            @{Name = "RetailDemo"; Desc = "零售演示服务"},
            @{Name = "lfsvc"; Desc = "地理定位服务"}
        )
        foreach ($svc in $disableServices) {
            Disable-ServiceSafe -ServiceName $svc.Name -Description $svc.Desc
        }

        # 优化虚拟内存（系统管理）
        Set-RegistryValue -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" `
            -Name "ClearPageFileAtShutdown" -Value 0 -Description "关机时不清理页面文件（加快关机）"

        # 禁用自动更新重启
        Set-RegistryValue -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU" `
            -Name "NoAutoRebootWithLoggedOnUsers" -Value 1 -Description "用户登录时不自动重启"

        Write-Log "性能优化完成" "SUCCESS"
    }
}

# ========== 网络优化 ==========
if (-not $PrivacyOnly -and -not $PerformanceOnly) {
    Write-Host "`n--- 网络优化 ---" -ForegroundColor Magenta

    if (Confirm-Action "是否应用网络优化设置?") {
        # 禁用自动更新上传（P2P）
        Set-RegistryValue -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\DeliveryOptimization\Config" `
            -Name "DODownloadMode" -Value 0 -Description "禁用更新P2P上传"

        # 刷新DNS缓存
        ipconfig /flushdns | Out-Null
        Write-Log "已刷新DNS缓存" "SUCCESS"

        # 重置Winsock
        if (Confirm-Action "是否重置Winsock目录（需要重启）?") {
            netsh winsock reset | Out-Null
            Write-Log "已重置Winsock，需要重启生效" "WARN"
        }

        Write-Log "网络优化完成" "SUCCESS"
    }
}

# ========== 完成 ==========
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  优化完成！" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

Write-Host "修改摘要:" -ForegroundColor Cyan
$changes | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }

Write-Host "`n备份位置: $backupDir" -ForegroundColor Yellow
Write-Host "建议重启电脑使所有设置生效`n" -ForegroundColor Yellow

# 保存操作日志
$logPath = "$backupDir\optimize-log.txt"
$changes | Out-File $logPath -Encoding UTF8
