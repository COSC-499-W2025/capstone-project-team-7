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
exports.DriveServiceReal = void 0;
var googleapis_1 = require("googleapis");
var stream_1 = require("stream");
var oauth_1 = __importDefault(require("./oauth"));
function getCredentials() {
    // Accept multiple env sources for convenience:
    // - GOOGLE_SERVICE_ACCOUNT_JSON: raw JSON
    // - GOOGLE_SERVICE_ACCOUNT: raw JSON (legacy/name variant)
    // - GOOGLE_SERVICE_ACCOUNT_B64: base64-encoded JSON
    var rawJson = process.env.GOOGLE_SERVICE_ACCOUNT_JSON || process.env.GOOGLE_SERVICE_ACCOUNT;
    var b64 = process.env.GOOGLE_SERVICE_ACCOUNT_B64;
    var raw = rawJson;
    if (!raw && b64) {
        try {
            raw = Buffer.from(b64, 'base64').toString('utf8');
        }
        catch (e) {
            return null;
        }
    }
    if (!raw)
        return null;
    try {
        return JSON.parse(raw);
    }
    catch (e) {
        return null;
    }
}
var DriveServiceReal = /** @class */ (function () {
    function DriveServiceReal() {
    }
    DriveServiceReal.prototype.authClient = function () {
        return __awaiter(this, void 0, void 0, function () {
            var credentials, auth, client, oauthClient;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        credentials = getCredentials();
                        if (!credentials) return [3 /*break*/, 2];
                        auth = new googleapis_1.google.auth.GoogleAuth({
                            credentials: credentials,
                            scopes: ['https://www.googleapis.com/auth/drive.file'],
                        });
                        return [4 /*yield*/, auth.getClient()];
                    case 1:
                        client = _a.sent();
                        return [2 /*return*/, client];
                    case 2:
                        oauthClient = oauth_1.default.getAuthClientFromOauth();
                        if (oauthClient)
                            return [2 /*return*/, oauthClient];
                        throw new Error('Missing GOOGLE_SERVICE_ACCOUNT or GOOGLE_SERVICE_ACCOUNT_JSON env, and no OAuth tokens.');
                }
            });
        });
    };
    DriveServiceReal.prototype.upload = function (buffer, filename) {
        return __awaiter(this, void 0, void 0, function () {
            var client, drive, stream, requestBody, folderId, res, data;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0: return [4 /*yield*/, this.authClient()];
                    case 1:
                        client = _a.sent();
                        drive = googleapis_1.google.drive({ version: 'v3', auth: client });
                        stream = new stream_1.PassThrough();
                        stream.end(buffer);
                        requestBody = { name: filename };
                        folderId = process.env.DRIVE_UPLOAD_FOLDER_ID;
                        if (folderId)
                            requestBody.parents = [folderId];
                        return [4 /*yield*/, drive.files.create({
                                requestBody: requestBody,
                                media: {
                                    mimeType: 'application/octet-stream',
                                    body: stream,
                                },
                                fields: 'id, webViewLink',
                                // allow uploads into shared drives if the target folder is on a shared drive
                                supportsAllDrives: true,
                            })];
                    case 2:
                        res = _a.sent();
                        data = res.data;
                        return [2 /*return*/, { id: data.id, url: data.webViewLink || '' }];
                }
            });
        });
    };
    return DriveServiceReal;
}());
exports.DriveServiceReal = DriveServiceReal;
exports.default = new DriveServiceReal();
