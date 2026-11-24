# Genera dist\Simulador_Equipo9.exe (Windows). Ejecutar desde la carpeta del proyecto:
#   powershell -ExecutionPolicy Bypass -File build.ps1
# Requiere: python -m pip install pytest pyinstaller
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { "py" }

# 1. Si algun test falla, no se genera nada
& $python -m pytest -q -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { throw "Hay tests fallando: no se genera el ejecutable." }

# 2. Ejecutable de un solo archivo, sin ventana de consola
& $python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name Simulador_Equipo9 `
    interfaz.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller fallo (si Simulador_Equipo9.exe esta abierto, cerrarlo y reintentar)." }

# 3. Al lado del .exe van los lotes de prueba y el instructivo en PDF
if (Test-Path dist\lotes) { Remove-Item -Recurse -Force dist\lotes }
Copy-Item -Recurse lotes dist\lotes
Copy-Item -Force README.pdf dist\README.pdf
if (Test-Path dist\README.md) { Remove-Item -Force dist\README.md }
Write-Host ""
Write-Host "Listo: dist\Simulador_Equipo9.exe (con dist\lotes y dist\README.pdf). Para entregar, comprimir la carpeta dist completa."
