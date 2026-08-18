import axios from 'axios'

const http = axios.create({ baseURL: '/api/v1', timeout: 60000 })

// ===== 文档 =====
export const listDocuments = () => http.get('/documents')
export const uploadDocument = (file, templateId) => {
  const fd = new FormData()
  fd.append('file', file)
  if (templateId) fd.append('template_id', templateId)
  return http.post('/documents/upload', fd)
}
export const deleteDocument = (id) => http.delete(`/documents/${id}`)
export const previewDocument = (id) => http.get(`/documents/${id}/preview`)

// ===== 格式规范模板 =====
export const listTemplates = () => http.get('/templates')
export const createTemplate = (data) => http.post('/templates', data)
export const updateTemplate = (id, data) => http.put(`/templates/${id}`, data)
export const deleteTemplate = (id) => http.delete(`/templates/${id}`)
export const setDefaultTemplate = (id) => http.post(`/templates/${id}/set-default`)

// ===== 专有名词库 =====
export const listTerms = () => http.get('/terms')
export const createTerm = (data) => http.post('/terms', data)
export const updateTerm = (id, data) => http.put(`/terms/${id}`, data)
export const deleteTerm = (id) => http.delete(`/terms/${id}`)
export const importTerms = (items) => http.post('/terms/import', { items })

// ===== 审查任务 =====
export const createTask = (data) => http.post('/tasks', data)
export const getTask = (id) => http.get(`/tasks/${id}`)
export const listTasks = () => http.get('/tasks')

// ===== 建议 =====
export const listSuggestions = (taskId, params) => http.get('/suggestions', { params: { task_id: taskId, ...params } })
export const updateSuggestion = (id, body) => http.patch(`/suggestions/${id}`, body)
export const batchUpdateSuggestions = (taskId, body) => http.post(`/suggestions/batch?task_id=${taskId}`, body)

// ===== 导出（下载修订版 docx）=====
export const exportTask = async (taskId, filename) => {
  const res = await http.post(`/tasks/${taskId}/export`, null, { responseType: 'blob' })
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url
  a.download = filename || `task_${taskId}_修订版.docx`
  a.click()
  URL.revokeObjectURL(url)
}
