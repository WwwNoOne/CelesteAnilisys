import { describe, expect, it } from 'vitest';
import { isSupportedFile } from '../../src/renderer/file-selection';

describe('selección de archivos', () => {
  it('acepta formatos financieros soportados', () => {
    expect(isSupportedFile('reporte.xlsx')).toBe(true);
    expect(isSupportedFile('reporte.xls')).toBe(true);
    expect(isSupportedFile('reporte.csv')).toBe(true);
  });

  it('rechaza formatos no soportados', () => {
    expect(isSupportedFile('reporte.pdf')).toBe(false);
  });
});
