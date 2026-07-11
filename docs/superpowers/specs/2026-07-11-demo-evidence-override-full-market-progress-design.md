# V13.27.1.4 Demo 证据、受控放行、全市场扫描与进度设计

## 目标

V13.27.1.4 让操作员始终看得见每条策略距离 OKX Demo 还缺什么，并能在明确审计和安全边界下仅跳过本地前向样本门槛进入 Demo。Demo 候选不再绑定单一币种，而是按冻结的策略规则扫描 OKX 全部可交易 USDT 线性永续合约。所有运行中的回测、前向和 Demo 流程统一显示真实或阶段型进度。

## 不变安全边界

- 受控放行仅创建 `experimental_override` Demo Release。
- 正式回测、目标盈亏比 `>= 2R`、完整策略定义和风险配置不能被跳过。
- 放行理由、确认短语、时间和结果必须写入审计日志。
- 放行不能创建实盘候选，不能开启实盘，不能绕过凭据、订单、自动化、停止开关或对账闸门。
- Runtime API 凭据继续只存在于进程环境，不写入仓库或本地状态。
- 全市场扫描只使用 OKX 公共 instruments、tickers、candles 和 instrument metadata。

## 永久证据清单

每张 Demo 策略卡始终返回并展示 `evidenceChecklist`。每项包含：

```text
evidenceId
label
status: passed | missing | bypassed | pending
current
target
sourceType: automatic | manual_runtime | controlled_override
blocking
detail
nextAction
```

清单至少覆盖正式回测、2R、策略定义、本地前向闭合样本、正式候选登记、不可变 Demo Release、Demo Runtime 和闭合 Demo 交易。系统自动采集的证据标记“系统自动”，需要操作员启动环境或确认放行的证据标记“人工操作”。

## 受控 Demo-only 放行

操作员可在证据卡中选择“仅放行到 OKX Demo”。请求必须包含非空理由，并精确输入确认短语：

```text
仅放行到OKX DEMO
```

服务端仍检查正式回测存在、目标 R 不低于 2、策略定义完整和有效 Demo 风险包。成功后：

1. 登记不可变的正式策略候选身份。
2. 创建内容哈希稳定的 `experimental_override` Demo Release。
3. 写入放行审计，记录理由、操作时间和被绕过的本地前向样本证据。
4. 将策略留在 Demo 队列；不创建订单，订单仍由独立 Demo Runtime 闸门控制。
5. Release 明确设置 `livePromotionAllowed=false`，后续投影不得自动形成实盘候选。

## OKX 全市场分层扫描

Release 冻结的是市场选择政策和策略规则，不冻结某一个币种。每次扫描按以下顺序运行：

1. 读取 OKX public instruments 与全部 SWAP tickers。
2. 仅保留 `state=live`、`*-USDT-SWAP`、线性永续、价格和成交量有效、买卖价差有效的合约。
3. 以公共成交额代理、价差和上市状态排序。
4. 只对排名前 N 个流动性合格合约读取 OHLCV 和指标，限制公共接口负载。
5. 用冻结策略规则评分，生成匹配、拒绝原因和数据新鲜度。
6. 由现有策略仲裁、并发、风险和持仓闸门决定是否形成 Demo 信号。

页面显示全市场总合约数、已扫描数、流动性合格数、策略匹配数、当前首选候选和候选排名。没有真实成交前，“交易币种”改为“当前首选候选”；实际订单或持仓币种单独展示。

## 每策略同时开仓币种数

每条策略新增 Demo 执行偏好 `maxConcurrentSymbols`，默认值为 `1`。操作员可在 Demo 卡片上调整，但最终有效值必须取以下限制的最小值：

```text
策略 maxConcurrentSymbols
组合 RiskProfile.maxConcurrentPositions
当前剩余组合持仓槽位
当前剩余风险预算可支持的仓位数
扫描后真正匹配且通过流动性门槛的候选数
```

该配置只决定同一策略最多可同时持有多少个不同币种，不能放大单笔风险、杠杆、订单名义金额或组合总风险。重复币种、已有持仓、相关性冲突和风险预算不足仍由现有仲裁与风控拒绝。设置需要写入本地审计状态，不保存任何凭据。

Demo 卡片只显示“全市场扫描、匹配数、允许持仓数、当前持仓数”和紧凑持仓列表；候选排名放在折叠详情。实盘页复用同一监控信息结构，但默认只显示已启用策略、实际持仓、浮动/已实现盈亏、组合风险和停止状态，研究证据与候选排名放入折叠详情。

## 统一运行进度

统一进度对象：

```text
mode: determinate | phase
status: queued | running | paused | completed | failed | blocked | cancelled
phase
label
completed
required
percent
detail
```

- 已知总量时，`percent = completed / required`，显示进度条、百分比和数量。
- 不知道总量时，使用明确的阶段步骤进度，不伪造耗时百分比。
- `queued`、`running`、`paused` 都保留进度条；暂停显示已完成位置。
- 回测使用现有双层回测阶段和官方下载进度。
- 全市场扫描使用合约扫描数量。
- Demo 工作流使用 6 个固定流程步骤并显示闭合交易数。
- 已完成显示 100%，失败和阻塞保留最后真实进度。

## 模块边界

- `demo_evidence.py`：构建永久证据清单和放行硬门槛判断。
- `okx_market_universe.py`：纯函数过滤排序和公共全市场加载。
- `demo_override_release.py`：验证、生成、持久化、审计 Demo-only Release。
- `demo_release_scanner.py`：支持动态全市场策略池和扫描统计。
- `demo_workflow_service.py`：编排全市场扫描、证据核对和受控放行。
- `demo_strategy_runtime_settings.py`：保存并审计每策略 Demo 同时开仓币种上限。
- `demo_workflow_projection.py`：把证据、市场统计、持仓和进度投影给 UI。
- `web/app.js`、`web/styles.css`：证据清单、全市场摘要、受控放行对话和统一进度条。

## 验收

1. Demo 卡永久显示证据缺项、当前值、目标值、来源和下一步。
2. 受控放行缺理由、确认短语错误、无正式回测、低于 2R 或定义不完整时失败关闭。
3. 放行成功仅创建 Demo Release，审计存在且实盘仍锁定。
4. 全市场过滤和排序可由固定 payload 单元测试复现。
5. 页面不再把首选候选误称为已交易币种。
6. 回测、全市场扫描、前向和 Demo 运行态均有进度条。
7. 所有 Python 测试、JS 语法检查、浏览器验收和安全扫描通过。
8. 每策略并发币种设置受组合风险硬上限约束，页面显示请求值和实际有效值。
9. Demo 与实盘使用一致的监控术语，实盘页面保持更精简。
