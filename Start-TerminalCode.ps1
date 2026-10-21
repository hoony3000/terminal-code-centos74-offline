param(
    [Parameter(Mandatory=$true)][string]$Target,
    [string]$Project = '.',
    [string]$Distribution = 'Ubuntu',
    [string]$RemoteBin = ''
)
$ErrorActionPreference = 'Stop'
$wslHome = (& wsl.exe -d $Distribution -- printenv HOME).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Cannot read the WSL home directory.' }
$launcher = "$wslHome/.local/lib/tode-client/bin/open-ghostty"
if ($RemoteBin) {
    & wsl.exe -d $Distribution -- env "TODE_REMOTE_BIN=$RemoteBin" $launcher --ssh $Target $Project
} else {
    & wsl.exe -d $Distribution -- $launcher --ssh $Target $Project
}
exit $LASTEXITCODE
