import { env } from './runtimeEnv.js';

export type CompanyConfig = {
  key: string;
  name: string;
  spreadsheetId: string;
  driveFolderId: string;
};

const normalize = (value: string) =>
  value
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim();

export const companyOptions: CompanyConfig[] = [
  {
    key: 'atomo',
    name: env.COMPANY_ATOMO_NAME,
    spreadsheetId: env.COMPANY_ATOMO_SPREADSHEET_ID,
    driveFolderId: env.COMPANY_ATOMO_DRIVE_FOLDER_ID,
  },
  {
    key: 'aprilis',
    name: env.COMPANY_APRILIS_NAME,
    spreadsheetId: env.COMPANY_APRILIS_SPREADSHEET_ID,
    driveFolderId: env.COMPANY_APRILIS_DRIVE_FOLDER_ID,
  },
  {
    key: 'masiva',
    name: env.COMPANY_MASIVA_NAME,
    spreadsheetId: env.COMPANY_MASIVA_SPREADSHEET_ID,
    driveFolderId: env.COMPANY_MASIVA_DRIVE_FOLDER_ID,
  },
];

export function resolveCompanySelection(selection: string): CompanyConfig | null {
  const trimmed = selection.trim();
  if (!trimmed) return null;
  const index = Number.parseInt(trimmed, 10);
  if (Number.isInteger(index) && index >= 1 && index <= companyOptions.length) {
    return companyOptions[index - 1];
  }
  const normalized = normalize(trimmed);
  if (!normalized) return null;
  return (
    companyOptions.find((option) => normalize(option.key) === normalized) ||
    companyOptions.find((option) => normalize(option.name) === normalized) ||
    null
  );
}

export function formatCompanySelectionPrompt(): string {
  const lines = ['¿A qué empresa corresponde este recibo? Responde con el número o toca un botón:'];
  companyOptions.forEach((option, index) => {
    lines.push(`${index + 1}) ${option.name}`);
  });
  return lines.join('\n');
}

export function isCompanyConfigured(company: CompanyConfig): boolean {
  return Boolean(company.spreadsheetId && company.driveFolderId);
}
