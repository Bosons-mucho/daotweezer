param(
    [switch]$SkipScoop,
    [switch]$SkipChocolatey
)

function Get-KnownMakeCommand {
    $knownCommands = @(
        (Get-Command make -ErrorAction SilentlyContinue),
        (Get-Command mingw32-make -ErrorAction SilentlyContinue)
    ) | Where-Object { $_ }

    if ($knownCommands) {
        return $knownCommands[0]
    }

    $candidatePaths = @(
        "C:\Program Files (x86)\GnuWin32\bin\make.exe",
        "C:\Program Files\GnuWin32\bin\make.exe",
        "$env:ProgramData\chocolatey\bin\make.exe",
        "$env:USERPROFILE\scoop\apps\make\current\bin\make.exe",
        "$env:USERPROFILE\scoop\shims\make.exe"
    )

    foreach ($candidatePath in $candidatePaths) {
        if (Test-Path $candidatePath) {
            return Get-Item $candidatePath
        }
    }

    return $null
}

function Add-DirectoryToProcessPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Directory
    )

    $pathEntries = $env:Path -split ";"
    if ($pathEntries -contains $Directory) {
        return
    }

    $env:Path = "$Directory;$env:Path"
}

function Test-MakeAvailable {
    return [bool](Get-KnownMakeCommand)
}

function Sync-PathFromRegistry {
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $combinedPath = @($userPath, $machinePath) | Where-Object { $_ } | Select-Object -Unique
    $env:Path = ($combinedPath -join ";")
}

function Resolve-MakeForCurrentSession {
    Sync-PathFromRegistry

    $makeCommand = Get-KnownMakeCommand
    if (-not $makeCommand) {
        return $null
    }

    $makePath = if ($makeCommand.PSObject.Properties["Source"]) {
        $makeCommand.Source
    }
    else {
        $makeCommand.FullName
    }

    if (-not $makePath) {
        return $null
    }

    Add-DirectoryToProcessPath -Directory (Split-Path $makePath -Parent)
    return $makePath
}

function Invoke-InstallStep {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Label,

        [Parameter(Mandatory = $true)]
        [scriptblock]$Action
    )

    Write-Host "Attempting $Label..."
    try {
        & $Action
        $resolvedMakePath = Resolve-MakeForCurrentSession
        if ($resolvedMakePath) {
            Write-Host "Installed make successfully via $Label."
            Write-Host "Using make from $resolvedMakePath"
            return $true
        }
        Write-Host "$Label completed, but make is still not available on PATH in this shell."
        return $false
    }
    catch {
        Write-Warning "$Label failed: $($_.Exception.Message)"
        return $false
    }
}

if (Test-MakeAvailable) {
    $resolvedMakePath = Resolve-MakeForCurrentSession
    Write-Host "GNU make is already available."
    if ($resolvedMakePath) {
        Write-Host "Using make from $resolvedMakePath"
    }
    exit 0
}

$wingetCommand = Get-Command winget -ErrorAction SilentlyContinue
if ($wingetCommand) {
    if (Invoke-InstallStep -Label "winget + GnuWin32.Make" -Action {
        & $wingetCommand.Source install -e --id GnuWin32.Make --accept-package-agreements --accept-source-agreements
    }) {
        exit 0
    }
}

if (-not $SkipScoop) {
    $scoopCommand = Get-Command scoop -ErrorAction SilentlyContinue
    if ($scoopCommand) {
        if (Invoke-InstallStep -Label "Scoop make" -Action {
            & $scoopCommand.Source install make
        }) {
            exit 0
        }
    }
}

if (-not $SkipChocolatey) {
    $chocoCommand = Get-Command choco -ErrorAction SilentlyContinue
    if ($chocoCommand) {
        if (Invoke-InstallStep -Label "Chocolatey make" -Action {
            & $chocoCommand.Source install make -y
        }) {
            exit 0
        }
    }
}

Write-Error @"
Could not install GNU make automatically.

Checked package managers:
  - winget package GnuWin32.Make
  - Scoop package make
  - Chocolatey package make

Next steps:
  1. Install GNU make with one of the supported package managers.
  2. Open a new PowerShell session so PATH is refreshed.
  3. Re-run:
       Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
       .\scripts\redpitaya\build_project.ps1
"@
exit 1
