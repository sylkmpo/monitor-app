# 🛡️ 智能监控系统 (Intelligent Monitor System)

![System Status](https://img.shields.io/badge/status-active-brightgreen)
![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)
![Vue Version](https://img.shields.io/badge/vue-3.x-brightgreen.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

基于深度学习与 WebRTC 的智能视频监控系统。本系统结合了先进的目标检测算法（YOLO 系列）、高效的流媒体服务器 (MediaMTX)、高性能 Python 接口服务 (FastAPI) 以及现代化控制台前端 (Vue 3)。

---

## 📑 目录

- [✨ 核心特性](#-核心特性)
- [🏗️ 系统架构](#️-系统架构)
- [📁 目录结构](#-目录结构)
- [🚀 快速开始](#-快速开始)
  - [1. 环境依赖](#1-环境依赖)
  - [2. 硬件及摄像头准备](#2-硬件及摄像头准备)
  - [3. 一键启动](#3-一键启动)
- [🛠️ 模块说明](#️-模块说明)
  - [前端监控面板 (monitor-app)](#前端监控面板-monitor-app)
  - [AI 与接口服务 (yolov26)](#ai-与接口服务-yolov26)
  - [流媒体服务 (MediaMTX)](#流媒体服务-mediamtx)
- [📷 摄像头推流说明 (FFmpeg)](#-摄像头推流说明-ffmpeg)

---

## ✨ 核心特性

- **⚡ 极速流媒体转发**：集成 `MediaMTX` WebRTC/RTSP 服务器，实现低延迟的监控视频流传输。
- **🧠 智能目标检测**：内置基于 YOLO 框架的 AI 视觉分析服务，实时进行画面目标识别。
- **🚀 高性能后端 API**：使用 `FastAPI` 构建控制中心，处理前端请求和设备管理。
- **📱 现代监控终端**：基于 `Vue 3` 构建的响应式控制台，支持大屏监控、多路并发显示。
- **⚙️ 一键部署与启动**：提供 Windows 批处理脚本，轻松调起各个微服务。

---

## 🏗️ 系统架构

系统的主要四个工作流模块组成如下：

1. **视频流采集端**：通过 `FFmpeg` 调用 USB 摄像头或网络摄像头，将视频流推送至 RTSP 服务器。
2. **WebRTC/RTSP 服务器 (`MediaMTX`)**：负责流媒体的分发和协议转换。
3. **AI 视觉分析层 (`yolov26`)**：使用 Python 拉取视频流进行逐帧推理 (YOLO 模型)，并提供 FastAPI 控制接口。
4. **前端看板 (`monitor-app`)**：展示实时监控画面与 AI 分析结果。

---

## 📁 目录结构

```text
monitor-app/
├── monitor-app/              # Vue3 前端应用目录
│   ├── src/                  # 前端源码
│   ├── package.json          # 依赖配置
│   └── ...
├── yolov26/                  # 后端及 AI 算法目录
│   ├── api_server.py         # FastAPI 控制中心
│   ├── ai_server.py          # AI 视频分析服务
│   └── ...
├── mediamtx_v1.17.../        # MediaMTX 流媒体服务器 (需自行下载放入)
├── fix_ips.py                # 动态 IP 修正脚本
├── start.bat                 # 一键启动集成脚本
└── readme.md                 # 项目说明文件
```

---

## 🚀 快速开始

### 1. 环境依赖

在开始之前，请确保您的系统中已安装以下软件：

*   **Node.js**: (推荐 v16 以上) 用于运行 Vue 3 前端。
*   **Miniconda / Anaconda**: 用于管理 Python 虚拟环境。
*   **FFmpeg**: 用于推送本地摄像头视频流。

**Python 环境初始化:**
```bash
# 创建并激活 Conda 虚拟环境
conda create -n sta python=3.8
conda activate sta

# 进入算法目录并安装依赖 (具体依赖根据 requirements 安装)
cd yolov26
pip install -r requirements.txt
```

**前端环境初始化:**
```bash
cd monitor-app
npm install
```

### 2. 硬件及摄像头准备

如果您使用 USB 摄像头，需要提前运行 FFmpeg 命令向流媒体服务器推流。项目中提供了示例推流命令（根据您的设备名称修改 `video=` 后面的值）：

```bash
# 摄像头 1 (Camera Sensor Front)
ffmpeg -f dshow -rtbufsize 1024M -i video="Camera Sensor Front" -c:v libx264 -preset ultrafast -tune zerolatency -f rtsp rtsp://127.0.0.1:8554/camera1

# 摄像头 2 (1080P USB Camera)
ffmpeg -f dshow -rtbufsize 1024M -video_size 1280x720 -framerate 30 -i video="1080P USB Camera" -c:v libx264 -preset ultrafast -tune zerolatency -f rtsp rtsp://127.0.0.1:8554/camera2
```

### 3. 一键启动

在 Windows 环境下，直接双击运行项目根目录下的 **`start.bat`**。该脚本将自动为您按顺序执行以下四个步骤：

1. 启动 `MediaMTX` 流媒体服务器。
2. 启动 FastAPI 控制中心 (`api_server.py`)。
3. 启动 AI 推理服务 (`ai_server.py`)。
4. 启动 Vue 3 监控大屏 (`npm run dev`)。

启动成功后，浏览器会自动打开或请手动访问：[http://localhost:5173](http://localhost:5173)

---

## 🛠️ 模块说明

### 前端监控面板 (monitor-app)
*   基于 Vite + Vue 3 构建。
*   主要功能：多路视频源播放、WebRTC 流媒体渲染、AI 报警信息展示、设备在线状态监控。

### AI 与接口服务 (yolov26)
*   基于 PyTorch 和 FastAPI。
*   **`ai_server.py`**: 后台挂载的进程，负责从 RTSP 拉流、执行深度学习推理并可能将结果回推或保存。
*   **`api_server.py`**: 提供前后端分离所需的 RESTful 接口，处理登录、历史数据查询和参数配置。

### 流媒体服务 (MediaMTX)
*   一个开箱即用的轻量级流媒体服务器。
*   将后端的 RTSP/RTMP 流转化为前端可以直接低延迟播放的 WebRTC 格式流。

---

## 📷 摄像头推流说明 (FFmpeg)

当您需要在本地测试推流时，可通过控制台输入以下命令以将本地 USB 设备转换为网络流：

```bash
# 测试命令示例
ffmpeg -f dshow -i video="1080P USB Camera" -c:v libx264 -preset ultrafast -tune zerolatency -f rtsp rtsp://127.0.0.1:8555/mystream
```
*   `-preset ultrafast` & `-tune zerolatency`：最大限度降低编码延迟，非常适合监控场景。

---
*Developed & Maintained by [sylkmpo](https://github.com/sylkmpo).*