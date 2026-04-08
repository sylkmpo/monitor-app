<template>
  <div class="manager-container">
    <h2>⚙️ 摄像头设备管理</h2>
    
    <div class="add-form" :class="{ 'edit-mode': isEditing }">
      <div class="form-title">{{ isEditing ? '📝 修改设备信息' : '➕ 添加新设备' }}</div>
      <div class="input-group">
        <input v-model="form.name" placeholder="名称 (选填)" />
        <input v-model="form.model" placeholder="型号 (选填)" />
        <input v-model="form.input_source" placeholder="* 视频源 (必填，如: 0 或 rtsp://...)" class="required-input" />
      </div>
      <div class="button-group">
        <button v-if="!isEditing" @click="submitCamera" class="add-btn">确认添加</button>
        <template v-else>
          <button @click="submitCamera" class="save-btn">保存修改</button>
          <button @click="cancelEdit" class="cancel-btn">取消</button>
        </template>
      </div>
    </div>

    <table class="cam-table">
      <thead>
        <tr>
          <th>ID</th><th>名称</th><th>型号</th><th>视频源</th><th>推流路径</th><th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="cam in cameras" :key="cam.id">
          <td>{{ cam.id }}</td>
          <td>{{ cam.name }}</td>
          <td>{{ cam.model || '-' }}</td>
          <td class="source-cell">{{ cam.input_source }}</td>
          <td>{{ cam.stream_path }}</td>
          <td class="actions">
            <button class="edit-btn" @click="startEdit(cam)">修改</button>
            <button class="delete-btn" @click="deleteCamera(cam.id)">删除</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import axios from 'axios';

const API_BASE = 'http://127.0.0.1:8000/api/cameras';
const cameras = ref([]);
const isEditing = ref(false);
const editingId = ref(null);

const form = ref({ name: '', model: '', input_source: '' });

const fetchCameras = async () => {
  const res = await axios.get(API_BASE);
  cameras.value = res.data;
};

// 启动编辑状态
const startEdit = (cam) => {
  isEditing.value = true;
  editingId.value = cam.id;
  form.value = { 
    name: cam.name, 
    model: cam.model, 
    input_source: cam.input_source 
  };
  window.scrollTo({ top: 0, behavior: 'smooth' });
};

const cancelEdit = () => {
  isEditing.value = false;
  editingId.value = null;
  form.value = { name: '', model: '', input_source: '' };
};

const submitCamera = async () => {
  if (!form.value.input_source) return alert('视频源不能为空！');

  try {
    if (isEditing.value) {
      // 执行修改
      await axios.put(`${API_BASE}/${editingId.value}`, form.value);
    } else {
      // 执行添加
      await axios.post(API_BASE, form.value);
    }
    cancelEdit();
    fetchCameras();
  } catch (err) {
    // 捕捉后端抛出的 400 错误（视频源已存在）
    if (err.response && err.response.data.detail) {
      alert(err.response.data.detail);
    } else {
      alert('操作失败，请检查网络或后端状态');
    }
  }
};

const deleteCamera = async (id) => {
  if (confirm('确认删除该摄像头吗？')) {
    await axios.delete(`${API_BASE}/${id}`);
    fetchCameras();
  }
};

onMounted(fetchCameras);
</script>

<style scoped>
.manager-container { padding: 24px; }
h2 { margin-top: 0; color: var(--text-main); }
.add-form { background: var(--bg-card); padding: 20px; border-radius: 8px; margin-bottom: 24px; border: 1px solid var(--border-color); box-shadow: var(--shadow); transition: 0.3s; }
.edit-mode { border-color: var(--warning); box-shadow: 0 0 0 1px var(--warning); }
.form-title { margin-bottom: 15px; font-weight: bold; color: var(--text-sub); font-size: 14px; }
.input-group { display: flex; gap: 10px; margin-bottom: 15px; }
.input-group input { flex: 1; padding: 12px; border-radius: 4px; border: 1px solid var(--border-color); background: var(--bg-input); color: var(--text-main); outline: none; transition: 0.3s; }
.input-group input:focus { border-color: var(--primary); }
.required-input { border-left: 4px solid var(--primary) !important; }
.button-group { display: flex; gap: 10px; }
.add-btn { background: var(--primary); color: white; border: none; padding: 10px 25px; border-radius: 4px; cursor: pointer; font-weight: bold; }
.save-btn { background: var(--warning); color: white; border: none; padding: 10px 25px; border-radius: 4px; cursor: pointer; font-weight: bold;}
.cancel-btn { background: var(--bg-body); color: var(--text-sub); border: 1px solid var(--border-color); padding: 10px 25px; border-radius: 4px; cursor: pointer; font-weight: bold;}
.cam-table { width: 100%; border-collapse: collapse; background: var(--bg-card); border-radius: 8px; overflow: hidden; box-shadow: var(--shadow); border: 1px solid var(--border-color); transition: 0.3s;}
.cam-table th { background: var(--hover-bg); color: var(--text-sub); font-weight: 600; border-bottom: 2px solid var(--border-color); }
.cam-table th, .cam-table td { padding: 14px 16px; text-align: left; border-bottom: 1px solid var(--border-color); color: var(--text-main); }
.actions { display: flex; gap: 8px; }
.edit-btn { background: var(--success); color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; }
.delete-btn { background: var(--danger); color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; }
.source-cell { max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-muted); }
</style>