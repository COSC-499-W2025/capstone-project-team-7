import { Router, Request, Response } from 'express';
import fs from 'fs';
import path from 'path';
import { defaultQueue } from '../../queue/index.js';
import { requireAdmin } from '../middlewares/requireAdmin.js';

const router = Router();

function deadletterFile() {
  return path.resolve(process.cwd(), 'data', 'deadletter.ndjson');
}

function readEntries() {
  const file = deadletterFile();
  if (!fs.existsSync(file)) return [];
  const raw = fs.readFileSync(file, 'utf8');
  const trimmed = raw.trim();
  if (!trimmed) return [];
  const lines = trimmed.split('\n').filter(Boolean);
  const entries: any[] = [];
  for (const l of lines) {
    try {
      entries.push(JSON.parse(l));
    } catch (e) {
      // ignore malformed lines but log server-side for debugging
      // eslint-disable-next-line no-console
      console.error('failed to parse dead-letter line', e);
    }
  }
  return entries;
}

router.get('/', requireAdmin, (req: Request, res: Response) => {
  try {
    const entries = readEntries().reverse();
    res.json(entries);
  } catch (err) {
    res.status(500).json({ error: 'failed to read dead-letter' });
  }
});

router.post('/requeue', requireAdmin, (req: Request, res: Response) => {
  try {
    const { jobId } = req.body;
    if (!jobId) return res.status(400).json({ error: 'missing jobId' });
    const entries = readEntries();
    const idx = entries.findIndex((e: any) => e.job && e.job.id === jobId);
    if (idx === -1) return res.status(404).json({ error: 'job not found' });
    const entry = entries.splice(idx, 1)[0];
    // write back remaining
    const file = deadletterFile();
    fs.writeFileSync(file, entries.map((e: any) => JSON.stringify(e)).join('\n') + (entries.length ? '\n' : ''));
    // reset attempts and enqueue
    const job = entry.job;
    job.attempts = 0;
    defaultQueue.enqueue(job);
    res.json({ requeued: true, jobId });
  } catch (err) {
    res.status(500).json({ error: 'failed to requeue' });
  }
});

router.delete('/:jobId', requireAdmin, (req: Request, res: Response) => {
  try {
    const jobId = req.params.jobId;
    const entries = readEntries();
    const remaining = entries.filter((e: any) => !(e.job && e.job.id === jobId));
    const file = deadletterFile();
    fs.writeFileSync(file, remaining.map((e: any) => JSON.stringify(e)).join('\n') + (remaining.length ? '\n' : ''));
    res.json({ deleted: true, jobId });
  } catch (err) {
    res.status(500).json({ error: 'failed to delete dead-letter entry' });
  }
});

export default router;
