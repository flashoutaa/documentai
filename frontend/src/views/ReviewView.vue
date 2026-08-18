<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  batchUpdateSuggestions, createTask, exportTask, getTask,
  listDocuments, listSuggestions, listTemplates, updateSuggestion,
} from '../api'

const route = useRoute()
const docId = ref(Number(route.query.doc_id) || null)
const taskId = ref(Number(route.query.task_id) || null)
const documents = ref([])
const templates = ref([])

// —— 审查配置 ——
const reviewTypes = ref(['typo', 'format', 'term', 'polish'])
const overrideTemplateId = ref(null)
const typeOptions = [
  { value: 'typo', label: '错别字', color: 'danger' },
  { value: 'format', label: '格式错误', color: 'warning' },
  { value: 'term', label: '专有名词补齐', color: 'primary' },
  { value: 'polish', label: '句意优化', color: 'success' },
]

// —— 任务状态 ——
const task = ref(null)
const progress = ref(0)
const pollTimer = ref(null)

// —— 建议 ——
const suggestions = ref([])
const filterType = ref('')
const filterStatus = ref('')
const loadingSugs = ref(false)
const editing = ref(null) // 正在修改的建议
const editText = ref('')
const editDialogVisible = computed({
  get: () => !!editing.value,
  set: (v) => { if (!v) editing.value = null },
})

const currentDoc = computed(() => documents.value.find((d) => d.id === docId.value))

const typeLabel = (v) => typeOptions.find((t) => t.value === v)?.label || v
const typeColor = (v) => typeOptions.find((t) => t.value === v)?.color || 'info'
const statusLabel = { pending: '待处理', accepted: '已接受', rejected: '已拒绝', modified: '已修改' }
const statusColor = { pending: 'info', accepted: 'success', rejected: 'danger', modified: 'warning' }

const startReview = async () => {
  if (!docId.value) return
  const res = await createTask({
    document_id: docId.value,
    review_types: reviewTypes.value,
    template_id: overrideTemplateId.value || undefined,
  })
  taskId.value = res.data.id
  ElMessage.success('审查任务已创建，正在执行…')
  pollTask()
}

const pollTask = async () => {
  clearInterval(pollTimer.value)
  const tick = async () => {
    const res = await getTask(taskId.value)
    task.value = res.data
    progress.value = res.data.progress
    if (['completed', 'failed'].includes(res.data.status)) {
      clearInterval(pollTimer.value)
      if (res.data.status === 'completed') {
        ElMessage.success('审查完成')
        await loadSuggestions()
      } else {
        ElMessage.error(`审查失败：${res.data.error || '未知错误'}`)
      }
    }
  }
  await tick()
  pollTimer.value = setInterval(tick, 1200)
}

const loadSuggestions = async () => {
  loadingSugs.value = true
  try {
    const params = {}
    if (filterType.value) params.review_type = filterType.value
    if (filterStatus.value) params.status = filterStatus.value
    suggestions.value = (await listSuggestions(taskId.value, params)).data
  } finally {
    loadingSugs.value = false
  }
}

const filteredCount = computed(() => suggestions.value.length)

const accept = async (s) => {
  await updateSuggestion(s.id, { status: 'accepted' })
  s.status = 'accepted'
  ElMessage.success('已接受')
}
const reject = async (s) => {
  await updateSuggestion(s.id, { status: 'rejected' })
  s.status = 'rejected'
  ElMessage.success('已拒绝')
}
const openModify = (s) => {
  editing.value = s
  editText.value = s.suggested_text
}
const submitModify = async () => {
  if (!editText.value.trim()) return ElMessage.warning('修改内容不能为空')
  await updateSuggestion(editing.value.id, { status: 'modified', modified_text: editText.value })
  editing.value.status = 'modified'
  editing.value.modified_text = editText.value
  editing.value = null
  ElMessage.success('已保存自行修改')
}
const batchAccept = async () => {
  await ElMessageBox.confirm('将全部「待处理」建议标记为已接受？', '批量接受', { type: 'info' })
  const res = await batchUpdateSuggestions(taskId.value, { status: 'accepted' })
  ElMessage.success(`已批量接受 ${res.data.updated} 条`)
  loadSuggestions()
}
const doExport = async () => {
  await exportTask(taskId.value, `${currentDoc.value?.filename.replace(/\.docx$/i, '') || '文档'}_审查修订版.docx`)
  ElMessage.success('已导出修订版文档')
}

const finalText = (s) => (s.status === 'modified' ? s.modified_text : s.suggested_text)

onMounted(async () => {
  documents.value = (await listDocuments()).data
  templates.value = (await listTemplates()).data
  if (taskId.value) pollTask()
})
onBeforeUnmount(() => clearInterval(pollTimer.value))
</script>

<template>
  <div>
    <!-- 审查配置（无任务时） -->
    <el-card v-if="!taskId" shadow="never" class="mb">
      <template #header><b>发起审查</b></template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="文档">
          {{ currentDoc?.filename || `#${docId}` }}
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          {{ currentDoc?.status }}
        </el-descriptions-item>
      </el-descriptions>
      <el-form class="mt" label-width="100px">
        <el-form-item label="审查类型">
          <el-checkbox-group v-model="reviewTypes">
            <el-checkbox v-for="t in typeOptions" :key="t.value" :value="t.value">{{ t.label }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="格式规范">
          <el-select v-model="overrideTemplateId" placeholder="沿用文档模板 / 默认模板" clearable style="width: 320px">
            <el-option v-for="t in templates" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :disabled="!reviewTypes.length" @click="startReview">
            开始审查
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 任务进度（进行中） -->
    <el-card v-if="taskId && task && ['pending', 'running'].includes(task.status)" shadow="never" class="mb">
      <template #header><b>审查进行中</b></template>
      <el-progress :percentage="Math.round(progress)" :stroke-width="14" striped striped-flow />
      <div class="mt dim">
        审查类型：{{ task.review_types.map(typeLabel).join('、') }}　（页面可离开，任务在后台执行）
      </div>
    </el-card>

    <!-- 审查结果（完成后） -->
    <template v-if="taskId && task && ['completed', 'failed'].includes(task.status)">
      <el-alert v-if="task.status === 'failed'" type="error" :title="`审查失败：${task.error}`" class="mb" show-icon />

      <el-card v-if="task.status === 'completed'" shadow="never">
        <template #header>
          <div class="card-head">
            <b>审查结果 — {{ currentDoc?.filename }}</b>
            <div>
              <el-button size="small" @click="batchAccept">批量接受待处理</el-button>
              <el-button size="small" type="success" @click="doExport">导出修订版文档</el-button>
            </div>
          </div>
        </template>

        <div class="mb filters">
          <el-radio-group v-model="filterType" @change="loadSuggestions">
            <el-radio-button value="">全部类型</el-radio-button>
            <el-radio-button v-for="t in typeOptions" :key="t.value" :value="t.value">{{ t.label }}</el-radio-button>
          </el-radio-group>
          <el-radio-group v-model="filterStatus" @change="loadSuggestions" class="ml">
            <el-radio-button value="">全部状态</el-radio-button>
            <el-radio-button value="pending">待处理</el-radio-button>
            <el-radio-button value="accepted">已接受</el-radio-button>
            <el-radio-button value="rejected">已拒绝</el-radio-button>
            <el-radio-button value="modified">已修改</el-radio-button>
          </el-radio-group>
        </div>

        <el-empty v-if="!filteredCount" description="当前筛选下没有建议" />
        <el-table v-else :data="suggestions" v-loading="loadingSugs" row-key="id">
          <el-table-column label="类型" width="110">
            <template #default="{ row }">
              <el-tag :type="typeColor(row.review_type)" size="small">{{ typeLabel(row.review_type) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="原文" min-width="240">
            <template #default="{ row }">
              <div class="dim small mb">第 {{ row.doc_position?.paragraph_index + 1 }} 段</div>
              <div class="orig">{{ row.original_text || '（格式问题，见下方说明）' }}</div>
              <div v-if="row.reason" class="dim small">{{ row.reason }}</div>
            </template>
          </el-table-column>
          <el-table-column label="建议修改" min-width="240">
            <template #default="{ row }">
              <div class="sugg">{{ finalText(row) }}</div>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="statusColor[row.status]" size="small">{{ statusLabel[row.status] }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <template v-if="row.status === 'pending'">
                <el-button size="small" type="success" @click="accept(row)">接受</el-button>
                <el-button size="small" type="danger" plain @click="reject(row)">拒绝</el-button>
                <el-button size="small" @click="openModify(row)">修改</el-button>
              </template>
              <span v-else class="dim small">{{ statusLabel[row.status] }}</span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>

    <!-- 自行修改对话框 -->
    <el-dialog v-model="editDialogVisible" title="自行修改建议内容" width="560px">
      <div class="dim small mb">原文：{{ editing?.original_text }}</div>
      <el-input v-model="editText" type="textarea" :rows="4" placeholder="输入修改后的内容" />
      <template #footer>
        <el-button @click="editing = null">取消</el-button>
        <el-button type="primary" @click="submitModify">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.mb { margin-bottom: 16px; }
.mt { margin-top: 16px; }
.ml { margin-left: 16px; }
.dim { color: #909399; }
.small { font-size: 12px; }
.card-head { display: flex; justify-content: space-between; align-items: center; }
.filters { display: flex; align-items: center; }
.orig { color: #f56c6c; }
.sugg { color: #67c23a; }
</style>
