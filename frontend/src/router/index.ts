import { createRouter, createWebHistory } from "vue-router";

import AlertCenter from "../views/AlertCenter.vue";
import Dashboard from "../views/Dashboard.vue";
import DeviceList from "../views/DeviceList.vue";
import LiveMonitor from "../views/LiveMonitor.vue";
import PerformanceTest from "../views/PerformanceTest.vue";
import RecordList from "../views/RecordList.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: Dashboard },
    { path: "/devices", component: DeviceList },
    { path: "/live", component: LiveMonitor },
    { path: "/alerts", component: AlertCenter },
    { path: "/records", component: RecordList },
    { path: "/experiments", component: PerformanceTest }
  ]
});

export default router;
