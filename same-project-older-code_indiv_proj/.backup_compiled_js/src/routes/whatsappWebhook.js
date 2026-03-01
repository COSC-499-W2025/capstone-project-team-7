"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
var express_1 = require("express");
var logger_1 = require("../services/logger");
var index_1 = require("../../queue/index");
var uuid_1 = require("uuid");
var router = (0, express_1.Router)();
// Verification endpoint used by WhatsApp to verify webhook
router.get('/', function (req, res) {
    var verifyToken = process.env.WHATSAPP_VERIFY_TOKEN || 'your-verify-token';
    var mode = req.query['hub.mode'];
    var token = req.query['hub.verify_token'];
    var challenge = req.query['hub.challenge'];
    if (mode && token && mode === 'subscribe' && token === verifyToken) {
        logger_1.logger.info('Webhook verified');
        res.status(200).send(challenge);
    }
    else {
        logger_1.logger.warn('Webhook verification failed', { mode: mode, token: token });
        res.sendStatus(403);
    }
});
// Receive incoming messages
router.post('/', function (req, res) {
    logger_1.logger.info('Webhook POST received', { body: req.body });
    try {
        var entry = req.body.entry && req.body.entry[0];
        var changes = entry && entry.changes && entry.changes[0];
        var value = changes && changes.value;
        var messages = value && value.messages;
        if (!messages || messages.length === 0) {
            res.status(200).send('no messages');
            return;
        }
        var message = messages[0];
        var from = message.from; // phone number
        var messageId = message.id;
        // if it's an image message
        if (message.type === 'image' && message.image && message.image.id) {
            var mediaId = message.image.id;
            var job = { id: (0, uuid_1.v4)(), payload: { type: 'processReceipt', from: from, messageId: messageId, mediaId: mediaId } };
            index_1.defaultQueue.enqueue(job);
            // ACK immediately
            res.status(202).json({ ack: true, jobId: job.id });
            return;
        }
        // simple text commands
        if (message.type === 'text' && message.text && message.text.body) {
            var txt = message.text.body.trim().toLowerCase();
            if (txt === 'help') {
                res.status(200).json({ reply: 'Send a photo of a receipt and I will parse it for you.' });
                return;
            }
        }
        res.status(200).send('ok');
    }
    catch (e) {
        logger_1.logger.error('Webhook handling error', e);
        res.sendStatus(500);
    }
});
exports.default = router;
