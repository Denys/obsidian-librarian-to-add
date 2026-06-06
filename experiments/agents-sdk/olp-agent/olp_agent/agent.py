from __future__ import annotations

import asyncio
import os

from olp_agent.schemas import AgentResult
from olp_agent import tools as olp_tools

AGENT_INSTRUCTIONS = """You are the OLP folder-deployment and library-ingestion operator.

The OLP source repo is not a library. A target folder such as AudioDSP_example_library is the
library candidate. Use the provided OLP tools. Do not invent shell commands. If approval is
missing, return needs_approval with exact required approval flags.

For target folders, first resolve environment, inspect deployment state, scan contents, then plan
the smallest useful ingest wave. For every librarian command, pass explicit --vault. For librarian
ingest, pass explicit --mode. For Patron, use slug terminology.

Never delete files, rewrite raw source files, write outside the target root, OCR, call OpenAI from
OLP, launch GUI, promote, unpromote, or force overwrite without the matching approval flag.
"""


def _sdk_imports():
    from agents import Agent, Runner, function_tool  # type: ignore

    return Agent, Runner, function_tool


def create_agent():
    Agent, _Runner, function_tool = _sdk_imports()
    tool_functions = [
        olp_tools.resolve_olp_environment,
        olp_tools.deploy_library_folder_tool,
        olp_tools.scan_library_folder_tool,
        olp_tools.classify_library_contents_tool,
        olp_tools.plan_ingest_wave_tool,
        olp_tools.run_librarian_ingest_preview,
        olp_tools.run_librarian_ingest_draft,
        olp_tools.run_librarian_validate,
        olp_tools.run_librarian_review_quality,
        olp_tools.run_librarian_enrich,
        olp_tools.run_librarian_index,
        olp_tools.run_librarian_search,
        olp_tools.run_librarian_report,
        olp_tools.launch_librarian_gui,
        olp_tools.run_patron_ingest,
        olp_tools.run_patron_propose,
        olp_tools.run_patron_link,
        olp_tools.run_patron_unmatched,
        olp_tools.run_patron_status,
        olp_tools.run_patron_promote,
        olp_tools.run_patron_unpromote,
        olp_tools.read_agent_state,
        olp_tools.read_olp_artifact,
    ]
    return Agent(
        name="OLP Folder Deployment Agent",
        model=os.getenv("OLP_AGENT_MODEL", "gpt-5.4-mini"),
        instructions=AGENT_INSTRUCTIONS,
        tools=[function_tool(func) for func in tool_functions],
        output_type=AgentResult,
    )


async def run_agent_request(request: str) -> AgentResult:
    if not os.getenv("OPENAI_API_KEY"):
        return AgentResult(
            status="blocked",
            intent=request,
            summary="OPENAI_API_KEY is not set; live Agents SDK run was not attempted.",
            next_actions=["Set OPENAI_API_KEY or use deterministic CLI commands such as health/scan."],
        )
    _Agent, Runner, _function_tool = _sdk_imports()
    result = await Runner.run(create_agent(), request)
    final = result.final_output
    if isinstance(final, AgentResult):
        return final
    return AgentResult(status="ok", intent=request, summary=str(final))


def run_agent_request_sync(request: str) -> AgentResult:
    return asyncio.run(run_agent_request(request))
