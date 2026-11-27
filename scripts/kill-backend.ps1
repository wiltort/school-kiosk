# Stops only this build's backend processes:
#   1. release python-backend.exe from <repo>/backend/dist (matched by exact path);
#   2. dev uvicorn/python serving src.main (including the one listening on 8765).
# Processes of other projects are not touched.
#
# Kept in a separate script (instead of a Makefile one-liner) because `$_`
# inside a make recipe may be expanded by the shell (PowerShell treats it as
# an automatic variable), which broke `make kill-backend`.

$ErrorActionPreference = 'SilentlyContinue'

$root = Split-Path -Parent $PSScriptRoot
$releaseExe = Join-Path $root 'backend/dist/python-backend.exe'

# 1. Release backend of this build (exact executable path).
Get-CimInstance Win32_Process |
    Where-Object {
        $_.Name -eq 'python-backend.exe' -and
        $_.ExecutablePath -eq $releaseExe
    } |
    ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }

# 2. Dev backend: python/uvicorn running src.main (poetry/uvicorn chain).
Get-CimInstance Win32_Process |
    Where-Object {
        $_.Name -in @('python.exe', 'uvicorn.exe') -and
        (
            $_.CommandLine -match 'src\.main' -or
            ($_.CommandLine -match 'uvicorn' -and $_.CommandLine -match '8765')
        )
    } |
    ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
