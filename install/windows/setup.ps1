# install/windows/setup.ps1
# ─────────────────────────────────────────────────────────────────────────────
# Smart Home Vulnerability Manager — Configuración inicial del entorno WSL2
# Se ejecuta UNA SOLA VEZ durante la instalación con privilegios de administrador
# ─────────────────────────────────────────────────────────────────────────────

param(
    [string]$RepoUrl = "https://github.com/Laudarias/smart-home-vuln-manager.git",
    [string]$InstallDir = "/home/shvm/smart-home-vuln-manager",
    [string]$WslUser = "shvm"
)

$ErrorActionPreference = "Stop"

function Log($msg) {
    Write-Host "[SHVM] $msg" -ForegroundColor Cyan
}

function LogOk($msg) {
    Write-Host "[OK]  $msg" -ForegroundColor Green
}

function LogWarn($msg) {
    Write-Host "[!]   $msg" -ForegroundColor Yellow
}

function LogError($msg) {
    Write-Host "[ERR] $msg" -ForegroundColor Red
}

# ─── 1. Verificar si WSL2 está instalado ─────────────────────────────────────
Log "Verificando WSL2..."

$wslInstalled = $false
try {
    $wslOutput = wsl.exe --status 2>&1
    $wslInstalled = $true
    LogOk "WSL2 ya está instalado"
} catch {
    LogWarn "WSL2 no está instalado. Instalando..."
}

if (-not $wslInstalled) {
    try {
        # Habilitar WSL y plataforma de máquina virtual
        dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart | Out-Null
        dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart | Out-Null

        # Instalar WSL2 con Ubuntu
        wsl.exe --install -d Ubuntu --no-launch | Out-Null
        wsl.exe --set-default-version 2 | Out-Null

        LogOk "WSL2 instalado. Es posible que necesites reiniciar el equipo."
        LogWarn "Si el sistema pide reiniciar, hazlo y vuelve a ejecutar el instalador."

        $restart = Read-Host "¿Deseas reiniciar ahora? (s/n)"
        if ($restart -eq "s") {
            Restart-Computer -Force
        }
        exit 0
    } catch {
        LogError "No se pudo instalar WSL2 automáticamente."
        LogError "Instálalo manualmente: wsl --install"
        exit 1
    }
}

# ─── 2. Verificar que Ubuntu está disponible ──────────────────────────────────
Log "Verificando distribución Ubuntu..."

$distros = wsl.exe --list --quiet 2>&1
if ($distros -notmatch "Ubuntu") {
    Log "Ubuntu no encontrado, instalando..."
    wsl.exe --install -d Ubuntu --no-launch | Out-Null
    # Esperar a que Ubuntu se configure
    Start-Sleep -Seconds 5
    LogOk "Ubuntu instalado"
} else {
    LogOk "Ubuntu disponible"
}

# ─── Función helper: ejecutar comando en WSL2 ─────────────────────────────────
function Wsl-Run($command) {
    $result = wsl.exe -e bash -c $command 2>&1
    return $result
}

function Wsl-RunAsUser($command) {
    # Ejecutar como el usuario de la aplicación
    $result = wsl.exe -u $WslUser -e bash -c $command 2>&1
    return $result
}

# ─── 3. Crear usuario dedicado shvm ───────────────────────────────────────────
Log "Configurando usuario del sistema..."

$userExists = Wsl-Run "id -u $WslUser 2>/dev/null"
if ($LASTEXITCODE -ne 0) {
    Wsl-Run "useradd -m -s /bin/bash $WslUser"
    LogOk "Usuario '$WslUser' creado"
} else {
    LogOk "Usuario '$WslUser' ya existe"
}

# ─── 4. Instalar dependencias del sistema ────────────────────────────────────
Log "Instalando dependencias del sistema (esto puede tardar unos minutos)..."

$deps = "python3 python3-pip python3-venv git arp-scan nmap"
Wsl-Run "apt-get update -qq && apt-get install -y -qq $deps" | Out-Null
LogOk "Dependencias del sistema instaladas"

# ─── 5. Instalar Nuclei ──────────────────────────────────────────────────────
Log "Instalando Nuclei..."

$nucleiInstalled = Wsl-Run "which nuclei 2>/dev/null"
if (-not $nucleiInstalled) {
    Wsl-Run "curl -sL https://github.com/projectdiscovery/nuclei/releases/latest/download/nuclei_linux_amd64.zip -o /tmp/nuclei.zip && unzip -q /tmp/nuclei.zip -d /usr/local/bin && chmod +x /usr/local/bin/nuclei && rm /tmp/nuclei.zip" | Out-Null
    LogOk "Nuclei instalado"
} else {
    LogOk "Nuclei ya está instalado"
}

# ─── 6. Clonar o actualizar el repositorio ───────────────────────────────────
Log "Configurando repositorio del proyecto..."

$repoExists = Wsl-RunAsUser "test -d $InstallDir/.git && echo yes || echo no"
if ($repoExists -match "yes") {
    Log "Actualizando repositorio existente..."
    Wsl-RunAsUser "cd $InstallDir && git pull --quiet" | Out-Null
    LogOk "Repositorio actualizado"
} else {
    Log "Clonando repositorio..."
    Wsl-RunAsUser "git clone $RepoUrl $InstallDir --quiet" | Out-Null
    LogOk "Repositorio clonado en $InstallDir"
}

# ─── 7. Configurar entorno Python ────────────────────────────────────────────
Log "Configurando entorno Python..."

Wsl-RunAsUser "cd $InstallDir/backend && python3 -m venv .venv && .venv/bin/pip install -q --upgrade pip && .venv/bin/pip install -q -r requirements.txt" | Out-Null
LogOk "Entorno Python configurado"

# ─── 8. Configurar permisos sudo para arp-scan y nmap ────────────────────────
Log "Configurando permisos de red..."

$sudoersContent = "$WslUser ALL=(ALL) NOPASSWD: /usr/sbin/arp-scan, /usr/bin/nmap"
Wsl-Run "echo '$sudoersContent' > /etc/sudoers.d/shvm && chmod 440 /etc/sudoers.d/shvm" | Out-Null
LogOk "Permisos configurados"

# ─── 9. Compilar el frontend ─────────────────────────────────────────────────
Log "Compilando interfaz de usuario..."

$nodeInstalled = Wsl-Run "which node 2>/dev/null"
if (-not $nodeInstalled) {
    Wsl-Run "curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt-get install -y nodejs" | Out-Null
}

Wsl-RunAsUser "cd $InstallDir/frontend && npm install --quiet && npm run build" | Out-Null
LogOk "Interfaz compilada"

# ─── 10. Verificar instalación ───────────────────────────────────────────────
Log "Verificando instalación..."

$testResult = Wsl-RunAsUser "cd $InstallDir/backend && .venv/bin/python -c 'import fastapi; print(\"ok\")' 2>&1"
if ($testResult -match "ok") {
    LogOk "Backend verificado correctamente"
} else {
    LogError "Hubo un problema verificando el backend"
    LogError $testResult
    exit 1
}

# ─── Fin ──────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " ✅ Instalación completada exitosamente" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "La app Smart Home Vulnerability Manager está lista." -ForegroundColor White
Write-Host "Ábrela desde el acceso directo del escritorio." -ForegroundColor White
Write-Host ""