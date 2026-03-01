#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

const OCR_DIR = path.join(__dirname, '..', 'test', 'ocr_raw');
const LABEL_DIR = path.join(__dirname, '..', 'test', 'labels');

// Prefer compiled JS parser if available
let parser;
try {
  parser = require('../src/services/parser');
} catch (e) {
  console.error('Failed to load parser module:', e.message);
  process.exit(1);
}

function safeLoadJSON(file) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (e) {
    return null;
  }
}

function compareField(a, b) {
  if (a == null || b == null) return false;
  return String(a).trim().toLowerCase() === String(b).trim().toLowerCase();
}

function computeMetrics() {
  const ocrFiles = fs.existsSync(OCR_DIR) ? fs.readdirSync(OCR_DIR).filter(f => f.endsWith('.json')) : [];
  if (ocrFiles.length === 0) {
    console.log('No OCR outputs found in', OCR_DIR);
    return;
  }

  let totals = { count: 0, vendor: 0, date: 0, total: 0, currency: 0, items_count: 0 };

  ocrFiles.forEach(file => {
    const base = path.basename(file);
    const labelPath = path.join(LABEL_DIR, base);
    if (!fs.existsSync(labelPath)) {
      console.warn('No label for', base);
      return;
    }
    const ocr = safeLoadJSON(path.join(OCR_DIR, file));
    const label = safeLoadJSON(labelPath);
    if (!ocr || !label) return;

    // parser expects either raw OCR text or an object shape; handle common fixtures
    const input = ocr.text || ocr.lines || JSON.stringify(ocr);
    let out;
    try {
      out = parser.parse(input);
    } catch (e) {
      try {
        out = parser.default.parse(input);
      } catch (e2) {
        console.error('Parser failed for', base, e.message);
        return;
      }
    }

    totals.count++;
    if (compareField(out.vendor, label.vendor)) totals.vendor++;
    if (compareField(out.date, label.date)) totals.date++;
    // total numeric compare
    const outTotal = parseFloat(String(out.total || '').replace(/[,$\s]/g, '').replace(',', '.'));
    const labelTotal = parseFloat(String(label.total || '').replace(/[,$\s]/g, '').replace(',', '.'));
    if (!isNaN(outTotal) && !isNaN(labelTotal) && Math.abs(outTotal - labelTotal) < 0.01) totals.total++;
    if (compareField(out.currency, label.currency)) totals.currency++;
    if (Array.isArray(out.items) && Array.isArray(label.items) && out.items.length === label.items.length) totals.items_count++;
  });

  console.log('Parsed files:', totals.count);
  if (totals.count === 0) return;
  console.log('Vendor accuracy:', (totals.vendor / totals.count * 100).toFixed(1) + '%');
  console.log('Date accuracy:  ', (totals.date / totals.count * 100).toFixed(1) + '%');
  console.log('Total accuracy: ', (totals.total / totals.count * 100).toFixed(1) + '%');
  console.log('Currency acc:   ', (totals.currency / totals.count * 100).toFixed(1) + '%');
  console.log('Items count acc:', (totals.items_count / totals.count * 100).toFixed(1) + '%');
}

computeMetrics();
