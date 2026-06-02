const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  /**
   * Recibe actualizaciones de progreso del backend (0-100).
   * Usado por loading.html para animar la barra de carga.
   */
  onProgress: (callback) => {
    ipcRenderer.on('progress', (_event, pct) => callback(pct));
  },

  /**
   * Consulta el estado actual del backend.
   * @returns {Promise<{backendRunning: boolean}>}
   */
  getStatus: () => ipcRenderer.invoke('get-status'),
});