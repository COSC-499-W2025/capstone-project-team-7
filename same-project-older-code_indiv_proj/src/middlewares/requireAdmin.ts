import { Request, Response, NextFunction } from 'express';
import { env } from '../config/runtimeEnv';

export function requireAdmin(req: Request, res: Response, next: NextFunction) {
  const auth = req.headers.authorization;
  if (!auth || !auth.startsWith('Bearer ')) return res.sendStatus(401);
  const token = auth.slice('Bearer '.length);
  if (!env.ADMIN_TOKEN || token !== env.ADMIN_TOKEN) return res.sendStatus(403);
  next();
}

export default requireAdmin;
