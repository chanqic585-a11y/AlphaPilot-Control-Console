"""Small HTTP-facing adapter for immutable strategy execution policies."""

from __future__ import annotations

from typing import Any

from .strategy_execution_policy_store import StrategyExecutionPolicyStore


class StrategyExecutionPolicyApi:
    ROOT = "/api/strategy-execution-policies"

    def __init__(self, store: StrategyExecutionPolicyStore) -> None:
        self.store = store

    @staticmethod
    def _query_value(query: dict[str, list[str]], key: str) -> str | None:
        values = query.get(key) or []
        value = str(values[0]).strip() if values else ""
        return value or None

    def get(self, path: str, query: dict[str, list[str]]) -> dict[str, Any]:
        suffix = path.removeprefix(self.ROOT).strip("/")
        if not suffix:
            return {
                "policies": self.store.list_policies(
                    environment=self._query_value(query, "environment"),
                    strategy_id=self._query_value(query, "strategyId"),
                ),
                "readOnly": True,
            }
        if suffix.endswith("/events"):
            policy_id = suffix.removesuffix("/events").strip("/")
            policy = self.store.get_policy(policy_id)
            return {
                "policyId": policy_id,
                "events": self.store.list_events(policy["policyKey"]),
                "readOnly": True,
            }
        return {"policy": self.store.get_policy(suffix), "readOnly": True}

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        suffix = path.removeprefix(self.ROOT).strip("/")
        if suffix == "bootstrap":
            identity = payload.get("identity")
            if not isinstance(identity, dict):
                raise ValueError("identity object is required")
            return {
                "ok": True,
                "policy": self.store.bootstrap_policy(identity),
                "executionEnabled": False,
            }
        if not suffix:
            policy = payload.get("policy")
            if not isinstance(policy, dict):
                raise ValueError("policy object is required")
            return {
                "ok": True,
                "policy": self.store.create_policy(policy),
                "executionEnabled": False,
            }
        if suffix.endswith("/revisions"):
            policy_id = suffix.removesuffix("/revisions").strip("/")
            changes = payload.get("changes")
            if not isinstance(changes, dict):
                raise ValueError("changes object is required")
            return {
                "ok": True,
                "policy": self.store.create_revision(policy_id, changes),
                "executionEnabled": False,
            }
        if suffix.endswith("/activate"):
            policy_id = suffix.removesuffix("/activate").strip("/")
            result = self.store.activate(
                policy_id,
                actor="user_manual",
                confirmation=str(payload.get("confirmation") or ""),
                reason=str(payload.get("reason") or "operator_strategy_policy_activation"),
            )
            return {"ok": True, **result}
        raise KeyError("Strategy execution policy route not found")


def read_strategy_execution_policy_api(
    path: str,
    query: dict[str, list[str]],
) -> dict[str, Any]:
    store = StrategyExecutionPolicyStore()
    try:
        return StrategyExecutionPolicyApi(store).get(path, query)
    finally:
        store.close()


def write_strategy_execution_policy_api(
    path: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    store = StrategyExecutionPolicyStore()
    try:
        return StrategyExecutionPolicyApi(store).post(path, payload)
    finally:
        store.close()
