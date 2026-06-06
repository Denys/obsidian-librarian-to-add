from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Status = Literal["ok", "needs_approval", "blocked", "error", "unavailable", "needs_review"]
Workflow = Literal["deployment", "inventory", "librarian", "patron", "mixed", "unknown"]
SafetyTier = Literal[
    "read_only",
    "infrastructure_write",
    "staging_write",
    "opt_in_ocr_or_llm",
    "gui_launch",
    "promotion",
    "force_overwrite",
]


class PlannedCommand(BaseModel):
    label: str
    argv: list[str]
    requires_approval: bool = False
    required_approvals: list[str] = Field(default_factory=list)


class ExecutedCommand(BaseModel):
    label: str
    argv: list[str]
    exit_code: int | None = None
    duration_ms: int = 0
    timed_out: bool = False
    stdout: str = ""
    stderr: str = ""


class Artifact(BaseModel):
    kind: str
    path: str
    description: str


class ToolResult(BaseModel):
    status: Status
    workflow: Workflow = "unknown"
    safety_tier: SafetyTier = "read_only"
    summary: str = ""
    required_approvals: list[str] = Field(default_factory=list)
    planned_commands: list[PlannedCommand] = Field(default_factory=list)
    executed_commands: list[ExecutedCommand] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)


class DeploymentResult(BaseModel):
    status: Status
    target_root: str
    profile: str
    mode: str
    planned_paths: list[str] = Field(default_factory=list)
    created_paths: list[str] = Field(default_factory=list)
    required_approvals: list[str] = Field(default_factory=list)
    writes_performed: bool = False
    summary: str = ""


class InventoryItem(BaseModel):
    path: str
    relative_path: str
    suffix: str
    size_bytes: int
    modified_time: float
    sha256: str
    route: Literal["unclassified", "librarian", "patron", "manual_review", "unsupported"] = (
        "unclassified"
    )
    reason: str = ""


class InventoryResult(BaseModel):
    status: Status
    target_root: str
    items: list[InventoryItem] = Field(default_factory=list)
    summary: dict[str, int] = Field(default_factory=dict)
    artifact_path: str | None = None


class IngestWave(BaseModel):
    status: Status
    target_root: str
    items: list[InventoryItem] = Field(default_factory=list)
    required_approvals: list[str] = Field(default_factory=list)
    summary: str = ""


class HealthResult(BaseModel):
    status: Status
    app: str = "olp-agents-sdk-agent"
    olp_repo_root: str
    olp_python: str
    target_library: str | None = None
    openai_api_key_present: bool = False
    agents_sdk_available: bool = False
    checks: dict[str, str] = Field(default_factory=dict)


class AgentResult(BaseModel):
    status: Status
    intent: str = ""
    target_root: str | None = None
    workflow: Workflow = "unknown"
    safety_tier: SafetyTier = "read_only"
    planned_commands: list[PlannedCommand] = Field(default_factory=list)
    executed_commands: list[ExecutedCommand] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    inventory_summary: dict[str, int] = Field(default_factory=dict)
    summary: str = ""
    next_actions: list[str] = Field(default_factory=list)
