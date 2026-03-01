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

export class SheetsService {
  async appendRow(
    spreadsheetId: string,
    row: SheetCell[],
    _options: { sheetName?: string | null; headerValues?: string[] | null } = {},
  ): Promise<void> {
    const preview = row.map((cell) => {
      if (cell && typeof cell === 'object' && 'hyperlink' in cell) {
        return `HYPERLINK(${cell.hyperlink.url}, ${cell.hyperlink.label || ''})`;
      }
      return cell;
    });
    // mock append: log to console for visibility
    console.log('[SHEETS] appendRow', spreadsheetId, preview);
  }
}

export default new SheetsService();
//Upload to sheets
