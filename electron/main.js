const { app, BrowserWindow, Menu, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn, execSync } = require('child_process');

// ─── Constantes ──────────────────────────────────────────────────────────────
const CONFIG_FILE = path.join(app.getPath('userData'), 'config.json');
const BACKEND_PORT = 8000;
const BACKEND_URL = `http://localhost:${BACKEND_PORT}`;
// Ruta dentro de WSL2 donde vive el proyecto (ajustable por el usuario)
const WSL_PROJECT_PATH = '/home/shvm/smart-home-vuln-manager';

// ─── Estado global ────────────────────────────────────────────────────────────
let mainWindow = null;
let loadingWindow = null;
let backendProcess = null;

// ─── Config ───────────────────────────────────────────────────────────────────
function loadConfig() {
  try {
    if (fs.existsSync(CONFIG_FILE)) {
      return JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8'));
    }
  } catch (e) { /* sin config */ }
  return {};
}

function saveConfig(data) {
  try {
    const current = loadConfig();
    fs.writeFileSync(CONFIG_FILE, JSON.stringify({ ...current, ...data }, null, 2));
    return true;
  } catch (e) { return false; }
}

// ─── Verificar WSL2 ──────────────────────────────────────────────────────────
function isWslAvailable() {
  try {
    execSync('wsl.exe --status', { stdio: 'pipe', timeout: 5000 });
    return true;
  } catch {
    try {
      // fallback: intentar correr un comando simple
      execSync('wsl.exe echo ok', { stdio: 'pipe', timeout: 5000 });
      return true;
    } catch {
      return false;
    }
  }
}

// ─── Lanzar backend en WSL2 ──────────────────────────────────────────────────
function startBackend() {
  return new Promise((resolve, reject) => {
    console.log('[backend] Iniciando en WSL2...');

    // Comando que activa el venv y lanza uvicorn
    const wslCommand = [
      `cd ${WSL_PROJECT_PATH}/backend`,
      '&& source .venv/bin/activate',
      `&& uvicorn app.main:app --host 0.0.0.0 --port ${BACKEND_PORT} --log-level warning`,
    ].join(' ');

    backendProcess = spawn('wsl.exe', ['-e', 'bash', '-c', wslCommand], {
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true, // invisible para el usuario
    });

    backendProcess.stdout.on('data', (data) => {
      console.log('[backend stdout]', data.toString());
    });

    backendProcess.stderr.on('data', (data) => {
      console.log('[backend stderr]', data.toString());
    });

    backendProcess.on('error', (err) => {
      console.error('[backend] Error al lanzar:', err);
      reject(err);
    });

    backendProcess.on('exit', (code) => {
      console.log(`[backend] Proceso terminó con código ${code}`);
      backendProcess = null;
    });

    // Esperar a que el backend responda (polling con timeout)
    waitForBackend(30000)
      .then(resolve)
      .catch(reject);
  });
}

// ─── Esperar a que el backend esté listo ─────────────────────────────────────
async function waitForBackend(timeoutMs = 30000) {
  const interval = 500;
  const maxAttempts = timeoutMs / interval;

  for (let i = 0; i < maxAttempts; i++) {
    try {
      const response = await fetch(`${BACKEND_URL}/api/auth/me`, {
        signal: AbortSignal.timeout(1000),
      });
      // El backend responde (401 también es válido — está corriendo)
      if (response.status < 500) {
        console.log('[backend] Listo en intento', i + 1);
        return true;
      }
    } catch {
      // Aún no disponible, esperar
    }
    await sleep(interval);

    // Actualizar progreso en loading window
    if (loadingWindow && !loadingWindow.isDestroyed()) {
      const progress = Math.min(0.9, (i + 1) / maxAttempts);
      loadingWindow.webContents.send('progress', Math.round(progress * 100));
    }
  }
  throw new Error(`El backend no respondió en ${timeoutMs / 1000} segundos`);
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ─── Detener backend ─────────────────────────────────────────────────────────
function stopBackend() {
  if (backendProcess) {
    console.log('[backend] Deteniendo...');
    try {
      // Matar el proceso uvicorn dentro de WSL2
      execSync(`wsl.exe -e bash -c "pkill -f 'uvicorn app.main:app'"`, {
        stdio: 'ignore', timeout: 3000,
      });
    } catch { /* ignorar errores al cerrar */ }
    backendProcess.kill();
    backendProcess = null;
  }
}

// ─── Ventana de carga ────────────────────────────────────────────────────────
function createLoadingWindow() {
  loadingWindow = new BrowserWindow({
    width: 420,
    height: 280,
    icon: path.join(__dirname, 'assets', 'icon.ico'),
    frame: false,
    resizable: false,
    center: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  loadingWindow.loadFile(path.join(__dirname, 'loading.html'));

  loadingWindow.on('closed', () => { loadingWindow = null; });
}

// ─── Ventana principal ───────────────────────────────────────────────────────
function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    icon: path.join(__dirname, 'assets', 'icon.ico'),
    show: false, // mostrar solo cuando cargue
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  mainWindow.loadURL(BACKEND_URL);

  mainWindow.once('ready-to-show', () => {
    if (loadingWindow && !loadingWindow.isDestroyed()) {
      loadingWindow.close();
    }
    mainWindow.show();
  });

  mainWindow.on('closed', () => { mainWindow = null; });
}

// ─── Menú ────────────────────────────────────────────────────────────────────
function createMenu() {
  const template = [
    {
      label: 'Archivo',
      submenu: [
        {
          label: 'Reiniciar backend',
          click: async () => {
            stopBackend();
            createLoadingWindow();
            try {
              await startBackend();
              if (mainWindow) mainWindow.reload();
              if (loadingWindow && !loadingWindow.isDestroyed()) loadingWindow.close();
            } catch (err) {
              showFatalError(err.message);
            }
          },
        },
        { type: 'separator' },
        { role: 'quit', label: 'Salir' },
      ],
    },
    {
      label: 'Ver',
      submenu: [
        { role: 'reload', label: 'Recargar' },
        { role: 'toggleDevTools', label: 'Herramientas de desarrollo' },
      ],
    },
  ];

  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

// ─── Error fatal ─────────────────────────────────────────────────────────────
function showFatalError(message) {
  if (loadingWindow && !loadingWindow.isDestroyed()) loadingWindow.close();
  dialog.showErrorBox(
    'Error al iniciar Smart Home Vulnerability Manager',
    `${message}\n\nVerifica que WSL2 esté instalado y vuelve a intentarlo.`
  );
  app.quit();
}

// ─── IPC ─────────────────────────────────────────────────────────────────────
ipcMain.handle('get-status', () => ({
  backendRunning: backendProcess !== null,
}));

// ─── App lifecycle ───────────────────────────────────────────────────────────
app.whenReady().then(async () => {
  createMenu();

  // 1. Verificar que WSL2 existe
  if (!isWslAvailable()) {
    showFatalError(
      'WSL2 no está disponible en este equipo.\n\n' +
      'Instálalo ejecutando en PowerShell (como administrador):\n' +
      'wsl --install\n\nLuego reinicia el equipo e intenta de nuevo.'
    );
    return;
  }

  // 2. Mostrar pantalla de carga
  createLoadingWindow();

  // 3. Lanzar backend
  try {
    await startBackend();
  } catch (err) {
    showFatalError(
      'No se pudo iniciar el backend.\n\n' +
      'Asegúrate de que la instalación se completó correctamente.\n\n' +
      `Detalle: ${err.message}`
    );
    return;
  }

  // 4. Abrir ventana principal
  createMainWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createMainWindow();
  });
});

app.on('window-all-closed', () => {
  stopBackend();
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
  stopBackend();
});