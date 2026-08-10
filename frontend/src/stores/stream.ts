import { defineStore } from "pinia";

import type { StreamProtocol } from "../api/stream";

export const useStreamStore = defineStore("stream", {
  state: () => ({
    currentStreamId: "drone_001",
    currentProtocol: "flv" as StreamProtocol
  }),
  actions: {
    setStream(streamId: string) {
      this.currentStreamId = streamId;
    },
    setProtocol(protocol: StreamProtocol) {
      this.currentProtocol = protocol;
    }
  }
});
