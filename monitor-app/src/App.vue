<template>
  <MonitorDashboard />
</template>

<script setup>
// 告诉 Vue 从哪里引入这个组件
import MonitorDashboard from './components/MonitorDashboard.vue';
</script>

<style>
/* 消除浏览器自带的白边 */
body {
  margin: 0;
  padding: 0;
}
</style>