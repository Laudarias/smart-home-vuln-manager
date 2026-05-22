const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  checkAndSavePi: (ip) => ipcRenderer.invoke("check-and-save-pi", ip),
});
