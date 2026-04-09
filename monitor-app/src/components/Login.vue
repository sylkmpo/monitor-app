<template>
  <div class="login-container">
    <div class="login-box">
      <div class="logo">🛡️ 智能监控管理中台</div>
      <form @submit.prevent="handleLogin" class="login-form">
        <div class="input-group">
          <label>用户名</label>
          <input v-model="username" type="text" placeholder="请输入管理员账号" required />
        </div>
        <div class="input-group">
          <label>密码</label>
          <input v-model="password" type="password" placeholder="请输入密码" required />
        </div>
        <button type="submit" class="login-btn" :disabled="loading">
          {{ loading ? '鉴权中...' : '安全登录' }}
        </button>
        <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios';

const username = ref('admin'); // 为了你测试方便，默认填好
const password = ref('');
const errorMsg = ref('');
const loading = ref(false);
const router = useRouter();

const handleLogin = async () => {
  loading.value = true;
  errorMsg.value = '';
  try {
    const formData = new URLSearchParams();
    formData.append('username', username.value);
    formData.append('password', password.value);

    const res = await axios.post('http://127.0.0.1:8000/api/login', formData);
    
    // 覆盖保存最新的令牌和用户名及角色信息
    sessionStorage.setItem('access_token', res.data.access_token);
    sessionStorage.setItem('username', res.data.username);
    sessionStorage.setItem('role', res.data.role || 'operator');
    
    // 🚨 绝杀修复：不用 router.push('/')，直接让浏览器强制刷新并跳转！
    // 这样能彻底清空 Vue 内存中卡住的旧名字，强制重新读取 sessionStorage。
    window.location.href = '/';
    
  } catch (err) {
    errorMsg.value = '账号或密码错误，请联系系统管理员';
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.login-container { display: flex; justify-content: center; align-items: center; height: 100vh; background-color: var(--bg-body); width: 100vw; position: absolute; top: 0; left: 0; z-index: 9999; transition: 0.3s; }
.login-box { background: var(--bg-card); padding: 40px; border-radius: 12px; box-shadow: var(--shadow); width: 100%; max-width: 400px; border: 1px solid var(--border-color); transition: 0.3s; }
.logo { font-size: 22px; font-weight: bold; color: var(--text-main); text-align: center; margin-bottom: 30px; letter-spacing: 1px; }
.input-group { margin-bottom: 20px; }
.input-group label { display: block; color: var(--text-sub); margin-bottom: 8px; font-size: 14px; font-weight: 500; }
.input-group input { width: 100%; padding: 12px; background: var(--bg-input); border: 1px solid var(--border-color); border-radius: 6px; color: var(--text-main); font-size: 16px; box-sizing: border-box; transition: 0.3s; }
.input-group input:focus { border-color: var(--primary); outline: none; }
.login-btn { width: 100%; padding: 14px; background: var(--primary); color: white; border: none; border-radius: 6px; font-size: 16px; font-weight: bold; cursor: pointer; transition: 0.3s; margin-top: 10px; }
.login-btn:hover { background: var(--primary-hover); }
.error-msg { color: var(--danger); margin-top: 15px; text-align: center; font-size: 14px; background: rgba(239, 68, 68, 0.1); padding: 10px; border-radius: 6px; }
</style>