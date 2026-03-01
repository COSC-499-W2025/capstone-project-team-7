import { InMemoryQueue } from '../queue/index';
const fs = require('fs');
const path = require('path');

// allow longer time for async loops
jest.setTimeout(20000);

function waitFor(predicate: () => boolean | Promise<boolean>, timeout = 5000, interval = 50) {
  const start = Date.now();
  return new Promise<void>(async (resolve, reject) => {
    while (true) {
      try {
        const ok = await Promise.resolve(predicate());
        if (ok) return resolve();
      } catch (e) {
        // ignore
      }
      if (Date.now() - start > timeout) return reject(new Error('timeout'));
      await new Promise((r) => setTimeout(r, interval));
    }
  });
}

describe('InMemoryQueue', () => {
  beforeEach(() => {
    // clear dead-letter file to avoid cross-test pollution
    const file = path.resolve(process.cwd(), 'data', 'deadletter.ndjson');
    try {
      if (fs.existsSync(file)) fs.unlinkSync(file);
    } catch (e) {
      /* ignore */
    }
  });

  test('enqueue and process a job', async () => {
    const q = new InMemoryQueue<any>();
    let processed: any[] = [];
    q.registerProcessor(async (job) => {
      processed.push(job);
    });

    q.enqueue({ id: '1', payload: { x: 1 } });

    await waitFor(() => processed.length === 1, 5000);

    expect(processed.length).toBe(1);
    expect(processed[0].id).toBe('1');
  });

  test('moves job to dead-letter after retries', async () => {
    const q = new InMemoryQueue<any>();
    q.registerProcessor(async (job) => {
      throw new Error('fail');
    });

    q.enqueue({ id: 'fail-1', payload: {} });

    const file = path.resolve(process.cwd(), 'data', 'deadletter.ndjson');

    await waitFor(() => fs.existsSync(file) && fs.readFileSync(file, 'utf8').includes('fail-1'), 10000);

    const content = fs.existsSync(file) ? fs.readFileSync(file, 'utf8') : '';
    expect(content.includes('fail-1')).toBe(true);
  });
});
