# AlphaPilot V13.15.2 OKX Demo Secure Integration Design

## 1. Decision

本阶段采用用户确认的方案 2：先加固 OKX Demo 接入，再立即进入方案 3 的 Demo 订单技术验证。

凭据和站点决定：

- 使用一把 OKX Demo Read + Trade Key。
- Key 必须在 OKX Demo Trading 页面创建。
- 不允许 Withdraw 权限。
- 账户属于全球站，REST 域名固定为 `https://openapi.okx.com`。
- 所有 Demo 私有请求必须携带 `x-simulated-trading: 1`。
- Key、Secret、Passphrase 只存在于启动进程内，不写入文件、浏览器、SQLite 或日志。

## 2. Goal

建立一条单一、可审计、故障关闭的 OKX Demo 私有连接链路：

1. 安全读取单一 Read + Trade Demo Key。
2. 验证账户配置、模拟余额和模拟持仓。
3. 清除旧服务中的重复签名实现。
4. 所有私有请求统一经过 allowlisted `OkxDemoClient`。
5. 完成加固后可直接进入 Demo 订单技术烟雾验证。
6. 策略自动执行仍只接受不可变 `DemoRelease`，不使用旧候选池或本地样本数代替晋级决定。

## 3. Current State

仓库已经具备：

- `scripts/start_okx_demo_console.ps1`
- `credential_runtime.py`
- `exchange_connectors/okx_demo_client.py`
- `exchange_demo_simulation.py`
- `demo_execution_engine.py`
- `demo_execution_store.py`
- Demo 风险包、幂等键、故障暂停和撤单能力
- 控制台只读检查和 Demo 页面

现有主要问题：

1. `exchange_demo_simulation.py` 内仍有独立的签名和 HTTP 请求实现。
2. `okx_demo_client.py` 又维护一套 allowlisted 客户端，形成双实现。
3. 旧候选扫描和票据路径可以绕开正式 `DemoRelease` 语义。
4. 当前生命周期真实状态为 Demo Release 0，不能伪造策略自动执行资格。
5. 连接状态、只读检查状态和策略执行资格需要在 UI 中明确分开。

## 4. Architecture

### 4.1 Credential Boundary

启动器继续使用 `Read-Host -AsSecureString` 读取三项凭据：

- API Key
- Secret Key
- Passphrase

启动器只向当前 Python 子进程注入：

```text
ALPHAPILOT_OKX_DEMO_API_KEY
ALPHAPILOT_OKX_DEMO_SECRET_KEY
ALPHAPILOT_OKX_DEMO_PASSPHRASE
ALPHAPILOT_OKX_DEMO_ENABLED=1
ALPHAPILOT_OKX_SITE=global
```

首次加固连接时：

```text
ALPHAPILOT_OKX_DEMO_ORDER_ENABLED=0
ALPHAPILOT_OKX_DEMO_AUTOMATION_ENABLED=0
ALPHAPILOT_OKX_DEMO_CANCEL_ENABLED=0
```

进程退出后由 `finally` 清理所有相关环境变量。

### 4.2 Site Boundary

新增显式站点映射，但本阶段固定使用 `global`：

```text
global -> https://openapi.okx.com
us     -> https://us.okx.com
eea    -> https://eea.okx.com
```

不根据 IP、语言、时区或系统区域自动推断站点。非 allowlist 域名必须本地拒绝。

### 4.3 Single Private Client

所有 OKX Demo 私有 REST 调用统一经过：

```text
alphapilot_control_console/exchange_connectors/okx_demo_client.py
```

`exchange_demo_simulation.py` 不再自行：

- 读取 raw credential 值
- 计算签名
- 构造私有 HTTP 请求
- 选择私有 API 域名

它只负责：

- 业务闸门
- 输入校验
- 调用 `OkxDemoClient`
- 生成脱敏状态摘要
- 保存不含敏感信息的审计事件

### 4.4 Endpoint Allowlist

加固阶段允许以下只读接口：

```text
GET /api/v5/account/config
GET /api/v5/account/balance
GET /api/v5/account/positions
GET /api/v5/trade/order
GET /api/v5/trade/orders-pending
GET /api/v5/trade/fills
```

方案 3 技术验证阶段只允许：

```text
POST /api/v5/trade/order
POST /api/v5/trade/cancel-order
POST /api/v5/trade/cancel-all-after
```

Withdraw、transfer、deposit、sub-account key、live domain 和任意未列出的路径一律本地拒绝。

### 4.5 Read-only Connection Check

`POST /api/exchange-demo/read-only-check` 按顺序执行：

1. 验证 `global` 域名 allowlist。
2. 验证三项凭据仅存在于进程内。
3. 调用 account config。
4. 调用 Demo balance。
5. 调用 Demo SWAP positions。
6. 检查所有响应顶层 `code == "0"`。
7. 返回脱敏摘要。
8. 保存审计事件。

审计事件只允许保存：

- 检查时间
- 请求类型
- HTTP 状态
- OKX 顶层 code
- 是否使用 Demo header
- 是否通过
- 标准化 blocker code

不得保存：

- Key、Secret、Passphrase
- 请求签名和私有请求头
- 完整余额 payload
- 完整持仓 payload
- 用户 UID、账户标识或可恢复敏感信息

### 4.6 Demo Order Technical Validation

加固和只读检查通过后，可以直接进入方案 3 的技术验证，但分成两条完全不同的通道。

#### Connectivity Smoke Channel

用于验证订单基础设施，不代表策略晋级：

- 必须显式使用 `-EnableOrder`。
- 必须人工确认一次测试动作。
- 必须使用 OKX Demo 环境。
- 必须服从 1000 USDT Demo 账户风险包和单笔名义上限。
- 测试记录标记为 `connectivity_smoke_only`。
- 不进入策略胜率、盈亏或晋级样本。
- 不生成 `DemoRelease` 或 `LiveCandidatePackage`。

#### Strategy Automation Channel

用于正式策略 Demo 验证：

- 必须同时使用 `-EnableOrder -EnableAutomation`。
- 必须读取不可变、校验通过的 `DemoRelease`。
- Release 必须绑定策略内容哈希、风险包和 OKX Demo only 边界。
- 没有 Release 时返回 `no_eligible_demo_release`，不提交订单。
- 本地 30 个闭合样本、旧 promoted candidate、旧票据和 UI 选择不能替代 Release。

## 5. UI Design

Demo 页面主区域只显示四个状态：

1. 凭据：未加载 / 已临时加载
2. 私有连接：未检查 / 通过 / 失败
3. 订单技术验证：关闭 / 可测试 / 已通过 / 暂停
4. 策略自动执行：无 Release / 待运行 / 运行中 / 已暂停

页面不显示：

- raw credential
- Key 片段
- 完整私有响应
- 旧通用候选池
- 旧“行情可用组合数”

高级折叠区可以保留连接日志和标准化 blocker，但不恢复旧策略票据作为主入口。

## 6. Failure Handling

以下任一情况必须故障关闭：

- 域名不是 global allowlist
- Demo header 缺失
- 凭据不完整
- OKX code 非 0
- 网络超时且订单状态未知
- 订单重复提交
- 没有正式 Demo Release
- Release hash 不匹配
- 风险包未通过
- kill switch 已激活
- 进程未显式开启对应开关

订单请求超时后不得自动重试。必须先查询 `clOrdId` 或订单状态，无法确认时暂停自动执行。

## 7. Testing

### Unit Tests

- global 域名允许，非 allowlist 域名拒绝
- 每个私有请求包含 `x-simulated-trading: 1`
- 签名包含完整 request path 和 body
- credential repr 和状态不泄露 raw secret
- 只读检查调用 config、balance、positions
- 审计事件不包含敏感字段和完整 payload
- 未开启 order gate 时拒绝下单
- 无 Demo Release 时自动执行拒绝下单
- connectivity smoke 不进入策略指标
- 重复 signal 只创建一个 Demo order intent
- 未知订单状态触发暂停
- withdraw 和 live 路径本地拒绝

### Integration Checks

在用户本机安全输入 Demo Key 后：

1. 启动只读模式。
2. 验证 account config code 0。
3. 验证 balance code 0。
4. 验证 positions code 0。
5. 检查控制台不显示 raw credential。
6. 检查日志和 SQLite 不包含 raw credential。
7. 再单独启动 `-EnableOrder` 进行 connectivity smoke。
8. 只有存在正式 Demo Release 时才测试 `-EnableAutomation`。

## 8. Non-goals

本阶段不做：

- 实盘 API Key
- 实盘域名和实盘订单
- Withdraw、transfer 或 deposit
- 自动生成或伪造 Demo Release
- 用 connectivity smoke 充当策略样本
- 绕过生命周期晋级
- 保存 raw credential
- 手机端输入 Key

## 9. Acceptance Criteria

1. 单一 Read + Trade Demo Key 由启动器安全读取。
2. 站点固定 global，私有 REST 域名固定 `openapi.okx.com`。
3. 私有请求统一经过 `OkxDemoClient`。
4. 旧服务不再维护重复签名和私有 HTTP 实现。
5. 只读检查覆盖 account config、balance、positions。
6. 返回和持久化内容不包含 raw credential 或完整私有 payload。
7. 默认启动不允许订单、自动执行或撤单。
8. 加固通过后可进入单独的 connectivity smoke。
9. connectivity smoke 不影响策略研究指标。
10. 自动策略订单必须绑定不可变 Demo Release。
11. 当前 Release 为 0 时自动化保持阻塞。
12. 实盘和 Withdraw 始终关闭。
13. 所有单元测试、smoke、`git diff --check` 和安全扫描通过。

## 10. Transition To Approach 3

完成本设计后不需要等待另一个版本即可开始方案 3 的技术验证：

```text
加固完成
-> 用户安全输入单一 Read + Trade Demo Key
-> 只读检查通过
-> connectivity smoke order
-> 查询订单状态
-> 必要时撤单或 kill switch 演练
-> 等待正式 Demo Release
-> 开启策略自动 Demo 执行
```

技术链路可以立即验证，策略自动运行资格不能伪造。
