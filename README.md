# Token 消耗看板

参考 [fuyi-git/token-dashboard](https://github.com/fuyi-git/token-dashboard) 的同款 WorkBuddy 用量看板。Python 3.8+，生成器只使用标准库，无需安装依赖；输出单文件 HTML，可离线打开。

## 实时统计真实用量（默认入口）

Python 3.8+，无需安装包。按终端提示在运行机器上打开看板；每 2 秒检查日志，发生变化后刷新。

### Codex 开发会话

```bash
python scripts/serve_dashboard.py --source codex
# 只统计开发某个项目的会话
python scripts/serve_dashboard.py --source codex --project-root /你的/项目路径
# 自定义 Codex 日志目录（例如设置过 CODEX_HOME）
python scripts/serve_dashboard.py --source codex --projects /你的/codex/sessions
```

默认读取 `~/.codex/sessions/**/*.jsonl` 中 `event_msg → token_count → info.total_token_usage`，累计快照转换为增量，重复快照去重。模型来自 `turn_context`，项目路径来自 `session_meta.cwd`。统计从日志记录的开始到最新已落盘用量，日期按钮可以筛选时间范围，支持项目/会话下钻。

**Codex 累计用量增量不是精确的 API 请求数**，界面使用“用量记录”。推理 Token 已包含在输出中，不再次相加；缓存输入已包含在输入中，不再次相加。日志缺失、不包含 usage 或平台不开放日志时显示“暂无数据”，无法凭聊天文本补出实际消耗。此适配器针对 Codex CLI 的 JSONL 格式；网页版/云任务没有本地会话日志时不会自动接通，也不能读取平台未公开的计费记录。不要把演示数据当作真实会话用量。

### 自己应用里的模型 API

在应用里，每次响应完成后把服务商提供的真实 `usage` 交给记录器：

```python
from scripts.record_usage import record_usage

# response 是你已有的 SDK 实际响应，不要自行构造 token 数。
record_usage(
    response,
    log_path="/你的/私有日志目录/api.jsonl",
    project="我的应用",
    session_id="本次开发会话ID",
    provider="openai",  # Anthropic 可用 anthropic
)
```

然后运行：

```bash
python scripts/serve_dashboard.py --source api --projects /你的/私有日志目录
```

记录器支持 OpenAI Responses / Chat Completions 和 Anthropic 的 usage 格式、SDK `model_dump()` 对象与字典。缺失 usage 会明确报错，不按字符估算。不记录提示词、回答正文或 API 密钥；按服务商及响应 ID 去重。没有响应 ID 时生成本地记录 ID，因此这类响应请只记录一次。多进程应用建议每个进程用独立 JSONL 文件，放在同一目录供看板扫描。

流式响应只在取得最终 usage 后记录一次：OpenAI Chat Completions 需配置 `stream_options={"include_usage": True}`，Responses 读取完成事件里的响应。没有最终 usage 的片段不能作为真实统计。应用的 SDK 调用和认证沿用你现有实现；看板不会主动调用模型。

### WorkBuddy（参考项目原有数据源）

```bash
python scripts/serve_dashboard.py --source workbuddy
```

默认扫描 `~/.workbuddy/projects`，可用 `--projects` 指定目录。

三种来源独立选择，不会把 Codex 的一次调用和你应用的同一次调用混加。真实数据不上传；服务只监听本机回环地址，Ctrl+C 退出，临时 HTML 自动清理。没有日志时显示“暂无数据”和 0 Token。Token 数来自日志/响应，金额是参考价估算；未配置匹配模型价格时显示“未配置价格”，不代表实际账单。

## 演示体验（非真实统计）

下载仓库后直接用浏览器打开 `demo.html`。演示文件只包含合成数据，不代表真实使用记录。

```bash
python scripts/make_demo.py           # 重新生成最近 30 天的合成演示
```

## 查看自己的真实用量

```bash
python scripts/gen_dashboard.py
python scripts/gen_dashboard.py --projects /你的/WorkBuddy/projects --out token-dashboard.html
```

默认扫描 `~/.workbuddy/projects/**/*.jsonl`。目录不存在时明确报错；空目录会生成无数据看板。生成后用浏览器打开 HTML。真实看板包含工作空间名、会话标题和用量，请妥善保存，勿上传公开仓库；默认输出已加入 `.gitignore`。工具不发送日志到网络。

## 全部功能

- 7 项 KPI：合计 Token、日均、会话/轮次、输入输出比、缓存命中率、预估金额。
- 20 分钟粒度日活热力图、时段占比及悬停明细。
- 0–24 时模型山脊图，对数轴和模型点击高亮。
- 每日模型用量堆叠柱与模型卡片高亮。
- 请求大小分布、模型 50% / 90% 分位。
- 工作空间 → 会话 → 请求三级下钻，散点图和明细表。
- 工作空间/会话视图、搜索、排序和活跃分布倍率。
- 深浅色主题及偏好记忆；1 / 3 / 7 / 30 天及自定义日期范围。
- 子代理归属父会话；相同会话名在不同工作空间独立统计。
- 桌面双列、移动端单列；离线无外部资源依赖。

金额按生成器内 JavaScript `PRICE` 表估算（元/百万 Token）。缓存命中使用缓存价，缓存写入按 1.25 倍输入价；未知模型使用默认参考价。请核对当前供应商和套餐价格，此数字不是账单。

## 作为 WorkBuddy Skill 使用

将 `SKILL.md` 和 `scripts/` 放到 `~/.workbuddy/skills/token-dashboard/`，Windows 对应 `%USERPROFILE%\.workbuddy\skills\token-dashboard\`。重启 WorkBuddy 后说“看看我的 token 用量”。

## 验证

```bash
python -m unittest discover -s tests -v
```

可选浏览器回归需要 Playwright 和 Chromium：

```bash
python -m pip install playwright
python scripts/make_demo.py
python tests/browser_smoke.py
python tests/browser_live.py
```

浏览器测试默认使用 `/usr/bin/chromium`，验证 KPI、各图表、主题记忆、日期、搜索、模型高亮、下钻和移动端宽度。可根据系统调整测试中的浏览器路径。真实数据生成器不依赖这些测试工具。

## 来源

详见 [UPSTREAM.md](UPSTREAM.md)。本项目保留参考实现并补充数据处理修复、演示和验证；未额外声明开源许可。
