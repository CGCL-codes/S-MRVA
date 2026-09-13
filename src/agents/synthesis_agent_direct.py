"""Direct Mutation Agent — LLM-only variant synthesis (§ Ablation Baseline).

Unlike SynthesisAgent (which transplants real-world snippets from GitHub code
search), this agent generates variants solely from the LLM's training knowledge
via equivalent-behavioral transformations, following the STAAgent / Statifer /
Fuzz4ALL paradigm.

Activated by: ``LLM_DIRECT_MUTATION=1`` (see pipeline_agent.py).

Design:
  - One LLM call per variant — mirrors SynthesisAgent's 1:1 call pattern.
  - No external snippet input — the LLM draws on its internal knowledge of
    real-world API alternatives, coding patterns, and language idioms.
  - Same output shape as SynthesisAgent for drop-in compatibility with the
    downstream verification pipeline.
  - Temperature defaults to 0.7 (configurable via ``LLM_DIRECT_MUTATION_TEMPERATURE``)
    to provide diversity across multiple calls — a deliberate choice following
    STAAgent/Statifer's practice of using non-zero temperature for creative
    code transformation.
"""

import json
import operator
import re
from typing import Any, Dict, List, Optional
from typing_extensions import Annotated, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END


# ---------------------------------------------------------------------------
# Prompts — "equivalent transformation" paradigm (no external snippet)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """[ System Prompt ]
You are an expert code transformation engineer with deep expertise in secure
coding, static-analysis rule testing, and real-world API knowledge across Java,
Python, C/C++, and other languages. You generate realistic code variants that
stress-test static analysis rules through EQUIVALENT TRANSFORMATIONS. Only answer
strictly in the following output format following the output format instructions.

[ Task / User Prompt ]
Generate variants of code snippets that test static analysis rules by applying
EQUIVALENT TRANSFORMATIONS.

An equivalent transformation:
1. Preserves the BEHAVIORAL SEMANTICS of the original code (in the intended
   security direction — see below).
2. Changes the SYNTACTIC FORM: uses alternative APIs, control flow, data
   structures, or coding patterns.
3. Is REALISTIC — patterns that appear in actual production codebases.
4. Targets a specific mapped code region in the seed test case.

You operate in TWO risk directions:

- **false_negative (FN)**: Transform the vulnerable code to use a DIFFERENT
  API, pattern, or control flow that achieves the SAME insecure effect. The
  variant must remain vulnerable (same security property) but be syntactically
  different enough to potentially EVADE the static analysis rule. Draw from
  your knowledge of real-world API alternatives and language idioms.

- **false_positive (FP)**: Transform the code to make it SECURE while keeping
  the overall structure as similar as possible to the original. Apply a
  MINIMAL semantic fix — change only what is necessary to remediate the
  vulnerability. The variant must be secure under the rule's threat model.

[ Do and Do Not ]
Do:
- Mutate only the mapped code region; keep all other code unchanged.
- Preserve the intended security direction (FN keeps the vulnerability, FP
  applies a minimal secure fix).
- Prefer realistic, production-style APIs and patterns.
- Return only the tagged output from the Output Format section.
Do Not:
- Do not change behavior beyond the intended security direction.
- Do not apply an invasive fix for the FP direction when a one-line change suffices.
- Do not output anything other than the <mutated_code> and <mutation_summary> tags.

[ Few-shot Example ]
Task (FN direction): a rule flags socket binds to the literal host "0.0.0.0";
produce a variant that still binds all interfaces through a different host spelling.

Seed:
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("0.0.0.0", 8080))

Mapped code region (to mutate):
    s.bind(("0.0.0.0", 8080))

Expected output:
<mutated_code>
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(("", 8080))
</mutated_code>
<mutation_summary>
Changed the bind host from "0.0.0.0" to "" (an empty host also binds all interfaces), keeping the same exposure while evading rules that match the literal "0.0.0.0".
</mutation_summary>

[ Output Format ]
Use EXACTLY these two tags:
<mutated_code>
...full self-contained code with only the mapped region transformed...
</mutated_code>
<mutation_summary>
...one line describing what changed and why...
</mutation_summary>"""


DIRECT_MUTATION_PROMPT = """[ System Prompt ]
You are an expert code transformation engineer who specializes in generating
equivalent-transformation variants that stress-test static analysis rules using
only your internal knowledge of real-world APIs, libraries, and language idioms.
Only answer strictly in the following output format following the output format
instructions.

[ Task / User Prompt ]
Generate ONE equivalent-transformation variant for the seed test case below.

Risk type: {risk_type}

----------------------------- SEED TEST CASE ---------------------------------
```{language}
{current_seed}
```

--------------------- MAPPED CODE REGION (to mutate) -----------------------
```{language}
{mapped_code}
```

--------------------------------- TARGET -------------------------------------
Target predicate: {target_predicate}
Predicate goal: {predicate_goal}
Rule goal: {rule_goal}

----------------------------- DIVERSITY HINT ---------------------------------
This is variant #{variant_index} of {total_variants} for this direction.
Make it structurally different from what would be obvious for variant #1.

------------------------------- GUIDANCE ------------------------------------
{risk_guidance}

[ Do and Do Not ]
Do:
- Mutate ONLY the mapped code region; keep ALL other code COMPLETELY unchanged.
- Add any missing imports or initialization the new code requires.
- Ensure the variant is a syntactically valid {language} program.
- Keep the intended security direction of the given risk type.
- Draw from your training knowledge of real-world APIs, libraries, and patterns.
- Return only the tagged output from the Output Format section.
Do Not:
- Do not alter code outside the mapped region.
- Do not repeat the same transformation across variants (see the diversity hint).
- Do not output anything other than the <mutated_code> and <mutation_summary> tags.

[ Few-shot Example ]
Task (FN direction, variant 1 of 3): a rule flags MessageDigest.getInstance("MD5");
produce a variant that still performs weak MD5 hashing through a different API.

Seed:
    import java.security.MessageDigest;
    String hash = new String(MessageDigest.getInstance("MD5").digest(password.getBytes()));

Mapped code region (to mutate):
    MessageDigest.getInstance("MD5").digest(password.getBytes())

Expected output:
<mutated_code>
import org.apache.commons.codec.digest.DigestUtils;
String hash = DigestUtils.md5Hex(password);
</mutated_code>
<mutation_summary>
Replaced java.security.MessageDigest MD5 with Apache Commons DigestUtils.md5Hex, retaining the same weak MD5 hash while evading rules that match MessageDigest.getInstance("MD5").
</mutation_summary>

[ Output Format ]
Return ONLY these two tagged blocks:
<mutated_code>
...full self-contained code with only the mapped region transformed...
</mutated_code>
<mutation_summary>
...one line describing what changed and why...
</mutation_summary>"""


# ---------------------------------------------------------------------------
# State & helpers
# ---------------------------------------------------------------------------

class DirectMutationState(TypedDict):
    messages: Annotated[List[AnyMessage], operator.add]
    language: str
    rule_implementation: str
    current_seed: str
    mapped_code: str
    target_predicate: str
    rule_goal: str
    predicate_goal: str
    false_positive_or_negative_risk: str
    variant_index: int
    total_variants: int
    synthesized_results: List[Dict[str, Any]]
    test_case: Dict[str, Any]
    oracle: Dict[str, Any]
    raw_response: str


def _extract_tag(text: str, tag: str) -> str:
    """Extract content between XML-style tags (shared with synthesis_agent.py)."""
    match = re.search(rf"<{tag}>\s*([\s\S]*?)\s*</{tag}>", text, re.IGNORECASE)
    if not match:
        return ""
    return match.group(1).strip()


def _build_oracle(risk_type: str, target_predicate: str) -> Dict[str, Any]:
    """Build the verification oracle (shared with synthesis_agent.py)."""
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


def _risk_guidance(risk_type: str) -> str:
    """Generate risk-type-specific guidance for the prompt."""
    if risk_type == "false_negative":
        return (
            "FALSE NEGATIVE direction:\n"
            "- The seed code is VULNERABLE and the rule detects it.\n"
            "- Transform it to achieve the SAME insecure effect using a DIFFERENT\n"
            "  API, control flow, or pattern.\n"
            "- The variant must REMAIN VULNERABLE but may evade the rule.\n"
            "- Examples of equivalent transformations:\n"
            "  * Replace os.system(cmd) with subprocess.run(cmd, shell=True)\n"
            "  * Replace hashlib.md5() with hashlib.new('md5')\n"
            "  * Replace exec(code) with eval(compile(code, '', 'exec'))\n"
            "  * Replace 0.0.0.0 with '' (empty string, also binds all interfaces)\n"
            "  * Replace concrete literal with dynamically computed equivalent\n"
        )
    else:
        return (
            "FALSE POSITIVE direction:\n"
            "- The seed code is VULNERABLE and the rule detects it.\n"
            "- Transform it to make it SECURE while keeping structure similar.\n"
            "- Apply a MINIMAL semantic fix — change only security-relevant parts.\n"
            "- Examples of minimal fixes:\n"
            "  * Replace os.system(cmd) with subprocess.run(cmd, shell=False)\n"
            "  * Replace hardcoded password with os.getenv('PASSWORD')\n"
            "  * Replace 0.0.0.0 with 127.0.0.1\n"
            "  * Replace chmod 0o777 with chmod 0o600\n"
            "  * Replace exec(...) with a safe function call\n"
        )


# ---------------------------------------------------------------------------
# LangGraph node
# ---------------------------------------------------------------------------

def direct_mutate_step(state: DirectMutationState, llm: BaseChatModel) -> dict:
    """Single-node LangGraph step: format prompt → invoke LLM → extract result."""
    language = state.get("language", "java")
    risk_type = state.get("false_positive_or_negative_risk", "")

    user_prompt = DIRECT_MUTATION_PROMPT.format(
        language=language,
        risk_type=risk_type,
        current_seed=state.get("current_seed", ""),
        mapped_code=state.get("mapped_code", ""),
        target_predicate=state.get("target_predicate", ""),
        predicate_goal=state.get("predicate_goal", ""),
        rule_goal=state.get("rule_goal", ""),
        variant_index=state.get("variant_index", 1),
        total_variants=state.get("total_variants", 1),
        risk_guidance=_risk_guidance(risk_type),
    )

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
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


def build_direct_mutation_workflow(llm: BaseChatModel) -> StateGraph:
    """One-node LangGraph workflow: START → direct_mutate → END."""
    workflow = StateGraph(DirectMutationState)

    def node(state: DirectMutationState) -> dict:
        return direct_mutate_step(state, llm)

    workflow.add_node("direct_mutate", node)
    workflow.add_edge(START, "direct_mutate")
    workflow.add_edge("direct_mutate", END)
    return workflow


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class DirectMutationAgent:
    """LLM-direct mutation agent for ablation baseline.

    Generates code variants from the LLM's internal knowledge using equivalent
    behavioral transformations, without any external code search.

    Interface mirrors SynthesisAgent.synthesize_test_case() — the return dict
    shape is identical so the downstream pipeline needs no changes.
    """

    def __init__(self, llm: BaseChatModel):
        self.llm = llm
        workflow = build_direct_mutation_workflow(llm)
        self.agent = workflow.compile()

    def direct_mutate(
        self,
        rule_implementation: str,
        current_seed: str,
        false_positive_or_negative_risk: str,
        target_predicate: str,
        rule_goal: str,
        predicate_goal: str,
        language: str = "java",
        mapped_code: str = "",
        variant_index: int = 1,
        total_variants: int = 1,
    ) -> Dict[str, Any]:
        """Generate one variant via equivalent transformation.

        Returns the same shape as ``SynthesisAgent.synthesize_test_case()``:
            {
                "synthesized_results": [{test_case: ..., oracle: ...}],
                "test_case": {language, code, mutation_summary},
                "oracle": {has_issue, reason, expected_focus},
                "raw_response": "..."
            }
        """
        initial_state: DirectMutationState = {
            "messages": [],
            "language": language,
            "rule_implementation": rule_implementation,
            "current_seed": current_seed,
            "mapped_code": mapped_code,
            "false_positive_or_negative_risk": false_positive_or_negative_risk,
            "synthesized_results": [],
            "target_predicate": target_predicate,
            "rule_goal": rule_goal,
            "predicate_goal": predicate_goal,
            "variant_index": variant_index,
            "total_variants": total_variants,
            "test_case": {},
            "oracle": {},
            "raw_response": "",
        }
        return self.agent.invoke(initial_state)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import os
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from agents.model import llm

    # Use a higher temperature for the direct mutation variant
    temp = float(os.getenv("LLM_DIRECT_MUTATION_TEMPERATURE", "0.7"))
    from langchain_openai import ChatOpenAI
    from agents.model import llm_config
    _cfg = llm_config()
    direct_llm = ChatOpenAI(
        model=_cfg["model"],
        temperature=temp,
        api_key=_cfg["api_key"],
        base_url=_cfg["base_url"],
        timeout=int(os.getenv("LLM_TIMEOUT_SECONDS", "300")),
    )

    agent = DirectMutationAgent(direct_llm)

    # Test: FN direction — bypass os.system detection
    result = agent.direct_mutate(
        rule_implementation="pattern: os.system($CMD)",
        current_seed="# rule: detect os.system calls\nimport os\nos.system('echo hello')",
        false_positive_or_negative_risk="false_negative",
        target_predicate="os_system_call",
        rule_goal="Detect os.system() calls that may lead to command injection",
        predicate_goal="Identify use of os.system()",
        language="python",
        mapped_code="os.system('echo hello')",
        variant_index=1,
        total_variants=3,
    )
    tc = result.get("test_case", {})
    print("=== Direct Mutation (FN, variant 1/3) ===")
    print(f"Summary: {tc.get('mutation_summary', '(none)')}")
    print()
    print(f"Code:\n{tc.get('code', '(empty)')}")
    print()
    print(f"Oracle: {json.dumps(result.get('oracle', {}), indent=2)}")
