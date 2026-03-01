import fs from 'fs';
import path from 'path';
import parser from '../src/services/parser';

function load(filebase: string){
  const ocr = JSON.parse(fs.readFileSync(path.join(__dirname,'ocr_raw', filebase + '.json'),'utf8'));
  const label = JSON.parse(fs.readFileSync(path.join(__dirname,'labels', filebase + '.json'),'utf8'));
  return {ocr, label};
}

describe('parser edge cases', ()=>{
  it('parses euro decimal commas and sets EUR', async ()=>{
    const {ocr,label} = load('sample-receipt-euro');
  const out = await parser.parse(ocr.text);
  console.log('DEBUG euro out=', out);
  expect(out.total).toBeCloseTo(label.total,2);
  expect(out.currency).toBe('EUR');
  });

  it('joins multiline vendor names', async ()=>{
    const {ocr,label} = load('sample-receipt-multiline-vendor');
  const out = await parser.parse(ocr.text);
  console.log('DEBUG multi out=', out);
  expect(out.vendor).toBe(label.vendor);
  });
});
