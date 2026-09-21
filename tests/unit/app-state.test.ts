import { describe, expect, it } from 'vitest';
import { demoCompanies, workspaceMenuItems } from '../../src/renderer/app-state';

describe('workspace por empresa', () => {
  it('provee empresas de ejemplo con períodos independientes', () => {
    expect(demoCompanies.length).toBeGreaterThan(0);
    expect(demoCompanies[0]).toMatchObject({ name: 'Comercial XYZ' });
    expect(demoCompanies[0]?.periods).toEqual(['2024', '2025', '2026']);
  });

  it('mantiene Archivos como el acceso principal a importaciones', () => {
    expect(workspaceMenuItems.find((item) => item.id === 'files')?.label).toBe('ARCHIVOS');
  });
});
