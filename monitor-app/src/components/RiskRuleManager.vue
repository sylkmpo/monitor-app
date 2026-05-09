<template>
  <div class="rules-page">
    <div class="page-header">
      <div>
        <h2>风险规则管理</h2>
        <p>为不同摄像头配置禁区入侵、越线、聚集、逗留和疑似倒地检测规则。</p>
      </div>
      <button class="refresh-btn" @click="refreshAll">刷新</button>
    </div>

    <div class="workspace">
      <section class="panel form-panel">
        <div class="panel-title">新增检测规则</div>

        <label class="field">
          <span>摄像头</span>
          <select v-model.number="selectedCameraId" @change="fetchRules">
            <option disabled :value="0">请选择摄像头</option>
            <option v-for="cam in cameras" :key="cam.id" :value="cam.id">
              {{ cam.name }} (#{{ cam.id }})
            </option>
          </select>
        </label>

        <label class="field">
          <span>规则类型</span>
          <select v-model="form.rule_type" @change="resetRuleDefaults">
            <option v-for="item in ruleTypes" :key="item.value" :value="item.value">
              {{ item.label }}
            </option>
          </select>
        </label>

        <label class="field">
          <span>规则名称</span>
          <input v-model="form.rule_name" placeholder="例如：仓库禁区入侵" />
        </label>

        <label class="field">
          <span>风险等级</span>
          <select v-model="form.risk_level">
            <option value="low">低</option>
            <option value="medium">中</option>
            <option value="high">高</option>
            <option value="critical">严重</option>
          </select>
        </label>

        <div class="rule-fields">
          <label class="field" v-if="needsRegion">
            <span>区域坐标 JSON</span>
            <textarea v-model="regionText" rows="5" spellcheck="false"></textarea>
          </label>

          <label class="field" v-if="form.rule_type === 'line_crossing'">
            <span>警戒线 JSON</span>
            <textarea v-model="lineText" rows="3" spellcheck="false"></textarea>
          </label>

          <label class="field" v-if="form.rule_type === 'line_crossing'">
            <span>方向</span>
            <select v-model="form.direction">
              <option value="any">任意方向</option>
              <option value="positive_to_negative">正侧到负侧</option>
              <option value="negative_to_positive">负侧到正侧</option>
            </select>
          </label>

          <label class="field" v-if="form.rule_type === 'crowding'">
            <span>人数阈值</span>
            <input v-model.number="form.person_threshold" type="number" min="2" />
          </label>

          <label class="field" v-if="form.rule_type === 'fall_suspected'">
            <span>宽高比阈值</span>
            <input v-model.number="form.aspect_ratio_threshold" type="number" min="1" step="0.1" />
          </label>

          <label class="field" v-if="usesDuration">
            <span>持续时间（秒）</span>
            <input v-model.number="form.duration_threshold" type="number" min="1" />
          </label>

          <label class="field">
            <span>冷却时间（秒）</span>
            <input v-model.number="form.cooldown_seconds" type="number" min="5" />
          </label>
        </div>

        <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>
        <button class="primary-btn" :disabled="!selectedCameraId || saving" @click="createRule">
          {{ saving ? '保存中...' : '保存规则' }}
        </button>
      </section>

      <section class="panel list-panel">
        <div class="panel-title">当前摄像头规则</div>

        <div v-if="!selectedCameraId" class="empty-state">请选择左侧摄像头。</div>
        <div v-else-if="rules.length === 0" class="empty-state">当前摄像头暂无自定义规则，将使用默认聚集和疑似倒地检测。</div>

        <div v-for="rule in rules" :key="rule.id" class="rule-card">
          <div class="rule-main">
            <div>
              <div class="rule-name">{{ rule.rule_name }}</div>
              <div class="rule-meta">
                {{ getRuleLabel(rule.rule_type) }} / {{ riskLabel(rule.risk_level) }} / {{ rule.enabled ? '启用' : '停用' }}
              </div>
            </div>
            <span class="status-pill" :class="{ disabled: !rule.enabled }">{{ rule.enabled ? 'ON' : 'OFF' }}</span>
          </div>

          <pre class="config-view">{{ formatConfig(rule.config) }}</pre>

          <div class="card-actions">
            <button class="ghost-btn" @click="toggleRule(rule)">
              {{ rule.enabled ? '停用' : '启用' }}
            </button>
            <button class="danger-btn" @click="deleteRule(rule.id)">删除</button>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import axios from 'axios';

const API_BASE = `http://${window.location.hostname}:8000/api`;

const cameras = ref([]);
const rules = ref([]);
const selectedCameraId = ref(0);
const saving = ref(false);
const errorMsg = ref('');

const ruleTypes = [
  { value: 'intrusion', label: '禁区入侵' },
  { value: 'line_crossing', label: '越线检测' },
  { value: 'crowding', label: '人员聚集' },
  { value: 'loitering', label: '长时间逗留' },
  { value: 'fall_suspected', label: '疑似倒地' }
];

const form = ref({
  rule_type: 'intrusion',
  rule_name: '禁区入侵',
  risk_level: 'high',
  direction: 'any',
  person_threshold: 3,
  duration_threshold: 2,
  aspect_ratio_threshold: 1.3,
  cooldown_seconds: 30
});

const regionText = ref('[[120,80],[600,80],[600,420],[120,420]]');
const lineText = ref('[[300,100],[300,600]]');

const needsRegion = computed(() => ['intrusion', 'crowding', 'loitering'].includes(form.value.rule_type));
const usesDuration = computed(() => ['intrusion', 'crowding', 'loitering', 'fall_suspected'].includes(form.value.rule_type));

const fetchCameras = async () => {
  const res = await axios.get(`${API_BASE}/cameras`);
  cameras.value = res.data;
  if (!selectedCameraId.value && cameras.value.length > 0) {
    selectedCameraId.value = cameras.value[0].id;
    await fetchRules();
  }
};

const fetchRules = async () => {
  if (!selectedCameraId.value) return;
  const res = await axios.get(`${API_BASE}/cameras/${selectedCameraId.value}/rules`);
  rules.value = res.data;
};

const refreshAll = async () => {
  await fetchCameras();
  await fetchRules();
};

const resetRuleDefaults = () => {
  const current = ruleTypes.find(item => item.value === form.value.rule_type);
  form.value.rule_name = current?.label || form.value.rule_type;
  form.value.risk_level = form.value.rule_type === 'fall_suspected' || form.value.rule_type === 'intrusion' ? 'high' : 'medium';
  form.value.duration_threshold = form.value.rule_type === 'loitering' ? 30 : 2;
  errorMsg.value = '';
};

const parseJsonField = (text, label) => {
  try {
    return JSON.parse(text);
  } catch (err) {
    throw new Error(`${label} 不是合法 JSON`);
  }
};

const buildConfig = () => {
  const type = form.value.rule_type;
  const config = {
    cooldown_seconds: Number(form.value.cooldown_seconds) || 30
  };

  if (needsRegion.value) {
    config.region = parseJsonField(regionText.value, '区域坐标');
    config.region_name = form.value.rule_name;
  }

  if (type === 'line_crossing') {
    config.line = parseJsonField(lineText.value, '警戒线');
    config.direction = form.value.direction;
  }

  if (type === 'intrusion') {
    config.min_duration = Number(form.value.duration_threshold) || 2;
  }

  if (type === 'crowding') {
    config.person_threshold = Number(form.value.person_threshold) || 3;
    config.duration_threshold = Number(form.value.duration_threshold) || 3;
  }

  if (type === 'loitering') {
    config.duration_threshold = Number(form.value.duration_threshold) || 30;
  }

  if (type === 'fall_suspected') {
    config.aspect_ratio_threshold = Number(form.value.aspect_ratio_threshold) || 1.3;
    config.duration_threshold = Number(form.value.duration_threshold) || 2;
  }

  return config;
};

const createRule = async () => {
  errorMsg.value = '';
  saving.value = true;
  try {
    await axios.post(`${API_BASE}/cameras/${selectedCameraId.value}/rules`, {
      rule_type: form.value.rule_type,
      rule_name: form.value.rule_name,
      risk_level: form.value.risk_level,
      enabled: true,
      config: buildConfig()
    });
    await fetchRules();
  } catch (err) {
    errorMsg.value = err.message || err.response?.data?.detail || '规则保存失败';
  } finally {
    saving.value = false;
  }
};

const toggleRule = async (rule) => {
  await axios.put(`${API_BASE}/rules/${rule.id}`, {
    rule_type: rule.rule_type,
    rule_name: rule.rule_name,
    risk_level: rule.risk_level,
    enabled: !rule.enabled,
    config: rule.config || {}
  });
  await fetchRules();
};

const deleteRule = async (id) => {
  if (!confirm('确定删除这条风险规则吗？')) return;
  await axios.delete(`${API_BASE}/rules/${id}`);
  await fetchRules();
};

const getRuleLabel = (type) => ruleTypes.find(item => item.value === type)?.label || type;
const riskLabel = (level) => ({ low: '低风险', medium: '中风险', high: '高风险', critical: '严重风险' }[level] || level);
const formatConfig = (config) => JSON.stringify(config || {}, null, 2);

onMounted(fetchCameras);
</script>

<style scoped>
.rules-page {
  padding: 28px 32px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.page-header h2 {
  margin: 0 0 8px;
  font-size: 24px;
  font-weight: 800;
  color: var(--text-main);
}

.page-header p {
  margin: 0;
  color: var(--text-sub);
  font-size: 14px;
}

.workspace {
  display: grid;
  grid-template-columns: minmax(320px, 420px) 1fr;
  gap: 24px;
  align-items: start;
}

.panel {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  box-shadow: var(--shadow-soft);
}

.form-panel {
  padding: 22px;
}

.list-panel {
  padding: 22px;
}

.panel-title {
  font-size: 17px;
  font-weight: 800;
  margin-bottom: 18px;
  color: var(--text-main);
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
  color: var(--text-sub);
  font-size: 14px;
  font-weight: 700;
}

.field input,
.field select,
.field textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--border-color);
  background: var(--bg-input);
  color: var(--text-main);
  border-radius: 6px;
  padding: 10px 12px;
  font-size: 14px;
  outline: none;
}

.field textarea {
  resize: vertical;
  font-family: Consolas, monospace;
  line-height: 1.45;
}

.field input:focus,
.field select:focus,
.field textarea:focus {
  border-color: var(--primary);
}

.primary-btn,
.refresh-btn,
.ghost-btn,
.danger-btn {
  border: none;
  border-radius: 6px;
  padding: 10px 16px;
  cursor: pointer;
  font-weight: 700;
}

.primary-btn {
  width: 100%;
  background: var(--primary);
  color: #fff;
}

.primary-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.refresh-btn,
.ghost-btn {
  background: var(--bg-card);
  color: var(--text-main);
  border: 1px solid var(--border-color);
}

.danger-btn {
  background: rgba(239, 68, 68, 0.12);
  color: var(--danger);
  border: 1px solid rgba(239, 68, 68, 0.28);
}

.error-msg {
  margin-bottom: 14px;
  padding: 10px 12px;
  border-radius: 6px;
  color: var(--danger);
  background: rgba(239, 68, 68, 0.1);
  font-size: 13px;
}

.empty-state {
  color: var(--text-muted);
  border: 1px dashed var(--border-color);
  border-radius: 8px;
  padding: 28px;
  text-align: center;
}

.rule-card {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 14px;
  background: var(--bg-elevated);
}

.rule-main {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: center;
}

.rule-name {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
}

.rule-meta {
  color: var(--text-sub);
  font-size: 13px;
  margin-top: 6px;
}

.status-pill {
  min-width: 48px;
  text-align: center;
  border-radius: 999px;
  padding: 4px 10px;
  color: #047857;
  background: rgba(16, 185, 129, 0.14);
  font-size: 12px;
  font-weight: 800;
}

.status-pill.disabled {
  color: var(--text-muted);
  background: var(--hover-bg);
}

.config-view {
  margin: 14px 0;
  max-height: 180px;
  overflow: auto;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 12px;
  color: var(--text-sub);
  font-size: 12px;
  line-height: 1.5;
}

.card-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

@media (max-width: 1000px) {
  .rules-page {
    padding: 22px;
  }

  .workspace {
    grid-template-columns: 1fr;
  }
}
</style>
