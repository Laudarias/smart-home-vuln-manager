const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  /**
   * Verifica la conexión con la Raspberry Pi y guarda su IP.
   * @param {string} ip - La IP de la Raspberry Pi introducida por el usuario
   * @returns {Promise<{success: boolean, error?: string}>}
   */
  checkAndSavePi: (ip) => ipcRenderer.invoke('check-and-save-pi', ip),
});