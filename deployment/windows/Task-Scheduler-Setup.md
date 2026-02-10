# Windows Task Scheduler Setup for FTE Personal AI Employee

This guide configures Windows Task Scheduler to run FTE watchers, orchestrator, and scheduled jobs automatically.

## Prerequisites

- Windows 10/11 or Windows Server
- Python 3.11+ installed
- FTE project cloned to `C:\FTE\Personal-AI-Employee`
- Virtual environment activated and dependencies installed

## Setup Steps

### 1. Create Log Directory

```powershell
New-Item -Path "C:\FTE\logs" -ItemType Directory -Force
```

### 2. Create Service User (Recommended)

```powershell
# Create dedicated user for FTE services
$Password = ConvertTo-SecureString "YourSecurePassword" -AsPlainText -Force
New-LocalUser "FTE-Service" -Password $Password -Description "FTE Personal AI Employee Service Account"
Add-LocalGroupMember -Group "Users" -Member "FTE-Service"

# Grant permissions to FTE directory
icacls "C:\FTE" /grant FTE-Service:(OI)(CI)F /T
```

### 3. Create Scheduled Tasks

#### Gmail Watcher (Continuous)

```xml
<!-- Save as: gmail-watcher-task.xml -->
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>FTE Gmail Watcher - Monitor Gmail for new tasks</Description>
  </RegistrationInfo>
  <Triggers>
    <BootTrigger>
      <Enabled>true</Enabled>
    </BootTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>FTE-Service</UserId>
      <LogonType>Password</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <DisallowStartOnRemoteAppSession>false</DisallowStartOnRemoteAppSession>
    <UseUnifiedSchedulingEngine>true</UseUnifiedSchedulingEngine>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
    <RestartOnFailure>
      <Interval>PT1M</Interval>
      <Count>3</Count>
    </RestartOnFailure>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>C:\FTE\Personal-AI-Employee\.venv\Scripts\python.exe</Command>
      <Arguments>C:\FTE\Personal-AI-Employee\src\watchers\gmail_watcher.py</Arguments>
      <WorkingDirectory>C:\FTE\Personal-AI-Employee</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
```

Import with PowerShell:
```powershell
Register-ScheduledTask -Xml (Get-Content "gmail-watcher-task.xml" | Out-String) -TaskName "FTE-Gmail-Watcher" -User "FTE-Service" -Password "YourSecurePassword"
```

#### Orchestrator (Every 5 minutes)

```powershell
$action = New-ScheduledTaskAction -Execute "C:\FTE\Personal-AI-Employee\.venv\Scripts\python.exe" `
    -Argument "-m src.orchestrator.scheduler" `
    -WorkingDirectory "C:\FTE\Personal-AI-Employee"

$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration ([TimeSpan]::MaxValue)

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

$principal = New-ScheduledTaskPrincipal -UserId "FTE-Service" -LogonType Password

Register-ScheduledTask -TaskName "FTE-Orchestrator" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "FTE Orchestrator - Process tasks every 5 minutes"
```

#### Health Check (Every 5 minutes)

```powershell
$action = New-ScheduledTaskAction -Execute "C:\FTE\Personal-AI-Employee\.venv\Scripts\fte.exe" `
    -Argument "orchestrator health" `
    -WorkingDirectory "C:\FTE\Personal-AI-Employee"

$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration ([TimeSpan]::MaxValue)

Register-ScheduledTask -TaskName "FTE-Health-Check" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "FTE Health Check - Monitor system health"
```

#### CEO Briefing (Weekly Monday 9 AM)

```powershell
$action = New-ScheduledTaskAction -Execute "C:\FTE\Personal-AI-Employee\.venv\Scripts\fte.exe" `
    -Argument "briefing generate --email" `
    -WorkingDirectory "C:\FTE\Personal-AI-Employee"

$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 9am

Register-ScheduledTask -TaskName "FTE-Weekly-Briefing" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "FTE CEO Briefing - Generate and email weekly report"
```

### 4. Verify Tasks

```powershell
# List all FTE tasks
Get-ScheduledTask | Where-Object {$_.TaskName -like "FTE-*"}

# Check task history
Get-ScheduledTaskInfo -TaskName "FTE-Gmail-Watcher"

# Manually run a task
Start-ScheduledTask -TaskName "FTE-Health-Check"

# View task logs
Get-EventLog -LogName "Application" -Source "Task Scheduler" -Newest 10 | Where-Object {$_.Message -like "*FTE*"}
```

### 5. Environment Variables

Set environment variables for the service user:

```powershell
# Option 1: User-level (logged in)
[System.Environment]::SetEnvironmentVariable("VAULT_DIR", "C:\Users\FTE-Service\AI_Employee_Vault", "User")
[System.Environment]::SetEnvironmentVariable("GMAIL_API_KEY", "your-key-here", "User")

# Option 2: System-level (all users)
[System.Environment]::SetEnvironmentVariable("VAULT_DIR", "C:\FTE\AI_Employee_Vault", "Machine")
```

## Monitoring

### View Running Tasks

```powershell
Get-ScheduledTask | Where-Object {$_.State -eq "Running" -and $_.TaskName -like "FTE-*"}
```

### Check Logs

```powershell
# Task Scheduler Event Log
Get-EventLog -LogName "Application" -Source "Task Scheduler" -After (Get-Date).AddDays(-1) |
    Where-Object {$_.Message -like "*FTE*"} |
    Format-Table TimeGenerated, EntryType, Message -AutoSize

# Application Logs (if configured)
Get-Content "C:\FTE\logs\orchestrator.log" -Tail 50
```

### Restart All FTE Tasks

```powershell
Get-ScheduledTask | Where-Object {$_.TaskName -like "FTE-*"} | ForEach-Object {
    Stop-ScheduledTask -TaskName $_.TaskName -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Start-ScheduledTask -TaskName $_.TaskName
}
```

## Troubleshooting

### Task Not Running
1. Check if task is enabled: `Get-ScheduledTask -TaskName "FTE-Gmail-Watcher"`
2. Verify user permissions: `icacls "C:\FTE" /T`
3. Check Event Viewer: Applications and Services Logs > Microsoft > Windows > TaskScheduler

### Python Script Errors
1. Test script manually:
   ```powershell
   cd C:\FTE\Personal-AI-Employee
   .\.venv\Scripts\activate
   python src\watchers\gmail_watcher.py
   ```
2. Check Python path in task: Should point to `.venv\Scripts\python.exe`
3. Verify working directory is set correctly

### Network Issues
- Ensure "Start the task only if the computer is on AC power" is UNCHECKED
- Enable "Run whether user is logged on or not"
- Check "Run with highest privileges" if needed

## Security Best Practices

1. **Use Dedicated Service Account**: Don't run as Administrator
2. **Secure Credentials**: Store API keys in Windows Credential Manager
3. **Least Privilege**: Grant only necessary permissions
4. **Log Rotation**: Implement log cleanup tasks
5. **Monitor Failed Runs**: Set up alerts for task failures

## Uninstall

```powershell
# Remove all FTE tasks
Get-ScheduledTask | Where-Object {$_.TaskName -like "FTE-*"} | Unregister-ScheduledTask -Confirm:$false

# Remove service user
Remove-LocalUser -Name "FTE-Service"

# Remove directories
Remove-Item -Path "C:\FTE" -Recurse -Force
```

## References

- [Task Scheduler Documentation](https://docs.microsoft.com/en-us/windows/win32/taskschd/task-scheduler-start-page)
- [PowerShell ScheduledTasks Module](https://docs.microsoft.com/en-us/powershell/module/scheduledtasks/)
