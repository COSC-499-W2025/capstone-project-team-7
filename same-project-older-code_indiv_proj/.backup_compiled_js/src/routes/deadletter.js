"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
var express_1 = require("express");
var fs_1 = __importDefault(require("fs"));
var path_1 = __importDefault(require("path"));
var index_1 = require("../../queue/index");
var requireAdmin_1 = require("../middlewares/requireAdmin");
var router = (0, express_1.Router)();
function deadletterFile() {
    return path_1.default.resolve(process.cwd(), 'data', 'deadletter.ndjson');
}
function readEntries() {
    var file = deadletterFile();
    if (!fs_1.default.existsSync(file))
        return [];
    var raw = fs_1.default.readFileSync(file, 'utf8');
    var trimmed = raw.trim();
    if (!trimmed)
        return [];
    var lines = trimmed.split('\n').filter(Boolean);
    var entries = [];
    for (var _i = 0, lines_1 = lines; _i < lines_1.length; _i++) {
        var l = lines_1[_i];
        try {
            entries.push(JSON.parse(l));
        }
        catch (e) {
            // ignore malformed lines but log server-side for debugging
            // eslint-disable-next-line no-console
            console.error('failed to parse dead-letter line', e);
        }
    }
    return entries;
}
router.get('/', requireAdmin_1.requireAdmin, function (req, res) {
    try {
        var entries = readEntries().reverse();
        res.json(entries);
    }
    catch (err) {
        res.status(500).json({ error: 'failed to read dead-letter' });
    }
});
router.post('/requeue', requireAdmin_1.requireAdmin, function (req, res) {
    try {
        var jobId_1 = req.body.jobId;
        if (!jobId_1)
            return res.status(400).json({ error: 'missing jobId' });
        var entries = readEntries();
        var idx = entries.findIndex(function (e) { return e.job && e.job.id === jobId_1; });
        if (idx === -1)
            return res.status(404).json({ error: 'job not found' });
        var entry = entries.splice(idx, 1)[0];
        // write back remaining
        var file = deadletterFile();
        fs_1.default.writeFileSync(file, entries.map(function (e) { return JSON.stringify(e); }).join('\n') + (entries.length ? '\n' : ''));
        // reset attempts and enqueue
        var job = entry.job;
        job.attempts = 0;
        index_1.defaultQueue.enqueue(job);
        res.json({ requeued: true, jobId: jobId_1 });
    }
    catch (err) {
        res.status(500).json({ error: 'failed to requeue' });
    }
});
router.delete('/:jobId', requireAdmin_1.requireAdmin, function (req, res) {
    try {
        var jobId_2 = req.params.jobId;
        var entries = readEntries();
        var remaining = entries.filter(function (e) { return !(e.job && e.job.id === jobId_2); });
        var file = deadletterFile();
        fs_1.default.writeFileSync(file, remaining.map(function (e) { return JSON.stringify(e); }).join('\n') + (remaining.length ? '\n' : ''));
        res.json({ deleted: true, jobId: jobId_2 });
    }
    catch (err) {
        res.status(500).json({ error: 'failed to delete dead-letter entry' });
    }
});
exports.default = router;
