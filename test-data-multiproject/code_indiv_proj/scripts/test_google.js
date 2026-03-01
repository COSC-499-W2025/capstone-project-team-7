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
var env_1 = require("../src/config/env");
var services_1 = __importDefault(require("../src/services"));
function run() {
    return __awaiter(this, void 0, void 0, function () {
        var _a, drive, sheets, e_1, res, e_2;
        return __generator(this, function (_b) {
            switch (_b.label) {
                case 0:
                    console.log('env.USE_MOCK_SERVICES=', env_1.env.USE_MOCK_SERVICES);
                    if (env_1.env.USE_MOCK_SERVICES) {
                        console.error('USE_MOCK_SERVICES is true — set USE_MOCK_SERVICES=false to test real Google APIs');
                        process.exit(2);
                    }
                    if (!process.env.SPREADSHEET_ID) {
                        console.error('Missing SPREADSHEET_ID env');
                        process.exit(2);
                    }
                    _a = services_1.default, drive = _a.drive, sheets = _a.sheets;
                    _b.label = 1;
                case 1:
                    _b.trys.push([1, 3, , 4]);
                    console.log('Attempting to append a test row to spreadsheet:', process.env.SPREADSHEET_ID);
                    return [4 /*yield*/, sheets.appendRow(process.env.SPREADSHEET_ID, [new Date().toISOString(), 'ankas-agent-test', 'ok'])];
                case 2:
                    _b.sent();
                    console.log('Appended test row to spreadsheet');
                    return [3 /*break*/, 4];
                case 3:
                    e_1 = _b.sent();
                    console.error('Failed to append row:', e_1 && e_1.message ? e_1.message : e_1);
                    process.exit(3);
                    return [3 /*break*/, 4];
                case 4:
                    _b.trys.push([4, 6, , 7]);
                    console.log('Attempting to upload a small test file to Drive');
                    return [4 /*yield*/, drive.upload(Buffer.from('ankas-agent test'), "ankas-agent-test-".concat(Date.now(), ".txt"))];
                case 5:
                    res = _b.sent();
                    console.log('Uploaded file to Drive:', res);
                    return [3 /*break*/, 7];
                case 6:
                    e_2 = _b.sent();
                    console.error('Failed to upload to Drive:', e_2 && e_2.message ? e_2.message : e_2);
                    process.exit(4);
                    return [3 /*break*/, 7];
                case 7:
                    console.log('Google Drive/Sheets test completed successfully');
                    return [2 /*return*/];
            }
        });
    });
}
run().catch(function (err) {
    console.error('Unexpected error', err);
    process.exit(10);
});
