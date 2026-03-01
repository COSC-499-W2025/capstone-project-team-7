"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
const parser_1 = __importDefault(require("../src/services/parser"));
function load(filebase) {
    const ocr = JSON.parse(fs_1.default.readFileSync(path_1.default.join(__dirname, 'ocr_raw', filebase + '.json'), 'utf8'));
    const label = JSON.parse(fs_1.default.readFileSync(path_1.default.join(__dirname, 'labels', filebase + '.json'), 'utf8'));
    return { ocr, label };
}
describe('parser edge cases', () => {
    it('parses euro decimal commas and sets EUR', async () => {
        const { ocr, label } = load('sample-receipt-euro');
        const out = await parser_1.default.parse(ocr.text);
        console.log('DEBUG euro out=', out);
        expect(out.total).toBeCloseTo(label.total, 2);
        expect(out.currency).toBe('EUR');
    });
    it('joins multiline vendor names', async () => {
        const { ocr, label } = load('sample-receipt-multiline-vendor');
        const out = await parser_1.default.parse(ocr.text);
        console.log('DEBUG multi out=', out);
        expect(out.vendor).toBe(label.vendor);
    });
});
