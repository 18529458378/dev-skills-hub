# Windows 系统清理与优化模块

PowerShell 脚本集合，用于 Windows 系统清理、优化、隐私保护。

## 功能

### 清理脚本 (cleanup.ps1)
- **系统临时文件**：`%TEMP%`、`C:\Windows\Temp`、预读取文件
- **浏览器缓存**：Chrome、Edge、Firefox 缓存与历史
- **系统缓存**：Windows Update 缓存、缩略图缓存、错误报告
- **用户垃圾**：回收站、下载目录（可选）、旧日志文件
- **应用缓存**：npm 缓存、pip 缓存、VS Code 缓存
- **磁盘清理**：清理系统还原点（可选）、休眠文件（可选）

### 优化脚本 (optimize.ps1)
- **启动项管理**：禁用不必要的启动程序
- **服务优化**：禁用非必要系统服务
- **注册表优化**：禁用遥测、Cortana、广告推送
- **隐私保护**：禁用诊断数据收集、位置追踪、广告ID
- **性能优化**：禁用视觉效果、调整虚拟内存、SSD优化
- **网络优化**：禁用自动更新上传、优化DNS缓存

## 使用方法

### 1. 以管理员身份运行 PowerShell

```powershell
# 右键开始菜单 → Windows PowerShell (管理员)
# 或 Win+X → 终端(管理员)
```

### 2. 允许脚本执行

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 3. 运行清理脚本

```powershell
# 完整清理（推荐）
.\cleanup.ps1

# 仅清理临时文件（快速模式）
.\cleanup.ps1 -Quick

# 清理并显示详细日志
.\cleanup.ps1 -Verbose

# 自动确认所有操作（无人值守）
.\cleanup.ps1 -Auto
```

### 4. 运行优化脚本

```powershell
# 应用所有优化
.\optimize.ps1

# 仅优化隐私设置
.\optimize.ps1 -PrivacyOnly

# 仅优化性能
.\optimize.ps1 -PerformanceOnly

# 恢复默认设置
.\optimize.ps1 -Restore
```

## 清理项说明

| 类别 | 路径/位置 | 安全等级 |
|------|-----------|----------|
| 用户临时文件 | `%TEMP%` | 安全 |
| 系统临时文件 | `C:\Windows\Temp` | 安全 |
| Windows Update缓存 | `C:\Windows\SoftwareDistribution\Download` | 安全 |
| 缩略图缓存 | `%LOCALAPPDATA%\Microsoft\Windows\Explorer` | 安全 |
| 浏览器缓存 | Chrome/Edge/Firefox | 安全 |
| 回收站 | 所有驱动器 | 安全 |
| 旧系统文件 | `C:\Windows.old` | 谨慎（删除后无法回退系统） |
| 休眠文件 | `C:\hiberfil.sys` | 谨慎（禁用休眠功能） |

## 注意事项

1. **建议先创建系统还原点**
   ```powershell
   Checkpoint-Computer -Description "Before cleanup" -RestorePointType MODIFY_SETTINGS
   ```

2. **清理前关闭所有应用程序**，避免文件占用导致清理不完整

3. **首次运行建议不加 `-Auto` 参数**，逐项确认清理内容

4. **优化脚本会修改注册表**，建议先导出注册表备份

## 兼容性

- Windows 10 (1809+)
- Windows 11 (所有版本)
- PowerShell 5.1+ / PowerShell 7+
