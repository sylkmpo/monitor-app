import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'
import axios from 'axios'

// 🚨 Axios 企业级拦截器
axios.interceptors.request.use(config => {
  const token = sessionStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

axios.interceptors.response.use(res => res, error => {
  // 如果后端发现 token 过期或者没带，返回 401
  if (error.response && error.response.status === 401) {
    sessionStorage.removeItem('access_token');
    router.push('/login'); // 强制踢回登录页
  }
  return Promise.reject(error);
});

const app = createApp(App)
app.use(router)
app.mount('#app')