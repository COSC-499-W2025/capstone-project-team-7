"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
var express_1 = __importDefault(require("express"));
var whatsappWebhook_1 = __importDefault(require("./routes/whatsappWebhook"));
var health_1 = __importDefault(require("./routes/health"));
var deadletter_1 = __importDefault(require("./routes/deadletter"));
var oauth_1 = __importDefault(require("./routes/oauth"));
var admin_1 = __importDefault(require("./routes/admin"));
var errorHandler_1 = require("./middlewares/errorHandler");
var validateSignature_1 = require("./middlewares/validateSignature");
var app = (0, express_1.default)();
// JSON body parser
app.use(express_1.default.json());
// health route
app.use('/health', health_1.default);
// dead-letter inspection
app.use('/deadletter', deadletter_1.default);
// OAuth helper routes (for interactive user consent)
app.use('/', oauth_1.default);
// admin routes
app.use('/admin', admin_1.default);
// webhook - apply a simple signature check middleware before the webhook
app.use('/webhook', validateSignature_1.validateSignature, whatsappWebhook_1.default);
// simple test route
app.get('/test', function (req, res) {
    res.send('Test route works!');
});
// error handler (must be after all routes)
app.use(errorHandler_1.errorHandler);
exports.default = app;
