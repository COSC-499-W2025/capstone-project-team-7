"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.defaultQueue = exports.InMemoryQueue = void 0;
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
class InMemoryQueue {
    constructor() {
        this.queue = [];
        this.processing = false;
        this.closed = false;
    }
    enqueue(job) {
        if (this.closed) {
            throw new Error('Queue is closed');
        }
        this.queue.push(job);
        this.run().catch(() => { });
    }
    registerProcessor(fn) {
        this.processor = fn;
        this.run().catch(() => { });
    }
    async drain(timeoutMs = 10000) {
        this.closed = true;
        const start = Date.now();
        while (this.processing || this.queue.length > 0) {
            if (Date.now() - start > timeoutMs) {
                return Promise.reject(new Error('Drain timed out'));
            }
            // wait a bit
            // eslint-disable-next-line no-await-in-loop
            await new Promise((r) => setTimeout(r, 100));
        }
        return Promise.resolve();
    }
    async run() {
        if (this.processing)
            return;
        this.processing = true;
        while (this.queue.length > 0) {
            const job = this.queue.shift();
            try {
                if (this.processor)
                    await this.processor(job);
            }
            catch (err) {
                job.attempts = (job.attempts || 0) + 1;
                if (job.attempts < 3) {
                    this.queue.push(job);
                }
                else {
                    try {
                        const dataDir = path_1.default.resolve(process.cwd(), 'data');
                        fs_1.default.mkdirSync(dataDir, { recursive: true });
                        const file = path_1.default.join(dataDir, 'deadletter.ndjson');
                        const errorMessage = err instanceof Error ? err.message : String(err);
                        const entry = {
                            job,
                            error: errorMessage,
                            timestamp: new Date().toISOString(),
                        };
                        fs_1.default.appendFileSync(file, JSON.stringify(entry) + '\n');
                        console.error('Job moved to dead-letter', entry);
                    }
                    catch (writeErr) {
                        console.error('Failed to write dead-letter', writeErr);
                    }
                }
            }
        }
        this.processing = false;
    }
}
exports.InMemoryQueue = InMemoryQueue;
const GLOBAL_KEY = '__whatsapp_agent_default_queue__';
const existingQueue = globalThis[GLOBAL_KEY];
exports.defaultQueue = existingQueue || new InMemoryQueue();
if (!existingQueue) {
    globalThis[GLOBAL_KEY] = exports.defaultQueue;
}
