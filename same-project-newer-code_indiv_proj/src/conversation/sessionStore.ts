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

export type PendingMedia = {
  mediaUrl: string;
  mediaSid?: string | null;
  messageSid?: string | null;
  mediaContentType?: string | null;
  filePath?: string | null;
};

export type SessionStage =
  | 'idle'
  | 'awaiting_image'
  | 'processing'
  | 'awaiting_confirmation'
  | 'awaiting_company_selection'
  | 'awaiting_field_selection'
  | 'awaiting_field_value';

export type Session = {
  stage: SessionStage;
  fields: Partial<Record<FieldKey, string>>;
  pendingField?: FieldKey;
  lastJobId?: string;
  lastMediaSid?: string;
  lastMessageSid?: string;
  lastConfirmationJobId?: string;
  lastErrorJobId?: string;
  selectedCompanyKey?: string;
  selectedCompanyName?: string;
  pendingMedia?: PendingMedia | null;
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
  const mergedPendingMedia =
    next.pendingMedia !== undefined ? next.pendingMedia ?? undefined : existing?.pendingMedia;
  const mergedSelectedCompanyKey =
    'selectedCompanyKey' in next ? next.selectedCompanyKey : existing?.selectedCompanyKey;
  const mergedSelectedCompanyName =
    'selectedCompanyName' in next ? next.selectedCompanyName : existing?.selectedCompanyName;
  const merged: Session = {
    stage: next.stage ?? existing?.stage ?? 'idle',
    fields: { ...(existing?.fields ?? {}), ...(next.fields ?? {}) },
    pendingField: next.pendingField ?? existing?.pendingField,
    lastJobId: next.lastJobId ?? existing?.lastJobId,
    lastMediaSid: next.lastMediaSid ?? existing?.lastMediaSid,
    lastMessageSid: next.lastMessageSid ?? existing?.lastMessageSid,
    lastConfirmationJobId: next.lastConfirmationJobId ?? existing?.lastConfirmationJobId,
    lastErrorJobId: next.lastErrorJobId ?? existing?.lastErrorJobId,
    selectedCompanyKey: mergedSelectedCompanyKey,
    selectedCompanyName: mergedSelectedCompanyName,
    pendingMedia: mergedPendingMedia,
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

export function setLastReceiptMeta(
  userId: string,
  jobId: string,
  mediaSid?: string | null,
  messageSid?: string | null,
): Session {
  const updates: Partial<Session> = { lastJobId: jobId };
  if (mediaSid) {
    updates.lastMediaSid = mediaSid;
  }
  if (messageSid) {
    updates.lastMessageSid = messageSid;
  }
  const session = upsertSession(userId, updates);
  session.lastJobId = jobId;
  if (mediaSid) {
    session.lastMediaSid = mediaSid;
  }
  if (messageSid) {
    session.lastMessageSid = messageSid;
  }
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
    lastMediaSid: undefined,
    lastMessageSid: undefined,
    lastConfirmationJobId: undefined,
    lastErrorJobId: undefined,
    selectedCompanyKey: undefined,
    selectedCompanyName: undefined,
    pendingMedia: undefined,
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
  companySelection?: {
    key: string;
    name: string;
  };
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
    pendingMedia: null,
    selectedCompanyKey: options.companySelection?.key,
    selectedCompanyName: options.companySelection?.name,
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

export type StorePendingConfirmationOptions = {
  jobId?: string;
  pendingMedia: PendingMedia;
};

export function storePendingReceiptForConfirmation(
  userId: string,
  fields: Partial<Record<FieldKey, string>>,
  options: StorePendingConfirmationOptions,
): Session {
  return upsertSession(userId, {
    stage: 'awaiting_confirmation',
    fields,
    pendingField: undefined,
    lastJobId: options.jobId ?? undefined,
    pendingMedia: options.pendingMedia,
    driveFile: undefined,
    sheet: undefined,
    links: undefined,
    selectedCompanyKey: undefined,
    selectedCompanyName: undefined,
  });
}

export type StorePendingReceiptOptions = {
  jobId?: string;
  pendingMedia: PendingMedia;
  sheet?: {
    spreadsheetId: string;
  };
  links?: SessionLinks;
};

export function storePendingReceiptData(
  userId: string,
  fields: Partial<Record<FieldKey, string>>,
  options: StorePendingReceiptOptions,
): Session {
  return upsertSession(userId, {
    stage: 'awaiting_field_value',
    fields,
    pendingField: 'date',
    lastJobId: options.jobId ?? undefined,
    pendingMedia: options.pendingMedia,
    selectedCompanyKey: undefined,
    selectedCompanyName: undefined,
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
  const lines = [...buildFieldLines(session)];
  lines.push('');
  lines.push('Toca un botón o responde SI/NO para confirmar o editar.');
  lines.push('Luego podrás elegir la empresa destino.');
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
