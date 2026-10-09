# Token 消耗看板

参考 [fuyi-git/token-dashboard](https://github.com/fuyi-git/token-dashboard) 的同款 WorkBuddy 用量看板。Python 3.8+，生成器只使用标准库，无需安装依赖；输出单文件 HTML，可离线打开。

## 立即体验

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
```

浏览器测试默认使用 `/usr/bin/chromium`，验证 KPI、各图表、主题记忆、日期、搜索、模型高亮、下钻和移动端宽度。可根据系统调整测试中的浏览器路径。真实数据生成器不依赖这些测试工具。

## 来源

详见 [UPSTREAM.md](UPSTREAM.md)。本项目保留参考实现并补充数据处理修复、演示和验证；未额外声明开源许可。
