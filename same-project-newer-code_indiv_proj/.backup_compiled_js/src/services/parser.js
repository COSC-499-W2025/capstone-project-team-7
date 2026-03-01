"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ParserService = void 0;
var ParserService = /** @class */ (function () {
    function ParserService() {
    }
    ParserService.prototype.parse = function (text) {
        // very naive parsing for mock / tests
        var lines = (text || '').split(/\r?\n/).map(function (l) { return l.trim(); }).filter(Boolean);
        // vendor detection: usually first line or first two lines (if second line isn't a Date/Item/Total)
        var vendor = null;
        if (lines.length > 0) {
            vendor = lines[0];
            if (lines.length > 1 && !/^(Date|Total|Items?)/i.test(lines[1]) && !/^\d+x\b/i.test(lines[1])) {
                vendor = (lines[0] + ' ' + lines[1]).trim();
            }
        }
        var dateMatch = text.match(/Date:\s*([0-9\-]+)/i);
        // extract total by scanning the whole text for a 'total' line and number; accept comma decimals
        var totalMatch = null;
        var totalRegex = /total[^0-9\n\r]*([0-9][0-9\.,]*)/i;
        var totalFullMatch = text.match(totalRegex);
        if (totalFullMatch)
            totalMatch = totalFullMatch;
        var items = [];
        var itemRe = /^(\d+)x\s+(.+?)\s*-\s*€?\$?\s*([0-9\.,]+)/i;
        for (var _i = 0, lines_1 = lines; _i < lines_1.length; _i++) {
            var line = lines_1[_i];
            var m = line.match(itemRe);
            if (m) {
                var rawPrice = m[3].replace(/,/g, '.');
                items.push({ name: m[2].trim(), qty: parseInt(m[1], 10), price: parseFloat(rawPrice) });
            }
        }
        return {
            vendor: vendor,
            date: dateMatch ? dateMatch[1] : null,
            total: totalMatch ? parseFloat((totalMatch[1] || '').replace(/,/g, '.')) : null,
            currency: totalMatch ? (text.includes('€') ? 'EUR' : (text.includes('$') ? 'USD' : null)) : null,
            items: items,
        };
    };
    return ParserService;
}());
exports.ParserService = ParserService;
exports.default = new ParserService();
//extract 
