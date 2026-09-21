import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('electronAPI', {
  selectFiles: (): Promise<string[]> => ipcRenderer.invoke('select-files'),
});
