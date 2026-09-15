import { createRouter, createWebHistory } from "vue-router";

import Dashboard from "../views/Dashboard.vue";
import DeviceList from "../views/DeviceList.vue";
import LiveMonitor from "../views/LiveMonitor.vue";

// 页面路由：
// /         系统总览，展示数量和链路示例；
// /devices  新增并查看视频源；
// /live     获取播放地址、播放 HTTP-FLV 并展示链路状态。
const router = createRouter({
  history: createWebHistory(),
  // 三个页面分别对应系统概览、视频源管理和实时播放。
  routes: [
    { path: "/", component: Dashboard },
    { path: "/devices", component: DeviceList },
    { path: "/live", component: LiveMonitor }
  ]
});

export default router;
