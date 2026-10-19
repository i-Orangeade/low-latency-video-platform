import { createRouter, createWebHistory } from "vue-router";

import Dashboard from "../views/Dashboard.vue";
import LiveMonitor from "../views/LiveMonitor.vue";
import SharePlayback from "../views/SharePlayback.vue";
import VideoSourceList from "../views/VideoSourceList.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: Dashboard },
    { path: "/video-sources", component: VideoSourceList },
    { path: "/live", component: LiveMonitor },
    {
      path: "/play/share",
      component: SharePlayback,
      meta: { standalone: true }
    }
  ]
});

export default router;
