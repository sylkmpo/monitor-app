<template>
  <router-view v-if="isLoginPage"></router-view>
  
  <div v-else class="app-layout">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 3l7 3v5c0 5-3 8-7 10-4-2-7-5-7-10V6l7-3z"></path>
            <path d="M9 12l2 2 4-5"></path>
          </svg>
        </div>
        <div>
          <div class="brand-name">MonitorOps</div>
          <div class="brand-subtitle">Risk Intelligence</div>
        </div>
      </div>
      <div class="user-info">
        <div class="avatar">{{ currentInitial }}</div>
        <div>
          <div class="user-label">当前账号 / {{ currentRoleLabel }}</div>
          <div class="name">{{ currentUsername }}</div>
        </div>
      </div>
      <nav>
        <router-link to="/" class="nav-btn">
          <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="4" width="18" height="13" rx="2"></rect><path d="M8 21h8M12 17v4"></path></svg>
          <span>实时监控</span>
        </router-link>
        <router-link to="/alerts" class="nav-btn">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 2h4l1 4 3 2 4-1 2 4-3 3v4l3 3-2 4-4-1-3 2-1 4h-4l-1-4-3-2-4 1-2-4 3-3v-4L0 11l2-4 4 1 3-2 1-4z" transform="scale(.75) translate(4 1)"></path><path d="M12 8v5M12 16h.01"></path></svg>
          <span>告警中心</span>
        </router-link>
        <router-link v-if="canOperate" to="/rules" class="nav-btn">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h16M4 12h10M4 19h7"></path><path d="M17 14l3 3-3 3"></path></svg>
          <span>风险规则</span>
        </router-link>
        <router-link v-if="canOperate" to="/settings" class="nav-btn">
          <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2"></rect><path d="M7 9h10M7 13h6"></path></svg>
          <span>设备管理</span>
        </router-link>
        <router-link to="/user" class="nav-btn">
          <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="4"></circle><path d="M4 21c1.5-4 14.5-4 16 0"></path></svg>
          <span>用户中心</span>
        </router-link>
      </nav>
      
      <div class="bottom-actions">
        <button @click="toggleTheme" class="utility-btn">
          {{ isDark ? '浅色模式' : '深色模式' }}
        </button>
        <button @click="logout" class="logout-btn">安全退出</button>
      </div>
    </aside>
    <main class="main-content">
      <router-view></router-view>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';

const route = useRoute();
const router = useRouter();

const isLoginPage = computed(() => route.path === '/login');
const currentUsername = computed(() => sessionStorage.getItem('username') || '管理员');
const currentInitial = computed(() => currentUsername.value.slice(0, 1).toUpperCase());
const currentRole = computed(() => sessionStorage.getItem('role') || 'viewer');
const currentRoleLabel = computed(() => ({
  admin: '管理员',
  operator: '运维',
  viewer: '只读',
  ai_worker: 'AI 服务'
}[currentRole.value] || currentRole.value));
const canOperate = computed(() => ['admin', 'operator'].includes(currentRole.value));

// ======= 🚨 主题切换逻辑 =======
// 从本地存储读取历史偏好，默认深色
const isDark = ref(localStorage.getItem('theme') !== 'light'); 

const applyTheme = () => {
  document.documentElement.setAttribute('data-theme', isDark.value ? 'dark' : 'light');
};

const toggleTheme = () => {
  isDark.value = !isDark.value;
  localStorage.setItem('theme', isDark.value ? 'dark' : 'light');
  applyTheme();
};

onMounted(() => {
  applyTheme(); // 页面加载时立刻应用主题
});
// ===============================

const logout = () => {
  sessionStorage.removeItem('access_token');
  sessionStorage.removeItem('username');
  router.push('/login');
};
</script>

<style>
.app-layout { display: flex; height: 100vh; overflow: hidden; }
.sidebar { width: 260px; background-color: var(--bg-sidebar); border-right: 1px solid rgba(255, 255, 255, 0.08); display: flex; flex-direction: column; transition: 0.2s; }
.brand { min-height: 74px; padding: 18px 20px; display: flex; align-items: center; gap: 12px; border-bottom: 1px solid rgba(255, 255, 255, 0.08); color: var(--sidebar-text); }
.brand-mark { width: 38px; height: 38px; border-radius: 8px; display: flex; align-items: center; justify-content: center; background: var(--primary); color: #fff; box-shadow: 0 10px 22px rgba(37, 99, 235, 0.28); }
.brand-name { font-size: 16px; font-weight: 800; letter-spacing: 0; }
.brand-subtitle { margin-top: 2px; font-size: 11px; color: var(--sidebar-muted); text-transform: uppercase; letter-spacing: 0.08em; }
.user-info { margin: 16px 14px 8px; padding: 12px; display: flex; align-items: center; gap: 10px; border: 1px solid rgba(255, 255, 255, 0.08); background: rgba(255, 255, 255, 0.04); border-radius: 8px; }
.user-info .avatar { font-size: 14px; font-weight: 800; color: #fff; background: rgba(37, 99, 235, 0.9); width: 34px; height: 34px; display: flex; align-items: center; justify-content: center; border-radius: 50%; }
.user-label { font-size: 11px; color: var(--sidebar-muted); }
.user-info .name { margin-top: 2px; font-size: 14px; color: var(--sidebar-text); font-weight: 700; }
.sidebar nav { display: flex; flex-direction: column; padding: 10px 12px 20px; gap: 4px; flex: 1; }
.nav-btn { text-decoration: none; color: var(--sidebar-muted); padding: 11px 12px; border-radius: 8px; transition: 0.15s; font-weight: 700; display: flex; align-items: center; gap: 11px; }
.nav-btn svg { width: 18px; height: 18px; stroke: currentColor; stroke-width: 2; fill: none; stroke-linecap: round; stroke-linejoin: round; flex: 0 0 auto; }
.nav-btn:hover { background-color: rgba(255, 255, 255, 0.06); color: var(--sidebar-text); }
.router-link-active { background-color: var(--sidebar-active); color: #fff; }
.bottom-actions { padding: 16px 12px; border-top: 1px solid rgba(255, 255, 255, 0.08); display: grid; gap: 8px; }
.utility-btn { width: 100%; padding: 10px; background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.08); color: var(--sidebar-text); border-radius: 8px; cursor: pointer; font-weight: 800; }
.utility-btn:hover { background: rgba(255, 255, 255, 0.1); }
.logout-btn { width: 100%; padding: 10px; background: transparent; border: 1px solid rgba(220, 38, 38, 0.5); color: #fecaca; border-radius: 8px; cursor: pointer; font-weight: 800; }
.logout-btn:hover { background: rgba(220, 38, 38, 0.16); color: #fff; }
.main-content { flex: 1; overflow-y: auto; background: radial-gradient(circle at top left, rgba(37, 99, 235, 0.04), transparent 320px), var(--bg-body); transition: 0.2s; }
</style>
