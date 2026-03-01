export class OcrService {
  async recognize(buffer: Buffer): Promise<string> {
    // mock OCR: return a fake extracted text
    return 'TOTAL: $12.34\nDATE: 2025-01-01\nITEMS:\n- coffee $3.00\n- sandwich $9.34';
  }
}

export default new OcrService();
//Google Vision wrapper