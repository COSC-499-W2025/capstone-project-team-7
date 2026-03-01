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
exports.getOauth2Client = getOauth2Client;
exports.getAuthUrl = getAuthUrl;
exports.exchangeCode = exchangeCode;
exports.hasToken = hasToken;
exports.getAuthClientFromOauth = getAuthClientFromOauth;
var googleapis_1 = require("googleapis");
var fs_1 = __importDefault(require("fs"));
var path_1 = __importDefault(require("path"));
var TOKEN_PATH = path_1.default.resolve(process.cwd(), 'data', 'google_oauth_tokens.json');
function ensureDataDir() {
    var dir = path_1.default.dirname(TOKEN_PATH);
    if (!fs_1.default.existsSync(dir))
        fs_1.default.mkdirSync(dir, { recursive: true });
}
function getClientConfig() {
    var clientId = process.env.GOOGLE_OAUTH_CLIENT_ID;
    var clientSecret = process.env.GOOGLE_OAUTH_CLIENT_SECRET;
    var redirectUri = process.env.GOOGLE_OAUTH_REDIRECT_URI;
    if (!clientId || !clientSecret || !redirectUri)
        return null;
    return { clientId: clientId, clientSecret: clientSecret, redirectUri: redirectUri };
}
function getOauth2Client() {
    var cfg = getClientConfig();
    if (!cfg)
        return null;
    var clientId = cfg.clientId, clientSecret = cfg.clientSecret, redirectUri = cfg.redirectUri;
    var oAuth2Client = new googleapis_1.google.auth.OAuth2(clientId, clientSecret, redirectUri);
    // load tokens if present
    try {
        if (fs_1.default.existsSync(TOKEN_PATH)) {
            var raw = fs_1.default.readFileSync(TOKEN_PATH, 'utf8');
            var tokens = JSON.parse(raw);
            oAuth2Client.setCredentials(tokens);
        }
    }
    catch (e) {
        // ignore
    }
    return oAuth2Client;
}
function getAuthUrl() {
    var cfg = getClientConfig();
    if (!cfg)
        throw new Error('Missing GOOGLE_OAUTH_CLIENT_ID/SECRET/REDIRECT_URI');
    var client = getOauth2Client();
    var scopes = [
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/spreadsheets',
    ];
    return client.generateAuthUrl({
        access_type: 'offline',
        scope: scopes,
        prompt: 'consent',
    });
}
function exchangeCode(code) {
    return __awaiter(this, void 0, void 0, function () {
        var client, r, tokens;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    client = getOauth2Client();
                    if (!client)
                        throw new Error('OAuth client not configured');
                    return [4 /*yield*/, client.getToken(code)];
                case 1:
                    r = _a.sent();
                    tokens = r.tokens;
                    ensureDataDir();
                    fs_1.default.writeFileSync(TOKEN_PATH, JSON.stringify(tokens, null, 2));
                    client.setCredentials(tokens);
                    return [2 /*return*/, tokens];
            }
        });
    });
}
function hasToken() {
    try {
        if (fs_1.default.existsSync(TOKEN_PATH)) {
            var raw = fs_1.default.readFileSync(TOKEN_PATH, 'utf8');
            var t = JSON.parse(raw);
            return !!(t && (t.refresh_token || t.access_token));
        }
    }
    catch (e) {
        return false;
    }
    return false;
}
function getAuthClientFromOauth() {
    var client = getOauth2Client();
    if (!client)
        return null;
    // If client has credentials set (including refresh_token), return it
    var creds = client.credentials;
    if (creds && (creds.refresh_token || creds.access_token))
        return client;
    return null;
}
exports.default = {
    getOauth2Client: getOauth2Client,
    getAuthUrl: getAuthUrl,
    exchangeCode: exchangeCode,
    hasToken: hasToken,
    getAuthClientFromOauth: getAuthClientFromOauth,
};
