import fs from 'fs';
import path from 'path';
import parser from '../src/services/parser';

describe('parser.parse()', () => {
  it('parses a simple receipt OCR output into structured data', async () => {
    const ocrRaw = JSON.parse(fs.readFileSync(path.join(__dirname, 'ocr_raw', 'sample-receipt.json'), 'utf8'));
    const expected = JSON.parse(fs.readFileSync(path.join(__dirname, 'labels', 'sample-receipt.json'), 'utf8'));

  const out = await parser.parse(ocrRaw.text || JSON.stringify(ocrRaw));

    // Check core fields
    expect(out.vendor).toBe(expected.vendor);
    expect(out.date).toBe(expected.date);
    expect(out.total).toBeCloseTo(expected.total, 2);
    expect(out.items.length).toBe(expected.items.length);
    expect(out.items[0].name).toContain(expected.items[0].name);
  });
});
