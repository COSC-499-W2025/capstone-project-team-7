"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
const parser_1 = __importDefault(require("../../src/services/parser"));
const ocr_1 = __importDefault(require("../../src/services/ocr"));
const useMocks = process.env.USE_MOCK_SERVICES !== 'false';
describe('integration: OCR -> parser', () => {
    it('runs OCR on a sample receipt and parses it (skips if using mocks)', async () => {
        if (useMocks) {
            console.warn('Skipping integration test: USE_MOCK_SERVICES is true');
            return;
        }
        const receiptDir = path_1.default.join(__dirname, '..', 'receipts');
        const files = fs_1.default.existsSync(receiptDir) ? fs_1.default.readdirSync(receiptDir).filter(f => /\.(png|jpe?g|pdf)$/i.test(f)) : [];
        if (files.length === 0) {
            console.warn('No receipts found in test/receipts; skipping');
            return;
        }
        const f = files[0];
        const buf = fs_1.default.readFileSync(path_1.default.join(receiptDir, f));
        const ocrRes = await ocr_1.default.recognize(buf);
        const text = typeof ocrRes === 'string' ? ocrRes : (ocrRes.text || JSON.stringify(ocrRes));
        const out = await parser_1.default.parse(text);
        expect(out.total).not.toBeNull();
        expect(out.date).not.toBeNull();
    });
});
