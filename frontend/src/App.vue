<script setup>
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const active = () => route.path
const menus = [
  { path: '/', label: '文档审查' },
  { path: '/templates', label: '格式规范' },
  { path: '/terms', label: '专有名词库' },
]
</script>

<template>
  <el-container class="layout">
    <el-header class="header">
      <div class="brand">📄 Word 文档智能审查系统</div>
      <el-menu mode="horizontal" :default-active="active()" router :ellipsis="false" class="menu">
        <el-menu-item v-for="m in menus" :key="m.path" :index="m.path">{{ m.label }}</el-menu-item>
      </el-menu>
    </el-header>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>

<style>
body { margin: 0; background: #f5f7fa; }
.layout { min-height: 100vh; }
.header { display: flex; align-items: center; background: #fff; border-bottom: 1px solid #e4e7ed; }
.brand { font-size: 18px; font-weight: 600; margin-right: 40px; white-space: nowrap; }
.menu { flex: 1; border-bottom: none !important; }
</style>
