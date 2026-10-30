// 页面里只多出一个 window.desktop：存文件（弹「另存为」）和打开刚存的文件夹，别的系统能力都不给
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('desktop', {
  saveFile: (name, bytes) => ipcRenderer.invoke('desktop:save-file', String(name), bytes),
  reveal: file => ipcRenderer.invoke('desktop:reveal', String(file)),
});
