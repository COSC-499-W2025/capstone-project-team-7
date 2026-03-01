export class OcrServiceReal {
  async recognize(buffer: Buffer): Promise<string> {
    throw new Error('OcrServiceReal.recognize not implemented. Replace with Vision API client.');
  }
}

export default new OcrServiceReal();
