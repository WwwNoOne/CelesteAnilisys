import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

const tsconfig = JSON.parse(readFileSync(new URL('../../tsconfig.electron.json', import.meta.url), 'utf8')) as {
  compilerOptions: { module: string; moduleResolution: string };
};

describe('configuración de TypeScript para Electron', () => {
  it('usa la resolución NodeNext compatible con TypeScript actual', () => {
    expect(tsconfig.compilerOptions.module).toBe('NodeNext');
    expect(tsconfig.compilerOptions.moduleResolution).toBe('NodeNext');
  });
});
