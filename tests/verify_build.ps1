$ErrorActionPreference = "Stop"

function Log {
    param($Message)
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Message" -ForegroundColor Cyan
}

function ErrorLog {
    param($Message)
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] ERROR: $Message" -ForegroundColor Red
}

$WorkspaceRoot = "C:\Users\fabia\GitHub\SwitchCraft"
Set-Location $WorkspaceRoot

# 1. Clean previous build
Log "Cleaning previous build artifacts..."
if (Test-Path "dist/SwitchCraft.exe") { Remove-Item "dist/SwitchCraft.exe" -Force }
if (Test-Path "build") { Remove-Item "build" -Recurse -Force }

# 2. Build with PyInstaller
Log "Starting PyInstaller build..."
$buildProcess = Start-Process -FilePath "python" -ArgumentList "-m PyInstaller switchcraft.spec" -NoNewWindow -PassThru -Wait
if ($buildProcess.ExitCode -ne 0) {
    ErrorLog "PyInstaller build failed with exit code $($buildProcess.ExitCode)."
    exit 1
}
Log "Build complete."

# 3. Verify EXE existence
if (-not (Test-Path "dist/SwitchCraft.exe")) {
    ErrorLog "dist/SwitchCraft.exe not found!"
    exit 1
}

# 4. Run EXE and capture output
Log "Running SwitchCraft.exe to check for startup errors..."
$exePath = "$WorkspaceRoot\dist\SwitchCraft.exe"
$out = ""
$err = ""

try {
    # We run it with a timeout. If it stays running for >5 seconds, we assume success (GUI started).
    # If it crashes immediately, it will exit.

    $p = New-Object System.Diagnostics.Process
    $p.StartInfo.FileName = $exePath
    # We can't easily capture stdout of a GUI app unless correct subsystem is set,
    # but we are building a console-enabled app (console=True in spec? check logging)
    # The user said terminal output closes fast, implying console IS attached.
    $p.StartInfo.RedirectStandardOutput = $true
    $p.StartInfo.RedirectStandardError = $true
    $p.StartInfo.UseShellExecute = $false
    $p.StartInfo.CreateNoWindow = $true # We capture output, don't show window

    # Run
    $p.Start() | Out-Null

    # Read output async or just wait a bit
    $startTime = Get-Date

    while (-not $p.HasExited) {
        $out += $p.StandardOutput.ReadToEnd()
        $err += $p.StandardError.ReadToEnd()

        if ((Get-Date) - $startTime -gt (New-TimeSpan -Seconds 5)) {
            Log "App has been running for 5 seconds. Assuming stable startup."
            $p.Kill()
            break
        }
        Start-Sleep -Milliseconds 100
    }

    # Capture remaining
    $out += $p.StandardOutput.ReadToEnd()
    $err += $p.StandardError.ReadToEnd()

    if ($p.HasExited -and $p.ExitCode -ne 0) {
        ErrorLog "App crashed with exit code $($p.ExitCode)!"
        ErrorLog "STDOUT: $out"
        ErrorLog "STDERR: $err"

        if ($out -match "ModuleNotFoundError" -or $err -match "ModuleNotFoundError") {
            ErrorLog "DETECTED: ModuleNotFoundError"
        }
        exit 1
    } else {
        Log "App started successfully (or ran for 5s). Output check:"
        # Check output for python tracebacks even if exit code 0 (some apps allow clean exit on error)
        if ($out -match "Traceback" -or $err -match "Traceback") {
             ErrorLog "Traceback detected in output!"
             ErrorLog "STDERR: $err"
             exit 1
        }
        Log "No tracebacks found."
    }

} catch {
    ErrorLog "Failed to execute: $_"
    exit 1
}

Log "Verification PASSED."
exit 0
