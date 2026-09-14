#Requires -Version 5.1
<#
    AquaLedger manual PostgreSQL backup client (Windows).

    Run with no arguments for normal use:

        .\scripts\backup-aqualedger.ps1

    Sequence: create -> download (scp -O, temp filenames) -> size check ->
    three-way SHA256 check (create-reported / sidecar / locally computed) ->
    rename to final filenames -> confirm. confirm is only ever reached if
    every earlier stage succeeded - a failure at any stage stops the script
    before confirm, and only removes THIS run's own incomplete temp files,
    never a previously completed backup.

    Uses only the dedicated `aqualedger-backup` SSH alias (never `fish-erp`,
    never an embedded IdentityFile - the alias in ~/.ssh/config owns that).
    Every download uses `scp -O` (legacy protocol) because the production
    wrapper (scripts/backup-ssh-wrapper.sh) only understands that protocol's
    plain `scp -f <path>` command form, not the default SFTP-subsystem mode.
#>
[CmdletBinding()]
param(
    [string]$BackupRoot = 'E:\AquaLedger-Backups\postgres',
    [string]$SshAlias = 'aqualedger-backup',
    [string]$RemoteBackupDir = '/home/ubuntu/backups'
)

Set-StrictMode -Version Latest

$BasenamePattern = '^fisherp_[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{6}\.dump$'
$Sha256Pattern = '^[0-9a-fA-F]{64}$'

# --- native-command helper -------------------------------------------------
# NOTE: redirecting a native exe's stderr with 2>&1 wraps each stderr line in
# an ErrorRecord and can make $? false even on success (a known PowerShell
# 5.1 quirk) - so every wrapper below relies ONLY on $LASTEXITCODE, never $?,
# and flattens the captured lines back to plain strings immediately.
function Invoke-NativeCapture {
    param(
        [Parameter(Mandatory)][string]$FilePath,
        [Parameter(Mandatory)][string[]]$ArgumentList
    )
    # Local override only (does not leak to the caller): with the caller's
    # $ErrorActionPreference = 'Stop' in effect (as the main block below
    # sets), a native exe's stderr line arriving via 2>&1 would otherwise be
    # promoted to a terminating exception here - before $LASTEXITCODE is
    # even read - masking every real failure behind a raw NativeCommandError
    # instead of the clean, stage-specific messages this script builds below.
    $ErrorActionPreference = 'Continue'
    $raw = & $FilePath @ArgumentList 2>&1
    $exitCode = $LASTEXITCODE
    $lines = @($raw | ForEach-Object { $_.ToString() })
    return [pscustomobject]@{ ExitCode = $exitCode; Lines = $lines }
}

# --- basename / hash validation --------------------------------------------
function Test-BackupBasename {
    param([string]$Basename)
    if ([string]::IsNullOrEmpty($Basename)) { return $false }
    if ($Basename -match '[\\/]') { return $false }
    if ($Basename -match '\.\.') { return $false }
    if ($Basename -match '\s') { return $false }
    return [bool]($Basename -cmatch $BasenamePattern)
}

function Test-Sha256Format {
    param([string]$Value)
    return [bool]($Value -cmatch $Sha256Pattern)
}

function Get-Sha256SidecarValue {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "checksum sidecar not found: $Path"
    }
    $content = (Get-Content -LiteralPath $Path -Raw)
    if ($content -match '^\s*([0-9a-fA-F]{64})\s') {
        return $Matches[1].ToLowerInvariant()
    }
    throw "checksum sidecar has an unexpected format: $Path"
}

# --- remote command output parsing ------------------------------------------
# Only ever acts on exact KEY=VALUE lines - never treats arbitrary human-
# readable text as meaningful, and treats a missing or duplicated field as a
# hard failure rather than guessing.
function ConvertFrom-CreateOutput {
    param([string[]]$Lines)

    $resultValues = @()
    $basenameValues = @()
    $sha256Values = @()
    $sizeBytesValues = @()

    foreach ($line in $Lines) {
        if ($line -match '^RESULT=(.*)$') { $resultValues += $Matches[1]; continue }
        if ($line -match '^BASENAME=(.*)$') { $basenameValues += $Matches[1]; continue }
        if ($line -match '^SHA256=(.*)$') { $sha256Values += $Matches[1]; continue }
        if ($line -match '^SIZE_BYTES=(.*)$') { $sizeBytesValues += $Matches[1]; continue }
    }

    if ($resultValues.Count -eq 0) { throw "create output is missing a RESULT= line" }
    if ($resultValues.Count -gt 1) { throw "create output contains RESULT= more than once (duplicate)" }
    if ($resultValues[0] -ne 'CREATED') { throw "create did not report success (RESULT=$($resultValues[0]))" }

    if ($basenameValues.Count -eq 0) { throw "create output is missing BASENAME=" }
    if ($basenameValues.Count -gt 1) { throw "create output contains BASENAME= more than once" }
    $basename = $basenameValues[0]
    if (-not (Test-BackupBasename $basename)) { throw "create returned an invalid BASENAME: '$basename'" }

    if ($sha256Values.Count -eq 0) { throw "create output is missing SHA256=" }
    if ($sha256Values.Count -gt 1) { throw "create output contains SHA256= more than once" }
    $sha256 = $sha256Values[0]
    if (-not (Test-Sha256Format $sha256)) { throw "create returned an invalid SHA256 value: '$sha256'" }

    if ($sizeBytesValues.Count -eq 0) { throw "create output is missing SIZE_BYTES=" }
    if ($sizeBytesValues.Count -gt 1) { throw "create output contains SIZE_BYTES= more than once" }
    $sizeBytesRaw = $sizeBytesValues[0]
    if ($sizeBytesRaw -notmatch '^[0-9]+$') { throw "create returned a non-numeric SIZE_BYTES value: '$sizeBytesRaw'" }

    return [pscustomobject]@{
        Basename  = $basename
        Sha256    = $sha256.ToLowerInvariant()
        SizeBytes = [int64]$sizeBytesRaw
    }
}

function ConvertFrom-ConfirmOutput {
    param([string[]]$Lines, [string]$ExpectedBasename)

    $resultValues = @()
    $basenameValues = @()
    $retainedValues = @()

    foreach ($line in $Lines) {
        if ($line -match '^RESULT=(.*)$') { $resultValues += $Matches[1]; continue }
        if ($line -match '^BASENAME=(.*)$') { $basenameValues += $Matches[1]; continue }
        if ($line -match '^RETAINED=(.*)$') { $retainedValues += $Matches[1]; continue }
    }

    # backup-postgres.sh confirm's actual success field is RESULT=CONFIRMED -
    # validated against the real script, not assumed.
    if ($resultValues.Count -ne 1 -or $resultValues[0] -ne 'CONFIRMED') {
        throw "confirm did not report the expected success field (RESULT=CONFIRMED). SSH connecting is not enough on its own."
    }
    if ($basenameValues.Count -ne 1 -or $basenameValues[0] -ne $ExpectedBasename) {
        throw "confirm's reported BASENAME did not match what was sent (expected '$ExpectedBasename')"
    }

    return [pscustomobject]@{
        Basename = $basenameValues[0]
        Retained = if ($retainedValues.Count -eq 1) { $retainedValues[0] } else { $null }
    }
}

# --- integrity verification -------------------------------------------------
function Test-DownloadedBackup {
    param(
        [Parameter(Mandatory)][string]$DumpPath,
        [Parameter(Mandatory)][string]$SidecarPath,
        [Parameter(Mandatory)][int64]$ExpectedSizeBytes,
        [Parameter(Mandatory)][string]$ExpectedSha256FromCreate
    )

    if (-not (Test-Path -LiteralPath $DumpPath -PathType Leaf)) {
        throw "downloaded dump file is missing: $DumpPath"
    }
    if (-not (Test-Path -LiteralPath $SidecarPath -PathType Leaf)) {
        throw "downloaded checksum sidecar is missing: $SidecarPath"
    }

    $actualSize = (Get-Item -LiteralPath $DumpPath).Length
    if ($actualSize -ne $ExpectedSizeBytes) {
        throw "size mismatch: create reported $ExpectedSizeBytes bytes, downloaded file is $actualSize bytes"
    }

    $expected = $ExpectedSha256FromCreate.ToLowerInvariant()
    $sidecarSha256 = Get-Sha256SidecarValue -Path $SidecarPath
    $localSha256 = (Get-FileHash -LiteralPath $DumpPath -Algorithm SHA256).Hash.ToLowerInvariant()

    if ($localSha256 -ne $expected) {
        throw "SHA256 mismatch: locally computed ($localSha256) does not match create's reported value ($expected)"
    }
    if ($sidecarSha256 -ne $expected) {
        throw "SHA256 mismatch: downloaded sidecar ($sidecarSha256) does not match create's reported value ($expected)"
    }
    if ($localSha256 -ne $sidecarSha256) {
        throw "SHA256 mismatch: locally computed ($localSha256) does not match the downloaded sidecar ($sidecarSha256)"
    }

    return $localSha256
}

# --- SSH config alias check (never modifies the file) ----------------------
function Test-SshAliasConfigured {
    param([Parameter(Mandatory)][string]$Alias)
    $configPath = Join-Path $env:USERPROFILE '.ssh\config'
    if (-not (Test-Path -LiteralPath $configPath -PathType Leaf)) { return $false }
    foreach ($line in (Get-Content -LiteralPath $configPath)) {
        if ($line -match '^\s*Host\s+(.+)$') {
            $hosts = $Matches[1].Trim() -split '\s+'
            if ($hosts -contains $Alias) { return $true }
        }
    }
    return $false
}

function Test-Prerequisites {
    param([Parameter(Mandatory)][string]$Alias)
    $ok = $true

    $sshCmd = Get-Command ssh.exe -ErrorAction SilentlyContinue
    if (-not $sshCmd) {
        Write-Host "ERROR: ssh.exe not found on PATH. Install the Windows OpenSSH Client optional feature." -ForegroundColor Red
        $ok = $false
    }
    $scpCmd = Get-Command scp.exe -ErrorAction SilentlyContinue
    if (-not $scpCmd) {
        Write-Host "ERROR: scp.exe not found on PATH. Install the Windows OpenSSH Client optional feature." -ForegroundColor Red
        $ok = $false
    }

    if ($sshCmd) {
        try {
            $verInfo = Invoke-NativeCapture -FilePath 'ssh.exe' -ArgumentList @('-V')
            Write-Host "  ssh.exe:  $($verInfo.Lines -join ' ') ($($sshCmd.Source))"
        } catch {
            Write-Host "  ssh.exe:  found at $($sshCmd.Source) (version check failed, non-fatal)"
        }
    }
    if ($scpCmd) {
        Write-Host "  scp.exe:  found at $($scpCmd.Source)"
    }

    if (-not (Test-SshAliasConfigured -Alias $Alias)) {
        Write-Host "ERROR: no 'Host $Alias' entry found in $env:USERPROFILE\.ssh\config" -ForegroundColor Red
        Write-Host "This script will not modify your SSH config. Add this block yourself:" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Host $Alias"
        Write-Host "    HostName <your VPS host>"
        Write-Host "    User ubuntu"
        Write-Host "    IdentityFile C:\Users\<you>\.ssh\aqualedger-backup-ed25519"
        Write-Host "    IdentitiesOnly yes"
        Write-Host ""
        $ok = $false
    } else {
        Write-Host "  SSH alias '$Alias': configured"
    }

    return $ok
}

# --- remote operations -------------------------------------------------------
function Invoke-RemoteCreate {
    param([string]$Alias = $SshAlias)
    Invoke-NativeCapture -FilePath 'ssh.exe' -ArgumentList @(
        '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=30', $Alias, 'backup-postgres.sh create'
    )
}

function Invoke-RemoteConfirm {
    param([Parameter(Mandatory)][string]$Basename, [string]$Alias = $SshAlias)
    Invoke-NativeCapture -FilePath 'ssh.exe' -ArgumentList @(
        '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=30', $Alias, "backup-postgres.sh confirm $Basename"
    )
}

function Invoke-ScpDownload {
    param(
        [Parameter(Mandatory)][string]$RemotePath,
        [Parameter(Mandatory)][string]$LocalPath,
        [string]$Alias = $SshAlias
    )
    Invoke-NativeCapture -FilePath 'scp.exe' -ArgumentList @(
        '-O', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=30', "${Alias}:$RemotePath", $LocalPath
    )
}

# ============================================================================
# Main - only runs when the script is executed directly, not when dot-sourced
# (a test harness dot-sources this file to load the functions above only).
# ============================================================================
if ($MyInvocation.InvocationName -ne '.') {

    $ErrorActionPreference = 'Stop'
    $currentStage = 'startup'
    $tempDumpPath = $null
    $tempSidecarPath = $null

    try {
        Write-Host ('=' * 40)
        Write-Host "AquaLedger PostgreSQL Backup"
        Write-Host ('=' * 40)
        Write-Host ""

        $currentStage = 'preflight'
        if (-not (Test-Prerequisites -Alias $SshAlias)) {
            throw "Preflight checks failed - see errors above. Nothing was attempted."
        }

        $currentStage = 'local directory'
        if (-not (Test-Path -LiteralPath $BackupRoot)) {
            New-Item -ItemType Directory -Path $BackupRoot -Force | Out-Null
        }

        $currentStage = 'create'
        Write-Host "Connecting to production VPS..."
        $createResult = Invoke-RemoteCreate
        if ($createResult.ExitCode -ne 0) {
            $createResult.Lines | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
            throw "create failed (exit code $($createResult.ExitCode))"
        }
        Write-Host "PostgreSQL health: PASS"
        Write-Host "Creating backup: PASS"

        $parsed = ConvertFrom-CreateOutput -Lines $createResult.Lines
        Write-Host "Backup validation: PASS"
        Write-Host "SHA256 generated: PASS"

        $finalDumpPath    = Join-Path $BackupRoot $parsed.Basename
        $finalSidecarPath = "$finalDumpPath.sha256"
        if (Test-Path -LiteralPath $finalDumpPath) {
            throw "a local backup already exists at this basename - refusing to overwrite: $finalDumpPath"
        }

        $tempDumpPath    = Join-Path $BackupRoot "$($parsed.Basename).download.tmp"
        $tempSidecarPath = Join-Path $BackupRoot "$($parsed.Basename).sha256.download.tmp"

        $currentStage = 'download'
        Write-Host "Downloading backup..."
        $remoteDumpPath    = "$RemoteBackupDir/$($parsed.Basename)"
        $remoteSidecarPath = "$RemoteBackupDir/$($parsed.Basename).sha256"

        $dl1 = Invoke-ScpDownload -RemotePath $remoteDumpPath -LocalPath $tempDumpPath
        if ($dl1.ExitCode -ne 0) {
            $dl1.Lines | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
            throw "scp -O download of the .dump file failed (exit code $($dl1.ExitCode))"
        }
        $dl2 = Invoke-ScpDownload -RemotePath $remoteSidecarPath -LocalPath $tempSidecarPath
        if ($dl2.ExitCode -ne 0) {
            $dl2.Lines | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
            throw "scp -O download of the .sha256 file failed (exit code $($dl2.ExitCode))"
        }
        Write-Host "Download: PASS"

        $currentStage = 'verification'
        Test-DownloadedBackup -DumpPath $tempDumpPath -SidecarPath $tempSidecarPath `
            -ExpectedSizeBytes $parsed.SizeBytes -ExpectedSha256FromCreate $parsed.Sha256 | Out-Null
        Write-Host "SHA256 verification: PASS"

        $currentStage = 'finalize local files'
        Rename-Item -LiteralPath $tempDumpPath -NewName (Split-Path $finalDumpPath -Leaf)
        $tempDumpPath = $null
        Rename-Item -LiteralPath $tempSidecarPath -NewName (Split-Path $finalSidecarPath -Leaf)
        $tempSidecarPath = $null

        $currentStage = 'confirm'
        Write-Host "Confirming with VPS..."
        $confirmResult = Invoke-RemoteConfirm -Basename $parsed.Basename
        if ($confirmResult.ExitCode -ne 0) {
            $confirmResult.Lines | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
            throw "confirm failed (exit code $($confirmResult.ExitCode)) - the local backup IS saved and verified at $finalDumpPath, but the VPS has not been told to retain/trim yet. Re-running confirm manually later is safe."
        }
        $confirmed = ConvertFrom-ConfirmOutput -Lines $confirmResult.Lines -ExpectedBasename $parsed.Basename

        Write-Host ""
        Write-Host "Backup saved:"
        Write-Host "$finalDumpPath"
        Write-Host ""
        if ($confirmed.Retained) {
            Write-Host "VPS retention:"
            Write-Host "Latest $($confirmed.Retained) backups retained."
            Write-Host ""
        }
        Write-Host "BACKUP SUCCESSFUL"
        Write-Host ('=' * 40)
        exit 0
    }
    catch {
        Write-Host ""
        Write-Host "BACKUP FAILED at stage: $currentStage" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red

        if ($tempDumpPath -and (Test-Path -LiteralPath $tempDumpPath)) {
            Remove-Item -LiteralPath $tempDumpPath -Force
            Write-Host "Cleaned up incomplete temp file: $tempDumpPath"
        }
        if ($tempSidecarPath -and (Test-Path -LiteralPath $tempSidecarPath)) {
            Remove-Item -LiteralPath $tempSidecarPath -Force
            Write-Host "Cleaned up incomplete temp file: $tempSidecarPath"
        }
        Write-Host ('=' * 40)
        exit 1
    }
}
