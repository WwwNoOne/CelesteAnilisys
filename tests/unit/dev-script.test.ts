import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

const packageJson = JSON.parse(readFileSync(new URL('../../package.json', import.meta.url), 'utf8')) as {
  scripts: { dev: string };
};

describe('comando de desarrollo', () => {
  it('compila Electron y configura la URL del servidor Vite antes de abrirlo', () => {
    expect(packageJson.scripts.dev).toContain('npm run build:electron');
    expect(packageJson.scripts.dev).toContain('VITE_DEV_SERVER_URL=http://localhost:5173');
  });
});
