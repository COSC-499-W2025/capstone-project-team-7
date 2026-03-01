"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g = Object.create((typeof Iterator === "function" ? Iterator : Object).prototype);
    return g.next = verb(0), g["throw"] = verb(1), g["return"] = verb(2), typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (g && (g = 0, op[0] && (_ = 0)), _) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.processReceipt = processReceipt;
var logger_1 = require("../services/logger");
var services_1 = require("../services");
var whatsapp_1 = __importDefault(require("../services/whatsapp"));
function processReceipt(job) {
    return __awaiter(this, void 0, void 0, function () {
        var filePath, buffer, uploaded, text, parsed, to, message;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    logger_1.logger.info('Processing job', { id: job.id });
                    if (job.payload && job.payload.fail) {
                        throw new Error('Simulated failure for testing dead-letter');
                    }
                    filePath = null;
                    _a.label = 1;
                case 1:
                    _a.trys.push([1, , 9, 10]);
                    if (!(job.payload && job.payload.mediaId)) return [3 /*break*/, 3];
                    return [4 /*yield*/, whatsapp_1.default.downloadMedia(job.payload.mediaId)];
                case 2:
                    // download media from whatsapp
                    filePath = _a.sent();
                    _a.label = 3;
                case 3:
                    buffer = filePath ? Buffer.from(require('fs').readFileSync(filePath)) : Buffer.from('fake-image-data');
                    return [4 /*yield*/, services_1.drive.upload(buffer, "".concat(job.id, ".png"))];
                case 4:
                    uploaded = _a.sent();
                    logger_1.logger.info('Uploaded to drive', uploaded);
                    return [4 /*yield*/, services_1.ocr.recognize(buffer)];
                case 5:
                    text = _a.sent();
                    logger_1.logger.info('OCR text', { text: text });
                    parsed = services_1.parser.parse(text);
                    logger_1.logger.info('Parsed data', parsed);
                    return [4 /*yield*/, services_1.sheets.appendRow('mock-spreadsheet', [job.id, parsed.date, parsed.total])];
                case 6:
                    _a.sent();
                    logger_1.logger.info('Appended to sheets');
                    if (!(job.payload && job.payload.from)) return [3 /*break*/, 8];
                    to = job.payload.from;
                    message = "Parsed receipt:\nVendor: ".concat(parsed.vendor || 'unknown', "\nDate: ").concat(parsed.date || 'unknown', "\nTotal: ").concat(parsed.total || 'unknown', " ").concat(parsed.currency || '');
                    return [4 /*yield*/, whatsapp_1.default.sendText(to, message)];
                case 7:
                    _a.sent();
                    _a.label = 8;
                case 8: return [3 /*break*/, 10];
                case 9:
                    // cleanup downloaded file
                    if (filePath) {
                        try {
                            require('fs').unlinkSync(filePath);
                        }
                        catch (e) { /* ignore */ }
                    }
                    return [7 /*endfinally*/];
                case 10: return [2 /*return*/];
            }
        });
    });
}
exports.default = processReceipt;
