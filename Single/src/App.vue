<template>
  <div class="app">
    <header class="header">
      <h1>单股分析</h1>
      <p class="subtitle">AI 驱动的智能股票分析，多维度评估投资价值与风险</p>
      <p class="subtitle disclaimer">本分析结论仅用于学习和验证AI股票分析技术，不构成投资建议。</p>
    </header>

    <main class="main">
      <section class="card form-card">

        <div class="form-grid">
          <div class="form-group">
            <label>股票代码</label>
            <input
              v-model="form.stockCode"
              type="text"
              placeholder="如：000001、AAPL、700"
              @keyup.enter="startAnalysis"
            />
          </div>
          <div class="form-group">
            <label>市场类型</label>
            <select v-model="form.market">
              <option value="A股">🇨🇳 A股</option>
              <option value="美股">🇺🇸 美股</option>
              <option value="港股">🇭🇰 港股</option>
            </select>
          </div>
          <div class="form-group">
            <label>分析日期</label>
            <input v-model="form.analysisDate" type="date" />
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>分析深度</label>
            <select v-model="form.researchDepth">
              <option :value="1">1级 - 快速分析 (2-5分钟)</option>
              <option :value="2">2级 - 基础分析 (3-6分钟)</option>
              <option :value="3">3级 - 标准分析 (4-8分钟，推荐)</option>
              <option :value="4">4级 - 深度分析 (6-11分钟)</option>
              <option :value="5">5级 - 全面分析 (8-16分钟)</option>
            </select>
          </div>
          <button
            class="btn btn-primary"
            :disabled="loading || submitting"
            @click="startAnalysis"
          >
            {{ submitting ? '提交中...' : '开始智能分析' }}
          </button>
        </div>
      </section>

      <section v-show="showProgress" class="card progress-card">
        <h3>分析进行中...</h3>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: progress + '%' }"></div>
        </div>
        <p class="progress-text">{{ progressMessage }}</p>
      </section>

      <section v-show="showResult" class="card result-card">
        <h3>📊 分析结果</h3>
        <div class="result-decision">
          <strong>分析倾向：</strong> {{ decisionText }}
          <template v-if="decisionReasoning">
            <br /><strong>分析依据：</strong> {{ decisionReasoning }}
          </template>
        </div>
        <div class="result-reports">
          <div class="report-tabs">
            <button
              v-for="(tab, i) in reportTabs"
              :key="tab.key"
              :class="['report-tab', { active: activeReportIndex === i }]"
              @click="activeReportIndex = i"
            >
              {{ tab.title }}
            </button>
          </div>
          <div v-if="reportTabs.length" class="report-content">
            {{ reportTabs[activeReportIndex]?.content || '暂无内容' }}
          </div>
          <p v-else class="no-reports">暂无详细报告</p>
        </div>
        <div class="result-actions">
          <button class="btn btn-primary" @click="reset">重新分析</button>
          <button class="btn btn-download" @click="downloadReport('pdf')" :disabled="downloading">
            {{ downloading === 'pdf' ? '生成中...' : '📥 下载 PDF' }}
          </button>
          <button class="btn btn-download" @click="downloadReport('markdown')" :disabled="downloading">
            {{ downloading === 'md' ? '生成中...' : '📝 下载 Markdown' }}
          </button>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

// 开发环境使用 .env.development 中的 VITE_API_BASE，避免 Vite 代理对 POST 的 405 问题
const API_BASE = import.meta.env.VITE_API_BASE || ''

const DEPTH_MAP = { 1: '快速', 2: '基础', 3: '标准', 4: '深度', 5: '全面' }
const REPORT_TITLES = {
  market_report: '📈 市场技术分析',
  fundamentals_report: '💰 基本面分析',
  news_report: '📰 新闻事件分析',
  research_team_decision: '🔬 研究经理分析',
  trader_investment_plan: '💼 交易员计划',
  risk_management_decision: '⚠️ 风险管理决策',
  final_trade_decision: '🎯 最终分析结果',
}

const form = ref({
  stockCode: '',
  market: 'A股',
  analysisDate: '',
  researchDepth: 3,
})

const loading = ref(false)
const submitting = ref(false)
const showProgress = ref(false)
const showResult = ref(false)
const progress = ref(0)
const progressMessage = ref('正在初始化...')
const resultData = ref(null)
const activeReportIndex = ref(0)
const currentTaskId = ref('')
const downloading = ref(false) // false | 'pdf' | 'md'

const token = computed(() =>
  localStorage.getItem('token') || localStorage.getItem('auth-token') || 'anonymous'
)

const headers = () => ({
  Authorization: 'Bearer ' + token.value,
  'Content-Type': 'application/json',
})

const decisionText = computed(() => {
  const d = resultData.value?.decision || {}
  return (
    d.analysis_view ||
    d.action ||
    resultData.value?.summary ||
    resultData.value?.recommendation ||
    '-'
  )
})

const decisionReasoning = computed(() => {
  return resultData.value?.decision?.reasoning || ''
})

const reportTabs = computed(() => {
  const reports = resultData.value?.reports || {}
  const keys = [
    'market_report',
    'fundamentals_report',
    'news_report',
    'research_team_decision',
    'trader_investment_plan',
    'risk_management_decision',
    'final_trade_decision',
  ]
  return keys
    .filter((k) => reports[k])
    .map((k) => {
      const v = reports[k]
      const content =
        typeof v === 'string' ? v : v?.content || v?.judge_decision || JSON.stringify(v)
      return { key: k, title: REPORT_TITLES[k] || k, content }
    })
})

function setDateToday() {
  const d = new Date()
  form.value.analysisDate = d.toISOString().slice(0, 10)
}

async function startAnalysis() {
  const code = form.value.stockCode.trim()
  if (!code) {
    alert('请输入股票代码')
    return
  }

  submitting.value = true
  showProgress.value = true
  showResult.value = false
  progress.value = 0
  progressMessage.value = '正在提交...'

  const payload = {
    symbol: code.toUpperCase(),
    stock_code: code.toUpperCase(),
    parameters: {
      market_type: form.value.market,
      analysis_date: form.value.analysisDate,
      research_depth: DEPTH_MAP[form.value.researchDepth] || '标准',
      selected_analysts: ['市场分析师', '基本面分析师', '新闻分析师'],
      include_sentiment: true,
      include_risk: true,
      language: 'zh-CN',
      quick_analysis_model: 'qwen-turbo',
      deep_analysis_model: 'qwen-max',
      engine: 'v2',
    },
  }

  try {
    const r = await fetch(API_BASE + '/api/analysis/single', {
      method: 'POST',
      headers: headers(),
      body: JSON.stringify(payload),
    })
    const data = await r.json()
    if (!data.success || !data.data?.task_id) {
      throw new Error(data.message || '提交失败')
    }
    pollTask(data.data.task_id)
  } catch (e) {
    alert('提交失败: ' + (e.message || e))
    submitting.value = false
    showProgress.value = false
  }
}

function pollTask(taskId) {
  submitting.value = false
  currentTaskId.value = taskId
  const timer = setInterval(async () => {
    try {
      const r = await fetch(API_BASE + `/api/analysis/tasks/${taskId}/status`, {
        headers: headers(),
      })
      const data = await r.json()
      const d = data.data || data

      if (d.progress !== undefined) progress.value = d.progress
      progressMessage.value =
        d.current_step_name || d.current_step_description || d.message || '分析进行中...'

      if (d.status === 'completed') {
        clearInterval(timer)
        showProgress.value = false
        await loadResult(taskId)
      } else if (d.status === 'failed') {
        clearInterval(timer)
        showProgress.value = false
        alert('分析失败: ' + (d.error_message || '未知错误'))
      }
    } catch (e) {
      console.error('轮询失败', e)
    }
  }, 3000)
}

async function loadResult(taskId) {
  try {
    const r = await fetch(API_BASE + `/api/analysis/tasks/${taskId}/result`, {
      headers: headers(),
    })
    const data = await r.json()
    resultData.value = data.data || data
    activeReportIndex.value = 0
    showResult.value = true
  } catch (e) {
    alert('加载结果失败: ' + (e.message || e))
  }
}

function reset() {
  showResult.value = false
  showProgress.value = false
  resultData.value = null
  currentTaskId.value = ''
}

async function downloadReport(format) {
  const reportId = currentTaskId.value || resultData.value?.analysis_id
  if (!reportId) {
    alert('无法获取报告 ID')
    return
  }

  downloading.value = format === 'pdf' ? 'pdf' : 'md'

  try {
    const url = API_BASE + `/api/reports/${reportId}/download?format=${format}`
    const r = await fetch(url, { headers: headers() })
    if (!r.ok) {
      const err = await r.json()
      throw new Error(err.detail || '下载失败')
    }
    const blob = await r.blob()
    const ext = format === 'pdf' ? 'pdf' : 'md'
    const stockCode = resultData.value?.stock_symbol || resultData.value?.stock_code || 'report'
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `${stockCode}_${reportId.slice(0, 8)}.${ext}`
    a.click()
    URL.revokeObjectURL(a.href)
  } catch (e) {
    alert('下载失败: ' + (e.message || e))
  } finally {
    downloading.value = false
  }
}

onMounted(setDateToday)
</script>

<style scoped>
.app {
  max-width: 920px;
  margin: 0 auto;
  padding: 32px 24px;
}

.header {
  margin-bottom: 32px;
  text-align: center;
}

.header h1 {
  font-size: 28px;
  font-weight: 600;
  margin: 0 0 8px 0;
  background: linear-gradient(90deg, #38bdf8, #818cf8);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.subtitle {
  color: #94a3b8;
  font-size: 15px;
  margin: 0;
}


.main {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.card {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 12px;
  padding: 24px;
  backdrop-filter: blur(8px);
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.form-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  align-items: flex-end;
}

.form-group {
  flex: 1;
  min-width: 160px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 14px;
  color: #94a3b8;
}

input,
select {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 8px;
  font-size: 14px;
  background: rgba(15, 23, 42, 0.6);
  color: #e2e8f0;
}

input:focus,
select:focus {
  outline: none;
  border-color: #38bdf8;
  box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.2);
}

.btn {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: linear-gradient(135deg, #38bdf8, #0ea5e9);
  color: #0f172a;
}

.btn-primary:hover:not(:disabled) {
  background: linear-gradient(135deg, #7dd3fc, #38bdf8);
  transform: translateY(-1px);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.progress-bar {
  height: 10px;
  background: rgba(15, 23, 42, 0.6);
  border-radius: 5px;
  overflow: hidden;
  margin: 16px 0;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #38bdf8, #818cf8);
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 14px;
  color: #94a3b8;
  margin: 8px 0 0 0;
}

.result-decision {
  padding: 16px;
  background: rgba(56, 189, 248, 0.1);
  border-radius: 8px;
  margin-bottom: 20px;
  border-left: 4px solid #38bdf8;
  line-height: 1.8;
}

.result-reports {
  margin-top: 16px;
}

.report-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.report-tab {
  padding: 8px 16px;
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 6px;
  background: rgba(15, 23, 42, 0.6);
  color: #94a3b8;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.report-tab:hover {
  border-color: #38bdf8;
  color: #e2e8f0;
}

.report-tab.active {
  background: rgba(56, 189, 248, 0.2);
  border-color: #38bdf8;
  color: #38bdf8;
}

.report-content {
  padding: 20px;
  background: rgba(15, 23, 42, 0.5);
  border-radius: 8px;
  line-height: 1.9;
  font-size: 14px;
  white-space: pre-wrap;
  max-height: 400px;
  overflow-y: auto;
}

.no-reports {
  color: #64748b;
  font-style: italic;
}

.result-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 20px;
}

.btn-download {
  background: rgba(56, 189, 248, 0.15);
  color: #38bdf8;
  border: 1px solid rgba(56, 189, 248, 0.4);
}

.btn-download:hover:not(:disabled) {
  background: rgba(56, 189, 248, 0.25);
  border-color: #38bdf8;
  transform: translateY(-1px);
}

.btn-download:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
