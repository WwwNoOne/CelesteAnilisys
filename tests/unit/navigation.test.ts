import { describe, expect, it } from 'vitest';
import { menuItems, initialPath } from '../../src/renderer/navigation';

describe('menú lateral', () => {
  it('inicia en Empresas y organiza el workspace por empresa', () => {
    expect(initialPath).toBe('/companies');
    expect(menuItems.map((item) => item.id)).toEqual([
      'dashboard',
      'statements',
      'analysis',
      'comparisons',
      'files',
      'settings',
    ]);
    expect(menuItems.find((item) => item.id === 'files')).toMatchObject({
      label: 'ARCHIVOS',
      path: '/files',
    });
  });

  it('no expone SUBIDA como una sección principal', () => {
    expect(menuItems.some((item) => item.id === 'subida')).toBe(false);
  });
});
