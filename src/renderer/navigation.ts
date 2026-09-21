export type MenuItem = {
  id: string;
  label: string;
  path: string;
  icon: string;
};

export const menuItems: MenuItem[] = [
  { id: 'resumen', label: 'RESUMEN', path: '/', icon: '⌂' },
  { id: 'subida', label: 'SUBIDA', path: '/subida', icon: '↑' },
  { id: 'analisis', label: 'ANÁLISIS', path: '/analisis', icon: '▥' },
  { id: 'configuracion', label: 'CONFIGURACIÓN', path: '/configuracion', icon: '⚙' },
];
