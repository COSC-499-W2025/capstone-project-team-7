export const IPC_CHANNELS = {
  PING: "desktop:ping",
  OPEN_FILE: "desktop:openFile",
  SELECT_DIRECTORY: "desktop:selectDirectory"
  , SAVE_SETTINGS: "desktop:saveSettings",
  LOAD_SETTINGS: "desktop:loadSettings"
} as const;

export type IpcChannel = (typeof IPC_CHANNELS)[keyof typeof IPC_CHANNELS];
