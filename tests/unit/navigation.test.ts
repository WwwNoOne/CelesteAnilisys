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

  it('reconoce rutas temporales de revisión de importación', async () => {
    const { isReviewPath, parseImportIdFromPath } = await import('../../src/renderer/navigation');
    expect(isReviewPath('/imports/42/review')).toBe(true);
    expect(isReviewPath('/files')).toBe(false);
    expect(parseImportIdFromPath('/imports/42/review')).toBe(42);
    expect(parseImportIdFromPath('/files')).toBeNull();
  });

  it('oculta los controles globales en Comparaciones y Archivos', async () => {
    const { showsGlobalContextControls } = await import('../../src/renderer/navigation');

    expect(showsGlobalContextControls('/comparisons')).toBe(false);
    expect(showsGlobalContextControls('/files')).toBe(false);
    expect(showsGlobalContextControls('/dashboard')).toBe(true);
  });
});
