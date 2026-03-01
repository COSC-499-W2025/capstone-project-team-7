type UploadOptions = {
  subfolderName?: string;
  parentFolderId?: string;
};

export class DriveService {
  async upload(
    buffer: Buffer,
    filename: string,
    _options: UploadOptions = {},
  ): Promise<{ id: string; url: string; folderId?: string | null }> {
    // mock upload: return a fake id and url
    return {
      id: `drive-${Date.now()}`,
      url: `https://drive.mock/${filename}`,
      folderId: _options.parentFolderId ?? null,
    };
  }
}

export default new DriveService();
//Upload to drive
