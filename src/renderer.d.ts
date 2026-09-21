export {};

declare global {
  interface Window {
    electronAPI?: {
      selectFiles: () => Promise<string[]>;
      readFile: (filePath: string) => Promise<{ name: string; data: string }>;
    };
  }
}
