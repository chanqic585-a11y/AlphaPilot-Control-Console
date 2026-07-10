# 策略生命周期控制台重构实施计划

## 目标

把控制台的策略状态统一到一个只读生命周期投影中，并让策略、本地模拟、Demo 模拟、实盘交易四个页面各自只展示当前阶段对象。同一策略不得跨页面重复，旧报告和旧实验功能保留在折叠档案中。

## 安全边界

- 不新增数据库 migration。
- 不写入策略晋级、Demo Release 或 Live Candidate 状态。
- 不新增 API Key 存储、Trade API、Withdraw API、账户/持仓读取或订单能力。
- 现有 Demo 与 Live 安全闸门保持不变。
- 所有新增接口均为只读。

## Task 1：生命周期投影单元测试

**新增文件**

- `tests/test_strategy_lifecycle_projection.py`

**测试内容**

1. usable sandbox strategy 映射为 `local_simulation_running`。
2. 30 个闭合样本和旧 `promoted_candidate` 只作为进度证据，不产生 `local_simulation_passed`。
3. 同一策略同时存在 survivor 和 sandbox 证据时只保留本地模拟阶段。
4. 正式 Demo Release 覆盖较早阶段，并只出现一次。
5. 正式 Live Candidate Package 覆盖 Demo 阶段，并只出现一次。
6. 同名不同 content hash 的策略保持独立。
7. 研究 artifacts 进入 archive summary，不进入主策略 items。
8. 冲突证据设置 `reconciliation_required`。

**验证命令**

```powershell
python -m unittest tests.test_strategy_lifecycle_projection
```

先确认测试失败，再实施投影模块。

## Task 2：实现只读生命周期投影

**新增文件**

- `alphapilot_control_console/strategy_lifecycle_projection.py`

**实现内容**

1. 定义阶段常量、中文标签、阶段页面映射和正式证据优先级。
2. 规范化 strategy identity，优先使用 `strategyId`、`candidateId`、`contentHash`，缺失时生成稳定 legacy hash。
3. 读取并适配：
   - `build_usable_strategy_catalog()`
   - `build_simulation_review()`
   - `build_strategy_promotion_gate(scan_quant_engine())`
   - `build_evolution_demo_status()`
   - `build_live_candidate_status()`
   - `strategyArtifactIndex`
4. 合并同 identity 的证据，输出单一 `currentStage`。
5. 只在存在正式 Demo Release 时进入 Demo 阶段。
6. 只在存在正式 Live Candidate Package 时进入实盘候选阶段。
7. 把旧报告、benchmark、baseline、factor report 和失败项计入 `archiveSummary`。
8. 对数据源异常返回 `sourceWarnings`，不伪造晋级结果。

模块支持依赖注入 payload，确保单元测试不读取或污染真实状态。

## Task 3：新增生命周期 HTTP 接口

**修改文件**

- `alphapilot_control_console/http_app.py`

**实现内容**

1. 导入生命周期 builder。
2. 新增 `GET /api/strategy-lifecycle`。
3. 使用短 TTL 只读缓存，支持现有 `?fresh=1`。
4. 不新增 POST、写状态或执行调用。

**验证**

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8766/api/strategy-lifecycle?fresh=1"
```

检查 summary 与 items 去重一致。

## Task 4：新增统一生命周期 UI 组件

**修改文件**

- `web/index.html`
- `web/app.js`
- `web/styles.css`

**实现内容**

1. 在四个主页面增加统一阶段摘要和当前阶段清单容器。
2. 新增 `renderStrategyLifecycle(payload)`，一次渲染四个页面。
3. 每张卡只显示：
   - 中文策略名
   - 当前阶段
   - 核心证据
   - 关键进度
   - 阻塞项
   - 下一道门槛
4. 新增明确空状态：
   - Demo 无 Release 时显示 0 和原因。
   - Live 无 Candidate Package 时显示 0 和原因。
5. 顶部数量只来自 `/api/strategy-lifecycle`。

## Task 5：四页面职责去重

**修改文件**

- `web/index.html`
- `web/app.js`
- `web/styles.css`

**策略页**

- 默认只显示 `research_candidate` 和 `backtest_passed`。
- 移除“可观察策略”“可复核”“晋级候选”等旧口径主指标。
- 研究报告、Testnet 旧实验区和 artifacts 放入折叠“研究档案与旧实验”。

**本地模拟页**

- 默认只显示 `local_simulation_running` 和 `local_simulation_passed`。
- 保留沙盒启动/停止、样本、质量和稳定性操作。
- 删除把 30 样本称为晋级的文案。

**Demo 模拟页**

- 默认只显示 `demo_validation_running` 和 `demo_validated`。
- 旧 public candidate scanner、无票据工作台和人工 Demo 演练放入折叠高级区。
- 主页面不显示“候选币种”“行情可用 12”或通用策略池。

**实盘交易页**

- 默认只显示 `live_candidate`。
- 保留现有 checksum 人工批准边界。
- 没有候选包时不显示沙盒或 Demo 候选占位。

## Task 6：加载性能与兼容

**修改文件**

- `web/app.js`

**实现内容**

1. `/api/strategy-lifecycle` 加入核心并发加载。
2. 四页面先渲染生命周期摘要，再按进入页面加载旧高级数据。
3. 保留旧 endpoint 和旧 renderer，避免破坏高级档案。
4. 旧 renderer 对隐藏区域继续安全运行，不得因缺少 DOM 节点报错。
5. 生命周期 endpoint 失败时显示“状态读取失败”，不得回退到误导性旧计数。

## Task 7：回归测试与视觉验收

**自动检查**

```powershell
python -m compileall alphapilot_control_console
python -m unittest discover -s tests
node --check web/app.js
git diff --check
```

**接口检查**

1. `/api/health`
2. `/api/strategy-lifecycle?fresh=1`
3. `/api/usable-strategy-catalog`
4. `/api/simulation-review`
5. `/api/exchange-demo/simulation`
6. `/api/live-candidates`

**视觉检查**

1. 1440x900 桌面截图。
2. 390x844 窄屏截图。
3. 策略、本地模拟、Demo、实盘四页分别截图。
4. 检查横向溢出、文字截断、重复策略和空状态。
5. 检查主界面不再出现误导性旧计数标签。

**安全扫描**

只扫描本次修改文件，确认没有新增凭据存储、私有账户读取、真实订单或自动实盘逻辑。

## Task 8：文档、提交与发布

**修改文件**

- `README.md`

记录：

- 单一策略生命周期口径。
- 四页面职责。
- 旧研究资产默认归档。
- 30 样本不代表晋级。
- Demo/Live 的正式证据边界。
- 无数据库 migration、无新增交易能力。

验证通过后提交并推送 Control Console。除非用户明确要求，本轮不打 APK，不修改手机 App，不新增版本 tag。
