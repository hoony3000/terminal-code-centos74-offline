# Requires Windows PowerShell 5.1 or later.
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
foreach ($line in [System.IO.File]::ReadAllLines((Join-Path $PSScriptRoot 'SHA256SUMS'))) {
    if ($line -notmatch '^([0-9a-f]{64})  ([a-zA-Z0-9.+_~-]+)$') {
        throw "Invalid entry in SHA256SUMS"
    }
    $expectedHash = $Matches[1]
    $file = $Matches[2]
    $actualHash = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash
    if ($actualHash -ne $expectedHash) { throw "SHA-256 mismatch: $file" }
}

$metadata = Get-Content -LiteralPath 'version.txt'
$version = $metadata[0]
$commit = $metadata[1]
if ($version -notmatch '^\d+\.\d+\.\d+$' -or $commit -notmatch '^[0-9a-f]{40}$') {
    throw "Invalid version or commit in version.txt"
}

$installation = Join-Path $PSScriptRoot "vscode-$version"
$cli = Join-Path $installation 'bin\code.cmd'
if (-not (Test-Path -LiteralPath $installation)) {
    $staging = Join-Path $PSScriptRoot ('.install-' + [Guid]::NewGuid().ToString('N'))
    try {
        Expand-Archive -LiteralPath "VSCode-win32-x64-$version.zip" -DestinationPath $staging
        if (-not (Test-Path -LiteralPath (Join-Path $staging 'bin\code.cmd') -PathType Leaf)) {
            throw 'The official VS Code archive is missing bin\code.cmd.'
        }
        [System.IO.Directory]::Move($staging, $installation)
    } finally {
        if (Test-Path -LiteralPath $staging) {
            Remove-Item -LiteralPath $staging -Recurse -Force
        }
    }
}

$settingsDir = Join-Path $installation 'data\user-data\User'
New-Item -ItemType Directory -Force -Path $settingsDir | Out-Null
$settings = Join-Path $settingsDir 'settings.json'
if (-not (Test-Path -LiteralPath $settings)) {
    Copy-Item -LiteralPath 'settings.json' -Destination $settings
}

$actual = & $cli --version
if ($LASTEXITCODE -ne 0 -or $actual -notcontains $commit) {
    throw "Unexpected VS Code commit. Expected $commit."
}
foreach ($extension in Get-Content -LiteralPath 'extensions.txt') {
    if ($extension -notmatch '^[a-zA-Z0-9.+_~-]+\.vsix$') {
        throw 'Invalid VSIX filename in extensions.txt.'
    }
    & $cli --install-extension (Join-Path $PSScriptRoot $extension)
    if ($LASTEXITCODE -ne 0) { throw "VSIX install failed: $extension" }
}
Write-Host ('Start: ' + (Join-Path $installation 'Code.exe'))
