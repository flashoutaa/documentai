<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  batchUpdateSuggestions, createTask, exportTask, getReviewDetail, getTask,
  listDocuments, listTemplates, updateSuggestion,
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

// —— 审查详情（原文 + 建议）——
const reviewDetail = ref(null)
const loadingDetail = ref(false)
const filterType = ref('')
const filterStatus = ref('')
const selectedSugId = ref(null)
const editing = ref(null)
const editText = ref('')
const editDialogVisible = computed({
  get: () => !!editing.value,
  set: (v) => { if (!v) editing.value = null },
})
const paraEls = reactive({})
const sugEls = reactive({})

const currentDoc = computed(() => documents.value.find((d) => d.id === docId.value))
const typeLabel = (v) => typeOptions.find((t) => t.value === v)?.label || v
const typeColor = (v) => typeOptions.find((t) => t.value === v)?.color || 'info'
const statusLabel = { pending: '待处理', accepted: '已接受', rejected: '已拒绝', modified: '已修改' }
const statusColor = { pending: 'warning', accepted: 'success', rejected: 'info', modified: 'primary' }

// —— 建议过滤（本地过滤，原文标注保持完整）——
const filteredSuggestions = computed(() => {
  if (!reviewDetail.value) return []
  return reviewDetail.value.suggestions.filter((s) => {
    if (filterType.value && s.review_type !== filterType.value) return false
    if (filterStatus.value && s.status !== filterStatus.value) return false
    return true
  })
})

// —— 段落分段渲染：把建议内联到原文（重叠时最长区间优先，与导出规则一致）——
const segmentMap = computed(() => {
  const map = {}
  if (!reviewDetail.value) return map
  for (const p of reviewDetail.value.paragraphs) {
    const sugs = reviewDetail.value.suggestions.filter(
      (s) => s.paragraph_index === p.index && s.review_type !== 'format'
        && s.start != null && s.end != null
    )
    const sorted = [...sugs].sort(
      (a, b) => (b.end - b.start) - (a.end - a.start) || a.id - b.id
    )
    const chosen = []
    for (const s of sorted) {
      if (chosen.some((c) => !(s.end <= c.start || s.start >= c.end))) continue
      chosen.push(s)
    }
    chosen.sort((a, b) => a.start - b.start)
    const segments = []
    let cursor = 0
    for (const s of chosen) {
      if (s.start > cursor) segments.push({ type: 'plain', text: p.text.slice(cursor, s.start) })
      segments.push({ type: 'change', ...s })
      cursor = s.end
    }
    if (cursor < p.text.length) segments.push({ type: 'plain', text: p.text.slice(cursor) })
    const fmtSugs = reviewDetail.value.suggestions.filter(
      (s) => s.paragraph_index === p.index && s.review_type === 'format'
    )
    map[p.index] = { segments, fmtSugs }
  }
  return map
})

// —— 发起审查 / 轮询 ——
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
        await loadDetail()
      } else {
        ElMessage.error(`审查失败：${res.data.error || '未知错误'}`)
      }
    }
  }
  await tick()
  pollTimer.value = setInterval(tick, 1200)
}

const loadDetail = async () => {
  loadingDetail.value = true
  try {
    reviewDetail.value = (await getReviewDetail(taskId.value)).data
  } finally {
    loadingDetail.value = false
  }
}

// —— 建议操作 ——
const patchLocal = (id, patch) => {
  const s = reviewDetail.value?.suggestions.find((x) => x.id === id)
  if (s) Object.assign(s, patch)
}

const accept = async (s) => {
  await updateSuggestion(s.id, { status: 'accepted' })
  patchLocal(s.id, { status: 'accepted', modified_text: null })
  ElMessage.success('已接受')
}
const reject = async (s) => {
  await updateSuggestion(s.id, { status: 'rejected' })
  patchLocal(s.id, { status: 'rejected', modified_text: null })
  ElMessage.success('已拒绝')
}
const openModify = (s) => {
  editing.value = s
  editText.value = s.modified_text || s.suggested_text
}
const submitModify = async () => {
  if (!editText.value.trim()) return ElMessage.warning('修改内容不能为空')
  await updateSuggestion(editing.value.id, { status: 'modified', modified_text: editText.value })
  patchLocal(editing.value.id, { status: 'modified', modified_text: editText.value })
  editing.value = null
  ElMessage.success('已保存自行修改')
}
const batchAccept = async () => {
  await ElMessageBox.confirm('将全部「待处理」建议标记为已接受？', '批量接受', { type: 'info' })
  const res = await batchUpdateSuggestions(taskId.value, { status: 'accepted' })
  if (reviewDetail.value) {
    for (const s of reviewDetail.value.suggestions) {
      if (s.status === 'pending') { s.status = 'accepted'; s.modified_text = null }
    }
  }
  ElMessage.success(`已批量接受 ${res.data.updated} 条`)
}
const doExport = async () => {
  await exportTask(taskId.value, `${currentDoc.value?.filename.replace(/\.docx$/i, '') || '文档'}_审查修订版.docx`)
  ElMessage.success('已导出修订版文档')
}

// —— 定位联动：原文标注 ⇄ 建议列表 ——
const focusParagraph = (s) => {
  selectedSugId.value = s.id
  const el = paraEls[s.paragraph_index]
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  const sugEl = sugEls[s.id]
  if (sugEl) sugEl.scrollIntoView({ behavior: 'smooth', block: 'center' })
}
const focusSuggestion = (id) => {
  selectedSugId.value = id
  const sugEl = sugEls[id]
  if (sugEl) sugEl.scrollIntoView({ behavior: 'smooth', block: 'center' })
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
      <div class="mt dim small">
        审查类型：{{ task.review_types.map(typeLabel).join('、') }}　（页面可离开，任务在后台执行）
      </div>
    </el-card>

    <!-- 审查结果（完成后）：左原文内联标注 / 右建议操作 -->
    <template v-if="taskId && task && ['completed', 'failed'].includes(task.status)">
      <el-alert v-if="task.status === 'failed'" type="error" :title="`审查失败：${task.error}`" class="mb" show-icon />

      <div v-if="task.status === 'completed'" v-loading="loadingDetail">
        <div class="toolbar mb">
          <div class="legend">
            <span class="legend-item"><i class="dot st-pending" />待处理</span>
            <span class="legend-item"><i class="dot st-accepted" />已接受</span>
            <span class="legend-item"><i class="dot st-modified" />已修改</span>
            <span class="legend-item"><i class="dot st-rejected" />已拒绝</span>
            <span class="legend-item dim small">红色删除线 = 原文，绿色文字 = 建议修改</span>
          </div>
          <div>
            <el-button size="small" @click="batchAccept">批量接受待处理</el-button>
            <el-button size="small" type="success" @click="doExport">导出修订版文档</el-button>
          </div>
        </div>

        <div class="review-layout">
          <!-- 左：原文 + 内联标注 -->
          <div class="doc-panel">
            <div class="panel-head">原文 — {{ reviewDetail?.filename }}</div>
            <div class="doc-body">
              <div
                v-for="p in reviewDetail?.paragraphs || []"
                :key="p.index"
                :ref="(el) => { if (el) paraEls[p.index] = el }"
                class="doc-para"
                :class="{ heading: p.is_heading, empty: !p.text }"
              >
                <span class="para-no">{{ p.index + 1 }}</span>
                <template v-if="segmentMap[p.index]">
                  <template v-for="(seg, si) in segmentMap[p.index].segments" :key="si">
                    <span v-if="seg.type === 'plain'">{{ seg.text }}</span>
                    <span
                      v-else
                      class="mark"
                      :class="['st-' + seg.status, { selected: seg.id === selectedSugId }]"
                      :title="seg.reason"
                      @click.stop="focusSuggestion(seg.id)"
                    >
                      <s class="mark-orig">{{ seg.original_text }}</s>
                      <span v-if="seg.status !== 'rejected'" class="mark-arrow">→</span>
                      <span v-if="seg.status !== 'rejected'" class="mark-new">{{ finalText(seg) }}</span>
                    </span>
                  </template>
                </template>
                <span v-if="!p.text" class="dim">（空段落）</span>
                <!-- 段落级格式问题 -->
                <span
                  v-for="f in (segmentMap[p.index]?.fmtSugs || [])"
                  :key="f.id"
                  class="fmt-chip"
                  :class="{ selected: f.id === selectedSugId }"
                  @click.stop="focusSuggestion(f.id)"
                >
                  <el-tag size="small" type="warning" effect="plain">格式</el-tag>
                  <span class="fmt-text">{{ f.suggested_text }}</span>
                </span>
              </div>
            </div>
          </div>

          <!-- 右：建议操作列表 -->
          <div class="sug-panel">
            <div class="panel-head">
              <span>修改建议（{{ filteredSuggestions.length }}）</span>
              <div class="filters">
                <el-select v-model="filterType" size="small" style="width: 120px" @change="selectedSugId = null">
                  <el-option value="" label="全部类型" />
                  <el-option v-for="t in typeOptions" :key="t.value" :value="t.value" :label="t.label" />
                </el-select>
                <el-select v-model="filterStatus" size="small" style="width: 110px" class="ml" @change="selectedSugId = null">
                  <el-option value="" label="全部状态" />
                  <el-option v-for="(lbl, v) in statusLabel" :key="v" :value="v" :label="lbl" />
                </el-select>
              </div>
            </div>
            <div class="sug-list">
              <el-empty v-if="!filteredSuggestions.length" description="当前筛选下没有建议" :image-size="60" />
              <div
                v-for="s in filteredSuggestions"
                :key="s.id"
                :ref="(el) => { if (el) sugEls[s.id] = el }"
                class="sug-item"
                :class="{ selected: s.id === selectedSugId }"
                @click="focusParagraph(s)"
              >
                <div class="sug-head">
                  <el-tag :type="typeColor(s.review_type)" size="small">{{ typeLabel(s.review_type) }}</el-tag>
                  <el-tag :type="statusColor[s.status]" size="small" effect="light">{{ statusLabel[s.status] }}</el-tag>
                  <span class="dim small">第 {{ s.paragraph_index + 1 }} 段</span>
                </div>
                <div class="sug-orig">{{ s.original_text || '（格式问题，见下方说明）' }}</div>
                <div v-if="s.status !== 'rejected'" class="sug-new">→ {{ finalText(s) }}</div>
                <div v-if="s.reason" class="dim small sug-reason">{{ s.reason }}</div>
                <div class="sug-actions" @click.stop>
                  <template v-if="s.status === 'pending'">
                    <el-button size="small" type="success" @click="accept(s)">接受</el-button>
                    <el-button size="small" type="danger" plain @click="reject(s)">拒绝</el-button>
                    <el-button size="small" @click="openModify(s)">修改</el-button>
                  </template>
                  <el-button size="small" text type="primary" @click="focusParagraph(s)">定位</el-button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
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
.ml { margin-left: 8px; }
.dim { color: #909399; }
.small { font-size: 12px; }

.toolbar { display: flex; justify-content: space-between; align-items: center; }
.legend { display: flex; align-items: center; gap: 12px; }
.legend-item { display: inline-flex; align-items: center; gap: 4px; font-size: 12px; }
.dot { display: inline-block; width: 10px; height: 10px; border-radius: 2px; }

.review-layout { display: flex; gap: 16px; align-items: flex-start; }
.doc-panel { flex: 3; min-width: 0; }
.sug-panel { flex: 2; min-width: 320px; max-width: 480px; }
.panel-head {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 12px; background: #fff; border: 1px solid #e4e7ed; border-bottom: none;
  border-radius: 6px 6px 0 0; font-weight: 600;
}

/* 原文区 */
.doc-body {
  background: #fff; border: 1px solid #e4e7ed; border-radius: 0 0 6px 6px;
  padding: 16px 20px; max-height: 72vh; overflow-y: auto; line-height: 2;
}
.doc-para { position: relative; padding-left: 30px; margin-bottom: 4px; text-align: justify; }
.doc-para.heading { font-weight: 700; font-size: 16px; }
.para-no {
  position: absolute; left: 0; top: 2px; width: 24px; font-size: 12px;
  color: #c0c4cc; text-align: right; user-select: none;
}

/* 内联修改标注 */
.mark {
  border-radius: 3px; padding: 0 2px; cursor: pointer;
  transition: box-shadow .15s;
}
.mark:hover { box-shadow: 0 0 0 2px rgba(64, 158, 255, .35); }
.mark.selected { box-shadow: 0 0 0 2px #409eff; }
.mark-orig { color: #f56c6c; text-decoration: line-through; text-decoration-thickness: 1.5px; }
.mark-arrow { color: #909399; margin: 0 3px; font-style: normal; }
.mark-new { color: #67c23a; font-weight: 600; }
.st-pending { background: rgba(245, 108, 108, .12); }
.st-accepted { background: rgba(103, 194, 58, .15); }
.st-modified { background: rgba(64, 158, 255, .12); }
.st-rejected { background: rgba(144, 147, 153, .12); }
.st-rejected .mark-new, .st-rejected .mark-arrow { display: none; }

/* 段落级格式问题 */
.fmt-chip {
  display: inline-flex; align-items: center; gap: 4px; margin-left: 8px;
  border-radius: 3px; padding: 0 4px; cursor: pointer; background: rgba(230, 162, 60, .1);
}
.fmt-chip.selected { box-shadow: 0 0 0 2px #e6a23c; }
.fmt-text { font-size: 12px; color: #b88230; }

/* 建议列表 */
.sug-list { background: #fff; border: 1px solid #e4e7ed; border-radius: 0 0 6px 6px; max-height: 72vh; overflow-y: auto; }
.sug-item { padding: 10px 12px; border-bottom: 1px solid #f0f0f0; cursor: pointer; transition: background .15s; }
.sug-item:last-child { border-bottom: none; }
.sug-item:hover { background: #f5f7fa; }
.sug-item.selected { background: #ecf5ff; box-shadow: inset 3px 0 0 #409eff; }
.sug-head { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.sug-orig { color: #f56c6c; font-size: 13px; }
.sug-new { color: #67c23a; font-size: 13px; margin-top: 2px; }
.sug-reason { margin-top: 4px; }
.sug-actions { margin-top: 8px; }

@media (max-width: 1100px) {
  .review-layout { flex-direction: column; }
  .sug-panel { max-width: none; }
}
</style>
