param(
  [string]$Pattern = "pm_crypto_updown|sequence38|replay",
  [string[]]$Roots = @("src", "tests", "make.cmd", "docs"),
  [string]$RgPath = ""
)

$ErrorActionPreference = "Continue"
$repoRoot = (Get-Location).Path
$existingRoots = @($Roots | Where-Object { Test-Path -LiteralPath $_ })

Write-Output "repo_root=$repoRoot"
Write-Output "pattern=$Pattern"
Write-Output "roots=$($existingRoots -join ',')"

if ($existingRoots.Count -eq 0) {
  Write-Output "status=NO_SEARCH_ROOTS"
  exit 2
}

$candidates = @()
if ($RgPath -ne "") {
  $candidates += [pscustomobject]@{ Source = $RgPath; Name = "rg" }
}
$pathCandidates = @(Get-Command rg -All -ErrorAction SilentlyContinue)
foreach ($candidate in $pathCandidates) {
  $candidates += $candidate
}

$usableRg = $null
foreach ($candidate in $candidates) {
  $source = [string]$candidate.Source
  if ($source -eq "" -or -not (Test-Path -LiteralPath $source)) {
    continue
  }
  Write-Output "rg_candidate=$source"
  try {
    $version = & $source --version 2>&1
    if ($LASTEXITCODE -eq 0) {
      $usableRg = $source
      Write-Output "rg_status=OK"
      Write-Output "rg_version=$($version | Select-Object -First 1)"
      break
    }
    Write-Output "rg_status=FAILED exit=$LASTEXITCODE"
    Write-Output "rg_error=$($version | Select-Object -First 1)"
  } catch {
    Write-Output "rg_status=FAILED"
    Write-Output "rg_error=$($_.Exception.Message)"
  }
}

if ($null -ne $usableRg) {
  Write-Output "search_tool=rg"
  & $usableRg $Pattern @existingRoots -n --glob "!data/**" --glob "!reports/**" --glob "!external/**" --glob "!tools/**" --glob "!.git/**"
  $exitCode = $LASTEXITCODE
  if ($exitCode -eq 1) {
    Write-Output "search_status=NO_MATCHES"
    exit 0
  }
  exit $exitCode
}

if (Get-Command git -ErrorAction SilentlyContinue) {
  Write-Output "search_tool=git grep"
  git grep -n -E $Pattern -- @existingRoots
  $exitCode = $LASTEXITCODE
  if ($exitCode -eq 1) {
    Write-Output "search_status=NO_MATCHES"
    exit 0
  }
  exit $exitCode
}

Write-Output "search_tool=powershell Select-String"
Get-ChildItem $existingRoots -Recurse -File | Select-String -Pattern $Pattern
exit 0
