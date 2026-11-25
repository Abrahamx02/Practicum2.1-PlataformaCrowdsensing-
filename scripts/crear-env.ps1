# Crea el archivo .env con tres claves nuevas al azar (Windows PowerShell). No necesita Python.
# Uso (desde la carpeta del proyecto):   powershell -ExecutionPolicy Bypass -File scripts\crear-env.ps1
$destino = Join-Path (Get-Location) ".env"
if (Test-Path $destino) { Write-Host ".env ya existe: no se toca. Bórralo si quieres claves nuevas." -ForegroundColor Yellow; exit 0 }

function Nueva-Clave {
    $bytes = New-Object byte[] 24
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return ([Convert]::ToBase64String($bytes)).TrimEnd('=').Replace('+', 'A').Replace('/', 'B')
}

$lineas = @(
    "# Archivo local: NO se sube a Git (esta en .gitignore).",
    "DATABASE_URL=postgresql://mcs:mcs@127.0.0.1:5433/mcs",
    "CLAVE_ESCRITURA=$(Nueva-Clave)",
    "CLAVE_LECTURA=$(Nueva-Clave)",
    "CLAVE_ADMIN=$(Nueva-Clave)",
    "API_URL=http://127.0.0.1:8000",
    "CONFIAR_EN_PROXY=1"
)
# ASCII y sin BOM: con UTF-8 "con BOM" (el de Set-Content -Encoding UTF8 en PowerShell 5) Docker Compose lee mal la primera linea.
[IO.File]::WriteAllLines($destino, $lineas, (New-Object Text.UTF8Encoding($false)))
Write-Host "Listo: .env creado." -ForegroundColor Green
Write-Host "Clave de administrador (para entrar al panel):" (($lineas | Select-String "^CLAVE_ADMIN=").ToString().Split("=")[1])
