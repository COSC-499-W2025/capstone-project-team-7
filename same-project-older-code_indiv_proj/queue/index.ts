export type Job<T = any> = {
	id: string;
	payload: T;
	attempts?: number;
};

import fs from 'fs';
import path from 'path';

type Processor<T = any> = (job: Job<T>) => Promise<void>;

export class InMemoryQueue<T = any> {
	private queue: Job<T>[] = [];
	private processing = false;
	private processor?: Processor<T>;
	private closed = false;

	enqueue(job: Job<T>) {
		if (this.closed) {
			throw new Error('Queue is closed');
		}
		this.queue.push(job);
		this.run().catch(() => {});
	}

	registerProcessor(fn: Processor<T>) {
		this.processor = fn;
		this.run().catch(() => {});
	}

	async drain(timeoutMs = 10000): Promise<void> {
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

	private async run() {
		if (this.processing) return;
		this.processing = true;
		while (this.queue.length > 0) {
			const job = this.queue.shift()!;
			try {
				if (this.processor) await this.processor(job);
			} catch (err) {
				job.attempts = (job.attempts || 0) + 1;
				if (job.attempts < 3) {
					this.queue.push(job);
				} else {
					try {
						const dataDir = path.resolve(process.cwd(), 'data');
						fs.mkdirSync(dataDir, { recursive: true });
						const file = path.join(dataDir, 'deadletter.ndjson');
						const errorMessage = err instanceof Error ? err.message : String(err);
						const entry = {
							job,
							error: errorMessage,
							timestamp: new Date().toISOString(),
						};
						fs.appendFileSync(file, JSON.stringify(entry) + '\n');
						console.error('Job moved to dead-letter', entry);
					} catch (writeErr) {
						console.error('Failed to write dead-letter', writeErr);
					}
				}
			}
		}
		this.processing = false;
	}
}

const GLOBAL_KEY = '__whatsapp_agent_default_queue__';

const existingQueue = (globalThis as any)[GLOBAL_KEY] as InMemoryQueue | undefined;
export const defaultQueue = existingQueue || new InMemoryQueue();
if (!existingQueue) {
	(globalThis as any)[GLOBAL_KEY] = defaultQueue;
}
