import { menuItems } from './navigation';

export type Company = {
  id: string;
  name: string;
  nit?: string;
  currency: string;
  country?: string;
  industry?: string;
  fiscalCloseMonth: string;
  lastData: string;
  periods: string[];
};

export const demoCompanies: Company[] = [
  {
    id: 'comercial-xyz',
    name: 'Comercial XYZ',
    nit: '0614-000000-000-0',
    currency: 'USD',
    country: 'El Salvador',
    industry: 'Comercio',
    fiscalCloseMonth: 'Diciembre',
    lastData: 'Agosto 2026',
    periods: ['2024', '2025', '2026'],
  },
  {
    id: 'constructora-abc',
    name: 'Constructora ABC',
    currency: 'USD',
    country: 'El Salvador',
    industry: 'Construcción',
    fiscalCloseMonth: 'Diciembre',
    lastData: 'Julio 2026',
    periods: ['2025', '2026'],
  },
];

export const workspaceMenuItems = menuItems;
