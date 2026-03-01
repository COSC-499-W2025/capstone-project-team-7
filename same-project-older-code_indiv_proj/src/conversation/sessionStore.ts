export type FieldKey =
  | 'company'
  | 'taxId'
  | 'documentType'
  | 'documentNumber'
  | 'date'
  | 'currency'
  | 'amount';

export type SessionDriveFile = {
  id: string | null;
  url: string;
  filename: string;
};

export type SessionSheetState = {
  spreadsheetId: string;
  appended: boolean;
};

export type SessionLinks = {
  folderUrl?: string | null;
  sheetUrl?: string | null;
};

export type SessionStage =
  | 'idle'
  | 'awaiting_image'
  | 'processing'
  | 'awaiting_confirmation'
  | 'awaiting_field_selection'
  | 'awaiting_field_value';

export type Session = {
  stage: SessionStage;
  fields: Partial<Record<FieldKey, string>>;
  pendingField?: FieldKey;
  lastJobId?: string;
  lastConfirmationJobId?: string;
  lastErrorJobId?: string;
  driveFile?: SessionDriveFile;
  sheet?: SessionSheetState;
  links?: SessionLinks;
  updatedAt: number;
};

const sessions = new Map<string, Session>();

const fieldOrder: FieldKey[] = [
  'company',
  'taxId',
  'documentType',
  'documentNumber',
  'date',
  'currency',
  'amount',
];

const fieldLabels: Record<FieldKey, string> = {
  company: 'Empresa',
  taxId: 'RUC',
  documentType: 'Tipo de Documento',
  documentNumber: 'Número de Documento',
  date: 'Fecha',
  currency: 'Moneda',
  amount: 'Monto',
};

const fallbackValue = (value?: string | null) => (value && value.trim() ? value.trim() : 'desconocido');

export function getSession(userId: string): Session | null {
  return sessions.get(userId) ?? null;
}

export function upsertSession(userId: string, next: Partial<Session> = {}): Session {
  const existing = sessions.get(userId);
  const mergedSheet =
    next.sheet != null
      ? { ...(existing?.sheet ?? {}), ...next.sheet }
      : existing?.sheet;
  const mergedLinks =
    next.links != null
      ? { ...(existing?.links ?? {}), ...next.links }
      : existing?.links;
  const merged: Session = {
    stage: next.stage ?? existing?.stage ?? 'idle',
    fields: { ...(existing?.fields ?? {}), ...(next.fields ?? {}) },
    pendingField: next.pendingField ?? existing?.pendingField,
    lastJobId: next.lastJobId ?? existing?.lastJobId,
    lastConfirmationJobId: next.lastConfirmationJobId ?? existing?.lastConfirmationJobId,
    lastErrorJobId: next.lastErrorJobId ?? existing?.lastErrorJobId,
    driveFile: next.driveFile ?? existing?.driveFile,
    sheet: mergedSheet,
    links: mergedLinks,
    updatedAt: Date.now(),
  };
  sessions.set(userId, merged);
  return merged;
}

export function setStage(userId: string, stage: SessionStage): Session {
  const session = upsertSession(userId, { stage });
  session.stage = stage;
  session.updatedAt = Date.now();
  sessions.set(userId, session);
  return session;
}

export function setPendingField(userId: string, field?: FieldKey | null): Session {
  const session = upsertSession(userId, { pendingField: field ?? undefined });
  session.pendingField = field ?? undefined;
  session.updatedAt = Date.now();
  sessions.set(userId, session);
  return session;
}

export function setLastJobId(userId: string, jobId: string): Session {
  const session = upsertSession(userId, { lastJobId: jobId });
  session.lastJobId = jobId;
  session.updatedAt = Date.now();
  sessions.set(userId, session);
  return session;
}

export function markConfirmationSent(userId: string, jobId: string): Session {
  const session = upsertSession(userId, { lastConfirmationJobId: jobId });
  session.lastConfirmationJobId = jobId;
  session.updatedAt = Date.now();
  sessions.set(userId, session);
  return session;
}

export function markErrorSent(userId: string, jobId: string): Session {
  const session = upsertSession(userId, { lastErrorJobId: jobId });
  session.lastErrorJobId = jobId;
  session.updatedAt = Date.now();
  sessions.set(userId, session);
  return session;
}

export function resetForGreeting(userId: string): Session {
  const session: Session = {
    stage: 'awaiting_image',
    fields: {},
    pendingField: undefined,
    lastJobId: undefined,
    lastConfirmationJobId: undefined,
    lastErrorJobId: undefined,
    driveFile: undefined,
    sheet: undefined,
    links: undefined,
    updatedAt: Date.now(),
  };
  sessions.set(userId, session);
  return session;
}

export function clearSession(userId: string): void {
  sessions.delete(userId);
}

export function applyFieldUpdate(userId: string, field: FieldKey, value: string): Session {
  const current = sessions.get(userId);
  const nextFields = { ...(current?.fields ?? {}), [field]: value };
  return upsertSession(userId, { fields: nextFields });
}

export type StoreReceiptOptions = {
  jobId?: string;
  driveFile?: SessionDriveFile;
  sheet?: {
    spreadsheetId: string;
  };
  links?: SessionLinks;
};

export function storeReceiptData(
  userId: string,
  fields: Partial<Record<FieldKey, string>>,
  options: StoreReceiptOptions = {},
): Session {
  return upsertSession(userId, {
    stage: 'awaiting_confirmation',
    fields,
    pendingField: undefined,
    lastJobId: options.jobId ?? undefined,
    driveFile: options.driveFile ?? undefined,
    sheet: options.sheet
      ? {
          spreadsheetId: options.sheet.spreadsheetId,
          appended: false,
        }
      : undefined,
    links: options.links,
  });
}

function buildFieldLines(session: Session): string[] {
  const lines: string[] = [];
  for (const key of fieldOrder) {
    const label = fieldLabels[key];
    let value = fallbackValue(session.fields[key]);
    lines.push(`${label}: ${value}`);
  }
  return lines;
}

export function formatSummary(session: Session): string {
  const lines = ['¡Listo! Estos son los datos encontrados:', ...buildFieldLines(session)];
  lines.push('\nToca un botón o responde SI/NO para confirmar o editar.');
  return lines.join('\n');
}

export function formatFieldLines(session: Session): string[] {
  return buildFieldLines(session);
}

export function formatFieldSelection(session: Session): string {
  const lines = ['¿Qué campo quieres modificar? Toca "Campo" para ver la lista o responde con el número correspondiente:'];
  fieldOrder.forEach((key, index) => {
    const label = fieldLabels[key];
    const value = fallbackValue(session.fields[key]);
    lines.push(`${index + 1}) ${label}: ${value}`);
  });
  lines.push('\nO responde CANCELAR para dejar los datos como están.');
  return lines.join('\n');
}

function normalizeSelection(value: string): string {
  return value
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim();
}

const fieldIdMap: Record<string, FieldKey> = {
  empresa_list: 'company',
  ruc_list: 'taxId',
  documentot_list: 'documentType',
  documenton_list: 'documentNumber',
  fecha_list: 'date',
  moneda_list: 'currency',
  monto_list: 'amount',
};

export function resolveFieldBySelection(selection: string): FieldKey | null {
  const trimmed = selection.trim();
  if (!trimmed) return null;
  const idx = Number.parseInt(trimmed, 10);
  if (Number.isInteger(idx) && idx >= 1 && idx <= fieldOrder.length) {
    return fieldOrder[idx - 1];
  }
  const normalized = normalizeSelection(trimmed);
  if (!normalized) return null;
  const byId = fieldIdMap[normalized];
  if (byId) return byId;
  return (
    fieldOrder.find((key) => normalizeSelection(fieldLabels[key]) === normalized) ||
    fieldOrder.find((key) => normalizeSelection(key) === normalized) ||
    null
  );
}

export function getFieldLabel(field: FieldKey): string {
  return fieldLabels[field];
}

export function markSheetAppended(userId: string): Session {
  const existing = sessions.get(userId);
  if (!existing?.sheet) {
    return upsertSession(userId, {});
  }
  return upsertSession(userId, {
    sheet: {
      spreadsheetId: existing.sheet.spreadsheetId,
      appended: true,
    },
  });
}
