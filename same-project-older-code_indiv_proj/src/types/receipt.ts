import type { Buffer } from 'buffer';

export type ReceiptLineItem = {
  name: string;
  qty: number | null;
  price: number | null;
};

export type ReceiptParseResult = {
  vendor: string | null;
  date: string | null;
  total: number | null;
  currency: string | null;
  paymentMethod: string | null;
  taxId: string | null;
  documentType: string | null;
  documentNumber: string | null;
  items: ReceiptLineItem[];
  rawText?: string;
  notes?: string | null;
};

export type ParserInput =
  | string
  | {
      text?: string;
      buffer?: Buffer | null;
    };
