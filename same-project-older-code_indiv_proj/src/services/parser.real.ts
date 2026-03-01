import type { Buffer } from 'buffer';
import OpenAI from 'openai';
import { jsonrepair } from 'jsonrepair';
import { env } from '../config/runtimeEnv';
import type { ParserInput, ReceiptLineItem, ReceiptParseResult } from '../types/receipt';

function coerceNumber(value: any): number | null {
  if (value === null || value === undefined || value === '') return null;
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
}

function ensureClient() {
  if (!env.OPENAI_API_KEY) {
    throw new Error('OPENAI_API_KEY not configured');
  }
  return new OpenAI({ apiKey: env.OPENAI_API_KEY });
}

function inferPaymentMethod(sourceText: string | undefined): string | null {
  if (!sourceText) return null;
  const text = sourceText.toLowerCase();
  if (text.includes('credit')) return 'CREDIT';
  if (text.includes('debit')) return 'DEBIT';
  if (text.includes('cash')) return 'CASH';
  if (text.includes('visa')) return 'VISA';
  if (text.includes('mastercard')) return 'MASTERCARD';
  if (text.includes('discover')) return 'DISCOVER';
  if (text.includes('amex') || text.includes('american express')) return 'AMEX';
  if (text.includes('card')) return 'CARD';
  return null;
}

function normalizeItemName(raw: any): string {
  const fallback = 'Artículo desconocido';
  if (typeof raw !== 'string') return fallback;
  const trimmed = raw.trim();
  if (!trimmed) return fallback;
  const normalized = trimmed.toLowerCase();
  if (normalized.includes('no item') || normalized.includes('no items')) {
    return 'Sin detalles de artículos.';
  }
  return trimmed;
}

export class ParserServiceReal {
  private client: OpenAI | null = null;

  private getClient() {
    if (!this.client) {
      this.client = ensureClient();
    }
    return this.client;
  }

  async parse(input: ParserInput, opts: { buffer?: Buffer | null } = {}): Promise<ReceiptParseResult> {
    const buffer = opts.buffer || (typeof input === 'object' ? input?.buffer : undefined);
    const fallbackText = typeof input === 'string' ? input : input?.text || '';

    if (!buffer || buffer.length === 0) {
      throw new Error('Parser requires the original receipt image buffer');
    }

    const client = this.getClient();
    const base64 = buffer.toString('base64');

    const prompt = [
      'You are a precise receipt parser.',
      'Return a strict JSON object with keys: vendor, tax_id, document_type, document_number, date, total, currency, payment_method, items, raw_text, and notes.',
      'items must be an array of objects: { "name": string, "qty": number|null, "price": number|null }.',
      'Use ISO 8601 format (YYYY-MM-DD) for dates when possible.',
      'total must be numeric (no currency symbols).',
      'currency should be a 3-letter code like USD, EUR, MXN when inferable, otherwise null.',
      'payment_method should capture how the receipt was paid (e.g., CREDIT, DEBIT, CASH, VISA, DISCOVER). Use null when unknown.',
      'raw_text should contain a plain-text transcription of the receipt for auditing.',
      'notes can include any ambiguities or assumptions.',
      'If information is missing, use null rather than guessing.',
      'Respond with ONLY the JSON object. Do not include code fences, markdown, or any commentary.',
    ].join(' ');

    const response = await client.responses.create({
      model: env.OPENAI_MODEL || 'gpt-4o-mini',
      input: [
        {
          role: 'system',
          content: [
            {
              type: 'input_text',
              text: prompt,
            },
          ],
        },
        {
          role: 'user',
          content: [
            {
              type: 'input_text',
              text: fallbackText
                ? `Optional OCR text of the receipt (may be noisy):\n${fallbackText}`
                : 'No OCR text provided. Rely on the image.',
            },
            {
              type: 'input_image',
              image_url: `data:image/png;base64,${base64}`,
              detail: 'high',
            },
          ],
        },
      ],
      // Ask for strict JSON in the prompt (omitting explicit response_format due to SDK type mismatch)
      max_output_tokens: 800,
    });

    let outputText = (response as any).output_text as string | undefined;
    if (!outputText) {
      throw new Error('OpenAI response did not include structured receipt output');
    }

    // Sanitize common formatting (e.g., markdown code fences) and extract JSON payload
    const tryParse = (text: string) => {
      const repaired = jsonrepair(text);
      return JSON.parse(repaired);
    };

    let data: any = null;
    let cleaned = outputText.trim();
    // Remove surrounding triple backticks like ```json ... ``` if present
    if (cleaned.startsWith('```')) {
      cleaned = cleaned.replace(/^```[a-zA-Z]*\s*/m, '').replace(/```\s*$/m, '').trim();
    }
    try {
      data = tryParse(cleaned);
    } catch (_e) {
      // Fallback: attempt to extract the first JSON object substring
      const match = cleaned.match(/\{[\s\S]*\}/);
      if (match) {
        try {
          data = tryParse(match[0]);
        } catch (e2) {
          throw new Error(`Failed to parse receipt JSON: ${outputText}`);
        }
      } else {
        throw new Error(`Failed to parse receipt JSON: ${outputText}`);
      }
    }

    const items: ReceiptLineItem[] = Array.isArray(data.items)
      ? data.items
          .filter((item: any) => item && (item.name || item.price || item.qty))
          .map((item: any) => ({
            name: normalizeItemName(item.name),
            qty: coerceNumber(item.qty),
            price: coerceNumber(item.price),
          }))
      : [];

    const rawText = data.raw_text ?? fallbackText ?? null;
    const paymentMethodJson = data.payment_method ?? data.paymentMethod ?? null;
    const inferredPayment = inferPaymentMethod(
      typeof paymentMethodJson === 'string' && paymentMethodJson.trim()
        ? paymentMethodJson
        : typeof rawText === 'string'
          ? rawText
          : undefined,
    );

    return {
      vendor: data.vendor ?? null,
      taxId: data.tax_id ?? data.taxId ?? null,
      documentType: data.document_type ?? data.documentType ?? null,
      documentNumber: data.document_number ?? data.documentNumber ?? null,
      date: data.date ?? null,
      total: coerceNumber(data.total),
      currency: data.currency ?? null,
      paymentMethod:
        typeof paymentMethodJson === 'string' && paymentMethodJson.trim()
          ? paymentMethodJson.trim().toUpperCase()
          : inferredPayment,
      items,
      rawText: rawText ?? undefined,
      notes: data.notes ?? null,
    };
  }
}

export default new ParserServiceReal();
