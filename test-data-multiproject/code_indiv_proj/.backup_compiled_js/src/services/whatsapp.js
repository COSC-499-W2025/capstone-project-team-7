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
exports.getMediaUrl = getMediaUrl;
exports.downloadMedia = downloadMedia;
exports.sendText = sendText;
var node_fetch_1 = __importDefault(require("node-fetch"));
var fs_1 = __importDefault(require("fs"));
var path_1 = __importDefault(require("path"));
var logger_1 = require("./logger");
var GRAPH_BASE = 'https://graph.facebook.com/v17.0';
var PHONE_NUMBER_ID = process.env.WHATSAPP_PHONE_NUMBER_ID;
var ACCESS_TOKEN = process.env.WHATSAPP_ACCESS_TOKEN;
function authHeader() {
    return { Authorization: "Bearer ".concat(ACCESS_TOKEN) };
}
function getMediaUrl(mediaId) {
    return __awaiter(this, void 0, void 0, function () {
        var url, res, j;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    url = "".concat(GRAPH_BASE, "/").concat(mediaId);
                    return [4 /*yield*/, (0, node_fetch_1.default)(url + "?access_token=".concat(ACCESS_TOKEN))];
                case 1:
                    res = _a.sent();
                    if (!res.ok)
                        throw new Error("getMediaUrl failed ".concat(res.status));
                    return [4 /*yield*/, res.json()];
                case 2:
                    j = _a.sent();
                    return [2 /*return*/, j.url];
            }
        });
    });
}
function downloadMedia(mediaId) {
    return __awaiter(this, void 0, void 0, function () {
        var url, res, buf, _a, _b, tmpDir, filePath;
        return __generator(this, function (_c) {
            switch (_c.label) {
                case 0: return [4 /*yield*/, getMediaUrl(mediaId)];
                case 1:
                    url = _c.sent();
                    return [4 /*yield*/, (0, node_fetch_1.default)(url, { headers: authHeader() })];
                case 2:
                    res = _c.sent();
                    if (!res.ok)
                        throw new Error("downloadMedia failed ".concat(res.status));
                    _b = (_a = Buffer).from;
                    return [4 /*yield*/, res.arrayBuffer()];
                case 3:
                    buf = _b.apply(_a, [_c.sent()]);
                    tmpDir = path_1.default.join(process.cwd(), 'tmp');
                    if (!fs_1.default.existsSync(tmpDir))
                        fs_1.default.mkdirSync(tmpDir);
                    filePath = path_1.default.join(tmpDir, "".concat(mediaId, ".bin"));
                    fs_1.default.writeFileSync(filePath, buf);
                    logger_1.logger.info('Downloaded media', { mediaId: mediaId, filePath: filePath });
                    return [2 /*return*/, filePath];
            }
        });
    });
}
function sendText(to, text) {
    return __awaiter(this, void 0, void 0, function () {
        var url, body, res, t, j;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    if (!PHONE_NUMBER_ID)
                        throw new Error('WHATSAPP_PHONE_NUMBER_ID not set');
                    url = "".concat(GRAPH_BASE, "/").concat(PHONE_NUMBER_ID, "/messages");
                    body = {
                        messaging_product: 'whatsapp',
                        to: to,
                        type: 'text',
                        text: { body: text }
                    };
                    return [4 /*yield*/, (0, node_fetch_1.default)(url, {
                            method: 'POST',
                            headers: Object.assign({ 'Content-Type': 'application/json' }, authHeader()),
                            body: JSON.stringify(body)
                        })];
                case 1:
                    res = _a.sent();
                    if (!!res.ok) return [3 /*break*/, 3];
                    return [4 /*yield*/, res.text()];
                case 2:
                    t = _a.sent();
                    logger_1.logger.error('sendText failed', { status: res.status, body: t });
                    throw new Error("sendText failed ".concat(res.status));
                case 3: return [4 /*yield*/, res.json()];
                case 4:
                    j = _a.sent();
                    logger_1.logger.info('Sent whatsapp message', { to: to, id: j && j.messages && j.messages[0] && j.messages[0].id });
                    return [2 /*return*/, j];
            }
        });
    });
}
exports.default = { getMediaUrl: getMediaUrl, downloadMedia: downloadMedia, sendText: sendText };
//graph calls
