---
name: token-dashboard
description: 生成 WorkBuddy Token 消耗看板（单文件离线 HTML，含 KPI / 日历热力图 / 0-24 时模型分布 / 每日模型比例 / 工作空间-会话-请求三级下钻）。当用户想查看自己的 token 用量、消耗统计、成本审计时使用，例如"看看我的 token 用量""token 审计""生成本月消耗看板"。
---

# Token 消耗看板

为本机 WorkBuddy 生成一张请求级真实 usage 的 Token 消耗看板（单文件自包含 HTML，离线可看，无外部依赖）。

## 实时统计

先依据用户目标选择数据源：Codex 开发会话用 `python <skill目录>/scripts/serve_dashboard.py --source codex`（默认），API 调用用 `--source api --projects <usage日志目录>`，WorkBuddy 用 `--source workbuddy`。可以用 `--project-root <项目路径>` 限定 Codex 项目。按终端提示在运行机器打开看板；每 2 秒检查真实日志。API 应用须通过 scripts/record_usage.py 的 record_usage 记录实际 SDK 响应。不要自行编造 usage，不要以 demo.html 代替真实统计。Codex 云任务未公开会话日志时保持暂无数据，不能声称已接通。

## 执行步骤

1. **确认数据目录**：默认 `~/.workbuddy/projects`（Windows / macOS / Linux 通用）。若用户想看其他目录的日志，用 `--projects` 参数传入。
2. **选择 Python**：优先使用平台的托管 Python 运行时；没有则用系统 `python3`（Windows 为 `python`）。脚本仅依赖标准库（3.8+），**无需安装任何依赖**。
3. **运行脚本**（scripts 与 SKILL.md 同目录，用绝对路径调用）：

   ```
   python <skill目录>/scripts/gen_dashboard.py --out <工作区>/token-dashboard.html
   ```

   - 默认输出 `token-dashboard.html` 到当前目录。
   - 数据目录不存在时脚本会报错退出并提示，此时告知用户本机可能未使用过 WorkBuddy。

4. **展示结果**：用文件展示工具打开发出的 HTML，并口头汇报关键数字：合计 token、日均、会话/轮次、输入输出比、缓存命中率、预估金额、TOP 模型。

## 看板能力

- KPI：合计 Token / 日均 / 会话 / 轮次 / 输入输出比 / 缓存命中率 / 预估金额（元）
- 日活热力图（20 分钟粒度）、0–24 时模型山脊图、每日模型用量堆叠柱、单次请求大小分布（50%/90% 分位）
- 工作空间 → 会话 → 单次请求三级下钻（散点 + 明细表）
- 深浅色主题（记忆偏好）、1/3/7/30 天窗口 + 自定义日期区间

## 数据与口径说明

- 数据源：`~/.workbuddy/projects/**/*.jsonl` 中每条记录的 `providerData.rawUsage / usage` 字段（请求级真实 usage，非估算）；深层子代理日志（subagents/agent-*.jsonl）自动归属父会话。
- 会话标题取首条非内部标签的用户消息前 42 字。
- 预估金额基于脚本头部 `PRICE` 表（单位：元/百万 token，格式 [输入, 输出, 缓存命中]），按每条请求的**实际缓存命中**计价：读命中走缓存价、缓存写入（Claude 系）按 1.25× 输入价、其余输入走输入价。不同用户套餐价格不同，**汇报时应说明这是按牌价的粗略预估，用户可自行修改 PRICE 表**。

## 注意

- Windows 控制台为 GBK 时脚本已内置 UTF-8 输出保护，若仍乱码不影响 HTML 生成。
- 看板内数据完全来自本机日志，不会外发；生成的是本地文件，不会自动上传。
