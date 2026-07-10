# AlphaPilot 策略生命周期控制台重构设计

## 状态

- 设计日期：2026-07-10
- 用户确认：已确认采用“状态总览 + 分组清单”方案
- 适用仓库：`AlphaPilot-Control-Console`
- 目标版本：V13.15.x 控制台信息架构补丁

## 背景与问题

当前控制台把策略、回测报告、研究基准、沙盒观察记录和晋级结果混在一起展示。同一批 10 条沙盒策略同时被标成“可复核 10”“晋级候选 10”和“本地已验收候选 10”，Demo 页面还显示“行情可用 12”。这些数字来自不同旧接口，含义并不相同：

- `totalUsableStrategies=10` 只表示 10 条策略可以进入本地沙盒观察。
- 10 条策略共积累 443 个闭合样本，并达到旧版每条 30 个样本的复核起点，但没有正式晋级决定。
- `dryRunApproved=false`、`liveTradingApproved=false`，因此不能称为“已晋级”或“已验收”。
- “行情可用 12”是策略与币种的扫描组合数量，不是 12 条策略，也不是 12 个 Demo 资格。
- 60 个 strategy artifacts 是报告、基准和研究资产，不是 60 条可运行策略。
- 正式 registry 当前没有 `DemoRelease`，也没有 `LiveCandidatePackage`。

用户需要一眼看清每条策略现在处于哪个阶段、正在做什么、下一步缺什么。界面不再展示内部扫描组合数、重复状态和难以解释的历史术语。

## 设计目标

1. 为每条策略计算且只计算一个当前生命周期阶段。
2. 策略晋级后从上一阶段主列表移走，历史只保留在详情时间线。
3. 策略、回测报告和研究资产分开建模、分开展示。
4. 策略、本地模拟、Demo 模拟、实盘交易四个页面各自只展示本阶段对象。
5. 失败、重复、淘汰和旧研究资产默认归档隐藏，但不删除数据。
6. 旧接口继续可用，现有执行和研究流程不因 UI 重构而中断。
7. 保持安全边界：本补丁不增加凭据存储、交易权限、订单能力或实盘适配器。

## 非目标

- 不修改策略规则、参数或回测结果。
- 不把 30 个闭合样本重新定义为正式晋级条件。
- 不伪造 `PromotionDecision`、`DemoRelease` 或 `LiveCandidatePackage`。
- 不在本补丁中实现 OKX 私有接口、Demo 下单或实盘下单。
- 不删除旧报告、旧状态或旧页面代码。
- 不新增数据库表，也不修改现有 schema。
- 不在本补丁中重写全市场扫描器；只规定扫描结果如何进入生命周期和 UI。
- 不在本次补丁中打包新的手机 APK。

## 生命周期模型

统一生命周期按以下顺序单向推进：

```text
候选待测
  -> 回测通过
  -> 本地模拟中
  -> 本地模拟通过
  -> Demo 验证中
  -> Demo 通过
  -> 实盘候选
```

失败、重复或被淘汰的对象进入归档，不出现在默认主流程中。

内部阶段值：

```text
research_candidate
backtest_passed
local_simulation_running
local_simulation_passed
demo_validation_running
demo_validated
live_candidate
archived
```

### 阶段语义

| 阶段 | 正式证据 | 所属页面 |
| --- | --- | --- |
| 候选待测 | 已识别为真实策略候选，但还没有满足回测门槛 | 策略 |
| 回测通过 | 存在可追溯的回测通过决定，不只是单份报告状态 | 策略 |
| 本地模拟中 | 已进入本地沙盒观察，尚无正式本地通过决定 | 本地模拟 |
| 本地模拟通过 | 存在正式本地晋级决定，等待或正在生成 Demo Release | 本地模拟 |
| Demo 验证中 | 存在不可变 `DemoRelease`，Demo 验证尚未完成 | Demo 模拟 |
| Demo 通过 | Demo Release 已完成并满足正式门槛，等待 Live Candidate 包 | Demo 模拟 |
| 实盘候选 | 存在不可变 `LiveCandidatePackage` | 实盘交易 |
| 已归档 | 失败、重复、淘汰或人工归档 | 默认隐藏 |

样本数、质量分、回测收益、行情可用性和研究报告状态都是阶段证据或进度指标，不能单独替代正式晋级决定。

## 单一当前阶段规则

每个策略必须有稳定身份，建议使用：

```text
strategyId + immutable contentHash
```

显示名称不参与唯一性判断，因为短周期变体可能使用相同中文名称。

生命周期投影先判断是否存在时间上更新且仍有效的终止归档决定；如果存在，当前阶段为 `archived`。没有终止归档决定时，再按正式证据优先级从高到低计算：

```text
LiveCandidatePackage
Demo accepted decision
DemoRelease
Local simulation promotion decision
Active local simulation enrollment
Backtest promotion decision
StrategyCandidate
```

同一策略即使保留多个历史证据，也只能出现在最高有效阶段对应的一个主页面。较早阶段写入 `history`，不再生成第二张主卡片。

如果证据互相冲突，投影仍选择最高正式阶段，但设置：

```text
consistencyStatus = reconciliation_required
```

UI 显示“状态待对账”，禁止为了消除冲突而静默晋级、回退或删除历史。

## 统一只读投影

新增独立领域模块，建议命名：

```text
alphapilot_control_console/strategy_lifecycle_projection.py
```

它只负责读取既有状态、统一身份、去重、判定当前阶段和生成页面视图，不写入研究状态或执行状态。

核心返回类型：

```text
StrategyLifecycleRecord
  lifecycleId
  strategyId
  displayName
  currentStage
  stageLabel
  sourceKind
  contentHash
  stageEnteredAt
  consistencyStatus
  evidenceSummary
  metrics
  nextGate
  blockers
  history
  archived
```

新增只读接口：

```text
GET /api/strategy-lifecycle
```

返回结构：

```text
generatedAt
summary
  strategyCandidateCount
  backtestPassedCount
  localSimulationRunningCount
  localSimulationPassedCount
  demoValidationRunningCount
  demoValidatedCount
  liveCandidateCount
  archivedCount
  reconciliationRequiredCount
items
archiveSummary
```

网页端生命周期数量和清单只能从该接口读取。旧接口仍可为详情、调试和兼容流程提供数据，但不能再分别驱动四个主页面的阶段计数。

## 正式数据与旧数据映射

### 正式 registry

正式对象优先作为生命周期事实来源：

- `StrategyCandidate`
- 回测/研究晋级决定
- 本地模拟晋级决定
- `DemoRelease`
- Demo 验证结果
- `LiveCandidatePackage`

这些对象保持不可变、可追溯。后续阶段不覆盖前一阶段记录。

### 旧数据兼容

旧数据通过 compatibility adapter 进入投影：

- 当前 10 条 usable sandbox strategies 映射为“本地模拟中”。
- 达到 30 个闭合样本只显示为“达到复核起点”，不映射为“本地模拟通过”。
- 旧 `reviewReadyStrategies` 和 `promotedCandidates` 不再作为正式晋级计数。
- 旧 promotion gate 中的 survivor 只映射为研究候选；如果其身份与本地模拟策略相同，按单一阶段规则去重，只显示在本地模拟页。
- 没有 `DemoRelease` 时，Demo 页面正式策略数量必须为 0。
- 没有 `LiveCandidatePackage` 时，实盘候选数量必须为 0。
- artifacts、benchmark、baseline、factor report 和诊断报告进入研究档案，不生成策略卡片。

旧数据缺少稳定 hash 时，适配器使用可重复的规范化规则生成兼容身份，并在 `sourceKind=legacy_projection` 中明确标记。兼容身份不能被当作新的正式 registry 记录写回。

## 页面职责

### 策略

只展示：

- 候选待测
- 回测通过

页面结构采用用户确认的“状态总览 + 分组清单”：

1. 顶部显示生命周期关键数量。
2. 主列表显示当前仍属于策略阶段的真实策略。
3. 卡片只显示中文名称、当前阶段、核心证据、阻塞原因和下一道门槛。
4. 提供“查看研究档案”折叠入口。

不再把报告、基准、研究文件或沙盒策略混入主列表。

### 本地模拟

只展示：

- 本地模拟中
- 本地模拟通过但尚未生成 Demo Release

当前旧数据应体现为 10 条“本地模拟中”，总闭合样本 443；正式本地模拟通过数为 0，除非存在明确晋级决定。

页面重点显示：

- 闭合样本数
- 数据质量
- 集中度和稳定性阻塞项
- 下一道门槛
- 最近观察时间

删除“晋级候选 10”等没有正式依据的标签。

### Demo 模拟

只展示：

- Demo 验证中
- Demo 通过但尚未生成 Live Candidate 包

进入该页面的必要条件是存在不可变 `DemoRelease`。没有 Demo Release 时显示明确空状态：

```text
暂无进入 Demo 验证的策略。本地模拟通过并生成 Demo Release 后会显示在这里。
```

页面不再展示通用策略候选池，不再显示“本地已验收候选 10”或“行情可用 12”。

### 实盘交易

只展示存在 `LiveCandidatePackage` 的实盘候选。当前真实数量为 0 时显示空状态，不使用 Demo 状态、沙盒状态或研究状态填充。

人工批准只表示批准进入未来发布复核，不启用订单执行。本补丁不增加实盘执行适配器。

### 手机控制台

本补丁不修改手机 App，也不触发 APK 构建。新的生命周期接口保持移动端友好，后续手机控制台可以直接复用同一摘要，避免再次产生不同口径。

## 研究档案

研究档案默认折叠，包含：

- 回测报告
- benchmark 和 baseline
- factor 研究资产
- 诊断报告
- 淘汰、失败和重复策略记录

档案只用于追溯和复盘，不参与顶部主阶段计数。所有数据保留，不执行删除或清空。

## 市场扫描边界

策略设计目标不是固定在 6 个币种。长期扫描范围是经过公共行情、流动性、数据质量和历史长度过滤后的 OKX USDT 永续市场。

本次生命周期 UI 补丁遵循以下规则：

- 不把当前 6 个去重币种解释为策略固定范围。
- 不在主界面展示 universe 数量、策略与币种组合数或内部候选币种数。
- Demo 页面只在正式 `DemoRelease` 存在后展示最终选择的币种和证据。
- 当前 scanner 的 `selected_pairs_public_probe` 限制记录在调试信息中，不伪装成全市场扫描。
- 全市场 scanner 的实现属于后续独立功能，不与本次页面去重混做。

## UI 规则

- 顶部只保留用户能理解的阶段数量，不展示旧接口名称。
- 页面内部使用紧凑列表和小型指标区，不增加营销式大卡或超大标题。
- 同一策略在四个主页面中最多出现一次。
- 卡片必须回答三个问题：现在在哪、为什么在这里、下一步缺什么。
- 失败和归档项默认隐藏，用户主动打开档案时才显示。
- 内部字段名、扫描组合数和历史兼容术语不直接暴露给普通用户。
- 桌面 1440px 和窄屏 390px 均不得横向溢出。

## 数据流

```text
正式 registry + 本地模拟状态 + 旧兼容数据 + 研究 artifacts
  -> 生命周期适配器
  -> 身份规范化与语义去重
  -> 正式证据优先级判定
  -> 单一当前阶段投影
  -> GET /api/strategy-lifecycle
  -> 策略 / 本地模拟 / Demo 模拟 / 实盘交易页面
```

研究档案走独立输出，不与策略清单合并。

## 错误处理

- 单个旧接口不可用：保留其他正式数据，并在响应中记录 `sourceWarnings`。
- 缺少稳定身份：生成只读兼容身份并标记 `legacy_projection`。
- 正式证据冲突：设置“状态待对账”，只在最高正式阶段显示一次。
- 正式 registry 不可用：不得用样本数自动伪造 Demo 或实盘阶段。
- 空数据：四个页面显示对应空状态，不报错、不填充 mock。
- 归档读取失败：不影响主阶段页面。

## 安全边界

本补丁只整理只读数据投影和页面展示，不新增：

- API Key 存储
- Trade API
- Withdraw API
- 私有账户读取
- 私有持仓读取
- 订单创建或撤销
- 自动实盘交易
- 自动生成 Live Candidate
- 绕过人工实盘批准

现有 OKX Demo 运行能力仍与正式 `DemoRelease` 隔离。生命周期投影不能调用执行引擎。

## 验证方案

### 单元测试

1. 同一策略含多个阶段证据时只返回最高有效阶段。
2. 同名不同 hash 的策略保持独立。
3. 同 identity 的旧候选和沙盒策略语义去重。
4. 30 个闭合样本只产生进度标记，不产生本地模拟通过决定。
5. 没有 `DemoRelease` 时 Demo 数量为 0。
6. 没有 `LiveCandidatePackage` 时实盘候选数量为 0。
7. 冲突证据产生 `reconciliation_required`，但不重复展示。
8. artifacts 只进入档案，不进入策略主清单。

### 接口测试

1. `GET /api/strategy-lifecycle` 返回稳定 schema。
2. summary 数量与去重后的 items 一致。
3. 同一 `lifecycleId` 只属于一个当前阶段。
4. 旧数据源超时时返回 warning，不伪造晋级数据。

### 页面测试

1. 策略页只显示候选待测和回测通过。
2. 本地模拟页只显示本地模拟中和本地模拟通过。
3. Demo 页在没有 `DemoRelease` 时为空。
4. 实盘页在没有 `LiveCandidatePackage` 时为空。
5. 页面不再以主指标显示“候选 10”“晋级候选 10”“本地已验收候选 10”或“行情可用 12”。
6. 研究档案默认折叠，打开后可以查看旧资产。
7. 1440px 和 390px 浏览器截图无重叠、截断或横向溢出。

### 工程检查

```powershell
python -m compileall alphapilot_control_console
python -m unittest discover -s tests
node --check web/app.js
git diff --check
```

同时运行控制台 smoke、关键接口检查和定向安全扫描。任何会写状态的验证必须先备份并在测试后恢复。

## 验收标准

1. 用户可以从四个主页面准确判断策略当前阶段。
2. 同一策略不会跨页面重复出现。
3. 旧 10 条沙盒策略不再被误称为已晋级或 Demo 已验收。
4. 60 个研究资产不再被当作 60 条策略。
5. Demo 页面只认正式 `DemoRelease`。
6. 实盘页面只认正式 `LiveCandidatePackage`。
7. 失败和归档记录默认隐藏且数据完整保留。
8. 主界面不显示内部市场扫描组合数。
9. 无数据库 migration，无旧数据删除。
10. 无新增交易权限、订单能力或自动实盘执行。

## 实施顺序

1. 建立生命周期投影和单元测试。
2. 暴露只读生命周期接口。
3. 将策略页改为候选/回测阶段清单，并拆出研究档案。
4. 将本地模拟页改为本地阶段清单。
5. 将 Demo 页改为只读取 Demo Release 阶段。
6. 将实盘页改为只读取 Live Candidate 阶段。
7. 完成桌面和窄屏视觉验收、安全扫描与回归测试。

该顺序先统一数据口径，再改页面，避免只改文案而继续引用错误统计。
