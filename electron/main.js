const { app, BrowserWindow, Menu, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');

let mainWindow;
let setupWindow;
const CONFIG_FILE = path.join(app.getPath('userData'), 'config.json');

function loadConfig() {
  try {
    if (fs.existsSync(CONFIG_FILE)) {
      return JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8'));
    }
  } catch (error) {
    console.error('Error loading config:', error);
  }
  return null;
}

function saveConfig(config) {
  try {
    fs.writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2));
    return true;
  } catch (error) {
    console.error('Error saving config:', error);
    return false;
  }
}

async function checkPiConnection(ip) {
  try {
    const response = await fetch(`http://${ip}:8000/api/auth/me`, {
      method: 'GET',
      timeout: 4000,
    });
    return response.ok;
  } catch (error) {
    return false;
  }
}

function createMainWindow(ip) {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  mainWindow.loadURL(`http://${ip}:8000`);

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function createSetupWindow() {
  setupWindow = new BrowserWindow({
    width: 500,
    height: 400,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  setupWindow.loadFile(path.join(__dirname, 'setup.html'));

  setupWindow.on('closed', () => {
    setupWindow = null;
  });
}

function createMenu() {
  const template = [
    {
      label: 'Archivo',
      submenu: [
        {
          label: 'Reconfigurar IP de la Raspberry Pi',
          click: () => {
            if (fs.existsSync(CONFIG_FILE)) {
              fs.unlinkSync(CONFIG_FILE);
            }
            if (mainWindow) {
              mainWindow.close();
            }
            app.relaunch();
            app.exit();
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

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

ipcMain.handle('check-and-save-pi', async (event, ip) => {
  const isConnected = await checkPiConnection(ip);

  if (!isConnected) {
    return { success: false, error: 'No se pudo conectar a la Raspberry Pi en esa IP' };
  }

  const saved = saveConfig({ piIp: ip });

  if (!saved) {
    return { success: false, error: 'Error al guardar la configuración' };
  }

  if (setupWindow) {
    setupWindow.close();
  }

  createMainWindow(ip);
  return { success: true };
});

app.whenReady().then(async () => {
  createMenu();

  const config = loadConfig();

  if (config && config.piIp) {
    const isConnected = await checkPiConnection(config.piIp);
    if (isConnected) {
      createMainWindow(config.piIp);
    } else {
      createSetupWindow();
    }
  } else {
    createSetupWindow();
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createSetupWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
