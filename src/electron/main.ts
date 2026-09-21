import { app, BrowserWindow, dialog, ipcMain } from 'electron';
import { join } from 'node:path';
import { readFile } from 'node:fs/promises';

function createWindow() {
  const window = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 960,
    minHeight: 640,
    backgroundColor: '#f4f7fc',
    webPreferences: {
      preload: join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (process.env.VITE_DEV_SERVER_URL) {
    void window.loadURL(process.env.VITE_DEV_SERVER_URL);
  } else {
    void window.loadFile(join(__dirname, '../dist/index.html'));
  }
}

ipcMain.handle('select-files', async () => {
  const result = await dialog.showOpenDialog({
    properties: ['openFile', 'multiSelections'],
    filters: [{ name: 'Archivos financieros', extensions: ['xlsx', 'xlsm'] }],
  });
  return result.canceled ? [] : result.filePaths;
});

ipcMain.handle('read-file', async (_event, filePath: string) => ({
  name: filePath.split(/[\\/]/).pop() ?? 'archivo.xlsx',
  data: (await readFile(filePath)).toString('base64'),
}));

app.whenReady().then(() => {
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
