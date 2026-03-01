import { google } from 'googleapis';
import { PassThrough } from 'stream';
import { logger } from './logger';

type UploadOptions = {
  subfolderName?: string;
  parentFolderId?: string;
};

function getCredentials() {
  // Accept multiple env sources for convenience:
  // - GOOGLE_SERVICE_ACCOUNT_JSON: raw JSON
  // - GOOGLE_SERVICE_ACCOUNT: raw JSON (legacy/name variant)
  // - GOOGLE_SERVICE_ACCOUNT_B64: base64-encoded JSON
  const rawJson = process.env.GOOGLE_SERVICE_ACCOUNT_JSON || process.env.GOOGLE_SERVICE_ACCOUNT;
  const b64 = process.env.GOOGLE_SERVICE_ACCOUNT_B64;
  let raw = rawJson;
  if (!raw && b64) {
    try {
      raw = Buffer.from(b64, 'base64').toString('utf8');
    } catch (e) {
      return null;
    }
  }
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch (e) {
    return null;
  }
}

export class DriveServiceReal {
  private folderCache = new Map<string, Map<string, string>>();
  private authMode: 'unknown' | 'service-account' = 'unknown';

  private logAuthMode(mode: 'service-account') {
    if (this.authMode === mode) return;
    this.authMode = mode;
    logger.info(`[drive] Using ${mode} credentials`);
  }

  private async authClient() {
    const credentials = getCredentials();
    if (credentials) {
      const auth: any = new (google.auth as any).GoogleAuth({
        credentials,
        scopes: ['https://www.googleapis.com/auth/drive.file'],
      });
      const client: any = await auth.getClient();
      this.logAuthMode('service-account');
      return client;
    }

    throw new Error('Missing GOOGLE_SERVICE_ACCOUNT / GOOGLE_SERVICE_ACCOUNT_JSON env — service account credentials are required.');
  }

  private cacheFolder(parentId: string, name: string, folderId: string) {
    const normalized = name.trim();
    const existing = this.folderCache.get(parentId) ?? new Map();
    existing.set(normalized, folderId);
    this.folderCache.set(parentId, existing);
  }

  private getCachedFolder(parentId: string, name: string): string | null {
    const normalized = name.trim();
    return this.folderCache.get(parentId)?.get(normalized) ?? null;
  }

  private async ensureSubfolder(
    drive: ReturnType<typeof google.drive>,
    parentId: string,
    name: string,
  ): Promise<string> {
    const cached = this.getCachedFolder(parentId, name);
    if (cached) return cached;

    const query = [
      "mimeType = 'application/vnd.google-apps.folder'",
      'trashed = false',
      `name = '${name.replace(/'/g, "\\'")}'`,
      `'${parentId}' in parents`,
    ].join(' and ');
    const existing = await drive.files.list({
      q: query,
      spaces: 'drive',
      fields: 'files(id, name)',
      pageSize: 1,
      supportsAllDrives: true,
      includeItemsFromAllDrives: true,
    });
    const match = existing.data.files?.[0];
    if (match?.id) {
      this.cacheFolder(parentId, name, match.id);
      return match.id;
    }

    const createRes = await drive.files.create({
      requestBody: {
        name,
        mimeType: 'application/vnd.google-apps.folder',
        parents: [parentId],
      },
      fields: 'id',
      supportsAllDrives: true,
    });
    const folderId = createRes.data.id as string;
    this.cacheFolder(parentId, name, folderId);
    return folderId;
  }

  async upload(
    buffer: Buffer,
    filename: string,
    options: UploadOptions = {},
  ): Promise<{ id: string; url: string; folderId?: string }> {
    const client = await this.authClient();
    const drive = google.drive({ version: 'v3', auth: client });
    const stream = new PassThrough();
    stream.end(buffer);
    const requestBody: any = { name: filename };
    let parentFolderId: string | undefined;
    const baseFolderId = options.parentFolderId || process.env.DRIVE_UPLOAD_FOLDER_ID;
    if (baseFolderId) {
      if (options.subfolderName) {
        parentFolderId = await this.ensureSubfolder(drive, baseFolderId, options.subfolderName);
      } else {
        parentFolderId = baseFolderId;
      }
    }
    if (parentFolderId) {
      requestBody.parents = [parentFolderId];
    }

    const res = await drive.files.create({
      requestBody,
      media: {
        mimeType: 'application/octet-stream',
        body: stream,
      },
      fields: 'id, webViewLink',
      // allow uploads into shared drives if the target folder is on a shared drive
      supportsAllDrives: true,
    });
    const data = res.data as any;
    return { id: data.id, url: data.webViewLink || '', folderId: parentFolderId };
  }
}

export default new DriveServiceReal();
