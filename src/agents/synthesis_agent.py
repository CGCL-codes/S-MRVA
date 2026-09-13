"""Synthesis Agent — one-step LangGraph workflow with 3-step prompt (§4.2.3).

The LLM is guided through three internal steps in a single prompt:
  Step 1: Semantic alignment — trim irrelevant code from insightful snippet.
  Step 2: Substitute & reconnect — replace mapped region, reconnect data flow.
  Step 3: Self-containment — add imports and initialization for new code.
"""

import json
import operator
import re
from typing import Any, Dict, List, Optional
from typing_extensions import Annotated, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END


SYSTEM_PROMPT = """[ System Prompt ]
You are a security test synthesis expert with deep expertise in secure coding,
static-analysis testing, and cross-language code transformation (Java, Python,
C/C++, and others). You craft realistic variants of seed test cases that
stress-test static analysis rules. Only answer strictly in the following output
format following the output format instructions.

[ Task / User Prompt ]
Synthesize a variant from a seed test case and a real-world insightful snippet
by following these THREE internal steps.

Step 1 — Semantic Alignment
- Trim the insightful snippet to its security-relevant core.
- Remove irrelevant statements (logging, comments, unrelated logic).
- Preserve the risky structure: the alternative API call (FN direction)
  or the mitigation/remediation check (FP direction).
- Keep variable declarations and data-flow edges the pattern depends on.
- Output a minimal but valid {language} fragment.

Step 2 — Substitute & Reconnect
- Replace ONLY the mapped code region in the seed with the trimmed snippet.
- Keep ALL code outside the mapped region COMPLETELY unchanged.
- Reconnect local data flow using variables/values already present in the seed.
- The variant must be realistic and may bypass the detection rule.

Step 3 — Self-Containment
- Make the final code self-contained.
- Add any missing imports / package declarations / initialization.
- Do NOT change existing logic, variable names, or control flow.

Run context:
Rule goal: {rule_goal}
Target predicate: {predicate_goal}

[ Do and Do Not ]
Do:
- Keep every line outside the mapped region byte-for-byte identical.
- Preserve the security-relevant data flow so the variant keeps its intended
  risk direction.
- Produce syntactically valid, self-contained code in the target language.
- Return only the tagged output requested in the Output Format section.
Do Not:
- Do not rename, reorder, or delete existing variables and statements outside
  the mapped region.
- Do not add unrelated features, comments, or dead code.
- Do not output anything other than the <mutated_code> and <mutation_summary> tags.

[ Few-shot Example ]
Task: transform the seed so the command-execution sink uses a different API that
the rule may miss (FN direction).

Seed:
    import os
    os.system('echo hello')

Mapped code region (to replace):
    os.system('echo hello')

Insightful snippet (from real-world code):
    subprocess.run('echo hello', shell=True)

Expected output:
<mutated_code>
import subprocess
subprocess.run('echo hello', shell=True)
</mutated_code>
<mutation_summary>
Replaced os.system('echo hello') with subprocess.run('echo hello', shell=True), preserving the same shell-command effect while evading os.system-based detection.
</mutation_summary>

[ Output Format ]
Use EXACTLY these two tags:
<mutated_code>
...final self-contained synthesized test case...
</mutated_code>
<mutation_summary>
...one line describing what changed from the seed and why...
</mutation_summary>
"""


SYNTHESIS_PROMPT = """[ System Prompt ]
You are a security test synthesis expert who follows the three-step synthesis
method (Semantic Alignment, Substitute & Reconnect, Self-Containment) from the
system instructions. Only answer strictly in the following output format
following the output format instructions.

[ Task / User Prompt ]
Synthesize one {language} variant by applying the three steps to the seed test
case below.

Risk type: {risk_type}

----------------------------- SEED TEST CASE ---------------------------------
```{language}
{current_seed}
```

---------------------- MAPPED CODE REGION (to replace) ----------------------
```{language}
{mapped_code}
```

---------------------- INSIGHTFUL SNIPPET (from real-world code) ------------
Insight reason: {insight_reason}
```{language}
{insightful_snippet}
```

[ Do and Do Not ]
Do:
- Replace ONLY the mapped code region; keep every other line of the seed identical.
- Reconnect data flow using variables and values already defined in the seed.
- Preserve the intended risk direction (FN keeps the vulnerability, FP applies
  a minimal secure fix).
- Make the output self-contained: add any missing imports, package declarations,
  and initialization.
- Return only the tagged output from the Output Format section.
Do Not:
- Do not change, rename, or remove code outside the mapped region.
- Do not invent variables or values that are not present in the seed or the snippet.
- Do not include explanations, markdown, or any text outside the two tags.

[ Few-shot Example ]
Task (FN direction): the detection rule only flags Statement.executeQuery() with
string concatenation; produce a variant that keeps the SQL injection sink through
a different API.

Seed:
    String name = request.getParameter("name");
    Statement stmt = conn.createStatement();
    ResultSet rs = stmt.executeQuery("SELECT * FROM users WHERE name = '" + name + "'");

Mapped code region (to replace):
    ResultSet rs = stmt.executeQuery("SELECT * FROM users WHERE name = '" + name + "'");

Insightful snippet (real-world alternative):
    boolean ok = stmt.execute("SELECT * FROM users WHERE name = '" + name + "'");

Expected output:
<mutated_code>
String name = request.getParameter("name");
Statement stmt = conn.createStatement();
boolean ok = stmt.execute("SELECT * FROM users WHERE name = '" + name + "'");
</mutated_code>
<mutation_summary>
Switched the taint sink from stmt.executeQuery(...) to stmt.execute(...) on the same concatenated SQL, keeping the injection while evading executeQuery-only detection.
</mutation_summary>

[ Output Format ]
Return ONLY these two tagged blocks:
<mutated_code>
...final self-contained synthesized test case...
</mutated_code>
<mutation_summary>
...one line describing what changed from the seed and why...
</mutation_summary>
"""


class SynthesisState(TypedDict):
    messages: Annotated[List[AnyMessage], operator.add]
    language: str
    rule_implementation: str
    current_seed: str
    insightful_snippet: str
    insight_reason: str
    mapped_code: str
    target_predicate: str
    rule_goal: str
    predicate_goal: str
    extra_context: Dict[str, Any]
    false_positive_or_negative_risk: str
    synthesized_results: List[Dict[str, Any]]
    test_case: Dict[str, Any]
    oracle: Dict[str, Any]
    raw_response: str


def _extract_tag(text: str, tag: str) -> str:
    match = re.search(rf"<{tag}>\s*([\s\S]*?)\s*</{tag}>", text, re.IGNORECASE)
    if not match:
        return ""
    return match.group(1).strip()


def _build_oracle(risk_type: str, target_predicate: str) -> Dict[str, Any]:
    is_false_negative = risk_type == "false_negative"
    return {
        "has_issue": bool(is_false_negative),
        "reason": (
            "This mutation aims to remain vulnerable and expose a potential false negative."
            if is_false_negative
            else "This mutation aims to be a secure variant and expose a potential false positive."
        ),
        "expected_focus": target_predicate,
    }


def synthesize_step(state: SynthesisState, llm: BaseChatModel) -> dict:
    language = state.get("language", "java")
    risk_type = state.get("false_positive_or_negative_risk", "")

    system_prompt = SYSTEM_PROMPT.format(
        language=language,
        rule_goal=state.get("rule_goal", ""),
        predicate_goal=state.get("predicate_goal", ""),
    )

    user_prompt = SYNTHESIS_PROMPT.format(
        language=language,
        risk_type=risk_type,
        current_seed=state.get("current_seed", ""),
        mapped_code=state.get("mapped_code", ""),
        insight_reason=state.get("insight_reason", ""),
        insightful_snippet=state.get("insightful_snippet", ""),
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    response = llm.invoke(messages)
    response_text = (
        response.content[0]["text"] if isinstance(response.content, list)
        else str(response.content)
    )

    code = _extract_tag(response_text, "mutated_code")
    mutation_summary = _extract_tag(response_text, "mutation_summary")
    if not code:
        return {
            "messages": [response],
            "synthesized_results": [],
            "test_case": {},
            "oracle": {},
            "raw_response": response_text,
        }

    test_case = {
        "language": language,
        "code": code,
        "mutation_summary": mutation_summary,
    }
    oracle = _build_oracle(risk_type, state.get("target_predicate", ""))

    return {
        "messages": [response],
        "synthesized_results": [{"test_case": test_case, "oracle": oracle}],
        "test_case": test_case,
        "oracle": oracle,
        "raw_response": response_text,
    }


def build_synthesis_workflow(llm: BaseChatModel) -> StateGraph:
    workflow = StateGraph(SynthesisState)

    def synthesize_node(state: SynthesisState) -> dict:
        return synthesize_step(state, llm)

    workflow.add_node("synthesize", synthesize_node)
    workflow.add_edge(START, "synthesize")
    workflow.add_edge("synthesize", END)
    return workflow


class SynthesisAgent:
    """One-step LangGraph synthesis agent with 3-step prompt (§4.2.3)."""

    def __init__(self, llm: BaseChatModel):
        self.llm = llm
        workflow = build_synthesis_workflow(llm)
        self.agent = workflow.compile()

    def synthesize_test_case(
        self,
        rule_implementation: str,
        current_seed: str,
        insightful_snippet: str,
        insight_reason: str,
        false_positive_or_negative_risk: str,
        target_predicate: str,
        rule_goal: str,
        predicate_goal: str,
        language: str = "java",
        mapped_code: str = "",
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        initial_state: SynthesisState = {
            "messages": [],
            "language": language,
            "rule_implementation": rule_implementation,
            "current_seed": current_seed,
            "insightful_snippet": insightful_snippet,
            "insight_reason": insight_reason,
            "mapped_code": mapped_code,
            "false_positive_or_negative_risk": false_positive_or_negative_risk,
            "synthesized_results": [],
            "target_predicate": target_predicate,
            "rule_goal": rule_goal,
            "predicate_goal": predicate_goal,
            "extra_context": extra_context or {},
            "test_case": {},
            "oracle": {},
            "raw_response": "",
        }
        return self.agent.invoke(initial_state)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from agents.model import llm

    agent = SynthesisAgent(llm)
    result = agent.synthesize_test_case(
        rule_implementation="pattern: os.system($CMD)",
        current_seed="# rule: detect os.system calls\nimport os\nos.system('echo hello')",
        insightful_snippet="subprocess.run(['echo', 'hello'], check=True)",
        insight_reason="subprocess.run is a safer alternative to os.system that the rule may miss",
        false_positive_or_negative_risk="false_negative",
        target_predicate="os_system_call",
        rule_goal="Detect os.system() calls that may lead to command injection",
        predicate_goal="Identify use of os.system()",
        language="python",
        mapped_code="os.system('echo hello')",
    )
    tc = result.get("test_case", {})
    print("=== Mutation Summary ===")
    print(tc.get("mutation_summary", "(none)"))
    print()
    print("=== Synthesized Code ===")
    print(tc.get("code", "(empty)"))
    print()
    print("=== Oracle ===")
    print(json.dumps(result.get("oracle", {}), indent=2))
