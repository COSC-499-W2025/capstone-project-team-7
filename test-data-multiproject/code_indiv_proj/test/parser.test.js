"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
const parser_1 = __importDefault(require("../src/services/parser"));
describe('parser.parse()', () => {
    it('parses a simple receipt OCR output into structured data', async () => {
        const ocrRaw = JSON.parse(fs_1.default.readFileSync(path_1.default.join(__dirname, 'ocr_raw', 'sample-receipt.json'), 'utf8'));
        const expected = JSON.parse(fs_1.default.readFileSync(path_1.default.join(__dirname, 'labels', 'sample-receipt.json'), 'utf8'));
        const out = await parser_1.default.parse(ocrRaw.text || JSON.stringify(ocrRaw));
        // Check core fields
        expect(out.vendor).toBe(expected.vendor);
        expect(out.date).toBe(expected.date);
        expect(out.total).toBeCloseTo(expected.total, 2);
        expect(out.items.length).toBe(expected.items.length);
        expect(out.items[0].name).toContain(expected.items[0].name);
    });
});
