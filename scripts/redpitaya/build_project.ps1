param(
    [string]$MainRepoProject,
    [string]$RedPitayaRepo,
    [switch]$MirrorLocalProject
)

function Convert-WindowsPathToWsl {
    param(
        [Parameter(Mandatory = $true)]
        [string]$WindowsPath
    )

    $normalized = $WindowsPath -replace "\\", "/"
    if ($normalized -match "^([A-Za-z]):/(.*)$") {
        $drive = $matches[1].ToLowerInvariant()
        $rest = $matches[2]
        return "/mnt/$drive/$rest"
    }

    throw "Unable to convert Windows path to a WSL path: $WindowsPath"
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

function Resolve-VivadoBinDirectory {
    $vivadoCommand = Get-Command vivado -ErrorAction SilentlyContinue
    if ($vivadoCommand) {
        return Split-Path $vivadoCommand.Source -Parent
    }

    $candidateVivadoPaths = @(
        "D:\Xilinx\Vivado\2020.1\bin\vivado.bat",
        "D:\Xilinx\Vivado\2020.1\bin\vivado.exe",
        "C:\Xilinx\Vivado\2020.1\bin\vivado.bat",
        "C:\Xilinx\Vivado\2020.1\bin\vivado.exe"
    )

    foreach ($candidateVivadoPath in $candidateVivadoPaths) {
        if (Test-Path $candidateVivadoPath) {
            return Split-Path $candidateVivadoPath -Parent
        }
    }

    return $null
}

function Invoke-RedPitayaMake {
    param(
        [Parameter(Mandatory = $true)]
        [string]$WorkingDirectory,

        [Parameter(Mandatory = $true)]
        [string[]]$MakeArguments
    )

    $makeCommand = Get-Command make -ErrorAction SilentlyContinue
    if ($makeCommand) {
        Push-Location $WorkingDirectory
        try {
            & $makeCommand.Source @MakeArguments
        }
        finally {
            Pop-Location
        }
        return
    }

    $mingwMakeCommand = Get-Command mingw32-make -ErrorAction SilentlyContinue
    if ($mingwMakeCommand) {
        Push-Location $WorkingDirectory
        try {
            & $mingwMakeCommand.Source @MakeArguments
        }
        finally {
            Pop-Location
        }
        return
    }

    $knownMakePaths = @(
        "C:\Program Files (x86)\GnuWin32\bin\make.exe",
        "C:\Program Files\GnuWin32\bin\make.exe",
        "$env:ProgramData\chocolatey\bin\make.exe",
        "$env:USERPROFILE\scoop\apps\make\current\bin\make.exe",
        "$env:USERPROFILE\scoop\shims\make.exe"
    )
    foreach ($knownMakePath in $knownMakePaths) {
        if (Test-Path $knownMakePath) {
            Push-Location $WorkingDirectory
            try {
                & $knownMakePath @MakeArguments
            }
            finally {
                Pop-Location
            }
            return
        }
    }

    $wslCommand = Get-Command wsl.exe -ErrorAction SilentlyContinue
    if ($wslCommand) {
        $wslDistros = & $wslCommand.Source -l -q 2>$null
        if ($LASTEXITCODE -eq 0 -and $wslDistros) {
            $wslWorkingDirectory = Convert-WindowsPathToWsl -WindowsPath $WorkingDirectory
            $quotedArgs = ($MakeArguments | ForEach-Object { "'$_'" }) -join " "
            & $wslCommand.Source bash -lc "cd '$wslWorkingDirectory' && make $quotedArgs"
            return
        }
    }

    throw "GNU make was not found. Install make on Windows, or configure WSL with a Linux distro and make installed, then rerun this script."
}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$WorkspaceRoot = Split-Path $RepoRoot -Parent

if (-not $MainRepoProject) {
    $MainRepoProject = Join-Path $RepoRoot "fpga\redpitaya_projects\daotweezer_v1"
}

if (-not $RedPitayaRepo) {
    $RedPitayaRepo = Join-Path $WorkspaceRoot "RedPitaya-FPGA"
}

$ExternalProjectDir = Join-Path $RedPitayaRepo "prj\daotweezer_v1\project"
$LocalMirrorDir = Join-Path $MainRepoProject "_generated_project"

if (-not (Test-Path $RedPitayaRepo)) {
    throw "RedPitaya-FPGA repository was not found at $RedPitayaRepo"
}

if (-not (Test-Path $MainRepoProject)) {
    throw "Main project source tree was not found at $MainRepoProject"
}

$vivadoBinDirectory = Resolve-VivadoBinDirectory
if (-not $vivadoBinDirectory) {
    throw "Vivado was not found. Install Xilinx Vivado 2020.1 or add vivado.bat to PATH, then rerun this script."
}

Add-DirectoryToProcessPath -Directory $vivadoBinDirectory
Invoke-RedPitayaMake -WorkingDirectory $RedPitayaRepo -MakeArguments @("project", "PRJ=daotweezer_v1", "MODEL=Z10")

if (-not (Test-Path $ExternalProjectDir)) {
    throw "Vivado project was not created at $ExternalProjectDir"
}

Write-Host "Vivado project is available at $ExternalProjectDir\redpitaya.xpr"

if ($MirrorLocalProject) {
    if (Test-Path $LocalMirrorDir) {
        Remove-Item -LiteralPath $LocalMirrorDir -Recurse -Force
    }

    New-Item -ItemType Directory -Path $LocalMirrorDir -Force | Out-Null
    Get-ChildItem -Path $ExternalProjectDir -Force | Copy-Item -Destination $LocalMirrorDir -Recurse -Force
    Write-Host "Mirrored generated Vivado project to $LocalMirrorDir"
}
