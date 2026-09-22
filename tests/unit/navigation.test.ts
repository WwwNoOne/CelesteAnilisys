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

  it('construye y reconoce rutas de selección y revisión por hoja', async () => {
    const {
      selectSheetPath,
      reviewSheetPath,
      isSelectSheetPath,
      isReviewPath,
      parseImportIdFromPath,
      parseSheetNameFromReviewPath,
    } = await import('../../src/renderer/navigation');

    expect(selectSheetPath(7)).toBe('/imports/7/select-sheet');
    expect(isSelectSheetPath('/imports/7/select-sheet')).toBe(true);
    expect(isSelectSheetPath('/imports/7/review/2025')).toBe(false);

    expect(reviewSheetPath(7, '2025')).toBe('/imports/7/review/2025');
    expect(reviewSheetPath(7, 'Flujo 2025')).toBe('/imports/7/review/Flujo%202025');
    expect(isReviewPath('/imports/7/review/2025')).toBe(true);
    expect(parseImportIdFromPath('/imports/7/review/2025')).toBe(7);
    expect(parseSheetNameFromReviewPath('/imports/7/review/Flujo%202025')).toBe('Flujo 2025');
    expect(parseSheetNameFromReviewPath('/imports/7/select-sheet')).toBeNull();
  });
});
