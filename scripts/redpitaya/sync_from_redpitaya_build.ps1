param(
    [string]$MainRepoProject,
    [string]$RedPitayaRepo
)

function Get-NormalizedRelativePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RootPath,

        [Parameter(Mandatory = $true)]
        [string]$FullPath
    )

    $relativePath = [System.IO.Path]::GetRelativePath($RootPath, $FullPath)
    return $relativePath -replace "\\", "/"
}

function Test-FileContentEqual {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FirstPath,

        [Parameter(Mandatory = $true)]
        [string]$SecondPath
    )

    if (-not (Test-Path $FirstPath) -or -not (Test-Path $SecondPath)) {
        return $false
    }

    $firstHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $FirstPath).Hash
    $secondHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $SecondPath).Hash
    return $firstHash -eq $secondHash
}

function Copy-CustomizedFilesFromReference {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ReferenceDir,

        [Parameter(Mandatory = $true)]
        [string]$ExternalDir,

        [Parameter(Mandatory = $true)]
        [string]$RepoDir
    )

    if (-not (Test-Path $ExternalDir)) {
        throw "Expected external source directory was not found: $ExternalDir"
    }

    if (Test-Path $RepoDir) {
        Remove-Item -LiteralPath $RepoDir -Recurse -Force
    }

    New-Item -ItemType Directory -Path $RepoDir -Force | Out-Null

    $copiedFiles = New-Object System.Collections.Generic.List[string]
    $externalFiles = Get-ChildItem -LiteralPath $ExternalDir -Recurse -File

    foreach ($externalFile in $externalFiles) {
        $relativePath = Get-NormalizedRelativePath -RootPath $ExternalDir -FullPath $externalFile.FullName
        $referenceFile = Join-Path $ReferenceDir ($relativePath -replace "/", "\")

        if ((Test-Path $referenceFile) -and (Test-FileContentEqual -FirstPath $externalFile.FullName -SecondPath $referenceFile)) {
            continue
        }

        $repoFile = Join-Path $RepoDir ($relativePath -replace "/", "\")
        $repoFileParent = Split-Path $repoFile -Parent
        if (-not (Test-Path $repoFileParent)) {
            New-Item -ItemType Directory -Path $repoFileParent -Force | Out-Null
        }

        Copy-Item -LiteralPath $externalFile.FullName -Destination $repoFile -Force
        $copiedFiles.Add($relativePath) | Out-Null
    }

    return $copiedFiles
}

function Write-RedPitayaTopPatch {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ReferenceTopFile,

        [Parameter(Mandatory = $true)]
        [string]$CustomizedTopFile,

        [Parameter(Mandatory = $true)]
        [string]$PatchFile
    )

    if (-not (Test-Path $ReferenceTopFile)) {
        throw "Reference top file was not found at $ReferenceTopFile"
    }

    if (-not (Test-Path $CustomizedTopFile)) {
        throw "Customized top file was not found at $CustomizedTopFile"
    }

    $gitCommand = Get-Command git -ErrorAction SilentlyContinue
    if (-not $gitCommand) {
        throw "git was not found in PATH. It is required to regenerate $PatchFile"
    }

    $patchParent = Split-Path $PatchFile -Parent
    if (-not (Test-Path $patchParent)) {
        New-Item -ItemType Directory -Path $patchParent -Force | Out-Null
    }

    $oldLabel = "a/RedPitaya-FPGA/prj/v0.94/rtl/red_pitaya_top.sv"
    $newLabel = "b/fpga/redpitaya_projects/daotweezer_v1/rtl/red_pitaya_top.sv"

    $patchOutput = & $gitCommand.Source diff --no-index --no-ext-diff --src-prefix=a/ --dst-prefix=b/ `
        "--label=$oldLabel" "--label=$newLabel" `
        $ReferenceTopFile $CustomizedTopFile 2>&1

    if ($LASTEXITCODE -gt 1) {
        throw "Failed to regenerate patch file: $($patchOutput -join [Environment]::NewLine)"
    }

    Set-Content -LiteralPath $PatchFile -Value $patchOutput
}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$WorkspaceRoot = Split-Path $RepoRoot -Parent

if (-not $MainRepoProject) {
    $MainRepoProject = Join-Path $RepoRoot "fpga\redpitaya_projects\daotweezer_v1"
}

if (-not $RedPitayaRepo) {
    $RedPitayaRepo = Join-Path $WorkspaceRoot "RedPitaya-FPGA"
}

$ReferenceProject = Join-Path $RedPitayaRepo "prj\v0.94"
$ExternalProject = Join-Path $RedPitayaRepo "prj\daotweezer_v1"

$ReferenceRtlDir = Join-Path $ReferenceProject "rtl"
$ReferenceSdcDir = Join-Path $ReferenceProject "sdc"
$ExternalRtlDir = Join-Path $ExternalProject "rtl"
$ExternalSdcDir = Join-Path $ExternalProject "sdc"
$RepoRtlDir = Join-Path $MainRepoProject "rtl"
$RepoSdcDir = Join-Path $MainRepoProject "sdc"
$PatchFile = Join-Path $MainRepoProject "patches\red_pitaya_top.patch"
$ReferenceTopFile = Join-Path $ReferenceRtlDir "red_pitaya_top.sv"
$CustomizedTopFile = Join-Path $ExternalRtlDir "red_pitaya_top.sv"

if (-not (Test-Path $RedPitayaRepo)) {
    throw "RedPitaya-FPGA repository was not found at $RedPitayaRepo"
}

if (-not (Test-Path $MainRepoProject)) {
    throw "Main project source tree was not found at $MainRepoProject"
}

if (-not (Test-Path $ReferenceRtlDir)) {
    throw "Reference Red Pitaya RTL directory was not found at $ReferenceRtlDir"
}

if (-not (Test-Path $ReferenceSdcDir)) {
    throw "Reference Red Pitaya constraint directory was not found at $ReferenceSdcDir"
}

$copiedRtlFiles = Copy-CustomizedFilesFromReference -ReferenceDir $ReferenceRtlDir -ExternalDir $ExternalRtlDir -RepoDir $RepoRtlDir
$copiedSdcFiles = Copy-CustomizedFilesFromReference -ReferenceDir $ReferenceSdcDir -ExternalDir $ExternalSdcDir -RepoDir $RepoSdcDir
Write-RedPitayaTopPatch -ReferenceTopFile $ReferenceTopFile -CustomizedTopFile $CustomizedTopFile -PatchFile $PatchFile

Write-Host "Reverse sync complete."
Write-Host "Copied customized RTL files:"
if ($copiedRtlFiles.Count -eq 0) {
    Write-Host "- none"
}
else {
    foreach ($rtlFile in $copiedRtlFiles) {
        Write-Host "- $rtlFile"
    }
}

Write-Host "Copied customized constraint files:"
if ($copiedSdcFiles.Count -eq 0) {
    Write-Host "- none"
}
else {
    foreach ($sdcFile in $copiedSdcFiles) {
        Write-Host "- $sdcFile"
    }
}

Write-Host "Regenerated patch file:"
Write-Host "- $PatchFile"
