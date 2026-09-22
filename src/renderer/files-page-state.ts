export function canDeleteImport(status: string): boolean {
  return status !== 'APPROVED' && status !== 'IMPORTED';
}
