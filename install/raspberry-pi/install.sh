#!/bin/bash
set -e

echo "=========================================="
echo "Smart Home Vulnerability Manager"
echo "Script de instalación para Raspberry Pi"
echo "=========================================="
echo ""

# Verificar que se ejecuta como root
if [ "$EUID" -ne 0 ]; then
  echo "❌ Este script debe ejecutarse como root"
  echo "   Ejecuta: sudo bash install.sh"
  exit 1
fi

echo "✓ Ejecutando como root"
echo ""

# 1. Actualizar sistema
echo "📦 Actualizando sistema..."
apt-get update -qq
apt-get upgrade -y -qq

# 2. Instalar dependencias
echo "📦 Instalando dependencias del sistema..."
apt-get install -y -qq \
  arp-scan \
  nmap \
  avahi-utils \
  samba-common-bin \
  python3 \
  python3-pip \
  python3-venv \
  git \
  curl \
  dnsutils

echo "✓ Dependencias del sistema instaladas"
echo ""

# 3. Instalar Nuclei
echo "📦 Instalando Nuclei..."
ARCH=$(uname -m)
if [ "$ARCH" = "aarch64" ]; then
  NUCLEI_ARCH="arm64"
else
  NUCLEI_ARCH="arm"
fi

NUCLEI_VERSION="v3.2.0"
NUCLEI_URL="https://github.com/projectdiscovery/nuclei/releases/download/${NUCLEI_VERSION}/nuclei_${NUCLEI_VERSION#v}_linux_${NUCLEI_ARCH}.zip"

cd /tmp
curl -sL "$NUCLEI_URL" -o nuclei.zip
unzip -qq -o nuclei.zip
mv nuclei /usr/local/bin/
chmod +x /usr/local/bin/nuclei
rm nuclei.zip

# Actualizar templates de Nuclei
echo "📥 Descargando templates de Nuclei..."
nuclei -update-templates -silent

echo "✓ Nuclei instalado y actualizado"
echo ""

# 4. Crear usuario del sistema
echo "👤 Configurando usuario del sistema..."
if ! id -u shvm > /dev/null 2>&1; then
  useradd -r -s /bin/bash -d /opt/smart-home-vuln-manager shvm
  echo "✓ Usuario 'shvm' creado"
else
  echo "✓ Usuario 'shvm' ya existe"
fi
echo ""

# 5. Clonar/actualizar repositorio
REPO_DIR="/opt/smart-home-vuln-manager"
echo "📥 Descargando código..."

if [ -d "$REPO_DIR/.git" ]; then
  echo "   Actualizando repositorio existente..."
  cd "$REPO_DIR"
  sudo -u shvm git pull
else
  echo "   Clonando repositorio..."
  git clone https://github.com/laudarias/smart-home-vuln-manager.git "$REPO_DIR"
  chown -R shvm:shvm "$REPO_DIR"
fi

echo "✓ Código descargado"
echo ""

# 6. Crear venv Python e instalar dependencias
echo "🐍 Configurando entorno Python..."
cd "$REPO_DIR/backend"

if [ ! -d ".venv" ]; then
  sudo -u shvm python3 -m venv .venv
fi

sudo -u shvm .venv/bin/pip install --quiet --upgrade pip
sudo -u shvm .venv/bin/pip install --quiet -r requirements.txt

echo "✓ Entorno Python configurado"
echo ""

# 7. Configurar sudoers para arp-scan y nmap
echo "🔐 Configurando permisos sudo..."
cat > /etc/sudoers.d/shvm << 'EOF'
shvm ALL=(ALL) NOPASSWD: /usr/sbin/arp-scan, /usr/bin/nmap
EOF

chmod 440 /etc/sudoers.d/shvm
echo "✓ Permisos configurados"
echo ""

# 8. Crear servicio Avahi (mDNS)
echo "📡 Configurando servicio mDNS..."
cat > /etc/avahi/services/shvm.service << 'EOF'
<?xml version="1.0" standalone='no'?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name replace-wildcards="yes">Smart Home Security</name>
  <service>
    <type>_http._tcp</type>
    <port>8000</port>
  </service>
</service-group>
EOF

systemctl restart avahi-daemon
echo "✓ Servicio mDNS configurado"
echo ""

# 9. Crear servicio systemd
echo "⚙️  Creando servicio systemd..."
cat > /etc/systemd/system/smart-home-scanner.service << EOF
[Unit]
Description=Smart Home Vulnerability Manager
After=network.target

[Service]
Type=simple
User=shvm
WorkingDirectory=$REPO_DIR/backend
Environment="PATH=$REPO_DIR/backend/.venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=$REPO_DIR/backend"
ExecStart=$REPO_DIR/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "✓ Servicio systemd creado"
echo ""

# 10. Habilitar e iniciar servicio
echo "🚀 Iniciando servicio..."
systemctl daemon-reload
systemctl enable smart-home-scanner.service
systemctl restart smart-home-scanner.service

echo "✓ Servicio iniciado"
echo ""

# Obtener IP de la Pi
PI_IP=$(hostname -I | awk '{print $1}')
MDNS_NAME=$(hostname).local

echo "=========================================="
echo "✅ INSTALACIÓN COMPLETADA"
echo "=========================================="
echo ""
echo "🌐 La aplicación está corriendo en:"
echo "   http://$PI_IP:8000"
echo "   http://$MDNS_NAME:8000"
echo ""
echo "🔑 Credenciales por defecto:"
echo "   Usuario: (no aplica)"
echo "   Contraseña: admin123"
echo ""
echo "⚠️  IMPORTANTE: Cambia la contraseña desde la interfaz"
echo ""
echo "📝 Comandos útiles:"
echo "   Ver logs:      sudo journalctl -u smart-home-scanner -f"
echo "   Reiniciar:     sudo systemctl restart smart-home-scanner"
echo "   Estado:        sudo systemctl status smart-home-scanner"
echo "   Detener:       sudo systemctl stop smart-home-scanner"
echo ""
echo "🎉 ¡Listo! Abre la URL en tu navegador o app Electron."
echo ""
