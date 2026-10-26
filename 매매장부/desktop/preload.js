'use strict';
// 장부 화면(웹 페이지)에 백업 폴더 기능만 노출한다. 파일 이름과 위치는 main.js가 검증한다.
const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('ledgerNative', {
  getDir: () => ipcRenderer.invoke('ledger:get-dir'),
  pickDir: () => ipcRenderer.invoke('ledger:pick-dir'),
  clearDir: () => ipcRenderer.invoke('ledger:clear-dir'),
  writeBackup: (name, text) => ipcRenderer.invoke('ledger:write', name, text),
  latestBackup: () => ipcRenderer.invoke('ledger:latest')
});
