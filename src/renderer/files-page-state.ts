export function canDeleteImport(status: string): boolean {
  return status === 'READY_FOR_REVIEW';
}
