import { google } from 'googleapis';
import { logger } from './logger';

type SheetCell =
  | string
  | number
  | null
  | undefined
  | {
      hyperlink: {
        url: string;
        label?: string | null;
      };
    };

function formatSheetRange(range: string) {
  const trimmed = range.trim();
  if (!trimmed) return trimmed;

  // If the user already provided a full range (sheet and columns), keep it as-is.
  if (trimmed.includes('!')) return trimmed;

  // If it's a bare A1 range (e.g., 'A:Z' or 'A1:C10'), keep it as-is.
  if (/^[A-Za-z]+[0-9]*(:[A-Za-z]+[0-9]*)?$/.test(trimmed)) {
    return trimmed;
  }

  // Otherwise quote the sheet name (doubling any embedded quotes) and append default range.
  const safeSheetName = `'${trimmed.replace(/'/g, "''")}'`;
  return `${safeSheetName}!A:Z`;
}

function getCredentials() {
  const rawJson = process.env.GOOGLE_SERVICE_ACCOUNT_JSON || process.env.GOOGLE_SERVICE_ACCOUNT;
  const b64 = process.env.GOOGLE_SERVICE_ACCOUNT_B64;
  let raw = rawJson;
  if (!raw && b64) {
    try {
      raw = Buffer.from(b64, 'base64').toString('utf8');
    } catch (e) {
      return null;
    }
  }
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch (e) {
    return null;
  }
}

type AppendOptions = {
  sheetName?: string | null;
  headerValues?: string[] | null;
};

function columnIndexToLetters(index: number): string {
  let result = '';
  let current = index + 1;
  while (current > 0) {
    const remainder = (current - 1) % 26;
    result = String.fromCharCode(65 + remainder) + result;
    current = Math.floor((current - 1) / 26);
  }
  return result || 'A';
}

export class SheetsServiceReal {
  private localeCache = new Map<string, string>();
  private sheetIdCache = new Map<string, Map<string, number>>();
  private authMode: 'unknown' | 'service-account' = 'unknown';

  private logAuthMode(mode: 'service-account') {
    if (this.authMode === mode) return;
    this.authMode = mode;
    logger.info(`[sheets] Using ${mode} credentials`);
  }

  private async authClient() {
    const credentials = getCredentials();
    if (credentials) {
      const auth: any = new (google.auth as any).GoogleAuth({
        credentials,
        scopes: ['https://www.googleapis.com/auth/spreadsheets'],
      });
      const client: any = await auth.getClient();
      this.logAuthMode('service-account');
      return client;
    }

    throw new Error('Missing GOOGLE_SERVICE_ACCOUNT / GOOGLE_SERVICE_ACCOUNT_JSON env — service account credentials are required.');
  }

  private normalizeSheetTitle(title: string): string {
    return title.replace(/^'/, '').replace(/'$/, '').replace(/''/g, "'").trim();
  }

  private cacheSheetId(spreadsheetId: string, title: string, sheetId: number) {
    const key = this.normalizeSheetTitle(title);
    const existing = this.sheetIdCache.get(spreadsheetId) ?? new Map();
    existing.set(key, sheetId);
    this.sheetIdCache.set(spreadsheetId, existing);
  }

  private async getSheetIdByName(api: ReturnType<typeof google.sheets>, spreadsheetId: string, sheetName: string): Promise<number | null> {
    const normalized = this.normalizeSheetTitle(sheetName);
    const cached = this.sheetIdCache.get(spreadsheetId)?.get(normalized);
    if (cached !== undefined) {
      return cached;
    }
    const meta = await api.spreadsheets.get({
      spreadsheetId,
      fields: 'sheets.properties(sheetId,title)',
    });
    const map = this.sheetIdCache.get(spreadsheetId) ?? new Map();
    for (const sheet of meta.data.sheets || []) {
      const title = sheet.properties?.title;
      const id = sheet.properties?.sheetId;
      if (title != null && id != null) {
        map.set(this.normalizeSheetTitle(title), id);
      }
    }
    this.sheetIdCache.set(spreadsheetId, map);
    return map.get(normalized) ?? null;
  }

  private extractSheetName(range: string): string | null {
    if (!range.includes('!')) return null;
    const [sheetPart] = range.split('!');
    if (!sheetPart) return null;
    return this.normalizeSheetTitle(sheetPart);
  }

  private async getSpreadsheetLocale(spreadsheetId: string, auth: any): Promise<string | null> {
    const fromEnv = process.env.SHEET_LOCALE;
    if (fromEnv && fromEnv.trim()) {
      const normalized = fromEnv.trim();
      this.localeCache.set(spreadsheetId, normalized);
      return normalized;
    }

    if (this.localeCache.has(spreadsheetId)) {
      return this.localeCache.get(spreadsheetId) || null;
    }

    const api = google.sheets({ version: 'v4', auth });
    const meta = await api.spreadsheets.get({
      spreadsheetId,
      fields: 'properties(locale)',
    });
    const locale = meta.data.properties?.locale || null;
    if (locale) {
      this.localeCache.set(spreadsheetId, locale);
    }
    return locale;
  }

  private localeUsesSemicolon(locale: string | null) {
    const override = process.env.SHEET_FORMULA_SEPARATOR;
    if (override === ',' || override === ';') {
      return override === ';';
    }
    if (!locale) return false;
    const normalized = locale.toLowerCase();
    const semicolonLocales = [
      'cs',
      'da',
      'de',
      'es',
      'fr',
      'it',
      'nl',
      'pl',
      'pt',
      'ru',
      'sv',
      'tr',
      'fi',
      'nb',
      'nn',
      'hu',
      'sk',
    ];
    return semicolonLocales.some((prefix) => normalized.startsWith(prefix));
  }

  private async resolveAppendRange(
    spreadsheetId: string,
    auth: any,
    api: ReturnType<typeof google.sheets>,
  ): Promise<{ range: string; locale: string | null; sheetId: number | null }> {
    // 1) If SHEET_RANGE is provided, use it directly (e.g., 'MySheet!A:Z' or 'A:Z')
    const sheetRange = process.env.SHEET_RANGE;
    if (sheetRange && sheetRange.trim()) {
      const normalized = formatSheetRange(sheetRange);
      const locale = await this.getSpreadsheetLocale(spreadsheetId, auth);
      const sheetName = this.extractSheetName(normalized);
      const sheetId = sheetName ? await this.getSheetIdByName(api, spreadsheetId, sheetName) : null;
      logger.info('Sheets range from SHEET_RANGE', { range: normalized });
      return { range: normalized, locale, sheetId };
    }

    // 2) If SHEET_NAME is provided, append to that sheet's A:Z
    const sheetName = process.env.SHEET_NAME;
    if (sheetName && sheetName.trim()) {
      const r = formatSheetRange(sheetName);
      const locale = await this.getSpreadsheetLocale(spreadsheetId, auth);
      const sheetId = await this.getSheetIdByName(api, spreadsheetId, sheetName);
      logger.info('Sheets range from SHEET_NAME', { range: r });
      return { range: r, locale, sheetId };
    }

    // 3) Discover the first sheet title and append to A:Z range
    const meta = await api.spreadsheets.get({
      spreadsheetId,
      fields: 'properties(locale),sheets.properties.title,sheets.properties.sheetId',
    });
    const locale = meta.data.properties?.locale || null;
    if (locale) {
      this.localeCache.set(spreadsheetId, locale);
    }
    const sheets = meta.data.sheets || [];
    const first = sheets[0];
    const title = first?.properties?.title || 'Sheet1';
    const r = formatSheetRange(title);
    const sheetId = first?.properties?.sheetId ?? null;
    if (sheetId != null && title) {
      this.cacheSheetId(spreadsheetId, title, sheetId);
    }
    logger.info('Sheets range from discovery', { range: r, title });
    return { range: r, locale, sheetId };
  }

  private extractRowNumber(cell?: string | null): number | null {
    if (!cell) return null;
    const match = cell.match(/(\d+)/);
    return match ? Number.parseInt(match[1], 10) : null;
  }

  private extractColumnLetters(cell?: string | null): string | null {
    if (!cell) return null;
    const match = cell.match(/([A-Z]+)/i);
    return match ? match[1].toUpperCase() : null;
  }

  private columnLettersToIndex(letters: string): number | null {
    if (!letters) return null;
    let index = 0;
    for (const char of letters) {
      index = index * 26 + (char.charCodeAt(0) - 64);
    }
    return Number.isFinite(index) ? index - 1 : null;
  }

  private parseRangeBounds(range?: string | null): {
    startRowIndex: number;
    endRowIndex: number;
    startColumnIndex: number;
    endColumnIndex: number;
  } | null {
    if (!range) return null;
    const rangePart = range.includes('!') ? range.split('!')[1] : range;
    if (!rangePart) return null;
    const [startCellRaw, endCellRaw] = rangePart.split(':');
    const startCell = startCellRaw?.trim();
    const endCell = (endCellRaw ?? startCellRaw)?.trim();
    if (!startCell || !endCell) return null;
    const startRow = this.extractRowNumber(startCell);
    const endRow = this.extractRowNumber(endCell);
    const startColLetters = this.extractColumnLetters(startCell);
    const endColLetters = this.extractColumnLetters(endCell);
    if (
      startRow == null ||
      endRow == null ||
      startColLetters == null ||
      endColLetters == null
    ) {
      return null;
    }
    const startColumnIndex = this.columnLettersToIndex(startColLetters);
    const endColumnIndex = this.columnLettersToIndex(endColLetters);
    if (startColumnIndex == null || endColumnIndex == null) return null;
    return {
      startRowIndex: startRow - 1,
      endRowIndex: endRow,
      startColumnIndex,
      endColumnIndex: endColumnIndex + 1,
    };
  }

  private async resolveSheetIdFromRange(
    api: ReturnType<typeof google.sheets>,
    spreadsheetId: string,
    range?: string | null,
  ): Promise<number | null> {
    if (!range) return null;
    const sheetName = this.extractSheetName(range);
    if (!sheetName) return null;
    return this.getSheetIdByName(api, spreadsheetId, sheetName);
  }

  private async ensureSheetRange(
    api: ReturnType<typeof google.sheets>,
    spreadsheetId: string,
    sheetName: string,
    headerValues?: string[] | null,
  ): Promise<{ range: string; sheetId: number | null }> {
    const existingId = await this.getSheetIdByName(api, spreadsheetId, sheetName);
    if (existingId != null) {
      return { range: formatSheetRange(sheetName), sheetId: existingId };
    }

    const addRes = await api.spreadsheets.batchUpdate({
      spreadsheetId,
      requestBody: {
        requests: [
          {
            addSheet: {
              properties: {
                title: sheetName,
              },
            },
          },
        ],
      },
    });
    const replies = addRes.data.replies || [];
    const created = replies.find((reply) => reply.addSheet?.properties);
    const newSheetId = created?.addSheet?.properties?.sheetId ?? null;
    if (newSheetId != null) {
      this.cacheSheetId(spreadsheetId, sheetName, newSheetId);
    }

    if (headerValues && headerValues.length) {
      const lastColumn = columnIndexToLetters(headerValues.length - 1);
      const quotedName = `'${sheetName.replace(/'/g, "''")}'`;
      const headerRange = `${quotedName}!A1:${lastColumn}1`;
      try {
        await api.spreadsheets.values.update({
          spreadsheetId,
          range: headerRange,
          valueInputOption: 'USER_ENTERED',
          requestBody: {
            values: [headerValues],
          },
        });
        if (newSheetId != null) {
          await this.applyHeaderFormatting(api, spreadsheetId, newSheetId, headerValues);
        }
      } catch (err) {
        logger.warn('Failed to write header row for new sheet', {
          sheetName,
          error: (err as Error).message,
        });
      }
    }

    return { range: formatSheetRange(sheetName), sheetId: newSheetId };
  }

  private async applyHeaderFormatting(
    api: ReturnType<typeof google.sheets>,
    spreadsheetId: string,
    sheetId: number,
    headerValues: string[],
  ): Promise<void> {
    const columnCount = headerValues.length;
    const minWidth = 90;
    const maxWidth = 260;
    const headerRequests: any[] = [
      {
        repeatCell: {
          range: {
            sheetId,
            startRowIndex: 0,
            endRowIndex: 1,
            startColumnIndex: 0,
            endColumnIndex: columnCount,
          },
          cell: {
            userEnteredFormat: {
              horizontalAlignment: 'CENTER',
              verticalAlignment: 'MIDDLE',
              wrapStrategy: 'WRAP',
              textFormat: {
                bold: true,
                fontSize: 12,
              },
              backgroundColor: {
                red: 0.95,
                green: 0.95,
                blue: 0.95,
              },
            },
          },
          fields: 'userEnteredFormat(horizontalAlignment,verticalAlignment,wrapStrategy,textFormat,backgroundColor)',
        },
      },
      {
        updateDimensionProperties: {
          range: {
            sheetId,
            dimension: 'ROWS',
            startIndex: 0,
            endIndex: 1,
          },
          properties: {
            pixelSize: 28,
          },
          fields: 'pixelSize',
        },
      },
    ];

    headerValues.forEach((value, index) => {
      const trimmed = value?.trim() ?? '';
      const estimated = Math.round(trimmed.length * 10 + 28);
      const pixelSize = Math.min(maxWidth, Math.max(minWidth, estimated));
      headerRequests.push({
        updateDimensionProperties: {
          range: {
            sheetId,
            dimension: 'COLUMNS',
            startIndex: index,
            endIndex: index + 1,
          },
          properties: {
            pixelSize,
          },
          fields: 'pixelSize',
        },
      });
    });

    try {
      await api.spreadsheets.batchUpdate({
        spreadsheetId,
        requestBody: { requests: headerRequests },
      });
    } catch (err) {
      logger.warn('Failed to apply header formatting', { error: (err as Error).message });
    }
  }

  private async applyFormatting(
    api: ReturnType<typeof google.sheets>,
    spreadsheetId: string,
    sheetIdHint: number | null,
    updatedRange?: string | null,
  ): Promise<void> {
    if (!updatedRange) return;
    const bounds = this.parseRangeBounds(updatedRange);
    if (!bounds) return;
    const sheetId = sheetIdHint ?? (await this.resolveSheetIdFromRange(api, spreadsheetId, updatedRange));
    if (sheetId == null) return;

    const requests: any[] = [
      {
        repeatCell: {
          range: {
            sheetId,
            startRowIndex: bounds.startRowIndex,
            endRowIndex: bounds.endRowIndex,
            startColumnIndex: bounds.startColumnIndex,
            endColumnIndex: bounds.endColumnIndex,
          },
          cell: {
            userEnteredFormat: {
              horizontalAlignment: 'CENTER',
              verticalAlignment: 'MIDDLE',
              wrapStrategy: 'WRAP',
            },
          },
          fields: 'userEnteredFormat(horizontalAlignment,verticalAlignment,wrapStrategy)',
        },
      },
    ];

    try {
      await api.spreadsheets.batchUpdate({
        spreadsheetId,
        requestBody: { requests },
      });
    } catch (err) {
      logger.warn('Failed to apply formatting to appended row', { error: (err as Error).message });
    }
  }

  private serializeCell(cell: SheetCell, separator: string): string | number | null {
    if (cell == null) return '';
    if (typeof cell === 'number') return cell;
    if (typeof cell === 'string') return cell;

    if (typeof cell === 'object' && 'hyperlink' in cell) {
      const url = cell.hyperlink.url;
      const label = cell.hyperlink.label;
      if (!url) return '';
      const safeUrl = url.replace(/"/g, '""');
      if (!label || !label.toString().trim()) {
        return `=HYPERLINK("${safeUrl}")`;
      }
      const safeLabel = label.toString().replace(/"/g, '""');
      return `=HYPERLINK("${safeUrl}"${separator}"${safeLabel}")`;
    }

    return '';
  }

  async appendRow(spreadsheetId: string, row: SheetCell[], options: AppendOptions = {}): Promise<void> {
    const client = await this.authClient();
    const sheetsApi = google.sheets({ version: 'v4', auth: client });
    let range: string;
    let locale: string | null = null;
    let sheetId: number | null = null;

    if (options.sheetName) {
      locale = await this.getSpreadsheetLocale(spreadsheetId, client);
      const ensured = await this.ensureSheetRange(
        sheetsApi,
        spreadsheetId,
        options.sheetName,
        options.headerValues,
      );
      range = ensured.range;
      sheetId = ensured.sheetId;
    } else {
      const resolved = await this.resolveAppendRange(spreadsheetId, client, sheetsApi);
      range = resolved.range;
      locale = resolved.locale;
      sheetId = resolved.sheetId;
    }

    const separator = this.localeUsesSemicolon(locale) ? ';' : ',';
    const serializedRow = row.map((cell) => this.serializeCell(cell, separator));
    logger.info('Appending row to sheets', {
      spreadsheetId,
      range,
      preview: serializedRow.slice(0, 5),
      locale,
    });
    const appendRes = await sheetsApi.spreadsheets.values.append({
      spreadsheetId,
      range,
      valueInputOption: 'USER_ENTERED',
      requestBody: {
        values: [serializedRow],
      },
    });
    const updatedRange = appendRes.data.updates?.updatedRange;
    await this.applyFormatting(sheetsApi, spreadsheetId, sheetId, updatedRange);
  }
}

export default new SheetsServiceReal();
