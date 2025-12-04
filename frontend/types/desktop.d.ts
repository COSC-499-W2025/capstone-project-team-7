export {};

declare global {
  interface Window {
    desktop?: {
      ping: () => Promise<string>;
    };
  }
}
