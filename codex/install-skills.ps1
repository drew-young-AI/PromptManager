param(
    [string]$CodexHome = "$env:USERPROFILE\.codex"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$source = Join-Path $repoRoot "codex\skills\prompt-manager"
$targetRoot = Join-Path $CodexHome "skills"
$target = Join-Path $targetRoot "prompt-manager"

if (!(Test-Path $source)) {
    throw "Skill source not found: $source"
}

New-Item -ItemType Directory -Force $targetRoot | Out-Null
if (Test-Path $target) {
    Remove-Item -LiteralPath $target -Recurse -Force
}

Copy-Item -LiteralPath $source -Destination $target -Recurse
Write-Host "Installed Codex skill: $target"
