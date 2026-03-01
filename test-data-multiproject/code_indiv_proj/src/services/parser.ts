import type { Buffer } from 'buffer';
import type { ParserInput, ReceiptParseResult } from '../types/receipt';

export class ParserService {
  async parse(input: ParserInput, _opts: { buffer?: Buffer | null } = {}): Promise<ReceiptParseResult> {
    const text = typeof input === 'string' ? input : input?.text || '';
    const lines = (text || '').split(/\r?\n/).map((l) => l.trim()).filter(Boolean);

    let vendor: string | null = null;
    if (lines.length > 0) {
      vendor = lines[0];
      if (
        lines.length > 1 &&
        !/^(Date|Total|Items?)/i.test(lines[1]) &&
        !/^\d+x\b/i.test(lines[1])
      ) {
        vendor = (lines[0] + ' ' + lines[1]).trim();
      }
    }

    const dateMatch = text.match(/Date:\s*([0-9\-]+)/i);
    const totalRegex = /total[^0-9\n\r]*([0-9][0-9\.,]*)/i;
    const totalMatch = text.match(totalRegex) as RegExpMatchArray | null;

    const items: Array<{ name: string; qty: number; price: number }> = [];
    const itemRe = /^(\d+)x\s+(.+?)\s*-\s*€?\$?\s*([0-9\.,]+)/i;
    for (const line of lines) {
      const match = line.match(itemRe);
      if (match) {
        const rawPrice = match[3].replace(/,/g, '.');
        items.push({
          name: match[2].trim(),
          qty: parseInt(match[1], 10),
          price: parseFloat(rawPrice),
        });
      }
    }

    const paymentMatch = text.match(/(credit|debit|cash|card)/i);
    const paymentMethod = paymentMatch ? paymentMatch[1].toUpperCase() : null;

    const taxIdMatch = text.match(/R\.?U\.?C\.?\s*[:\-]?\s*([0-9\-]+)/i);
    const documentTypeMatch = text.match(/\b(factura|boleta|recibo|ticket)\b/i);
    const documentNumberMatch =
      text.match(/(?:N[º°o]|num(?:ero)?\.?)\s*[:\-]?\s*([A-Za-z0-9\-]+)/i) ||
      text.match(/\b([A-Z]{1,4}-\d{4,})\b/);

    return {
      vendor,
      date: dateMatch ? dateMatch[1] : null,
      total: totalMatch ? parseFloat((totalMatch[1] || '').replace(/,/g, '.')) : null,
      currency: totalMatch
        ? text.includes('€')
          ? 'EUR'
            : text.includes('$')
              ? 'USD'
              : null
        : null,
      paymentMethod,
      taxId: taxIdMatch ? taxIdMatch[1].trim() : null,
      documentType: documentTypeMatch ? documentTypeMatch[1].toUpperCase() : null,
      documentNumber: documentNumberMatch ? documentNumberMatch[1].trim() : null,
      items,
      rawText: text,
      notes: null,
    };
  }
}

export default new ParserService();
