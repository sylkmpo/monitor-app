`rtsp2web` 的核心工作原理是**接收 RTSP 视频流，并将其转换为前端可直接播放的格式**（如 jsmpeg 或 flv）。

如果你的摄像头连接在服务器上，具体怎么做取决于你的摄像头类型。通常分为以下两种情况：

### 情况一：网络摄像头（IP Camera，如海康、大华等）

如果你的摄像头是自带网络接口的安防摄像头，通过网线连接到服务器所在的局域网，那么这类摄像头本身就支持输出 RTSP 流。

**做法：**

1. **获取摄像头的 RTSP 地址**：通常格式类似于 `rtsp://[账号]:[密码]@[IP地址]:554/h264/ch1/main/av_stream`（具体格式请参考你所用摄像头品牌的说明书）。
2. **在前端代码中替换 URL**：把你获取到的 RTSP 地址直接替换掉前端代码中的测试视频源即可。

JavaScript

```
// 把这里的地址换成你服务器局域网内的网络摄像头 RTSP 地址
var rtsp1 = 'rtsp://admin:yourpassword@192.168.1.100:554/stream'; 

window.onload = () => {
  new JSMpeg.Player('ws://localhost:9999/rtsp?url=' + btoa(rtsp1), {
    canvas: document.getElementById('canvas-1')
  });
}
```

------

### 情况二：USB 摄像头（直接插在服务器上的物理摄像头）

如果你的摄像头是直接通过 USB 接口插在服务器上的（例如笔记本自带的摄像头，或外接的免驱 USB 摄像头），它本身并不提供 RTSP 流。因为 `rtsp2web` 必须接收 RTSP 地址，你需要先**把 USB 摄像头画面推流成 RTSP 格式**。

**做法（需要两步）：**

**第一步：将 USB 摄像头转换为 RTSP 流**

你需要借助其他工具（例如 `mediamtx` 或 `VLC` 或 `FFmpeg` 命令行）在服务器上搭建一个简单的本地 RTSP 流。

以 `FFmpeg` 和 `mediamtx` 为例：

1. 下载开源的轻量级 RTSP 服务器软件 `mediamtx`（原名 rtsp-simple-server），双击运行它（它默认会在 `8554` 端口开启流媒体服务）。

2. 使用 FFmpeg 将 USB 摄像头推流到本地（Windows 下通常使用 `dshow`）：

   Bash

   ```
   # 查看你的 USB 摄像头名称
   ffmpeg -list_devices true -f dshow -i dummy
   
   # 假设你的摄像头名字叫 "USB Camera"，将它推流到本地 RTSP
   ffmpeg -f dshow -i video="USB Camera" -c:v libx264 -preset ultrafast -tune zerolatency -f rtsp rtsp://127.0.0.1:8554/mystream
   ```

   此时，你的 USB 摄像头就有了一个 RTSP 地址：`rtsp://127.0.0.1:8554/mystream`。

**第二步：使用 rtsp2web 播放**

现在你已经有 RTSP 地址了，流程就和情况一完全一样了。在你的前端代码中填入刚刚本地生成的 RTSP 链接：

JavaScript

```
var rtsp1 = 'rtsp://127.0.0.1:8554/mystream'; // 填入第一步生成的本地 RTSP 地址

window.onload = () => {
  new JSMpeg.Player('ws://localhost:9999/rtsp?url=' + btoa(rtsp1), {
    canvas: document.getElementById('canvas-1')
  });
}
```





没问题！因为你用的是直接插在电脑上的 USB 摄像头，我们需要借助一个中间工具把它变成“网络摄像头”。

整个过程你最终需要保持 **3个黑框框（命令行窗口）** 同时运行。下面是在 Windows 11 上的具体保姆级操作步骤：

### 准备工作：下载 MediaMTX (轻量级 RTSP 服务器)

1. 打开浏览器，访问 MediaMTX 的官方发布页：`https://github.com/bluenviron/mediamtx/releases`
2. 找到最新的版本，下载 Windows 的压缩包（通常名字叫 `mediamtx_vX.X.X_windows_amd64.zip`）。
3. 下载后解压到一个文件夹里。

------

### 第一步：启动本地 RTSP 服务器 (第 1 个黑框框)

1. 进入你刚刚解压的 `mediamtx` 文件夹。
2. 双击运行里面的 `mediamtx.exe`。
3. 会弹出一个黑色的命令行窗口，里面会显示 `[RTSP] listener opened on :8554` 之类的日志。
4. **不要关掉它，把它最小化放在一边。** （此时你的电脑已经具备了接收 RTSP 视频流的能力）。

------

### 第二步：获取你的 USB 摄像头名称

1. 按下键盘上的 `Win + R` 键，输入 `cmd` 然后回车，打开一个新的命令行窗口。

2. 在里面复制粘贴并运行这行命令：

   Bash

   ```
   ffmpeg -list_devices true -f dshow -i dummy
   ```

3. 这时屏幕上会打印一堆红白相间的文字。往上翻一翻，找到 `[dshow @ xxxx] DirectShow video devices` 这一行下面的内容。

4. 你会看到类似这样的字眼：

   `[dshow @ xxxx]  "USB Video Device"`  或者 `"Integrated Camera"`

   **把引号里的名字（例如 `USB Video Device`）准确地记下来。**

------

### 第三步：将摄像头画面推送到本地服务器 (第 2 个黑框框)

1. 还是在刚才那个 CMD 窗口里（或者新建一个也可以），把你刚才记下来的名字替换到下面的命令中（注意保留英文双引号）：

   Bash

   ```
   ffmpeg -f dshow -i video="Camera Sensor Front" -c:v libx264 -preset ultrafast -tune zerolatency -f rtsp rtsp://127.0.0.1:8555/mystream
   ```

   *举个例子：如果你的设备叫 `USB Video Device`，命令就是：*

   `ffmpeg -f dshow -i video="USB Video Device" -c:v libx264 -preset ultrafast -tune zerolatency -f rtsp rtsp://127.0.0.1:8554/mystream`

2. 敲回车运行。

3. 这时你会看到屏幕上开始不断跳动 `frame=  123 fps= 30 q=...` 这样的数据，这说明你的摄像头已经成功开启，并且正在持续发送画面！

4. **同样，不要关掉这个窗口，把它最小化。** （如果你关了，摄像头就停了）。

------

### 第四步：启动 rtsp2web 服务 (第 3 个黑框框)

这步就是你之前做过的：

1. 打开一个新的 CMD 窗口，`cd` 进入你之前创建的 `rtsp_server` 文件夹。

2. 确保你的 `main.js` 里写了 `transportType: 'tcp'` （为了更稳定）。

3. 运行命令启动服务：

   Bash

   ```
   node main.js
   ```

4. **保持这个窗口运行。**

------

### 第五步：修改前端代码并观看

1. 用记事本或代码编辑器打开你的那个 `index.html` 测试文件。

2. 把 RTSP 地址换成你刚才本地生成的地址：

   JavaScript

   ```
   var rtsp1 = 'rtsp://127.0.0.1:8554/mystream'; // 换成这个
   
   window.onload = () => {
     new JSMpeg.Player('ws://localhost:9999/rtsp?url=' + btoa(rtsp1), {
       canvas: document.getElementById('canvas-1')
     });
   }
   ```

3. 保存 HTML 文件，然后在浏览器中双击打开它。

4. 等待一两秒钟，你就能在网页上看到你自己 USB 摄像头的实时画面了！

**总结一下：**

此时你电脑后台应该有：**MediaMTX进程**（管接收流的） + **FFmpeg进程**（管摄像头的） + **Node进程**（管 rtsp2web 转发的）。这三个必须同时开着，你的网页才能看到画面。测试完后，把这三个黑框框全部按叉关掉即可。



Camera Sensor Front

ffmpeg -f dshow -i video="1080P USB Camera" -c:v libx264 -preset ultrafast -tune zerolatency -f rtsp rtsp://127.0.0.1:8555/mystream



ffmpeg -f dshow -rtbufsize 1024M -i video="Camera Sensor Front" -c:v libx264 -preset ultrafast -tune zerolatency -f rtsp rtsp://127.0.0.1:8554/camera1



ffmpeg -f dshow -rtbufsize 1024M -video_size 1280x720 -framerate 30 -i video="1080P USB Camera" -c:v libx264 -preset ultrafast -tune zerolatency -f rtsp rtsp://127.0.0.1:8554/camera2





根据提供的项目文件，`rtsp2web` 是一个在 Web 页面中直接播放 RTSP 视频流的解决方案。它的架构、技术栈以及实时速率分析如下：

### 一、 架构与技术栈分析

该项目采用的是“后端转码 + WebSocket 传输 + 前端解码播放”的整体架构。具体采用的技术如下：

**1. 后端服务与核心引擎：**

- **Node.js**：`rtsp2web` 本质上是一个 `Node.js` 包，作为服务端运行。
- **FFmpeg**：这是项目的核心转码引擎。项目通过依赖 `fluent-ffmpeg` 包在 Node.js 中调用系统的 FFmpeg 程序，负责将 RTSP 视频流转换并重新封装为前端可用的格式。
- **WebSocket (`ws`)**：项目依赖了 `ws` 包，通过 WebSocket（或 WSS 协议）建立服务端与前端页面之间的长连接，用来实时推送转码后的二进制视频流数据。
- **进程管理（可选）**：可以使用 `pm2` 这类进程管理工具来启动和管理转码服务。

**2. 前端播放器与解码技术：**

前端主要支持两种技术栈来接收并播放 WebSocket 传来的流数据：

- **`jsmpeg.js`（默认方案）**：在页面中使用 `<canvas>` 容器进行画面渲染。`jsmpeg.js` 采用的是软解码方式，它要求后端的流必须转码为 mpeg1 格式的视频和 mp2 格式的音频。
- **`flv.js`（可选方案）**：在页面中使用 HTML5 原生的 `<video>` 标签渲染。`flv.js` 会通过原生的 JS 去解码接收到的 FLV 数据（通常包含 H.264 视频和 AAC/MP3 音频），然后再通过 HTML5 提供的 Media Source Extensions (MSE) API 喂给原生 Video 标签进行播放。

**3. 项目开发与构建工具：**

- 源码的打包编译使用了 `rollup`，并且使用了 Babel (`@babel/core`, `@babel/preset-env` 等) 来处理 JavaScript 的语法转换。

### 二、 实时速率分析

根据官方文档的描述，`rtsp2web` 具有极低的延迟特性：

- 文档中明确指出该工具的特点是：“延时非常低，视频流稳定，几乎是实时的，满足任何需求”。
- 它通过 FFmpeg 转码并直接通过 WebSocket 持续推流到内存/缓冲区进行软解码（如使用 jsmpeg）或利用 MSE（如使用 flv.js），这种直接流转机制省略了传统 HLS 的切片生成时间，因此能够实现接近实时的视频播放效果。



在这种架构下，AI 分析在服务器端完成，`rtsp2web` 仅负责展示处理后的结果画面。

1. **获取原始流与 AI 推理：** 使用 Python 编写 YOLOv8 脚本（结合 OpenCV）。通过 Python 直接拉取摄像头的原始 RTSP 流，并逐帧输入给 YOLOv8 模型进行目标检测、人体姿态估计或行为分析。
2. **绘制结果与重新推流：** Python 脚本将 YOLOv8 的分析结果（如识别框、行为标签）绘制在视频帧上。然后，利用 FFmpeg 或 OpenCV 的 VideoWriter 将这些带有分析结果的画面作为**一个新的 RTSP 流**推送到一个本地的流媒体服务器（例如 MediaMTX 或 SRS）。
3. **前端展示：** 此时，将这个**带有 AI 绘制框的新 RTSP 流地址**交给 `rtsp2web`。 `rtsp2web` 就会像处理普通流一样，把带有行为分析结果的画面实时、低延迟地转发给前端 Web 页面进行播放。

**优点：** 行为分析通常需要跟踪算法（如 DeepSORT）和时序逻辑，在 Python 服务端做算力充足，不依赖客户端硬件。

**缺点：** 服务器需要配备 GPU 来支撑 YOLOv8 的实时推理。

虽然 `rtsp2web` 的官方文档中提到，如果前端选择使用 `flv.js` 播放器，它默认就具备进度条、在线回放等功能，但这仅仅是前端播放器组件自带的 UI 交互能力。`rtsp2web` 作为一个底层服务，它的核心定位是“直播流的实时转发”，**它本身并不提供视频的录制、物理保存和历史文件管理功能**。

要实现“缓存一个月内、且已经带有 YOLOv8 行为分析画面的视频”并支持前端回放，你的架构设计需要这样调整：

### 1. 视频录制（在 AI 端完成）

在你负责 YOLOv8 分析的后端服务（例如 Python 推理服务）中，当模型将目标框、警报文字渲染到视频帧上之后，你需要做两件事：

- **分支 A（走实时流）：** 继续将带有分析结果的流推给媒体服务器，交由 `rtsp2web` 转码推给前端，用于实时的低延迟观看。
- **分支 B（走录制存储）：** 利用 `OpenCV (cv2.VideoWriter)` 或者 `FFmpeg` 命令行，把这些带有 AI 分析画面的视频帧，实时写成物理视频文件（如 MP4 或 HLS 格式）保存到服务器的磁盘上。

### 2. 视频切片与周期管理

- **分段存储：** 不要把好几天的视频存成一个超大文件。建议按固定时间长度（如每小时生成一个 MP4 文件：`cam1_2026-04-07_1400.mp4`）进行切片存储。
- **生命周期（一个月缓存）：** 在服务器上编写一个简单的定时任务脚本（如 Cron job），每天凌晨扫描录像文件夹，自动删除创建时间超过 30 天的旧视频文件，以防止服务器硬盘被撑爆。

### 3. 前端历史回放（脱离 rtsp2web）

当用户想要看历史回放时，你的前后端交互逻辑应当是普通的“点播”逻辑，而不再是“直播”逻辑：

- 用户在前端页面选择指定的日期和时间段。
- 前端直接向你的普通业务后端发起 HTTP 请求获取对应的 MP4 文件地址。
- **前端使用常规的方式播放：** 此时不需要再借助 WebSocket 建立长连接，直接使用 HTML5 原生的 `<video>` 标签，或者直接用普通的 `flv.js` 加载该静态视频文件的 URL 即可播放。

**总结来说：** 你需要采用双轨制。**看当前实时监控**：走 `YOLOv8 -> 重新推流 -> rtsp2web -> 浏览器 Websocket`；**看历史回放**：走 `YOLOv8 -> 保存为 MP4 -> Nginx/静态文件服务器 -> 浏览器普通的 Video 标签点播`。两者互不干扰，完美配合。



### 第一步：创建一个 Vue 3 工程

打开你的命令行终端（新建一个黑框框），依次输入以下命令：

1. 创建一个名为 `monitor-app` 的 Vue 项目：

   ```bash
   npm create vite@latest monitor-app -- --template vue
   ```

2. 进入刚刚创建的项目文件夹：

   ```bash
   cd monitor-app
   ```

3. 安装项目依赖：

   ```bash
   npm install
   ```

---

### 第二步：配置全局 `jsmpeg` 依赖

刚才我们在代码里提过，这步很关键！
找到你刚刚新建的 `monitor-app` 文件夹，打开里面的 `index.html` 文件（在项目最外层）。
在 `<head>` 标签里面加上引入 `jsmpeg` 的代码，修改后大概长这样：

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Vite + Vue</title>
    
    <script src="https://jsmpeg.com/jsmpeg.min.js"></script>

  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>
```

---

### 第三步：把你的组件放进去

1. 进入 `src/components/` 目录，新建一个文件叫 `MonitorDashboard.vue`。
2. 把我上一条回答给你的**那一整段包含 `<template>、<script setup>、<style>` 的代码**，完整地粘贴进这个 `MonitorDashboard.vue` 文件中保存。

---

### 第四步：在主页面中引用它

打开 `src/App.vue` 文件，把里面原本默认的代码全部删掉，替换成下面这几行简单的代码：

```vue
<template>
  <MonitorDashboard />
</template>

<script setup>
// 引入你刚刚创建的组件
import MonitorDashboard from './components/MonitorDashboard.vue';
</script>

<style>
/* 去除浏览器默认的边距 */
body {
  margin: 0;
  padding: 0;
}
</style>
```

---

### 第五步：运行项目看效果！

回到你的命令行窗口，确保你还在 `monitor-app` 文件夹下，输入：

```bash
npm run dev
```

这时候命令行会闪过一道绿光，并告诉你项目跑起来了，通常会给你一个本地地址，比如：
`➜  Local:   http://localhost:5173/`
`➜  Network: http://192.168.237.170:5173/`

**在浏览器里输入这个地址，你就能看到那个高级暗黑风的 Vue 监控看板了！**
