"""Typed failures raised before AlphaPilot can trust an AI result."""


class AIOrchestrationError(RuntimeError):
    """Base error for the research-only AI boundary."""


class ModelRegistryError(AIOrchestrationError):
    pass


class ForbiddenAITaskError(AIOrchestrationError):
    pass


class SensitiveDataError(AIOrchestrationError):
    pass


class ToolPolicyError(AIOrchestrationError):
    pass


class OutputValidationError(AIOrchestrationError):
    pass


class ProviderResponseError(AIOrchestrationError):
    pass


class ProviderUnavailableError(AIOrchestrationError):
    pass


class BudgetExceededError(AIOrchestrationError):
    pass


class BatchConflictError(AIOrchestrationError):
    pass
