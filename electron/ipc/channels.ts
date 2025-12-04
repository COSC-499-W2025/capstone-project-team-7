export const IPC_CHANNELS = {
  PING: "desktop:ping"
} as const;

export type IpcChannel = (typeof IPC_CHANNELS)[keyof typeof IPC_CHANNELS];
