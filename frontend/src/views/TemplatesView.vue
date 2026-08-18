<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createTemplate, deleteTemplate, listTemplates, setDefaultTemplate, updateTemplate } from '../api'

const templates = ref([])
const dialogVisible = ref(false)
const editingId = ref(null)
const form = reactive({
  name: '',
  description: '',
  body: {
    font: '宋体',
    size_pt: 12,
    first_line_indent_chars: 2,
    line_spacing_pt: 28,
    alignment: 'justify',
  },
  headings: {
    1: { font: '黑体', size_pt: 16, alignment: 'center', bold: true },
    2: { font: '黑体', size_pt: 14, bold: true },
    3: { font: '黑体', size_pt: 12, bold: true },
  },
})

const alignOptions = [
  { value: 'justify', label: '两端对齐' },
  { value: 'left', label: '左对齐' },
  { value: 'center', label: '居中' },
  { value: 'right', label: '右对齐' },
]
const alignLabel = (v) => alignOptions.find((a) => a.value === v)?.label || v

const load = async () => { templates.value = (await listTemplates()).data }

const openCreate = () => {
  editingId.value = null
  Object.assign(form, {
    name: '', description: '',
    body: { font: '宋体', size_pt: 12, first_line_indent_chars: 2, line_spacing_pt: 28, alignment: 'justify' },
    headings: {
      1: { font: '黑体', size_pt: 16, alignment: 'center', bold: true },
      2: { font: '黑体', size_pt: 14, bold: true },
      3: { font: '黑体', size_pt: 12, bold: true },
    },
  })
  dialogVisible.value = true
}

const openEdit = (t) => {
  editingId.value = t.id
  Object.assign(form, {
    name: t.name,
    description: t.description || '',
    body: { ...t.content.body },
    headings: { ...(t.content.headings || {}) },
  })
  dialogVisible.value = true
}

const submit = async () => {
  if (!form.name) return ElMessage.warning('请输入模板名称')
  const payload = {
    name: form.name,
    description: form.description,
    content: { body: form.body, headings: form.headings },
  }
  if (editingId.value) {
    await updateTemplate(editingId.value, payload)
    ElMessage.success('已更新')
  } else {
    await createTemplate(payload)
    ElMessage.success('已创建')
  }
  dialogVisible.value = false
  load()
}

const setDefault = async (t) => {
  await setDefaultTemplate(t.id)
  ElMessage.success(`已将「${t.name}」设为默认`)
  load()
}

const onDelete = async (t) => {
  await ElMessageBox.confirm(`确认删除模板「${t.name}」？`, '删除确认', { type: 'warning' })
  await deleteTemplate(t.id)
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-head">
        <b>格式规范模板</b>
        <el-button type="primary" @click="openCreate">新建模板</el-button>
      </div>
    </template>

    <el-table :data="templates" stripe>
      <el-table-column prop="name" label="模板名称" min-width="180" />
      <el-table-column prop="description" label="说明" min-width="260" show-overflow-tooltip />
      <el-table-column label="默认" width="80">
        <template #default="{ row }">
          <el-tag v-if="row.is_default" type="success" size="small">默认</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="正文规则" min-width="300">
        <template #default="{ row }">
          <div class="dim small">
            {{ row.content.body.font || '—' }} / {{ row.content.body.size_pt || '—' }}pt /
            缩进 {{ row.content.body.first_line_indent_chars ?? '—' }}字符 /
            行距 {{ row.content.body.line_spacing_pt || row.content.body.line_spacing || '—' }} /
            {{ alignLabel(row.content.body.alignment) }}
          </div>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" :disabled="row.is_default" @click="setDefault(row)">设为默认</el-button>
          <el-button size="small" type="danger" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-dialog v-model="dialogVisible" :title="editingId ? '编辑模板' : '新建模板'" width="680px">
    <el-form label-width="110px">
      <el-form-item label="模板名称" required>
        <el-input v-model="form.name" placeholder="如：公司公文模板" />
      </el-form-item>
      <el-form-item label="说明">
        <el-input v-model="form.description" type="textarea" :rows="2" />
      </el-form-item>

      <el-divider content-position="left">正文规则</el-divider>
      <el-row :gutter="12">
        <el-col :span="8"><el-form-item label="字体"><el-input v-model="form.body.font" placeholder="宋体" /></el-form-item></el-col>
        <el-col :span="8"><el-form-item label="字号(pt)"><el-input-number v-model="form.body.size_pt" :min="5" :max="72" /></el-form-item></el-col>
        <el-col :span="8"><el-form-item label="首行缩进(字符)"><el-input-number v-model="form.body.first_line_indent_chars" :min="0" :max="10" /></el-form-item></el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :span="8"><el-form-item label="固定行距(磅)"><el-input-number v-model="form.body.line_spacing_pt" :min="0" :max="100" /></el-form-item></el-col>
        <el-col :span="8"><el-form-item label="对齐方式">
          <el-select v-model="form.body.alignment"><el-option v-for="a in alignOptions" :key="a.value" :label="a.label" :value="a.value" /></el-select>
        </el-form-item></el-col>
      </el-row>

      <el-divider content-position="left">标题规则（一级 / 二级 / 三级）</el-divider>
      <div v-for="lv in [1, 2, 3]" :key="lv" class="heading-row">
        <span class="heading-label">{{ lv }} 级标题：</span>
        <el-input v-model="form.headings[lv].font" placeholder="字体" style="width: 120px" />
        <el-input-number v-model="form.headings[lv].size_pt" :min="5" :max="72" size="small" />
        <el-select v-model="form.headings[lv].alignment" placeholder="对齐" style="width: 110px" clearable>
          <el-option v-for="a in alignOptions" :key="a.value" :label="a.label" :value="a.value" />
        </el-select>
        <el-checkbox v-model="form.headings[lv].bold">加粗</el-checkbox>
      </div>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.card-head { display: flex; justify-content: space-between; align-items: center; }
.heading-row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.heading-label { width: 90px; color: #606266; }
</style>
