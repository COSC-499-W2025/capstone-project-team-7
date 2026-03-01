const MIN_YEAR = 2000;
const EARLIEST_REASONABLE_YEAR = 2020;
const LEGAL_SUFFIXES = [
	'S.A.C.',
	'S.A.',
	'SAC',
	'SA',
	'S.R.L.',
	'SRL',
	'LLC',
	'INC',
	'LTDA',
	'LTD',
	'LIMITED',
	'COMPANY',
	'CORP',
];

const ITEM_HINT_REGEX =
	/\b(und|pqt|paq|paquete|unidad|kg|gr|ml|lt|rollo|bolsa|botella|caja|pack)\b/i;
const PRICE_REGEX = /\b\d{1,4}(?:[.,]\d{1,2})\b/;

const DOCUMENT_TYPE_MAPPINGS: Array<{ match: RegExp; label: string }> = [
	{ match: /factur/i, label: 'Factura Electrónica' },
	{ match: /bolet/i, label: 'Boleta' },
	{ match: /recib/i, label: 'Recibo' },
	{ match: /nota\s+de\s+cr[eé]dit/i, label: 'Nota de Crédito' },
	{ match: /nota\s+de\s+d[eé]bit/i, label: 'Nota de Débito' },
	{ match: /gu[ií]a/i, label: 'Guía' },
	{ match: /ticket/i, label: 'Ticket' },
	{ match: /voucher/i, label: 'Voucher' },
	{ match: /proforma/i, label: 'Proforma' },
];

const COMPANY_DENY_REGEX =
	/\b(RUC|R\.U\.C|SUNAT|IGV|I\.G\.V|TOTAL|SUBTOTAL|SUB TOTAL|DNI|DOC(UMENTO)?|SERIE|N[°º#]|NUM\.?|NUMERO|CUENTA|CTA)\b/i;
const COMPANY_SHORT_DENY = /[%@]|http/i;
const LONG_NUMBER_REGEX = /\d{5,}/;
const LETTER_REGEX = /[A-Z]/i;
const RUC_REGEX = /\b(?:1\d|20)\d{9}\b/;
const RUC_TOKEN_REGEX = /\bR\.?U\.?C\.?[:\s-]*\d{8,12}\b/gi;

const DOC_HINT_REGEX =
	/\b(doc(umento)?|n[°º#]|num\.?|numero|serie|comprobante|factura|boleta|nota)\b/i;
const DOC_PREFIX_REGEX =
	/^(?:doc(?:umento)?|n[°º#]|num\.?|numero|serie|ser\.|comprobante|factura|boleta)\s*[:\-]?\s*/i;
const DOC_SERIES_REGEX = /\b[A-Z]{1,4}\d{0,4}-\d{3,9}\b/g;
const DOC_DIGITS_REGEX = /\b\d{6,12}\b/g;
const ADDRESS_KEYWORDS =
	/\b(av(?:enida)?|cal(?:le)?|jr\.?|jir[oó]n|mz\.?|manzana|lt\.?|lote|urb\.?|urbanizaci[oó]n|pje\.?|pasaje|km|dpto|departamento|piso|of\.?|oficina|int\.?|interior|plaza|mall|condom|local|blk|block|pje\b)/i;

const LABEL_REGEX = /\b(fecha|fec\.?|emisi[oó]n|issue|issued|fecha doc|fecha comp)\b/i;
const DATE_PATTERNS = [
	/\b\d{4}[./-]\d{1,2}[./-]\d{1,2}\b/,
	/\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b/,
];
const MONTH_NAME_PATTERN =
	/\b(\d{1,2})(?:\s+|-|\/)?(?:de\s+)?(ENE|FEB|MAR|ABR|MAY|JUN|JUL|AGO|SET|SEPT|SEP|OCT|NOV|DIC)(?:\.)?(?:\s+|-|\/)?(?:de\s+)?(\d{2,4})\b/i;
const MONTH_MAPPINGS: Record<string, number> = {
	ENE: 1,
	FEB: 2,
	MAR: 3,
	ABR: 4,
	MAY: 5,
	JUN: 6,
	JUL: 7,
	AGO: 8,
	SET: 9,
	SEPT: 9,
	SEP: 9,
	OCT: 10,
	NOV: 11,
	DIC: 12,
	DEC: 12,
};

type ParseDateOptions = { preferDMY?: boolean };

function pad(value: number) {
	return String(value).padStart(2, '0');
}

function normalizeYear(part: string): number | null {
	if (!/^\d{2,4}$/.test(part)) return null;
	let year = Number.parseInt(part, 10);
	if (!Number.isFinite(year)) return null;
	if (part.length === 2) {
		const currentYear = new Date().getFullYear();
		const baseCentury = Math.floor(currentYear / 100) * 100;
		year += baseCentury;
		if (year > currentYear + 2) {
			year -= 100;
		}
	}
	if (year < MIN_YEAR) return null;
	return year;
}

function formatIsoDate(year: number, month: number, day: number): string | null {
	if (!Number.isFinite(year) || !Number.isFinite(month) || !Number.isFinite(day)) return null;
	if (month < 1 || month > 12) return null;
	if (day < 1 || day > 31) return null;
	const candidate = new Date(Date.UTC(year, month - 1, day));
	if (
		candidate.getUTCFullYear() !== year ||
		candidate.getUTCMonth() !== month - 1 ||
		candidate.getUTCDate() !== day
	) {
		return null;
	}
	return `${year}-${pad(month)}-${pad(day)}`;
}

function parseFlexibleDate(value?: string | null, options?: ParseDateOptions): string | null {
	if (!value) return null;
	const trimmed = value.trim();
	if (!trimmed) return null;
	const directIso = trimmed.match(/^(\d{4})-(\d{2})-(\d{2})$/);
	if (directIso) {
		const year = Number.parseInt(directIso[1], 10);
		const month = Number.parseInt(directIso[2], 10);
		const day = Number.parseInt(directIso[3], 10);
		return formatIsoDate(year, month, day);
	}
	if (!/[./-]/.test(trimmed) && !MONTH_NAME_PATTERN.test(trimmed)) return null;
	const preferDMY = options?.preferDMY ?? false;
	const parts = trimmed.split(/[./-]/).map((part) => part.trim());
	let tryOrders: Array<'ymd' | 'dmy' | 'mdy'> = [];
	if (parts.length === 3) {
		const [first, , third] = parts;
		if (first.length === 4) {
			tryOrders = ['ymd'];
		} else if (third.length === 4) {
			tryOrders = preferDMY ? ['dmy', 'mdy'] : ['mdy', 'dmy'];
		} else {
			tryOrders = preferDMY ? ['dmy', 'mdy'] : ['mdy', 'dmy'];
		}
		for (const order of tryOrders) {
			let day: number | null = null;
			let month: number | null = null;
			let year: number | null = null;
			const [firstPart, secondPart, thirdPart] = parts;
			if (order === 'ymd') {
				year = normalizeYear(firstPart);
				month = Number.parseInt(secondPart, 10);
				day = Number.parseInt(thirdPart, 10);
			} else if (order === 'mdy') {
				month = Number.parseInt(firstPart, 10);
				day = Number.parseInt(secondPart, 10);
				year = normalizeYear(thirdPart);
				if (preferDMY && day != null && month != null && day > 12 && month <= 12) {
					continue;
				}
			} else {
				day = Number.parseInt(firstPart, 10);
				month = Number.parseInt(secondPart, 10);
				year = normalizeYear(thirdPart);
			}
			if (
				Number.isFinite(day) &&
				Number.isFinite(month) &&
				year !== null &&
				year !== undefined
			) {
				const iso = formatIsoDate(year, month, day);
				if (iso) return iso;
			}
		}
	}

	const monthNameMatch = trimmed.match(MONTH_NAME_PATTERN);
	if (monthNameMatch) {
		const day = Number.parseInt(monthNameMatch[1], 10);
		const month = MONTH_MAPPINGS[monthNameMatch[2].toUpperCase()] ?? null;
		const year = normalizeYear(monthNameMatch[3]);
		if (month && year) {
			return formatIsoDate(year, month, day);
		}
	}
	return null;
}

function findDateInLine(line: string): string | null {
	for (const pattern of DATE_PATTERNS) {
		const match = line.match(pattern);
		if (match && match[0]) {
			const iso = parseFlexibleDate(match[0], { preferDMY: true });
			if (iso) return iso;
		}
	}
	const monthName = line.match(MONTH_NAME_PATTERN);
	if (monthName) {
		const iso = parseFlexibleDate(monthName[0], { preferDMY: true });
		if (iso) return iso;
	}
	return null;
}

function extractDateFromText(rawText?: string | null): string | null {
	if (!rawText) return null;
	const lines = rawText
		.split(/\r?\n/)
		.map((line) => line.trim())
		.filter((line) => line.length);

	for (let i = 0; i < lines.length; i += 1) {
		if (LABEL_REGEX.test(lines[i])) {
			const candidates = [lines[i - 1], lines[i], lines[i + 1], lines[i + 2]].filter(Boolean);
			for (const candidate of candidates) {
				const iso = findDateInLine(candidate);
				if (iso) return iso;
			}
		}
	}

	for (const line of lines) {
		const iso = findDateInLine(line);
		if (iso) return iso;
	}

	return null;
}

function stripLegalSuffix(value: string): string {
	const upper = value.toUpperCase();
	for (const suffix of LEGAL_SUFFIXES) {
		if (upper.endsWith(suffix)) {
			return value.slice(0, value.length - suffix.length).trim();
		}
	}
	return value.trim();
}

function stripRucTokens(value: string): string {
	return value.replace(RUC_TOKEN_REGEX, '').trim();
}

function getLetterRatio(value: string): number {
	const letters = value.replace(/[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ]/g, '').length;
	const total = value.replace(/\s+/g, '').length;
	if (!total) return 0;
	return letters / total;
}

function isLikelyRucLine(line: string): boolean {
	return /RUC/i.test(line) || RUC_REGEX.test(line.replace(/\s+/g, ''));
}

function isLikelyAddressLine(line: string): boolean {
	if (!line) return false;
	if (ADDRESS_KEYWORDS.test(line)) return true;
	if (/#/.test(line)) return true;
	if (/\bP-?\d+\b/i.test(line)) return true;
	const digitTokens = line.match(/\d+/g) || [];
	if (digitTokens.some((token) => token.length >= 1 && token.length <= 4)) {
		return true;
	}
	return false;
}

function hasLegalSuffix(line: string): boolean {
	const normalized = line.toUpperCase();
	return LEGAL_SUFFIXES.some((suffix) => {
		const cleaned = suffix.replace(/\./g, '');
		if (!cleaned) return false;
		const pattern = cleaned.split('').join('\\.?\\s*');
		const regex = new RegExp(`\\b${pattern}\\b`);
		return regex.test(normalized);
	});
}

function isLikelyItemLine(line: string): boolean {
	if (!line) return false;
	const hasDigits = /\d/.test(line);
	const hasItemHint = ITEM_HINT_REGEX.test(line);
	const hasPrice = PRICE_REGEX.test(line);
	return (hasItemHint && hasDigits) || (hasPrice && /[A-Za-z]/.test(line));
}

function scoreCompanyLine(
	line: string,
	index: number,
	lines: string[],
	rucIndexes: Set<number>,
): number {
	if (!LETTER_REGEX.test(line)) return 0;
	if (COMPANY_DENY_REGEX.test(line) || COMPANY_SHORT_DENY.test(line)) return 0;
	if (LONG_NUMBER_REGEX.test(line)) return 0;

	let score = 1;
	const length = line.length;
	if (length >= 4 && length <= 32) score += 2;
	else if (length <= 48) score += 1;
	else score -= 1;

	const ratio = getLetterRatio(line);
	score += ratio * 2;

	const hasLegal = hasLegalSuffix(line);
	if (hasLegal) {
		score += 4;
	}

	if (rucIndexes.has(index + 1) || rucIndexes.has(index - 1)) {
		score += 2.5;
	}

	if (/[,:]$/.test(line)) {
		score -= 0.5;
	}

	if (/[0-9]{3,}/.test(line)) {
		score -= 1;
	}

	if (isLikelyItemLine(line)) {
		score -= 3;
	}

	if (isLikelyAddressLine(line)) {
		score -= 3;
	}

	if (line.split(' ').length <= 1) {
		score -= 0.5;
	}

	return score;
}

function pickCompanyFromText(rawText?: string | null): string | null {
	if (!rawText) return null;
	const lines = rawText
		.split(/\r?\n/)
		.map((line) => line.trim())
		.filter((line) => line.length);
	if (!lines.length) return null;

	const rucIndexes = new Set<number>();
	lines.forEach((line, idx) => {
		if (isLikelyRucLine(line)) {
			rucIndexes.add(idx);
		}
	});

	let best: { line: string; score: number } | null = null;
	let bestLegal: { line: string; score: number } | null = null;
	const limit = Math.min(lines.length, 12);
	for (let i = 0; i < limit; i += 1) {
		const line = lines[i];
		const score = scoreCompanyLine(line, i, lines, rucIndexes);
		if (score > 0) {
			if (hasLegalSuffix(line) && (!bestLegal || score > bestLegal.score)) {
				bestLegal = { line, score };
			}
			if (!best || score > best.score) {
				best = { line, score };
			}
		}
	}
	return bestLegal?.line ?? best?.line ?? null;
}

function cleanDocumentLine(value?: string | null): string {
	if (!value) return '';
	return value
		.replace(RUC_TOKEN_REGEX, '')
		.replace(DOC_PREFIX_REGEX, '')
		.replace(/\s{2,}/g, ' ')
		.replace(/^[^A-Za-z0-9]+/, '')
		.trim();
}

function isLikelyTaxId(value: string): boolean {
	return /^\d{11}$/.test(value) && /^(1\d|20)/.test(value);
}

function extractDocumentFromLine(line?: string | null): string | null {
	const cleaned = cleanDocumentLine(line);
	if (!cleaned) return null;
	const candidates = new Set<string>();
	const seriesMatches = cleaned.match(DOC_SERIES_REGEX);
	if (seriesMatches) {
		seriesMatches.forEach((match) => candidates.add(match));
	}
	const digitMatches = cleaned.match(DOC_DIGITS_REGEX);
	if (digitMatches) {
		digitMatches.forEach((match) => {
			if (!isLikelyTaxId(match)) {
				candidates.add(match);
			}
		});
	}
	if (
		/^[A-Z0-9-]+$/.test(cleaned) &&
		(cleaned.includes('-') || cleaned.length >= 7) &&
		!isLikelyTaxId(cleaned)
	) {
		candidates.add(cleaned);
	}
	if (!candidates.size) return null;
	const ordered = Array.from(candidates).sort((a, b) => scoreDocumentCandidate(b) - scoreDocumentCandidate(a));
	return ordered[0] ?? null;
}

function scoreDocumentCandidate(value: string): number {
	let score = 0;
	if (value.includes('-')) score += 3;
	if (/[A-Z]/.test(value)) score += 1;
	if (value.length >= 8 && value.length <= 14) score += 1;
	if (/\d{6,}/.test(value)) score += 1;
	return score;
}

export function resolveReceiptDate(rawDate?: string | null, rawText?: string | null): string | null {
	const fromText = extractDateFromText(rawText);
	if (fromText) return fromText;
	return parseFlexibleDate(rawDate, { preferDMY: true });
}

export function stabilizeDate(dateStr?: string | null, fallback?: Date): string | null {
	const fallbackDate = fallback ?? new Date();
	const base = dateStr ? new Date(dateStr) : null;
	let date = base && !Number.isNaN(base.getTime()) ? base : fallbackDate;
	const now = fallbackDate;
	const maxAllowed = new Date(now);
	maxAllowed.setDate(maxAllowed.getDate() + 3);
	while (date.getTime() > maxAllowed.getTime()) {
		const previousYear = date.getFullYear() - 1;
		if (previousYear < EARLIEST_REASONABLE_YEAR) break;
		date.setFullYear(previousYear);
	}
	const minAllowed = new Date(now);
	minAllowed.setMonth(minAllowed.getMonth() - 18);
	if (date.getTime() < minAllowed.getTime()) {
		date = fallbackDate;
	}
	if (date.getFullYear() < EARLIEST_REASONABLE_YEAR) {
		date = new Date(EARLIEST_REASONABLE_YEAR, date.getMonth(), date.getDate());
	}
	return formatIsoDate(date.getFullYear(), date.getMonth() + 1, date.getDate());
}

function trimLength(value: string, max = 48) {
	return value.length <= max ? value : value.slice(0, max).trim();
}

export function sanitizeCompanyName(rawVendor?: string | null, rawText?: string | null): string {
	const fromText = pickCompanyFromText(rawText);
	const cleanedVendor = rawVendor ? stripLegalSuffix(stripRucTokens(rawVendor)) : '';
	if (fromText && !isLikelyAddressLine(fromText)) {
		return trimLength(fromText);
	}
	if (cleanedVendor) {
		return trimLength(cleanedVendor);
	}
	return fromText ? trimLength(fromText) : '';
}

function titleCase(value: string): string {
	return value
		.split(/\s+/)
		.filter(Boolean)
		.map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
		.join(' ');
}

export function normalizeDocumentType(rawType?: string | null): string {
	if (!rawType) return '';
	const trimmed = rawType.trim();
	if (!trimmed) return '';
	for (const mapping of DOCUMENT_TYPE_MAPPINGS) {
		if (mapping.match.test(trimmed)) {
			return mapping.label;
		}
	}
	return titleCase(trimmed);
}

export function normalizeDocumentNumber(rawNumber?: string | null, rawText?: string | null): string {
	const fromValue = extractDocumentFromLine(rawNumber);
	if (fromValue) return fromValue;
	if (!rawText) return '';
	const lines = rawText
		.split(/\r?\n/)
		.map((line) => line.trim())
		.filter((line) => line.length);
	for (let i = 0; i < lines.length; i += 1) {
		const line = lines[i];
		const window = DOC_HINT_REGEX.test(line)
			? [lines[i - 1], line, lines[i + 1]].filter(Boolean)
			: [line];
		for (const candidate of window) {
			const normalized = extractDocumentFromLine(candidate);
			if (normalized) return normalized;
		}
	}
	return '';
}

export function sanitizeTaxId(raw?: string | null): string {
	if (!raw) return '';
	const digits = raw.replace(/[^0-9]/g, '');
	return digits || raw.trim();
}
