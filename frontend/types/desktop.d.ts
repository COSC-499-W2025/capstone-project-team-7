import type { AppSettings } from "@/lib/settings";

export {};

declare global {
  type DesktopOpenDialogOptions = {
    title?: string;
    filters?: Array<{ name: string; extensions: string[] }>;
    properties?: Array<"openFile" | "openDirectory" | "multiSelections" | "showHiddenFiles">;
  };

  type DesktopFilePayload = {
    name: string;
    type: string;
    size: number;
    data: string;
  };

  interface Window {
    desktop?: {
      ping: () => Promise<string>;
      openFile: (options?: DesktopOpenDialogOptions) => Promise<string[]>;
      readFile?: (filePath: string) => Promise<DesktopFilePayload>;
      selectDirectory: (options?: DesktopOpenDialogOptions) => Promise<string[]>;
      selectScanSource?: (options?: DesktopOpenDialogOptions) => Promise<string[]>;
      saveSettings?: (settings?: AppSettings) => Promise<{ ok: boolean; path?: string; error?: string }>;
      loadSettings?: () => Promise<{ ok: boolean; settings?: AppSettings; path?: string; error?: string }>;
    };
  }
}
