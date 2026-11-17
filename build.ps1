# Genera dist\SimuladorMVT.exe (Windows). Ejecutar desde la carpeta del proyecto:
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
    --name SimuladorMVT `
    interfaz.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller fallo (si SimuladorMVT.exe esta abierto, cerrarlo y reintentar)." }

# 3. Al lado del .exe van los lotes de prueba y el README (en Markdown y en PDF)
Copy-Item -Recurse -Force lotes dist\lotes
Copy-Item -Force README.md dist\README.md
Copy-Item -Force README.pdf dist\README.pdf
Write-Host ""
Write-Host "Listo: dist\SimuladorMVT.exe (con dist\lotes y dist\README.pdf). Para entregar, comprimir la carpeta dist completa."
