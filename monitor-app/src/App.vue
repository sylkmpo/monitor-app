<template>
  <router-view v-if="isLoginPage"></router-view>
  
  <div v-else class="app-layout">
    <aside class="sidebar">
      <div class="logo">🛡️ 智能监控中台</div>
      <div class="user-info">
        <div class="avatar">👨‍💻</div>
        <div class="name">欢迎, {{ currentUsername }}</div>
      </div>
      <nav>
        <router-link to="/" class="nav-btn">📺 实时监控</router-link>
        <router-link to="/alerts" class="nav-btn">🚨 告警中心</router-link>
        <router-link to="/settings" class="nav-btn">⚙️ 设备管理</router-link>
      </nav>
      
      <div class="bottom-actions">
        <button @click="toggleTheme" class="theme-btn">
          {{ isDark ? '☀️ 切换浅色模式' : '🌙 切换深色模式' }}
        </button>
        <button @click="logout" class="logout-btn">🚪 安全退出</button>
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
const currentUsername = computed(() => localStorage.getItem('username') || '管理员');

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
  localStorage.removeItem('access_token');
  localStorage.removeItem('username');
  router.push('/login');
};
</script>

<style>
/* 这里的颜色全部换成刚才定义的 var() 变量 */
.app-layout { display: flex; height: 100vh; overflow: hidden; }
.sidebar { width: 240px; background-color: var(--bg-sidebar); border-right: 1px solid var(--border-color); display: flex; flex-direction: column; transition: 0.3s; }
.logo { padding: 20px; font-size: 18px; font-weight: bold; border-bottom: 1px solid var(--border-color); text-align: center; color: var(--text-main); }
.user-info { padding: 20px; display: flex; align-items: center; gap: 10px; border-bottom: 1px solid var(--border-color); }
.user-info .avatar { font-size: 24px; background: var(--bg-body); width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; border-radius: 50%; }
.user-info .name { font-size: 14px; color: var(--text-main); font-weight: bold; }
.sidebar nav { display: flex; flex-direction: column; padding: 20px 10px; gap: 10px; flex: 1; }
.nav-btn { text-decoration: none; color: var(--text-sub); padding: 12px 16px; border-radius: 8px; transition: 0.2s; font-weight: 500; }
.nav-btn:hover { background-color: var(--hover-bg); color: var(--text-main); }
.router-link-active { background-color: var(--hover-bg); color: var(--text-main); font-weight: bold; }

.bottom-actions { padding: 20px 10px; border-top: 1px solid var(--border-color); display: flex; flex-direction: column; gap: 10px; }
.theme-btn { width: 100%; padding: 10px; background: var(--hover-bg); border: none; color: var(--text-main); border-radius: 8px; cursor: pointer; transition: 0.3s; font-weight: bold; }
.theme-btn:hover { background: var(--border-color); }
.logout-btn { width: 100%; padding: 10px; background: transparent; border: 1px solid var(--danger); color: var(--danger); border-radius: 8px; cursor: pointer; transition: 0.3s; font-weight: bold; }
.logout-btn:hover { background: var(--danger); color: white; }

.main-content { flex: 1; overflow-y: auto; background-color: var(--bg-body); transition: 0.3s; }
</style>