const fs = require('fs');
const path = require('path');
const ocr = require('../src/services/ocr').default;

async function run() {
  const inDir = path.resolve(__dirname, '..', 'test', 'receipts');
  const outDir = path.resolve(__dirname, '..', 'test', 'ocr_raw');
  if(!fs.existsSync(inDir)){
    console.error('No receipts folder at', inDir);
    process.exit(1);
  }
  if(!fs.existsSync(outDir)) fs.mkdirSync(outDir, {recursive:true});

  const files = fs.readdirSync(inDir).filter(f=>/\.(png|jpe?g|pdf)$/i.test(f));
  for(const f of files){
    const buf = fs.readFileSync(path.join(inDir,f));
    try{
      const res = await ocr.recognize(buf);
      fs.writeFileSync(path.join(outDir, f + '.json'), typeof res === 'string' ? JSON.stringify({text:res},null,2) : JSON.stringify(res,null,2));
      console.log('OCR',f,'-> ok');
    }catch(e){
      console.error('OCR failed',f,e.message);
    }
  }
}

run().catch(e=>{ console.error(e); process.exit(2); });
