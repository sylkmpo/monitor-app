<template>
  <div class="user-center">
    <header class="header">
      <h1>👤 用户中心</h1>
    </header>

    <div class="content-wrapper">
      <!-- 基本信息卡片 -->
      <div class="card profile-card">
        <h3>基本信息</h3>
        <div class="profile-info">
          <div class="avatar-large">👨‍💻</div>
          <div class="info-text">
            <p><strong>登录账户：</strong> {{ username }}</p>
            <p><strong>账号角色：</strong> <span class="role-badge">{{ roleDisplay }}</span></p>
            <p><strong>系统状态：</strong> <span class="status-badge">正常运行</span></p>
          </div>
        </div>
      </div>

      <!-- 修改密码卡片 -->
      <div class="card password-card">
        <h3>🔑 修改登录密码</h3>
        <form @submit.prevent="submitPwdChange" class="pwd-form">
          <div class="form-group">
            <label>当前密码</label>
            <input v-model="pwdForm.old_password" type="password" placeholder="请输入当前密码验证身份" class="enterprise-input" required />
          </div>
          <div class="form-group">
            <label>新密码</label>
            <input v-model="pwdForm.new_password" type="password" placeholder="请输入新密码 (不少于6位)" class="enterprise-input" required minlength="6" />
          </div>
          <div class="form-group">
            <label>确认新密码</label>
            <input v-model="pwdForm.confirm_password" type="password" placeholder="请再次输入新密码" class="enterprise-input" required minlength="6" />
          </div>
          <div v-if="pwdError" class="error-msg">{{ pwdError }}</div>
          <div class="actions">
            <button type="submit" class="submit-btn" :disabled="isSubmitting">
              {{ isSubmitting ? '正在安全提交...' : '确认修改密码' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import axios from 'axios';
import { useRouter } from 'vue-router';

const router = useRouter();
const username = ref(sessionStorage.getItem('username') || '管理员');
const rawRole = sessionStorage.getItem('role');
const roleDisplay = computed(() => rawRole === 'admin' ? '系统超级管理员' : '普通操作员');

const pwdForm = ref({ old_password: "", new_password: "", confirm_password: "" });
const pwdError = ref("");
const isSubmitting = ref(false);

const submitPwdChange = async () => {
  pwdError.value = "";
  if (pwdForm.value.new_password !== pwdForm.value.confirm_password) {
    pwdError.value = "两次输入的新密码不一致，请重新输入";
    return;
  }
  
  try {
    isSubmitting.value = true;
    await axios.put('http://127.0.0.1:8000/api/users/me/password', {
      old_password: pwdForm.value.old_password,
      new_password: pwdForm.value.new_password
    });
    alert("密码修改成功！为了系统安全，请使用新密码重新登录。");
    // 踢下线机制
    sessionStorage.removeItem('access_token');
    sessionStorage.removeItem('username');
    sessionStorage.removeItem('role');
    router.push('/login');
  } catch (e) {
    pwdError.value = e.response?.data?.detail || "密码修改失败，请检查原密码是否正确";
  } finally {
    isSubmitting.value = false;
  }
};
</script>

<style scoped>
.user-center {
  padding: 30px;
}

.header {
  margin-bottom: 30px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header h1 {
  margin: 0;
  font-size: 24px;
  color: var(--text-main);
}

.content-wrapper {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 30px;
  align-items: start;
}

/* 企业级卡片设计 */
.card {
  background-color: var(--bg-card);
  border-radius: 12px;
  padding: 25px;
  border: 1px solid var(--border-color);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.card h3 {
  margin-top: 0;
  margin-bottom: 25px;
  color: var(--text-main);
  border-bottom: 2px solid var(--hover-bg);
  padding-bottom: 15px;
  font-size: 18px;
}

/* 左侧：基本信息 */
.profile-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.avatar-large {
  font-size: 60px;
  background: var(--bg-body);
  width: 100px;
  height: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  margin-bottom: 20px;
  border: 2px solid var(--border-color);
  box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}

.info-text p {
  color: var(--text-sub);
  margin: 12px 0;
  font-size: 15px;
}

.info-text strong {
  color: var(--text-main);
}

.role-badge {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: bold;
}

.status-badge {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: bold;
}

/* 右侧：密码表单 */
.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  font-weight: bold;
  margin-bottom: 10px;
  color: var(--text-main);
  font-size: 14px;
}

.enterprise-input {
  width: 100%;
  padding: 14px;
  background-color: var(--bg-body);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-main);
  box-sizing: border-box;
  font-size: 15px;
  transition: all 0.3s ease;
}

.enterprise-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
}

.error-msg {
  color: #ef4444;
  font-size: 14px;
  background: rgba(239, 68, 68, 0.1);
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 20px;
  border-left: 4px solid #ef4444;
}

.actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 30px;
}

.submit-btn {
  background: #3b82f6;
  color: white;
  border: none;
  padding: 12px 30px;
  border-radius: 8px;
  cursor: pointer;
  transition: 0.3s;
  font-size: 15px;
  font-weight: bold;
}

.submit-btn:hover:not(:disabled) {
  background: #2563eb;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
}

.submit-btn:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

/* 响应式设计：屏幕小的时候变成上下堆叠 */
@media (max-width: 1000px) {
  .content-wrapper {
    grid-template-columns: 1fr;
  }
}
</style>