# Notification System for Claude Code Sessions

## Problem
Claude Code doesn't have built-in "waiting for user" notifications, and hooks are limited to specific tool events.

## Solutions

### Option 1: Manual Notification (Simplest)
When you see this marker in my responses:
```
🔔 === NEED YOUR INPUT === 🔔
```
Or:
```
✅ === TASK COMPLETE === ✅
```

Run: `C:\Users\steph\notify.bat`

### Option 2: Watch for Text Pattern
Use a terminal that supports text notifications (Windows Terminal + PowerShell):
```powershell
# This watches for my markers and beeps
# (Run in a separate terminal)
Get-Content -Path "C:\Users\steph\.claude\history.jsonl" -Wait |
  Where-Object { $_ -match "NEED YOUR INPUT|TASK COMPLETE" } |
  ForEach-Object { [console]::beep(1000,500) }
```

### Option 3: PowerShell Scripts
Created two scripts in your home directory:

**Simple (most reliable):**
```powershell
powershell -File C:\Users\steph\notify-simple.ps1 -Message "Check Claude Code"
```

**Full (toast + sound):**
```powershell
powershell -File C:\Users\steph\notify.ps1 -Title "Claude Code" -Message "Ready for input"
```

### Option 4: External Monitoring
Use a tool like:
- **AutoHotkey** - Monitor clipboard or specific window text
- **Windows Task Scheduler** - Run notification every N minutes during work
- **Browser Extension** - Some can monitor claude.com for specific text

## My Convention

I will use these markers clearly:

**When I need your input:**
```
🔔 === NEED YOUR INPUT === 🔔
[Explanation of what I need]
```

**When I'm done with a phase/task:**
```
✅ === TASK COMPLETE === ✅
[Summary of what was done]
```

**When there's an error/blocker:**
```
⚠️ === BLOCKED === ⚠️
[Explanation of the blocker]
```

You can Ctrl+F for these markers in the conversation.

## Testing

Run this to test the simple notification:
```batch
C:\Users\steph\notify.bat "Test successful"
```

You should hear 3 beeps (ascending pitch) if your system volume is on.
