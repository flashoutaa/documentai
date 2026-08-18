import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'documents', component: () => import('../views/DocumentsView.vue'), meta: { title: '文档审查' } },
  { path: '/review', name: 'review', component: () => import('../views/ReviewView.vue'), meta: { title: '审查详情' } },
  { path: '/reviews', name: 'reviews', component: () => import('../views/ReviewsView.vue'), meta: { title: '审查结果' } },
  { path: '/templates', name: 'templates', component: () => import('../views/TemplatesView.vue'), meta: { title: '格式规范' } },
  { path: '/terms', name: 'terms', component: () => import('../views/TermsView.vue'), meta: { title: '专有名词库' } },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
