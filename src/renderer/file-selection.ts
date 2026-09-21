const supportedExtensions = ['.xls', '.xlsx', '.csv'];

export function isSupportedFile(fileName: string): boolean {
  const normalizedName = fileName.toLowerCase();
  return supportedExtensions.some((extension) => normalizedName.endsWith(extension));
}

export function fileNameFromPath(filePath: string): string {
  return filePath.split(/[\\/]/).pop() ?? filePath;
}
