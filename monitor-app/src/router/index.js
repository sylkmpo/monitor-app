import { createRouter, createWebHistory } from 'vue-router'
import MonitorDashboard from '../components/MonitorDashboard.vue'
import CameraManager from '../components/CameraManager.vue'
import AlertCenter from '../components/AlertCenter.vue'
import Login from '../components/Login.vue' // 新增
import UserCenter from '../components/UserCenter.vue' // 新增

const routes = [
  { path: '/login', component: Login },
  { path: '/', component: MonitorDashboard },
  { path: '/alerts', component: AlertCenter },
  { path: '/settings', component: CameraManager },
  { path: '/user', component: UserCenter }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 🚨 全局路由守卫 (看门大爷)
router.beforeEach((to, from, next) => {
  const token = sessionStorage.getItem('access_token');
  if (to.path !== '/login' && !token) {
    // 没登录且想去其它页面，直接打回登录页
    next('/login');
  } else if (to.path === '/login' && token) {
    // 已经登录了还来登录页，打回首页
    next('/');
  } else {
    next();
  }
})

export default router