<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createTerm, deleteTerm, importTerms, listTerms, updateTerm } from '../api'

const terms = ref([])
const dialogVisible = ref(false)
const editingId = ref(null)
const importVisible = ref(false)
const importText = ref('')
const form = reactive({ full_name: '', short_names: '', category: '' })

const load = async () => { terms.value = (await listTerms()).data }

const parseShortNames = (s) => s.split(/[,，;；\n]/).map((x) => x.trim()).filter(Boolean)

const openCreate = () => {
  editingId.value = null
  Object.assign(form, { full_name: '', short_names: '', category: '' })
  dialogVisible.value = true
}
const openEdit = (t) => {
  editingId.value = t.id
  Object.assign(form, {
    full_name: t.full_name,
    short_names: (t.short_names || []).join('，'),
    category: t.category || '',
  })
  dialogVisible.value = true
}

const submit = async () => {
  if (!form.full_name) return ElMessage.warning('请输入规范全称')
  const payload = {
    full_name: form.full_name,
    short_names: parseShortNames(form.short_names),
    category: form.category || null,
  }
  if (editingId.value) {
    await updateTerm(editingId.value, payload)
    ElMessage.success('已更新')
  } else {
    await createTerm(payload)
    ElMessage.success('已添加')
  }
  dialogVisible.value = false
  load()
}

const onDelete = async (t) => {
  await ElMessageBox.confirm(`确认删除「${t.full_name}」？`, '删除确认', { type: 'warning' })
  await deleteTerm(t.id)
  ElMessage.success('已删除')
  load()
}

const doImport = async () => {
  const lines = importText.value.split('\n').map((l) => l.trim()).filter(Boolean)
  const items = lines.map((line) => {
    // 格式：全称,简称1,简称2,...  或  全称|简称1|简称2
    const parts = line.split(/[,，|]/).map((x) => x.trim()).filter(Boolean)
    return { full_name: parts[0], short_names: parts.slice(1), category: null }
  })
  if (!items.length) return ElMessage.warning('没有可导入的词条')
  const res = await importTerms(items)
  ElMessage.success(`导入成功 ${res.data.imported} 条，跳过 ${res.data.skipped} 条`)
  importVisible.value = false
  importText.value = ''
  load()
}

onMounted(load)
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-head">
        <b>专有名词库（审查时自动补全为规范全称）</b>
        <div>
          <el-button @click="importVisible = true">批量导入</el-button>
          <el-button type="primary" @click="openCreate">新增词条</el-button>
        </div>
      </div>
    </template>

    <el-table :data="terms" stripe>
      <el-table-column prop="full_name" label="规范全称" min-width="240" />
      <el-table-column label="简称 / 不完整写法" min-width="260">
        <template #default="{ row }">
          <el-tag v-for="s in row.short_names || []" :key="s" size="small" class="mr">{{ s }}</el-tag>
          <span v-if="!(row.short_names || []).length" class="dim small">—</span>
        </template>
      </el-table-column>
      <el-table-column prop="category" label="分类" width="120" />
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-dialog v-model="dialogVisible" :title="editingId ? '编辑词条' : '新增词条'" width="520px">
    <el-form label-width="110px">
      <el-form-item label="规范全称" required>
        <el-input v-model="form.full_name" placeholder="如：中国特色社会主义" />
      </el-form-item>
      <el-form-item label="简称/写法">
        <el-input v-model="form.short_names" placeholder="多个用逗号分隔，如：特色社会主义，中特社" />
      </el-form-item>
      <el-form-item label="分类">
        <el-input v-model="form.category" placeholder="如：政治 / 政策 / 机构" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" @click="submit">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="importVisible" title="批量导入词条" width="560px">
    <div class="dim small mb">每行一个词条，第一列为规范全称，其余列为简称，逗号或竖线分隔，例如：</div>
    <div class="dim small mb">全面建设社会主义现代化国家,全面建设社会主义现代化</div>
    <el-input v-model="importText" type="textarea" :rows="8" placeholder="全称,简称1,简称2&#10;全称2,简称A" />
    <template #footer>
      <el-button @click="importVisible = false">取消</el-button>
      <el-button type="primary" @click="doImport">导入</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.card-head { display: flex; justify-content: space-between; align-items: center; }
.mr { margin-right: 6px; }
</style>
