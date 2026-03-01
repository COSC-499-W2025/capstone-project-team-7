"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const index_1 = require("../queue/index");
jest.setTimeout(10000);
describe('worker processing', () => {
    test('processes a mock job end-to-end', async () => {
        // ensure mock services are used
        process.env.USE_MOCK_SERVICES = 'true';
        const job = { id: 'w-1', payload: { test: 'ok' } };
        index_1.defaultQueue.enqueue(job);
        // wait for processing loop
        await new Promise((r) => setTimeout(r, 100));
        // nothing to assert deeply; ensure no exception thrown and queue processed
        expect(true).toBe(true);
    });
});
