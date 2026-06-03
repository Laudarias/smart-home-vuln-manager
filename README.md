<div align="center">

<h1>🏠Smart Home Vulnerability Manager🛡️</h1>

<p><strong>Plataforma open source de gestión de vulnerabilidades IoT para usuarios domésticos no técnicos</strong></p>

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18%2B-61DAFB?logo=react)](https://react.dev/)
[![Electron](https://img.shields.io/badge/Electron-30%2B-47848F?logo=electron)](https://www.electronjs.org/)
[![Plataforma](https://img.shields.io/badge/Plataforma-Windows%20%7C%20Raspberry%20Pi-lightgrey)]()
[![Académico](https://img.shields.io/badge/Proyecto-Tesis%20%40%20Uniandes-d62728)]()

<br/>
<p><em>Descubrimiento automático de dispositivos, escaneo de vulnerabilidades y reportes en lenguaje claro — sin conocimientos técnicos.</em></p>

</div>

---

## 📋 Tabla de contenidos

- [Descripción general](#descripción-general)
- [Características principales](#características-principales)
- [Arquitectura](#arquitectura)
- [Modos de distribución](#modos-de-distribución)
- [Primeros pasos](#primeros-pasos)
  - [Modo A — Aplicación de escritorio Windows](#modo-a--aplicación-de-escritorio-windows)
  - [Modo B — Servidor Raspberry Pi](#modo-b--servidor-raspberry-pi)
  - [Modo C — Raspberry Pi + cliente Windows](#modo-c--raspberry-pi--cliente-windows)
- [Stack tecnológico](#stack-tecnológico)
- [Referencia de la API](#referencia-de-la-api)
- [Notas de seguridad](#notas-de-seguridad)

---

## Descripción general

**Smart Home Vulnerability Manager (SHVM)** es una plataforma open source que escanea automáticamente la red doméstica en busca de vulnerabilidades en dispositivos IoT y presenta los resultados en lenguaje claro y accesible. El proyecto cierra la brecha entre las herramientas de seguridad empresarial (OWASP OVMG, NIST SP 800-40r4) y los usuarios del hogar que no cuentan con formación técnica para operarlas manualmente.

> **Principio de diseño central:** el sistema gestiona toda la complejidad técnica de forma autónoma. El usuario solo es interrumpido cuando se requiere una decisión humana indispensable.

SHVM integra descubrimiento de dispositivos (arp-scan), enumeración de puertos y servicios (Nmap), y detección de CVEs con verificación de credenciales por defecto (Nuclei) en un único pipeline automatizado. Los resultados se exponen a través de un panel React y se distribuyen como aplicación de escritorio Windows o como servidor Raspberry Pi.

Este proyecto fue desarrollado como tesis de pregrado en la **Universidad de los Andes** (Bogotá, Colombia), bajo la asesoría de **Sandra Rueda**.

---

## Características principales

- 🔍 **Descubrimiento automático de dispositivos** — detecta todos los dispositivos en la red local sin configuración previa
- 🛡️ **Escaneo de CVEs y credenciales por defecto** — verifica cada dispositivo contra miles de plantillas de vulnerabilidades conocidas
- 📊 **Reportes en lenguaje sencillo** — los resultados se presentan como niveles de impacto Bajo / Medio / Alto, nunca como puntuaciones CVSS crudas
- 🔄 **Escaneos programados** — intervalo configurable que mantiene el panorama de riesgo actualizado sin esfuerzo manual
- 🖥️ **Aplicación de escritorio Windows** — instalador en un clic, sin línea de comandos (usa WSL2 internamente)
- 🍓 **Modo Raspberry Pi** — escáner dedicado siempre activo, accesible desde cualquier navegador en la red local
- 🌐 **Monitoreo pasivo de tráfico** *(solo Raspberry Pi)* — análisis continuo en segundo plano mediante tcpdump
- 🔒 **Solo local** — todos los datos permanecen en tu red; no se requieren cuentas en la nube ni telemetría

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│                    Pipeline de escaneo                   │
│                                                          │
│  arp-scan  ──►  Nmap (XML)  ──►  Nuclei (NDJSON)       │
│ (descubrir)   (puertos/svcs)  (CVEs + credenciales)     │
└──────────────────────────┬──────────────────────────────┘
                           │
                  FastAPI + SQLite
                 (backend REST API)
                           │
            ┌──────────────┴──────────────┐
            │                             │
     React + Vite                  Shell Electron
     (SPA frontend)            (app escritorio Windows)
```

**Flujo de datos:**
1. `arp-scan` recorre la red local y devuelve la lista de pares IP/MAC activos.
2. Nmap realiza enumeración de puertos y servicios en cada host; el resultado se guarda como XML.
3. Nuclei toma las IPs extraídas del XML de Nmap y las verifica contra plantillas de CVEs y credenciales por defecto, generando NDJSON.
4. El backend FastAPI parsea los resultados, los persiste en SQLite y los expone vía REST.
5. El frontend React consulta la API y muestra los dispositivos, escaneos y hallazgos de vulnerabilidades.

---

## Modos de distribución

| | Modo A | Modo B | Modo C |
|---|---|---|---|
| **Plataforma** | Windows (WSL2) | Raspberry Pi | Raspberry Pi + Windows |
| **Tipo de escaneo** | Solo activo | Activo + Pasivo | Activo + Pasivo |
| **Acceso** | App Electron en escritorio | Cualquier navegador en la LAN | App Electron (cliente remoto) |
| **Dificultad de instalación** | Baja (instalador) | Media (un script) | Media |

---

## Primeros pasos

### Requisitos previos — todos los modos

- Una red doméstica de la que seas administrador
- Los dispositivos a escanear deben estar en la misma LAN

---

### Modo A — Aplicación de escritorio Windows

**Requisitos:** Windows 10/11 (x64), permisos de administrador.

1. Descarga el instalador más reciente desde [Releases](https://github.com/Laudarias/smart-home-vuln-manager/releases).
2. Ejecuta `SmartHomeVulnManager-Setup.exe` como administrador.
3. El instalador habilitará WSL2 automáticamente, instalará Ubuntu y configurará todas las dependencias de escaneo.
4. Cuando la pantalla de configuración confirme que todo está listo, haz clic en **Abrir aplicación**.

> ⚠️ Es posible que se requiera reiniciar el equipo la primera vez que se habilita WSL2. El instalador te lo indicará si es necesario.

**Desinstalar:** Panel de control → *Agregar o quitar programas* → *Smart Home Vulnerability Manager*.

---

### Modo B — Servidor Raspberry Pi

**Requisitos:** Raspberry Pi 3B+ o superior, Raspberry Pi OS (64 bits), conexión a internet durante la instalación.

```bash
# 1. Clonar el repositorio
git clone https://github.com/Laudarias/smart-home-vuln-manager.git
cd smart-home-vuln-manager

# 2. Ejecutar el instalador (requiere root)
sudo bash install/raspberry-pi/install.sh
```

El script realizará automáticamente:
- Instalación de dependencias del sistema (arp-scan, nmap, Nuclei, Avahi/mDNS)
- Creación del usuario de sistema `shvm`
- Configuración del entorno virtual Python e instalación de dependencias del backend
- Reglas de sudoers para las herramientas de escaneo
- Registro de un servicio `systemd` que inicia automáticamente con el equipo

Al finalizar, la aplicación estará disponible en:

```
http://<ip-de-la-raspberry>:8000
http://<nombre-del-host>.local:8000   ← mDNS, sin necesidad de conocer la IP
```

**Contraseña por defecto:** `admin123` — **cámbiala inmediatamente desde la página de Configuración.**

Comandos útiles:
```bash
sudo systemctl status smart-home-scanner    # Ver estado del servicio
sudo journalctl -u smart-home-scanner -f    # Ver logs en tiempo real
sudo systemctl restart smart-home-scanner   # Reiniciar el servicio
sudo systemctl stop smart-home-scanner      # Detener el servicio
```

---

### Modo C — Raspberry Pi + cliente Windows

1. Completa la [instalación del Modo B](#modo-b--servidor-raspberry-pi) en la Raspberry Pi.
2. Instala la aplicación de escritorio Windows desde [Releases](https://github.com/Laudarias/smart-home-vuln-manager/releases).
3. Al abrir la app por primera vez, ingresa la dirección de la Raspberry Pi (`http://<nombre>.local:8000`) cuando se te solicite.

La app Electron funcionará como cliente puro — no realiza escaneos locales, todos los datos provienen de la Pi.

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Frontend | React 18 + Vite + Tailwind CSS |
| Backend | FastAPI + SQLAlchemy + SQLite |
| Empaquetado de escritorio | Electron 30 + instalador NSIS |
| Entorno Linux en Windows | WSL2 + Ubuntu |
| Descubrimiento de dispositivos | arp-scan |
| Escaneo de puertos/servicios | Nmap (salida XML) |
| Detección de vulnerabilidades | Nuclei (salida NDJSON) |
| Monitoreo pasivo | tcpdump *(solo Raspberry Pi)* |
| Descubrimiento de servicios | Avahi / mDNS *(solo Raspberry Pi)* |
| Marcos de referencia | OWASP OVMG, NIST SP 800-40r4 |

---

## Referencia de la API

El backend expone una API REST documentada interactivamente en `http://localhost:8000/docs` (Swagger UI) cuando corre en modo desarrollo.

### Endpoints principales

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/health` | Verificación de estado del servidor |
| `POST` | `/auth/login` | Autenticarse y obtener token |
| `POST` | `/auth/change-password` | Cambiar la contraseña de administrador |
| `GET` | `/devices` | Listar todos los dispositivos descubiertos |
| `GET` | `/devices/{id}` | Obtener detalles de un dispositivo |
| `GET` | `/scans` | Listar todos los resultados de escaneo |
| `POST` | `/scans/trigger` | Iniciar un escaneo manual |
| `GET` | `/scans/{id}/vulnerabilities` | Obtener hallazgos de un escaneo |

---

## Notas de seguridad

- **Esta herramienta realiza escaneo activo de red.** Úsala solo en redes de tu propiedad o sobre las que tengas permiso explícito.
- La contraseña de administrador por defecto es `admin123`. **Cámbiala inmediatamente tras la instalación.**
- Todos los datos se almacenan localmente en `data/shvm.db`. No se envía ninguna información al exterior.
- El CORS está configurado actualmente como `allow_origins=["*"]` por conveniencia en redes locales. Si expones el backend fuera de tu LAN, restringe este valor en `backend/app/main.py`.
- Las plantillas de Nuclei se actualizan en el momento de la instalación. Ejecuta `nuclei -update-templates` periódicamente para mantener la cobertura al día.
