"use strict";
// Simple console logger for local development
Object.defineProperty(exports, "__esModule", { value: true });
exports.logger = exports.LoggerService = void 0;
var LoggerService = /** @class */ (function () {
    function LoggerService() {
    }
    LoggerService.prototype.info = function (message, meta) {
        console.info('[INFO]', message, meta || '');
    };
    LoggerService.prototype.warn = function (message, meta) {
        console.warn('[WARN]', message, meta || '');
    };
    LoggerService.prototype.error = function (message, meta) {
        console.error('[ERROR]', message, meta || '');
    };
    return LoggerService;
}());
exports.LoggerService = LoggerService;
exports.logger = new LoggerService();
