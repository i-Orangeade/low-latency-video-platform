<template>
  <div class="app-shell">
    <aside class="sidebar">
      <h1>Low-Latency Live Video Platform</h1>
      <RouterLink to="/">总览</RouterLink>
      <RouterLink to="/video-sources">视频源管理</RouterLink>
      <RouterLink to="/live">实时监控</RouterLink>
    </aside>
    <main class="main-content">
      <RouterView />
    </main>
  </div>
</template>
