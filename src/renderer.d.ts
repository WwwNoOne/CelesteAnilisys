export {};

declare global {
  interface Window {
    electronAPI?: {
      selectFiles: () => Promise<string[]>;
    };
  }
}
