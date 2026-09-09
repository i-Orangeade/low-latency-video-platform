import { createRouter, createWebHistory } from "vue-router";

import Dashboard from "../views/Dashboard.vue";
import DeviceList from "../views/DeviceList.vue";
import LiveMonitor from "../views/LiveMonitor.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: Dashboard },
    { path: "/devices", component: DeviceList },
    { path: "/live", component: LiveMonitor }
  ]
});

export default router;
