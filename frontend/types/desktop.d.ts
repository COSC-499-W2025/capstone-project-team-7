export {};

declare global {
  type DesktopOpenDialogOptions = {
    title?: string;
    filters?: Array<{ name: string; extensions: string[] }>;
    properties?: Array<"openFile" | "openDirectory" | "multiSelections" | "showHiddenFiles">;
  };

  interface Window {
    desktop?: {
      ping: () => Promise<string>;
      openFile: (options?: DesktopOpenDialogOptions) => Promise<string[]>;
      selectDirectory: (options?: DesktopOpenDialogOptions) => Promise<string[]>;
      saveSettings?: (settings?: any) => Promise<{ ok: boolean; path?: string; error?: string }>;
      loadSettings?: () => Promise<{ ok: boolean; settings?: any; path?: string; error?: string }>;
    };
  }
}
