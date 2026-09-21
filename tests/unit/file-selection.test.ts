import { describe, expect, it } from 'vitest';
import { isSupportedFile } from '../../src/renderer/file-selection';

describe('selección de archivos', () => {
  it('acepta formatos financieros soportados', () => {
    expect(isSupportedFile('reporte.xlsx')).toBe(true);
    expect(isSupportedFile('reporte.xlsm')).toBe(true);
  });

  it('rechaza formatos no soportados', () => {
    expect(isSupportedFile('reporte.xls')).toBe(false);
    expect(isSupportedFile('reporte.csv')).toBe(false);
    expect(isSupportedFile('reporte.pdf')).toBe(false);
  });
});
