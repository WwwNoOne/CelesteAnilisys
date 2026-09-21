import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('electronAPI', {
  selectFiles: (): Promise<string[]> => ipcRenderer.invoke('select-files'),
  readFile: (filePath: string): Promise<{ name: string; data: string }> => ipcRenderer.invoke('read-file', filePath),
});
