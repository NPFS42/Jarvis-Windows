# Standalone public Windows frontend build. The private Jarvis backend is not bundled.
param([switch]$SkipDependencies)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
Push-Location $root
try {
  $py = Join-Path $root '.venv-build\Scripts\python.exe'
  if(-not (Test-Path $py)){
    & python -m venv '.venv-build'
    if($LASTEXITCODE -ne 0){throw 'Python build environment failed'}
  }
  if(-not $SkipDependencies){
    & $py -m pip install --disable-pip-version-check -r requirements-build.txt
    if($LASTEXITCODE -ne 0){throw 'Build dependencies failed'}
  }
  & $py -m unittest discover -s tests -v
  if($LASTEXITCODE -ne 0){throw 'Windows tests failed'}
  & $py -m PyInstaller --clean --noconfirm --onefile --windowed --name Jarvis-Frontend --icon assets\jarvis.ico --hidden-import webview.platforms.edgechromium --hidden-import webview.platforms.winforms --collect-all webview --collect-all clr_loader jarvis_frontend.py
  if($LASTEXITCODE -ne 0){throw 'PyInstaller failed'}
  $exe=Join-Path $root 'dist\Jarvis-Frontend.exe'
  if(-not (Test-Path $exe)){throw 'Missing frontend EXE'}
  $p=Start-Process -FilePath $exe -ArgumentList '--self-test' -PassThru -Wait
  if($p.ExitCode -ne 0){throw 'EXE self-test failed'}
  Write-Output ("WINDOWS_FRONTEND_BUILT="+$exe)
  Write-Output ("SHA256="+(Get-FileHash $exe -Algorithm SHA256).Hash)
} finally { Pop-Location }
