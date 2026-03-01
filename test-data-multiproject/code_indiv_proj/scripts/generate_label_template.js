#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

const RECEIPTS_DIR = path.join(__dirname, '..', 'test', 'receipts');
const LABELS_DIR = path.join(__dirname, '..', 'test', 'labels');

if (!fs.existsSync(LABELS_DIR)) fs.mkdirSync(LABELS_DIR, { recursive: true });

const files = fs.existsSync(RECEIPTS_DIR) ? fs.readdirSync(RECEIPTS_DIR).filter(f => /\.(jpg|jpeg|png)$/i.test(f)) : [];
if (files.length === 0) {
  console.log('No receipt images found in', RECEIPTS_DIR);
  process.exit(0);
}

files.forEach(file => {
  const base = path.basename(file);
  const name = base.replace(/\.[^.]+$/, '') + '.json';
  const outPath = path.join(LABELS_DIR, name);
  if (fs.existsSync(outPath)) {
    console.log('Label exists, skipping', name);
    return;
  }
  const template = {
    vendor: '',
    date: '',
    total: '',
    currency: '',
    items: []
  };
  fs.writeFileSync(outPath, JSON.stringify(template, null, 2));
  console.log('Wrote label template', outPath);
});
