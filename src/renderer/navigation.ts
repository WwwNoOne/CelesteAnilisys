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
