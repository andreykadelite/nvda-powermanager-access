param(
    [ValidatePattern('^[A-Za-z0-9_.-]+$')]
    [string]$RepositoryName = 'nvda-powermanager-access'
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$ghCommand = Get-Command gh -ErrorAction SilentlyContinue
$ghExe = if ($ghCommand) { $ghCommand.Source } else { Join-Path $env:ProgramFiles 'GitHub CLI\gh.exe' }
if (-not (Test-Path -LiteralPath $ghExe)) { throw 'Install GitHub CLI first: winget install --id GitHub.cli --exact' }

function Run-Checked([string]$Program, [string[]]$CommandArgs) {
    & $Program @CommandArgs
    if ($LASTEXITCODE -ne 0) { throw "Command failed: $Program $($CommandArgs[0])" }
}

if (-not (Test-Path -LiteralPath '.git')) { throw 'Initialize and commit the reviewed public files first.' }
$changes = Run-Checked 'git' @('status', '--porcelain')
if ($changes) { throw 'Commit or resolve the working-tree changes before publishing.' }
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Run tools/bootstrap.ps1 first.' }
Run-Checked $python @('-m', 'pytest', '-q')
Run-Checked $python @('-m', 'ruff', 'check', 'addon', 'tests', 'tools/build.py', 'tools/check_docs.py')
Run-Checked $python @('tools/check_docs.py')
Run-Checked $python @('tools/build.py')
if (Run-Checked 'git' @('status', '--porcelain')) { throw 'The build changed tracked files. Review and commit them first.' }

$versionLine = Get-Content -LiteralPath 'addon\manifest.ini' | Where-Object { $_ -match '^version\s*=\s*\d+\.\d+\.\d+$' }
if (@($versionLine).Count -ne 1) { throw 'Invalid release version.' }
$version = ($versionLine -split '=', 2)[1].Trim()
$tag = "v$version"
$account = (& $ghExe api user --jq .login)
if ($LASTEXITCODE -ne 0 -or -not $account) { throw 'Sign in first: gh auth login --hostname github.com --git-protocol https --web --scopes workflow' }
$repository = "$account/$RepositoryName"
$url = "https://github.com/$repository"
$description = 'NVDA add-on for keyboard access and readable UPS data in Richcomm PowerManagerII. Russian interface; English and Russian documentation.'

$remotes = Run-Checked 'git' @('remote')
if ($remotes -contains 'origin') {
    $remoteUrl = Run-Checked 'git' @('remote', 'get-url', 'origin')
    if ($remoteUrl -notin @($url, "$url.git", "git@github.com:$repository.git")) { throw 'Origin points to a different repository.' }
    Run-Checked 'git' @('push', '-u', 'origin', 'main')
} else {
    & $ghExe repo view $repository --json name 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { throw 'That repository already exists. Verify it before adding a remote.' }
    Run-Checked $ghExe @('repo', 'create', $repository, '--public', '--description', $description, '--source', '.', '--remote', 'origin', '--push')
}
Run-Checked $ghExe @('repo', 'edit', $repository, '--add-topic', 'nvda,nvda-addon,accessibility,ups,powermanager,screen-reader')
$head = Run-Checked 'git' @('rev-parse', 'HEAD')
Write-Output 'Waiting for GitHub build and tests...'
$runId = $null
for ($attempt = 0; $attempt -lt 20; $attempt++) {
    $runsJson = Run-Checked $ghExe @('run', 'list', '--repo', $repository, '--workflow', 'ci.yml', '--commit', $head, '--limit', '1', '--json', 'databaseId')
    $runs = @($runsJson | ConvertFrom-Json)
    if ($runs.Count -gt 0) { $runId = $runs[0].databaseId; break }
    Start-Sleep -Seconds 3
}
if (-not $runId) { throw 'No CI run found. Check GitHub Actions before publishing.' }
Run-Checked $ghExe @('run', 'watch', "$runId", '--repo', $repository, '--interval', '10', '--exit-status')

$tags = Run-Checked 'git' @('tag', '--list', $tag)
if ($tags) {
    $tagCommit = Run-Checked 'git' @('rev-parse', "$tag^{}")
    if ($tagCommit -ne $head) { throw 'The release tag already points to another commit.' }
} else {
    Run-Checked 'git' @('tag', '-a', $tag, '-m', "PowerManagerII Access $version")
}
Run-Checked 'git' @('push', 'origin', "refs/tags/$tag")
& $ghExe release view $tag --repo $repository --json tagName 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) { throw 'The release already exists. It will not be overwritten.' }
$assetNames = @("powerManagerAccess-$version.nvda-addon", "powerManagerAccess-$version-source.zip", 'SHA256SUMS.txt')
$assetPaths = @($assetNames | ForEach-Object { Join-Path 'dist' $_ })
$releaseArgs = @('release', 'create', $tag, '--repo', $repository, '--verify-tag', '--latest', '--title', "PowerManagerII Access $version", '--notes-file', 'docs/release-notes.md') + $assetPaths
Run-Checked $ghExe $releaseArgs

$verifyDir = Join-Path $projectRoot "dist\verified-$tag"
New-Item -ItemType Directory -Path $verifyDir -Force | Out-Null
foreach ($name in $assetNames) {
    Run-Checked $ghExe @('release', 'download', $tag, '--repo', $repository, '--pattern', $name, '--dir', $verifyDir, '--clobber')
    $builtHash = (Get-FileHash -LiteralPath (Join-Path 'dist' $name) -Algorithm SHA256).Hash
    $remoteHash = (Get-FileHash -LiteralPath (Join-Path $verifyDir $name) -Algorithm SHA256).Hash
    if ($builtHash -ne $remoteHash) { throw "Published asset differs: $name" }
}
Write-Output "Repository: $url"
Write-Output "Verified release: $url/releases/tag/$tag"
