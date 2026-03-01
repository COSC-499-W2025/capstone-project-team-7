import { defaultQueue } from '../queue/index.js';
import processReceipt from './workers/processReceipt.js';

defaultQueue.registerProcessor(async (job) => {
  await processReceipt(job);
});

export default null;
