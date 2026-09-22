export type MenuItem = {
  id: string;
  label: string;
  path: string;
  icon: string;
};

export const initialPath = '/companies';

export const menuItems: MenuItem[] = [
  { id: 'dashboard', label: 'DASHBOARD', path: '/dashboard', icon: '⌂' },
  { id: 'statements', label: 'ESTADOS FINANCIEROS', path: '/statements', icon: '▤' },
  { id: 'analysis', label: 'ANÁLISIS', path: '/analysis', icon: '▥' },
  { id: 'comparisons', label: 'COMPARACIONES', path: '/comparisons', icon: '⇄' },
  { id: 'files', label: 'ARCHIVOS', path: '/files', icon: '□' },
  { id: 'settings', label: 'CONFIGURACIÓN', path: '/settings', icon: '⚙' },
];

export function isReviewPath(path: string): boolean {
  return /^\/imports\/\d+\/review$/.test(path);
}

export function parseImportIdFromPath(path: string): number | null {
  const match = path.match(/^\/imports\/(\d+)\/review$/);
  return match ? Number.parseInt(match[1], 10) : null;
}

export function showsGlobalContextControls(path: string): boolean {
  return path !== '/comparisons' && path !== '/files';
}
