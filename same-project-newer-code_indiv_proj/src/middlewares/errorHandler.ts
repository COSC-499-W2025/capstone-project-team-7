import { Request, Response, NextFunction } from 'express';

export function errorHandler(err: any, req: Request, res: Response, next: NextFunction) {
	const status = err && err.status ? err.status : 500;
	const message = err && err.message ? err.message : 'Internal Server Error';
	res.status(status).json({ error: message });
}