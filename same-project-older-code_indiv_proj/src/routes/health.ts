import { Router, Request, Response } from 'express';
import { healthCheck } from '../services/index.js';

const router = Router();

router.get('/', (req: Request, res: Response) => {
	res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

router.get('/check', async (req: Request, res: Response) => {
	const status = await healthCheck();
	res.json(status);
});

export default router;
