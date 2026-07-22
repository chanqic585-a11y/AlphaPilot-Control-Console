# V13.27.1.62 Test Results

| Repository | Check | Result |
| --- | --- | --- |
| Console | Full pytest | 731 passed, 108 subtests passed |
| Console | compileall | Passed |
| Console | JavaScript syntax | Passed |
| Console | UI browser acceptance | Passed |
| Console | git diff --check | Passed |
| Quant | pytest tests --import-mode=importlib | 1384 passed, 164 subtests passed |
| Quant | compileall | Passed |
| Quant | validate_config | Passed; Live, Trade API, and Withdraw disabled |
| Quant | check_safety.ps1 | Passed |
| Quant | git diff --check | Passed |
| Docs | git diff --check | Passed |

The initial repository-root Quant pytest attempt was intentionally discarded as non-authoritative because it collected the separately packaged `third_party/tradingagents` test tree and its unrelated optional dependencies. No product failure was hidden.
