# AlphaPilot 第四阶段更新版：正式 Release 准入与 OKX 策略验证 Demo

> **执行状态前提**：阶段 1、阶段 2 已完成；阶段 4 只能在更新后的第三阶段真实 Campaign 完成后启动。  
> **本文件替代**：`docs/superpowers/plans/2026-07-15-strategy-validation-demo-admission-and-cutover.md`。旧文件保留并标记 `supersededBy`。  
> **执行方式**：建议使用 `superpowers:subagent-driven-development` 或 `superpowers:executing-plans` 按复选框实施。  
> **核心目标**：只允许第三阶段正式回测通过的不可变候选，经 Hash 绑定的人工批准后，进入隔离的 OKX 策略验证 Demo。影子观察、工程烟测、旧 Release 和历史本地模拟永远不能成为策略晋级证据。

---

## 1. 阶段定位

阶段 4 负责：

```text
正式回测 Evidence Bundle
→ 不可变策略验证 Release
→ 未批准导入
→ Hash 绑定人工批准
→ Runtime 独立 ARM
→ OKX 策略验证 Demo
→ 实际委托、成交、持仓、退出和对账
→ 闭合交易前向复核
```

阶段 4 不负责：

```text
生成新策略
重新调参
修改第三阶段结果
恢复完整本地模拟
将工程烟测算作策略成绩
进入实盘 Canary
```

---

## 2. 已完成前置阶段契约

阶段 4 必须复用、不得重做：

```text
阶段 1：
- 权威 Demo Account Instruments 服务
- 公共 PIT 候选池与 Demo 可交易 SWAP 的精确交集
- 工程烟测 Release
- 工程烟测独立 Ledger
- 订单、持仓、退出、对账工程链路

阶段 2：
- 完整本地模拟永久停用
- 历史模拟只读
- 旧 Release = legacy_diagnostic
- 无 PnL 轻量影子观察
```

启动前验证：

```text
engineeringSmokeQualifiedForStrategy = false
shadowPerformanceEligible = false
legacyReleasePromotionEligible = false
fullLocalSimulationEnabled = false
```

任一不满足：

```text
停止第四阶段
```

---

## 3. 第三阶段输入契约

阶段 4 只接受：

```text
reports/backtest_screening/<campaignId>/formal_pass_evidence/*.json
```

每个 Evidence Bundle 至少包含：

```text
campaignId
candidateId
strategyId
strategyFamilyId
marketMechanismId
strategyDefinitionHash
externalReferenceManifestHash
dataManifestHash
dataSnapshotHash
factorRegistryHash
factorShortlistHash
factorDefinitionHashes
factorRoles
preregistrationHash
costModelHash
riskConfigHash
backtestReportHash
formalGateHash
holdoutIsolationPassed
walkForwardPassed
baseCostPassed
stress1_5xPassed
formalPass=true
artifactManifestHash
```

缺失任一必需字段：

```text
failed_closed
```

---

## 4. 外部参考采用边界

### 4.1 CryptoAgentPro.beta 可参考的阶段 4 概念

允许参考并在 AlphaPilot 内重写：

```text
下单前单笔损失上限
每日亏损暂停
保证金占用上限
连续亏损熔断
最大回撤熔断
人工重置
任务状态与错误码展示
```

必须重新实现为：

```text
可持久化
可恢复
Hash 绑定
不可变 Risk Profile
Append-only 风险事件
与 Release 审批分离
与工程烟测 Ledger 分离
```

### 4.2 明确拒绝

禁止引入：

```text
Paper Account
虚拟权益
AI 在线热调参
根据近期几笔交易自动换策略
止损只能增大的放宽逻辑
马丁策略
其自有回测引擎
自动驾驶
Live Connector
```

任何参数变化都必须：

```text
停止旧 Release
创建新策略版本
重新进入第三阶段
```

不能在 Demo 中热更新。

---

## 5. 全局安全约束

```text
正式回测通过是必要条件，不是自动执行条件
人工批准必须绑定 Release Hash 和 Risk Config Hash
Release 生成不自动批准
批准不自动 ARM
ARM 不自动批准
最多 3 条 Release / Campaign
0 条 Release 是有效状态
只允许 OKX Demo
不保存新 raw API Key
不在前端输入或返回凭证
不接 Withdraw API
不读取 Live 账户或持仓
不创建 Live 订单
不自动进入 Live Canary
初始目标 >= 2R
风险用 R 表示
初始止损不得放宽
```

---

# 任务 1：正式 Evidence Schema 与晋级 Gate

仓库：

```text
D:\Codex-Workspace\AlphaPilot-Quant-Engine
```

建议修改 / 新增：

```text
alphapilot/evolution/promotion/formal_backtest_evidence.py
alphapilot/evolution/promotion/gate.py
tests/evolution/test_formal_backtest_evidence.py
tests/evolution/test_promotion_gate.py
```

要求：

- [ ] 只接受 `formalPass=true`。
- [ ] 验证全部 Hash。
- [ ] 验证 Holdout、5 折、基础成本、1.5 倍成本。
- [ ] 验证 Factor Registry、Shortlist 和因子定义 Hash。
- [ ] 验证市场机制 ID。
- [ ] 本地闭合样本、影子计数、工程烟测、旧 Demo 历史不能满足 Gate。
- [ ] 缺失字段保持失败，不能推断通过。
- [ ] 旧晋级结构只保留 deprecated reader。

---

# 任务 2：生成不可变策略验证 Release

建议新增：

```text
alphapilot/evolution/promotion/strategy_validation_release.py
alphapilot/scripts/generate_strategy_validation_releases.py
tests/evolution/test_strategy_validation_release.py
```

输出：

```text
reports/backtest_screening/<campaignId>/candidate_releases/<releaseHash>.json
```

Release 字段：

```text
releaseId
releaseHash
campaignId
candidateId
strategyId
strategyFamilyId
marketMechanismId
strategyDefinitionHash
externalReferenceManifestHash
dataSnapshotHash
factorRegistryHash
factorShortlistHash
factorDefinitionHashes
factorRoles
preregistrationHash
costModelHash
riskConfigHash
backtestReportHash
formalGateHash
releasePurpose=strategy_forward_validation
evidenceClass=demo_strategy_validation
environment=demo
approvalRequired=true
approved=false
createdAt
```

要求：

- [ ] 只有正式通过者可生成。
- [ ] 每个 Campaign 最多 3 条。
- [ ] 排名确定性，不只按收益。
- [ ] Canonical JSON + SHA-256。
- [ ] Hash 地址文件不可覆盖。
- [ ] 不写批准记录。
- [ ] 不修改来源策略。
- [ ] 0 个正式通过时生成 0 条 Release。

---

# 任务 3：不可变 Risk Profile

建议新增：

```text
alphapilot/evolution/promotion/demo_risk_profile.py
tests/evolution/test_demo_risk_profile.py
```

Risk Profile 至少包含：

```text
riskConfigHash
riskPerTradeR
maximumConcurrentPositions
maximumOpenRiskR
maximumSingleSymbolRiskR
maximumCorrelatedClusterRiskR
maximumDailyLossR
maximumWeeklyLossR
maximumConsecutiveLosses
maximumDemoDrawdownPct
minimumTargetR
stopWideningAllowed=false
addingToLossAllowed=false
martingaleAllowed=false
automaticParameterChangeAllowed=false
```

原则：

```text
Risk Gateway 只能拒绝或暂停
不能改变信号
不能放宽止损
不能自动缩放为更高风险
不能修改 Release
```

---

# 任务 4：Console 导入，不自动启用

仓库：

```text
D:\Codex-Workspace\AlphaPilot-Control-Console
```

建议新增：

```text
alphapilot_control_console/strategy_validation_release_store.py
alphapilot_control_console/strategy_validation_release_service.py
tests/test_strategy_validation_release_store.py
tests/test_strategy_validation_release_service.py
```

存储：

```text
data/strategy_validation_releases.sqlite
data/strategy_validation_release_contracts/<releaseHash>.json
```

要求：

- [ ] 保留原始 canonical bytes。
- [ ] 校验来源 Hash。
- [ ] 默认状态 `demo_waiting_approval`。
- [ ] 导入不进入 Runtime discovery。
- [ ] 排除 legacy_diagnostic。
- [ ] 排除 engineering_smoke。
- [ ] 排除未知 purpose。
- [ ] 相同 Release 重复导入幂等。
- [ ] 字节变化或 Hash 冲突失败。

---

# 任务 5：Hash 绑定人工批准与撤销

建议新增：

```text
alphapilot_control_console/strategy_validation_approval_store.py
alphapilot_control_console/strategy_validation_approval_service.py
tests/test_strategy_validation_approval.py
tests/test_strategy_validation_approval_http.py
```

批准记录：

```text
approvalId
releaseId
releaseHash
riskConfigHash
action=approve|revoke
actor=human_local_operator
reason
createdAt
previousApprovalHash
recordHash
```

接口：

```http
POST /api/strategy-validation-releases/approve
POST /api/strategy-validation-releases/revoke
```

要求：

- [ ] 仅 loopback。
- [ ] 必须显式提供 Release ID、Hash、Risk Hash、理由。
- [ ] Append-only。
- [ ] 旧 Hash、风险配置变化、已撤销、非正式 Release 均拒绝。
- [ ] 不接收浏览器提供的 API Key。
- [ ] 批准不 ARM、不下单。
- [ ] 撤销后立即失去新订单资格。

---

# 任务 6：Runtime 准入

修改：

```text
alphapilot_control_console/evolution_demo_service.py
alphapilot_control_console/unified_auto_execution_runner.py
alphapilot_control_console/unified_auto_execution_controller.py
alphapilot_control_console/demo_release_scanner.py
tests/test_strategy_validation_runtime_admission.py
```

Runtime 发现条件：

```text
Release Hash 有效
Formal Evidence 有效
当前批准有效
Risk Profile Hash 有效
environment=demo
Demo Universe 新鲜可用
Runtime 已独立 ARM
未触发风险暂停
```

要求：

- [ ] 批准和 ARM 分离。
- [ ] 创建 Order Intent 前再次校验全部 Hash。
- [ ] Demo Universe stale / blocked 时失败关闭。
- [ ] Release Store / Approval Store 错误时失败关闭。
- [ ] 影子写入失败不能修改 Demo 执行判断。
- [ ] 工程烟测状态不能修改策略订单。

---

# 任务 7：策略验证 Demo 专用 Ledger

新增：

```text
alphapilot_control_console/strategy_validation_demo_store.py
alphapilot_control_console/strategy_validation_demo_models.py
tests/test_strategy_validation_demo_store.py
```

存储：

```text
data/strategy_validation_demo.sqlite
```

记录：

```text
Release
Order Intent
Exchange Order
Partial Fill
Position Snapshot
Fee
Funding
Reference Price
Slippage
Stop / Target
Exit / Cancel
Reconciliation Event
Risk Event
Closed Trade
Runtime Checkpoint
```

要求：

- [ ] 与工程烟测 Ledger 分离。
- [ ] 与影子数据分离。
- [ ] 与历史本地模拟分离。
- [ ] 货币和单位显式。
- [ ] UTC 原始时间 + 北京显示投影。
- [ ] 拒绝保存敏感字段。
- [ ] 闭合交易必须有已对账的入场和退出 Fill。
- [ ] clientOrderId、exchangeOrderId、fillId、closedTradeId 有唯一约束。

---

# 任务 8：策略验证 Demo 服务

新增 / 修改：

```text
alphapilot_control_console/strategy_validation_demo_service.py
alphapilot_control_console/demo_execution_engine.py
alphapilot_control_console/evolution_demo_service.py
tests/test_strategy_validation_demo_service.py
tests/test_strategy_validation_demo_recovery.py
```

接口：

```python
def run_strategy_validation_cycle(
    *,
    approvedReleases,
    universe,
    client,
) -> dict:
    ...

def reconcile_strategy_validation_demo(*, client) -> dict:
    ...

def recover_strategy_validation_runtime(*, client) -> dict:
    ...
```

必须测试：

```text
无匹配
匹配后风控拒绝
委托接受
部分成交
完整成交
持仓读取
止损退出
目标退出
Funding 更新
撤单
闭合交易
重启恢复
重复订单阻断
孤立持仓识别
真实 OKX 错误码
```

原则：

```text
不伪造成交
不伪造持仓
不使用公共币池替代 Demo 可交易交集
```

---

# 任务 9：风险网关与安全熔断

建议新增：

```text
alphapilot_control_console/strategy_validation_risk_gateway.py
alphapilot_control_console/strategy_validation_safety_valve.py
alphapilot_control_console/strategy_validation_risk_store.py
tests/test_strategy_validation_risk_gateway.py
tests/test_strategy_validation_safety_valve.py
```

风险检查：

```text
单笔最大 R
总开放风险
单币风险
相关簇风险
最大同时持仓
保证金占用
日损失
周损失
连续亏损
Demo 最大回撤
对账异常
数据陈旧
```

安全事件：

```text
risk_check_passed
risk_rejected
daily_loss_pause
consecutive_loss_pause
drawdown_pause
reconciliation_pause
manual_resume
approval_revoked
```

要求：

- [ ] 风险状态持久化。
- [ ] 重启可恢复。
- [ ] 熔断只暂停，不修改参数。
- [ ] 恢复必须人工、本地、带理由。
- [ ] 风险暂停不能自动撤销批准。
- [ ] 批准撤销必须阻止新 Order Intent。

---

# 任务 10：影子与 Demo 事件关联，禁止重复计票

影子观察和 Demo 订单使用共同：

```text
marketEventHash
```

要求：

```text
影子记录 = 实时信号诊断
Demo 闭合交易 = 前向成交证据
```

禁止：

```text
把同一事件的影子记录和 Demo 订单计作两份独立样本
```

影子不能包含：

```text
虚拟 PnL
模拟 Fill
模拟持仓
策略晋级字段
```

---

# 任务 11：前向复核

新增：

```text
alphapilot_control_console/strategy_validation_forward_review.py
tests/test_strategy_validation_forward_review.py
```

状态：

```text
0-29 闭合交易：收集中
30-99 闭合交易：初步复核可用
>=100 闭合交易：严肃复核可用
```

同时报告但不自动设门：

```text
日历覆盖
市场状态覆盖
币种覆盖
方向覆盖
真实手续费
Funding
参考价滑点
净 PnL
最大回撤
连续亏损
币种集中
月份集中
对账异常
订单拒绝率
部分成交率
```

硬规则：

```text
只有 strategy_validation_demo.sqlite 中已对账的闭合交易计数
```

以下不计入：

```text
开放订单
开放持仓
影子观察
工程烟测
legacy_diagnostic
历史本地模拟
```

30 和 100 不自动：

```text
批准 Live
创建 Live Candidate
提高风险
扩大仓位
```

---

# 任务 12：只读回测投影

新增：

```text
alphapilot_control_console/backtest_screening_projection.py
tests/test_backtest_screening_projection.py
tests/test_backtest_screening_http.py
```

接口：

```http
GET /api/backtest-screening?campaignId=<id>
```

读取第三阶段：

```text
数据就绪
外部参考
因子 Shortlist
预注册
事件预筛
完整回测
基础通过
正式通过
失败归因
预算
候选 Release
```

要求：

- [ ] 只读。
- [ ] 校验 Hash。
- [ ] 防路径穿越。
- [ ] 不触发回测、下载、Release 生成、批准或 Demo。
- [ ] 0 正式通过正常显示。

---

# 任务 13：Strategy 页面

显示：

```text
数据就绪
外部参考和 License
因子实验室
因子 Shortlist
预注册 Campaign
事件预筛
完整回测
基础通过
正式通过
失败归因
预算
待批准不可变 Release
```

排序不能只看收益：

```text
正式状态
OOS PF
平均净 R
1.5x PF
正 Fold 比例
最大回撤
集中度
样本量
证据完整性
```

高级信息折叠：

```text
Hash
Fold
成本
FDR
因子来源
外部参考
```

不提供：

```text
绕过按钮
强制批准
自动 ARM
```

---

# 任务 14：Demo 页面证据隔离

区域一：Demo 工程状态

```text
Runtime
认证合约数
公共 / Demo 交集
工程订单
工程持仓
退出
对账
重复 / 孤立
```

区域二：策略验证 Demo

```text
已批准 Release
扫描 / 匹配 / 风控 / 委托
订单和持仓
入场、止损、目标
手续费、Funding、滑点
净 PnL
闭合交易
前向复核状态
阻塞和下一动作
风险暂停
```

要求：

```text
工程数字不进入策略 PF、胜率、PnL 或样本
legacy_diagnostic 不进入活跃列表
历史本地模拟不显示为当前阶段
```

---

# 任务 15：端到端测试

必须覆盖：

```text
formal pass
→ immutable release
→ import
→ waiting approval
→ explicit approval
→ Runtime ARM
→ Demo universe
→ signal
→ risk
→ order
→ fill
→ position
→ exit
→ reconciliation
→ closed trade
→ review count
```

失败路径：

```text
basic-only
failed
missing factor hash
changed factor definition
changed data snapshot
changed release bytes
revoked
legacy
engineering
shadow-only
local-history
wrong environment
stale universe
risk pause
```

验证：

```text
批准不 ARM
ARM 不批准
风险熔断不调参
重启不重复下单
孤立持仓可识别
```

---

# 任务 16：安全和运行验收

Console：

```powershell
python -m unittest discover -s tests -v
python -m compileall alphapilot_control_console
node --check web/app.js
python -m alphapilot_control_console.http_app --smoke
git diff --check
```

Quant：

```powershell
python -m pytest tests -q
python -m compileall alphapilot
python -m alphapilot.scripts.validate_config
powershell -ExecutionPolicy Bypass -File scripts\check_safety.ps1
git diff --check
```

扫描：

```text
raw credential
browser API key
Withdraw
Live order
auto approval
auto ARM
local simulation writes
cross-ledger aggregation
AI hot tuning
stop widening
martingale
```

---

# 任务 17：提交、推送与 Tag

建议提交：

Quant：

```text
Add factor-lineage formal strategy-validation releases
```

Console：

```text
Cut over to approved strategy-validation Demo v2
```

Docs：

```text
Document updated Phase 3 and Phase 4 workflow
```

要求：

```text
每仓库独立测试
独立 Commit
独立 Push
工作区清楚
Tag 不覆盖现有版本
```

本阶段禁止：

```text
Live Tag
Live Release
Live Approval
Canary 实现
```

---

## 6. 第四阶段退出门

必须同时满足：

```text
非正式证据不能生成 Release
Release 包含完整数据和因子谱系
每条可执行 Release 有当前人工批准
Risk Profile Hash 冻结
Demo Universe 使用阶段 1 权威交集
工程与策略 Ledger 分离
影子与 Demo 不重复计票
只有已对账闭合策略 Demo 交易计入复核
风险熔断可持久化和恢复
风险熔断不修改策略
UI 不存在活跃本地模拟阶段
Live / Withdraw 完全关闭
```

### 0 正式通过路径

```text
生成 0 条 Release
导入 0 条
批准 0 条
策略验证 Demo 保持空
工程烟测和影子观察继续可用
阶段 4 仍可完成基础准入框架
```

### 存在正式通过路径

```text
最多生成 3 条 Release
默认未批准
用户明确批准后才可被 Runtime 发现
Runtime 还需独立 ARM
```

---

## 7. Codex 最终自检

必须输出：

```text
第三阶段 Campaign ID
正式通过数量
Release 数量
每条 Release Hash
市场机制 ID
因子定义 Hash
数据 Snapshot Hash
预注册 Hash
Risk Config Hash
导入状态
批准状态
Runtime ARM 状态
Demo Universe 状态
订单尝试
委托 / 成交 / 持仓 / 退出
重复订单
孤立持仓
风险拒绝
风险暂停
影子事件数
策略 Demo 闭合交易数
前向复核状态
工程烟测是否进入策略统计
旧 Release 是否进入活跃列表
本地模拟是否重新写入
是否 AI 热调参
是否放宽止损
是否访问 Live
是否接 Withdraw
是否创建 Live 订单
全部测试
Commit / Push / Tag
已知问题
下一步建议
```

---

## 8. 最终原则

```text
正式回测通过 ≠ 自动 Demo
人工批准 ≠ 自动 ARM
工程烟测 ≠ 策略成绩
影子观察 ≠ 成交证据
Demo 闭合交易 ≠ 实盘批准
风险系统只阻断，不创造 Alpha
策略变化必须创建新版本并回到第三阶段
```

第四阶段结束后，下一步只能是：

```text
继续收集策略验证型 Demo 闭合交易
或
由独立后续版本评估小额实盘 Canary
```

本阶段绝不实现 Live Canary。
