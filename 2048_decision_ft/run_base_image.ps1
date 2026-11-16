# Detach run_base_image.py. The window can close; watch ckpt\base_image\progress.log
# and ckpt\base_image\.done. Extra args are passed through (last --out wins).
param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$Rest
)
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = if ($env:PLAYLAYA_PYTHON) { $env:PLAYLAYA_PYTHON } else { "python" }
$outDir = Join-Path $here "ckpt\base_image"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$argList = @("-u", (Join-Path $here "run_base_image.py"), "--out", $outDir) + $Rest
Start-Process -FilePath $py -WorkingDirectory $here -ArgumentList $argList `
  -RedirectStandardOutput (Join-Path $outDir "console.log") `
  -RedirectStandardError (Join-Path $outDir "console.err") `
  -WindowStyle Hidden
Write-Output "detached. console: $outDir\console.log  progress: $outDir\progress.log  done: $outDir\.done"
