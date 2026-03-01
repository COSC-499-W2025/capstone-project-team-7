import fs from 'fs';
import path from 'path';
import parser from '../../src/services/parser';
import ocr from '../../src/services/ocr';

const useMocks = process.env.USE_MOCK_SERVICES !== 'false';

describe('integration: OCR -> parser', () => {
  it('runs OCR on a sample receipt and parses it (skips if using mocks)', async () => {
    if(useMocks){
      console.warn('Skipping integration test: USE_MOCK_SERVICES is true');
      return;
    }

    const receiptDir = path.join(__dirname, '..', 'receipts');
    const files = fs.existsSync(receiptDir) ? fs.readdirSync(receiptDir).filter(f=>/\.(png|jpe?g|pdf)$/i.test(f)) : [];
    if(files.length===0){
      console.warn('No receipts found in test/receipts; skipping');
      return;
    }

    const f = files[0];
    const buf = fs.readFileSync(path.join(receiptDir,f));
  const ocrRes:any = await ocr.recognize(buf);
  const text = typeof ocrRes === 'string' ? ocrRes : (ocrRes.text || JSON.stringify(ocrRes));
    const out = await parser.parse(text);

    expect(out.total).not.toBeNull();
    expect(out.date).not.toBeNull();
  });
});
