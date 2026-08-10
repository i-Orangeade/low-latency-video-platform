<template>
  <div class="app-shell">
    <aside class="sidebar">
      <h1>无人机巡检监控</h1>
      <RouterLink to="/">总览</RouterLink>
      <RouterLink to="/devices">设备管理</RouterLink>
      <RouterLink to="/live">实时监控</RouterLink>
      <RouterLink to="/alerts">告警中心</RouterLink>
      <RouterLink to="/records">录像回放</RouterLink>
      <RouterLink to="/experiments">性能实验</RouterLink>
    </aside>
    <main class="main-content">
      <RouterView />
    </main>
  </div>
</template>
