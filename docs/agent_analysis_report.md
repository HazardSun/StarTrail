# StarTrail 三 Agent 协作分析报告

> 生成时间：2026-07-08
> 本文件记录三位专家 Agent 对 StarTrail 项目的完整分析，供后续修改时参考。

---

## Agent 1: 架构师 & UI/UX 设计师

### 功能模块图

```
StarTrail
├── 应用核心
│   ├── Config ──── 全局配置：模式/位置/API密钥/专业设置
│   ├── Theme ────── 主题系统：颜色/字体/组件样式
│   └── MainWindow ── 主窗口框架
├── 视图层
│   ├── SkyView ──── 实时星空（核心视图）
│   ├── ForecastView ─── 观星预报
│   ├── CalendarView ─── 天文日历
│   └── SettingsView ─── 设置面板
├── 组件层
│   ├── StarChart ────── 2D QPainter 星空渲染
│   ├── GLHybridChart ── OpenGL+QPainter 混合渲染
│   ├── GlassCard / CollapsibleCard / LoadingOverlay
│   ├── HudPanel / CameraPanel / GuidePanel / SeeingChart
├── API层
│   ├── astronomy_api ── 天文计算（Skyfield）
│   ├── weather_api ──── 天气
│   ├── location_api ─── IP 定位
│   ├── nasa_api ─────── NASA 图库
│   ├── adsb_api ─────── 航空追踪
│   └── atmosphere_api ─ 大气质量
└── 工具层
    ├── background_worker ── 后台线程管理
    └── system_monitor ───── 系统监控
```

### 关键设计问题

1. **StarChart 职责过重**（God Object）：1519 行，需拆分为 Renderer/HitTester/SkyProjector/Cache
2. **渲染器接口不统一**：StarChart 和 GLHybridChart 无公共接口
3. **模式切换分散耦合**：每个视图独立实现 on_mode_changed()，易遗漏
4. **配置项缺少验证**：直接 setattr，无类型检查
5. **缓存策略不统一**：各 API 独立管理缓存，无统一策略
6. **缺少错误恢复机制**：无重试，无离线降级
7. **GLHybridChart 功能不完整**：set_camera_fov() 为空实现
8. **视图缺少生命周期管理**：无 on_hide()、on_pause()、on_resume()

---

## Agent 2: 天文学家 & 后端专家

### 天文计算核心参数

| 参数 | 实现 | 精度 |
|------|------|------|
| 历元 | J2000.0 (Skyfield 默认) | ±0.001° |
| 恒星位置 | BRIGHT_STARS 硬编码 | ±0.01° |
| 太阳位置 | Skyfield DE421 或经验公式 | ±0.001° / ±1° |
| 月球位置 | Skyfield DE421 或相位推算 | ±0.01° / ±5° |
| 恒星时 | _approx_lst() 儒略日公式 | ±0.1° |
| 大气折射 | Saemundsson 模型 | ±0.01° (alt>15°) |
| 卫星轨道 | SGP4/SDP4 (CelesTrak TLE) | ±1 km (LEO) |

### 数据流架构

```
UI Layer (Views)
    ↓
Widget Layer (StarChart / GLHybridChart / Cards)
    ↓
API Layer (astronomy / weather / adsb / atmosphere / location / nasa)
    ↓
External Services (Skyfield DE421 / OpenWeatherMap / CelesTrak / OpenSky / ip-api)
```

### API 缓存策略

| API | 频率 | 缓存 TTL |
|-----|------|----------|
| astronomy_api | 10 分钟 | 600s |
| weather_api | 每次进入 | 会话级 |
| adsb_api | 10 分钟 | 60s (位置), 永久 (注册) |
| atmosphere_api | 每次调用 | 180s |
| TLE 数据 | 每小时 | 3600s |

### 关键问题

- 降级路径使用 hash() 伪随机（数据不真实）
- 星表无索引，全量遍历（性能瓶颈）
- 行星星等硬编码（未动态计算）
- 配置保存无锁（线程安全）
- _approx_lst() 不含岁差修正（误差累积）

---

## Agent 3: 全栈性能工程师

### 依赖问题

当前 requirements.txt 仅 3 项，缺少 numpy、PyOpenGL、onnxruntime。

### 生成的文件

| 文件 | 用途 |
|------|------|
| docs/dev_env_setup.md | 完整开发环境配置文档 |
| scripts/check_npu_env.py | NPU/DirectML 环境检测脚本 |
| scripts/setup_env.ps1 | PowerShell 一键环境配置 |
| scripts/setup_env.bat | CMD 一键环境配置 |
| requirements-dev.txt | 增强版依赖清单 |
| app/api/star_index.py | 星表空间索引模块（替代全量遍历） |

### 核心建议

1. **NPU 路径**：onnxruntime-directml==1.19.0 → Windows 10 1903+ / DirectX 12 GPU
2. **线程池拆分**：当前限 2 线程，建议拆分为 NPU/IO/Compute 三个池
3. **GL 优化**：顶点数据应缓存 VAO/VBO，避免每帧重传
4. **ASCOM**：当前无依赖，可选 v2.0 阶段集成

---

## 协作修改流程

后续每次修改应用时，按以下流程执行：

1. **Agent 1（架构师）审核**：评估修改是否符合 UI 框架设计，是否引入新的架构问题
2. **Agent 2（天文专家）审核**：评估修改对天文计算精度和数据流的影响
3. **Agent 3（性能工程师）审核**：评估修改对性能的影响，是否需要优化
4. **综合修改**：根据三位 Agent 的建议进行修改
5. **再次审核**：修改完成后，再次调用三位 Agent 确认无遗漏
