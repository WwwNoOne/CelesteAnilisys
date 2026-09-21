import { describe, expect, it } from 'vitest';
import { menuItems } from '../../src/renderer/navigation';

describe('menú lateral', () => {
  it('incluye SUBIDA como una sección navegable, sin convertirla en la pantalla inicial', () => {
    expect(menuItems.find((item) => item.id === 'subida')).toMatchObject({
      label: 'SUBIDA',
      path: '/subida',
    });
    expect(menuItems[0]?.id).not.toBe('subida');
  });
});
