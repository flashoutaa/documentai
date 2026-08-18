<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { deleteDocument, listDocuments, listTemplates, previewDocument, uploadDocument } from '../api'

const router = useRouter()
const documents = ref([])
const templates = ref([])
const templateId = ref(null)
const uploading = ref(false)

// —— 预览 ——
const previewVisible = ref(false)
const previewLoading = ref(false)
const previewData = ref(null)

const openPreview = async (doc) => {
  previewVisible.value = true
  previewLoading.value = true
  previewData.value = null
  try {
    previewData.value = (await previewDocument(doc.id)).data
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '预览失败')
    previewVisible.value = false
  } finally {
    previewLoading.value = false
  }
}

const load = async () => {
  documents.value = (await listDocuments()).data
}
const loadTemplates = async () => {
  templates.value = (await listTemplates()).data
}

const beforeUpload = (file) => {
  const ok = /\.docx$/i.test(file.name)
  if (!ok) ElMessage.error('仅支持 .docx 格式')
  return ok
}

const onUpload = async (options) => {
  uploading.value = true
  try {
    const res = await uploadDocument(options.file, templateId.value)
    ElMessage.success(`上传成功：${res.data.filename}`)
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '上传失败')
  } finally {
    uploading.value = false
  }
}

const goReview = (doc) => router.push({ path: '/review', query: { doc_id: doc.id } })

const onDelete = async (doc) => {
  await ElMessageBox.confirm(`确认删除「${doc.filename}」及其全部审查记录？`, '删除确认', { type: 'warning' })
  await deleteDocument(doc.id)
  ElMessage.success('已删除')
  load()
}

const statusMap = {
  uploaded: { label: '已上传', type: 'info' },
  parsed: { label: '已解析', type: 'primary' },
  reviewed: { label: '已审查', type: 'success' },
  failed: { label: '失败', type: 'danger' },
}

onMounted(() => {
  load()
  loadTemplates()
})
</script>

<template>
  <div>
    <el-card shadow="never" class="mb">
      <template #header><b>上传文档</b></template>
      <el-form inline>
        <el-form-item label="格式规范模板">
          <el-select v-model="templateId" placeholder="使用默认模板" clearable style="width: 260px">
            <el-option v-for="t in templates" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <el-upload
        drag
        :auto-upload="false"
        :show-file-list="false"
        :before-upload="beforeUpload"
        :http-request="onUpload"
        accept=".docx"
        :disabled="uploading"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">将 .docx 文件拖到此处，或 <em>点击上传</em></div>
        <template #tip>
          <div class="el-upload__tip">上传后选择审查类型与规范模板，进入审查结果页逐条确认（接受 / 拒绝 / 自行修改）</div>
        </template>
      </el-upload>
    </el-card>

    <el-card shadow="never">
      <template #header><b>文档列表</b></template>
      <el-table :data="documents" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="filename" label="文件名" min-width="260" show-overflow-tooltip>
          <template #default="{ row }">
            <el-link type="primary" @click="openPreview(row)">{{ row.filename }}</el-link>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusMap[row.status]?.type || 'info'">{{ statusMap[row.status]?.label || row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="模板" width="180">
          <template #default="{ row }">
            {{ templates.find((t) => t.id === row.template_id)?.name || '—' }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="上传时间" width="180">
          <template #default="{ row }">{{ new Date(row.created_at).toLocaleString() }}</template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openPreview(row)">预览</el-button>
            <el-button type="primary" size="small" @click="goReview(row)">开始审查</el-button>
            <el-button type="danger" size="small" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty>暂无文档，请先上传</template>
      </el-table>
    </el-card>

    <!-- 文档预览对话框 -->
    <el-dialog
      v-model="previewVisible"
      :title="previewData ? `文档预览 — ${previewData.filename}` : '文档预览'"
      width="720px"
      top="5vh"
    >
      <div v-loading="previewLoading" class="preview-wrap">
        <template v-if="previewData">
          <div class="preview-meta dim small mb">
            共 {{ previewData.paragraph_count }} 段 / {{ previewData.char_count }} 字
            （点击文件名或「预览」查看内容，开始审查请使用「开始审查」）
          </div>
          <div class="preview-body">
            <div
              v-for="p in previewData.paragraphs"
              :key="p.index"
              class="preview-para"
              :class="{
                heading: p.is_heading,
                empty: !p.text,
              }"
              :style="{
                '--para-size': p.size_pt ? p.size_pt + 'pt' : '14px',
                textAlign: p.alignment === 'center' ? 'center' : p.alignment === 'right' ? 'right' : 'justify',
              }"
            >
              <span class="para-no">{{ p.index + 1 }}</span>
              {{ p.text || '（空段落）' }}
              <span v-if="p.font || p.size_pt" class="para-meta dim small">
                {{ [p.font, p.size_pt ? p.size_pt + 'pt' : null].filter(Boolean).join(' / ') }}
              </span>
            </div>
          </div>
        </template>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.mb { margin-bottom: 16px; }
.dim { color: #909399; }
.small { font-size: 12px; }
.preview-wrap { min-height: 200px; }
.preview-body {
  max-height: 62vh;
  overflow-y: auto;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 12px 16px;
  background: #fff;
}
.preview-para {
  position: relative;
  padding: 4px 0 4px 34px;
  font-size: var(--para-size);
  line-height: 1.8;
  border-bottom: 1px dashed #f0f0f0;
}
.preview-para:last-child { border-bottom: none; }
.preview-para.heading { font-weight: 700; }
.preview-para.empty { color: #c0c4cc; }
.para-no {
  position: absolute;
  left: 0;
  top: 4px;
  width: 26px;
  color: #909399;
  font-size: 12px;
  text-align: right;
  user-select: none;
}
.para-meta { margin-left: 8px; }
</style>
