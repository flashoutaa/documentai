<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { listTasks } from '../api'

const router = useRouter()
const tasks = ref([])
const loading = ref(false)

const typeLabel = { typo: '错别字', format: '格式', term: '专有名词', polish: '句意优化' }
const typeColor = { typo: 'danger', format: 'warning', term: 'primary', polish: 'success' }
const statusLabel = { pending: '待执行', running: '执行中', completed: '已完成', failed: '失败' }
const statusType = { pending: 'info', running: 'warning', completed: 'success', failed: 'danger' }

const load = async () => {
  loading.value = true
  try {
    tasks.value = (await listTasks()).data
  } finally {
    loading.value = false
  }
}

const open = (t) => router.push({ path: '/review', query: { task_id: t.id } })

onMounted(load)
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-head">
        <b>审查结果</b>
        <el-button size="small" :loading="loading" @click="load">刷新</el-button>
      </div>
    </template>

    <el-table :data="tasks" stripe v-loading="loading" @row-click="open" class="clickable">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column label="文档" min-width="220" show-overflow-tooltip>
        <template #default="{ row }">
          <el-link type="primary" @click="open(row)">{{ row.filename || `#${row.document_id}` }}</el-link>
        </template>
      </el-table-column>
      <el-table-column label="审查类型" min-width="220">
        <template #default="{ row }">
          <el-tag
            v-for="t in row.review_types"
            :key="t"
            :type="typeColor[t] || 'info'"
            size="small"
            class="mr"
          >{{ typeLabel[t] || t }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="statusType[row.status]" size="small">{{ statusLabel[row.status] || row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="进度" width="150">
        <template #default="{ row }">
          <el-progress
            :percentage="Math.round(row.progress)"
            :status="row.status === 'failed' ? 'exception' : row.status === 'completed' ? 'success' : undefined"
            :stroke-width="10"
          />
        </template>
      </el-table-column>
      <el-table-column prop="suggestion_total" label="建议数" width="90" />
      <el-table-column label="创建时间" width="180">
        <template #default="{ row }">{{ new Date(row.created_at).toLocaleString() }}</template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" plain @click="open(row)">查看</el-button>
        </template>
      </el-table-column>
      <template #empty>暂无审查记录，请先在「文档审查」中上传并审查文档</template>
    </el-table>
  </el-card>
</template>

<style scoped>
.card-head { display: flex; justify-content: space-between; align-items: center; }
.mr { margin-right: 6px; }
:deep(.clickable .el-table__row) { cursor: pointer; }
</style>
