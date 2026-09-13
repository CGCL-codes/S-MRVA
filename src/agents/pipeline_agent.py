"""Pipeline Agent - Full end-to-end static rule testing pipeline.

Workflow (LangGraph):
    analyze  →  generate_mutants  →  verify_mutants  →  group_results  →  build_report

Each sub-agent is composed as a subgraph / callable inside the top-level nodes:
    • analyze          : AnalysisAgent  (analysis_agent.py)
    • generate_mutants : QueryAgent + SynthesisAgent, parallel per predicate
    • verify_mutants   : VerifyAgent, parallel per mutant
    • group_results    : groups reportable verified mutants (no dedup)
    • build_report     : pure aggregation node, no LLM call
"""

import json
import operator
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from typing_extensions import Annotated, TypedDict
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AnyMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.func import task

from analyzers.analyzer import Analyzer
from agents.analysis_agent import build_analysis_workflow, AnalysisState

# Query stage: GitHub code search via the serializing code-search server.
from agents.query_agent_api import find_code_snippets as query_find_code_snippets
from agents.synthesis_agent import SynthesisAgent
from agents.synthesis_agent_direct import DirectMutationAgent
from agents.verify_agent import VerifyAgent
from agents.langfuse_debug import get_callback_handler
from agents.cost_tracker import CostTracker, active_callbacks, set_active_tracker


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class PipelineInputState(TypedDict):
    rule_id: str
    language: str


class PipelineOutputState(TypedDict):
    pipeline_summary: Dict[str, Any]
    markdown_report: str


class PipelinePrivateState(TypedDict):
    grouped_reported_mutants: Dict[str, Any]


class PipelineState(TypedDict):
    # Input channels
    rule_id: str
    language: str

    # Internal channels
    messages: Annotated[List[AnyMessage], operator.add]

    # ── analysis outputs ──────────────────────────────────────────────────
    rule_goal: str
    covered_variants: List[str]
    logic_tree: Dict[str, Any]
    logic_tree_with_code: Dict[str, Any]
    detection_formula: str
    rule_implementation: str   # raw rule source, used as context for synthesis
    current_seed: str          # first seed test-case source code
    early_exit_reason: str     # set when LOGIC_TREE_EARLY_EXIT fires (0 mutants)

    # ── mutant generation outputs ─────────────────────────────────────────
    # Each item: {predicate, predicate_goal, test_case, oracle, risk_type,
    #             snippet_url, mutant_reason}
    all_mutants: List[Dict[str, Any]]

    # ── verification outputs ──────────────────────────────────────────────
    # Each item mirrors _verify_one_mutant output dict
    verified_results: List[Dict[str, Any]]
    raw_reported_mutants: List[Dict[str, Any]]
    grouped_reported_mutants: Dict[str, Any]

    # ── final report ─────────────────────────────────────────────────────
    pipeline_summary: Dict[str, Any]
    markdown_report: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_predicates(
    node: Any,
    parent_goal: str = "",
) -> List[Dict[str, Any]]:
    """Recursively walk the logic_tree_with_code and collect named predicates.

    Returns a flat list of::

        {
            "predicate": str,
            "predicate_goal": str,
            "tree_node": dict,   # the raw sub-tree for this predicate
        }
    """
    predicates: List[Dict[str, Any]] = []

    if isinstance(node, list):
        for item in node:
            predicates.extend(_extract_predicates(item, parent_goal))
        return predicates

    if not isinstance(node, dict):
        return predicates

    name: str = (
        node.get("predicate")
        or node.get("name")
        or node.get("label")
        or ""
    )
    goal: str = (
        node.get("description")
        or node.get("goal")
        or node.get("detail")
        or parent_goal
    )

    # Collect children from any common child container key
    children: List[Any] = []
    for key in ("sub_predicates", "conditions", "children", "sub_conditions", "parts"):
        val = node.get(key)
        if isinstance(val, list) and val:
            children = val
            break

    covered = node.get("covered", []) if isinstance(node, dict) else []
    has_matched_code = isinstance(covered, list) and len(covered) > 0

    # Only keep predicate nodes that have matched code from analysis mapping.
    if name and has_matched_code:
        predicates.append({"predicate": name, "predicate_goal": goal, "tree_node": node})

    for child in children:
        predicates.extend(_extract_predicates(child, goal or name))

    return predicates


# ---------------------------------------------------------------------------
# Node 1 – analyze
# ---------------------------------------------------------------------------

def analyze_node(
    state: PipelineState,
    analyzer: Analyzer,
    llm: BaseChatModel,
) -> Dict[str, Any]:
    """Run the 4-step AnalysisAgent subgraph and surface its results."""
    print(f"[pipeline] analyze — rule_id={state['rule_id']}")

    subgraph = build_analysis_workflow(analyzer, llm).compile()

    init: AnalysisState = {
        "messages": [],
        "rule_id": state["rule_id"],
        "rule_content": "",
        "test_cases": {},
        "dynamic_analysis_report": {},
        "current_seed": "",
        "language": state["language"],
        "rule_goal": "",
        "covered_variants": [],
        "logic_tree": {},
        "detection_formula": "",
        "logic_tree_with_code": {},
        "early_exit_reason": "",
    }

    lf_handler = get_callback_handler()
    invoke_config: Dict[str, Any] = {"configurable": {"thread_id": f"analyze-{state['rule_id']}"}}
    if lf_handler is not None:
        invoke_config["callbacks"] = [lf_handler]

    result = subgraph.invoke(init, config=invoke_config)

    test_cases: Dict[str, str] = result.get("test_cases", {})
    current_seed_key: str = result.get("current_seed", "")
    current_seed_code: str = test_cases.get(current_seed_key, "")

    print(
        f"[pipeline] analyze done — rule_goal='{result.get('rule_goal', '')[:60]}...'"
    )
    return {
        "messages": result.get("messages", []),
        "rule_goal": result.get("rule_goal", ""),
        "covered_variants": result.get("covered_variants", []),
        "logic_tree": result.get("logic_tree", {}),
        "logic_tree_with_code": result.get("logic_tree_with_code", {}),
        "detection_formula": result.get("detection_formula", ""),
        "rule_implementation": result.get("rule_content", ""),
        "current_seed": current_seed_code,
        "early_exit_reason": result.get("early_exit_reason", ""),
    }


# ---------------------------------------------------------------------------
# Node 2 – generate_mutants  (parallel per predicate)
# ---------------------------------------------------------------------------

def _process_predicate(
    predicate_info: Dict[str, Any],
    state: PipelineState,
    llm: BaseChatModel,
    snippets_per_direction: Optional[int] = None,
    max_search_iter: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """For one predicate: QueryAgent → SynthesisAgent per snippet.

    When ``LLM_DIRECT_MUTATION=1``, skips QueryAgent (no GitHub search) and
    uses DirectMutationAgent to generate variants from the LLM's training
    knowledge via equivalent-behavioural transformations (STAAgent/Statifer
    ablation baseline).
    """
    if snippets_per_direction is None:
        snippets_per_direction = int(os.getenv("QUERY_SNIPPETS_PER_DIRECTION", "5"))
    if max_search_iter is None:
        max_search_iter = int(os.getenv("QUERY_MAX_SEARCH_ITER", "3"))

    predicate_name = predicate_info["predicate"]
    predicate_goal = predicate_info["predicate_goal"]
    tree_node = predicate_info["tree_node"]

    # Extract mapped code region from predicate's covered snippets
    covered = (
        predicate_info.get("tree_node", {}).get("covered", [])
        if isinstance(predicate_info.get("tree_node"), dict)
        else []
    )
    mapped_code = covered[0] if isinstance(covered, list) and covered else ""

    # ── Ablation variant: LLM-direct mutation (no external code search) ──
    use_direct = os.getenv("LLM_DIRECT_MUTATION", "0").lower() in ("1", "true", "yes", "on")
    if use_direct:
        return _process_predicate_direct(
            predicate_name=predicate_name,
            predicate_goal=predicate_goal,
            state=state,
            llm=llm,
            mapped_code=mapped_code,
            variants_per_direction=snippets_per_direction,
        )

    # ── 1. find code snippets ────────────────────────────────────────────
    lf_handler = get_callback_handler()
    query_result = query_find_code_snippets(
        llm=llm,
        language=state["language"],
        target_predicate=predicate_name,
        logic_tree_with_code=tree_node,
        target_cnt=snippets_per_direction,
        max_iterations=max_search_iter,
        callback_handler=[lf_handler] if lf_handler is not None else None,
    )

    snippets_with_risk: List[Tuple[Dict[str, Any], str]] = [
        (s, "false_negative") for s in query_result.get("false_negative_examples", [])
    ] + [
        (s, "false_positive") for s in query_result.get("false_positive_examples", [])
    ]
    print(
        f"[pipeline]   predicate='{predicate_name}' query returned "
        f"FN={len(query_result.get('false_negative_examples', []))} "
        f"FP={len(query_result.get('false_positive_examples', []))} "
        f"(search_iters={query_result.get('search_iterations', 0)})"
    )

    # ── 2. synthesise mutants for each snippet ───────────────────────────
    # NOTE: synthesis runs serially here (no inner @task). The outer
    # `_process_one_predicate` @task already parallelizes per-predicate; an
    # additional nested @task layer would starve the shared thread pool
    # (default max_workers = min(32, nproc+4)), since outer tasks block on
    # `.result()` of inner tasks that can never get a worker -> deadlock.
    mutants: List[Dict[str, Any]] = []

    def _synthesize_one(snippet: Dict[str, Any], risk_type: str) -> List[Dict[str, Any]]:
        synthesis_agent = SynthesisAgent(llm=llm)
        snippet_code = snippet.get("code") or snippet.get("snippet") or ""
        snippet_url = snippet.get("url", "")
        if not snippet_code.strip():
            return []

        insight_reason = (
            f"This snippet from '{snippet.get('repo', 'unknown')}' represents a "
            f"{'potentially vulnerable alternative pattern' if risk_type == 'false_negative' else 'secure mitigation/remediation pattern'}. "
            f"URL: {snippet_url}"
        )

        try:
            synthesis_result = synthesis_agent.synthesize_test_case(
                rule_implementation=state["rule_implementation"],
                current_seed=state["current_seed"],
                insightful_snippet=snippet_code,
                insight_reason=insight_reason,
                false_positive_or_negative_risk=risk_type,
                target_predicate=predicate_name,
                rule_goal=state["rule_goal"],
                predicate_goal=predicate_goal,
                language=state["language"],
                mapped_code=mapped_code,
            )
            task_mutants: List[Dict[str, Any]] = []
            for item in synthesis_result.get("synthesized_results", []):
                task_mutants.append({
                    "predicate": predicate_name,
                    "predicate_goal": predicate_goal,
                    "test_case": item["test_case"],
                    "oracle": item["oracle"],
                    "risk_type": risk_type,
                    "snippet_url": snippet_url,
                    "mutant_reason": item["test_case"].get("mutation_summary", ""),
                })
            return task_mutants
        except Exception as e:
            print(
                f"[pipeline] synthesis failed for predicate='{predicate_name}' "
                f"snippet='{snippet_url}': {e}"
            )
            return []

    for snippet, risk_type in snippets_with_risk:
        mutants.extend(_synthesize_one(snippet, risk_type))

    return mutants


def _process_predicate_direct(
    predicate_name: str,
    predicate_goal: str,
    state: PipelineState,
    llm: BaseChatModel,
    mapped_code: str,
    variants_per_direction: int = 5,
) -> List[Dict[str, Any]]:
    """LLM-direct mutation: skip QueryAgent, generate variants from LLM knowledge.

    Creates ``variants_per_direction`` mutants each for FN and FP risk types
    using equivalent-behavioural transformations (STAAgent/Statifer paradigm).
    No external code search or GitHub tokens required.
    """
    # Use temperature > 0 for creative diversity in direct mutation
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
        callbacks=active_callbacks(),
    )

    agent = DirectMutationAgent(llm=direct_llm)
    mutants: List[Dict[str, Any]] = []

    # NOTE: mutations run serially here (no inner @task) — same thread-pool
    # starvation reason as _synthesize_one: outer @task would block on inner
    # futures that can never get a worker.
    def _direct_mutate_one(
        variant_idx: int,
        risk_type: str,
    ) -> List[Dict[str, Any]]:
        try:
            result = agent.direct_mutate(
                rule_implementation=state["rule_implementation"],
                current_seed=state["current_seed"],
                false_positive_or_negative_risk=risk_type,
                target_predicate=predicate_name,
                rule_goal=state["rule_goal"],
                predicate_goal=predicate_goal,
                language=state["language"],
                mapped_code=mapped_code,
                variant_index=variant_idx,
                total_variants=variants_per_direction,
            )
            task_mutants: List[Dict[str, Any]] = []
            for item in result.get("synthesized_results", []):
                task_mutants.append({
                    "predicate": predicate_name,
                    "predicate_goal": predicate_goal,
                    "test_case": item["test_case"],
                    "oracle": item["oracle"],
                    "risk_type": risk_type,
                    "snippet_url": "llm_direct",
                    "mutant_reason": item["test_case"].get("mutation_summary", ""),
                })
            return task_mutants
        except Exception as e:
            print(
                f"[pipeline] direct mutation failed for predicate='{predicate_name}' "
                f"risk_type='{risk_type}' variant={variant_idx}: {e}"
            )
            return []

    for risk_type in ("false_negative", "false_positive"):
        for i in range(variants_per_direction):
            mutants.extend(_direct_mutate_one(i + 1, risk_type))

    return mutants


def generate_mutants_node(
    state: PipelineState,
    llm: BaseChatModel,
) -> Dict[str, Any]:
    """Parallel per-predicate: QueryAgent + SynthesisAgent subgraphs."""
    predicates = _extract_predicates(state.get("logic_tree_with_code", {}))
    predicates = [
        p for p in predicates
        if isinstance(p.get("tree_node", {}).get("covered", []), list)
        and len(p.get("tree_node", {}).get("covered", [])) > 0
    ]
    print(f"[pipeline] generate_mutants — {len(predicates)} predicate(s) extracted")

    # Hard constraint: process only the top N predicates (by covered-snippet
    # count), so the mutant budget per rule stays bounded (~N * 2 directions *
    # snippets-per-direction). N = MAX_PREDICATES_PER_RULE (default 5 → ~50
    # mutants per rule at 5 snippets/direction).
    max_predicates = int(os.getenv("MAX_PREDICATES_PER_RULE", "5"))
    if max_predicates > 0 and len(predicates) > max_predicates:
        ranked = sorted(
            predicates,
            key=lambda p: len(p.get("tree_node", {}).get("covered", []) or []),
            reverse=True,
        )
        predicates = ranked[:max_predicates]
        print(f"[pipeline] HARD CONSTRAINT: capped to top {max_predicates} predicates")

    if not predicates:
        print("[pipeline] WARNING: no predicates found in logic tree.")
        return {"all_mutants": []}

    all_mutants: List[Dict[str, Any]] = []

    @task
    def _process_one_predicate(predicate_info: Dict[str, Any]) -> Dict[str, Any]:
        pred_name = predicate_info["predicate"]
        try:
            mutants = _process_predicate(predicate_info, state, llm)
            return {
                "predicate": pred_name,
                "mutants": mutants,
                "error": "",
            }
        except Exception as e:
            return {
                "predicate": pred_name,
                "mutants": [],
                "error": str(e),
            }

    futures = [_process_one_predicate(predicate) for predicate in predicates]
    for future in futures:
        result = future.result()
        pred_name = result["predicate"]
        error = result.get("error", "")
        if error:
            print(f"[pipeline] ERROR in predicate='{pred_name}': {error}")
            continue

        mutants = result.get("mutants", [])
        all_mutants.extend(mutants)
        print(
            f"[pipeline]   predicate='{pred_name}' → {len(mutants)} mutant(s)"
        )

    print(f"[pipeline] generate_mutants done — total={len(all_mutants)} mutant(s)")
    return {"all_mutants": all_mutants}


# ---------------------------------------------------------------------------
# Node 3 – verify_mutants  (parallel per mutant)
# ---------------------------------------------------------------------------

def _verify_one_mutant(
    mutant: Dict[str, Any],
    state: PipelineState,
    llm: BaseChatModel,
    analyzer: Analyzer,
) -> Dict[str, Any]:
    """Run NewVerifyAgent subgraph for one mutant."""
    agent = VerifyAgent(llm=llm, analyzer=analyzer)

    test_case = mutant["test_case"]
    oracle = mutant["oracle"]

    result = agent.verify_mutant(
        rule_id=state["rule_id"],
        mutant_code=test_case.get("code", ""),
        oracle=oracle,
        target_predicate=mutant["predicate"],
        rule_goal=state["rule_goal"],
        predicate_goal=mutant["predicate_goal"],
        mutant_reason=mutant.get("mutant_reason", ""),
        language=state["language"],
    )

    return {
        "predicate": mutant["predicate"],
        "risk_type": mutant.get("risk_type", ""),
        "snippet_url": mutant.get("snippet_url", ""),
        "mutant_code": test_case.get("code", ""),
        "oracle": oracle,
        "classification": result.get("classification", "NONE"),
        "disagreement": result.get("disagreement", False),
        "should_report": result.get("should_report", False),
        "report": result.get("report"),
        "llm_has_issue": result.get("llm_has_issue"),
        "tool_has_issue": result.get("tool_has_issue"),
        "tool_runtime_error": result.get("tool_runtime_error", False),
        "is_valid": result.get("is_valid"),
        "is_common": result.get("is_common"),
        "is_critical": result.get("is_critical"),
        "assessment_reason": result.get("assessment_reason", ""),
    }


def verify_mutants_node(
    state: PipelineState,
    llm: BaseChatModel,
    analyzer: Analyzer,
) -> Dict[str, Any]:
    """Parallel per-mutant: NewVerifyAgent subgraph."""
    all_mutants = state.get("all_mutants", [])
    print(f"[pipeline] verify_mutants — {len(all_mutants)} mutant(s) to verify")

    if not all_mutants:
        return {"verified_results": []}

    verified: List[Dict[str, Any]] = []

    @task
    def _verify_one_mutant_task(mutant: Dict[str, Any], idx: int) -> Dict[str, Any]:
        try:
            result = _verify_one_mutant(mutant, state, llm, analyzer)
            return {
                "idx": idx,
                "result": result,
                "error": "",
            }
        except Exception as e:
            return {
                "idx": idx,
                "result": {},
                "error": str(e),
            }

    futures = [_verify_one_mutant_task(mutant, idx) for idx, mutant in enumerate(all_mutants)]
    for future in futures:
        item = future.result()
        idx = item["idx"]
        error = item.get("error", "")
        if error:
            print(f"[pipeline] ERROR verifying mutant[{idx}]: {error}")
            continue

        vr = item["result"]
        verified.append(vr)
        print(
            f"[pipeline]   mutant[{idx}] "
            f"classification={vr['classification']} "
            f"report={vr['should_report']}"
        )

    print(
        f"[pipeline] verify_mutants done — "
        f"reportable={sum(1 for v in verified if v.get('should_report'))}/{len(verified)}"
    )
    return {"verified_results": verified}


# ---------------------------------------------------------------------------
# Node 4 – group_results
# ---------------------------------------------------------------------------

def _score_order(v: Dict[str, Any]) -> int:
    score = (v.get("report") or {}).get("score", "P2")
    return {"P0": 0, "P1": 1, "P2": 2}.get(score, 3)


def _get_root_cause_groups(
    raw_reported: List[Dict[str, Any]],
    state: PipelineState,
    llm: BaseChatModel,
) -> Dict[str, Any]:
    """Use LLM to group reported mutants by root cause (technique or rule-specific issues).
    
    Returns:
        {
            "root_cause_groups": [
                {
                    "root_cause": "Missing constant propagation analysis",
                    "group_type": "TECHNIQUE",  # or "RULE_SPECIFIC"
                    "indices": [0, 2, 5],
                    "items": [...]
                },
                ...
            ]
        }
    """
    if not raw_reported:
        return {"root_cause_groups": []}

    # Build mutant summary for LLM analysis
    mutant_summaries = []
    for idx, item in enumerate(raw_reported):
        report = item.get("report") or {}
        classification = item.get("classification", "NONE")
        predicate = item.get("predicate", "")
        bug_desc = str(report.get("bug_description", "") or "").strip()
        code = item.get("mutant_code", "")
        
        summary = f"""
[Mutant {idx}] Classification: {classification} | Predicate: {predicate}
Bug Description: {bug_desc}
Code:
{code}
---"""
        mutant_summaries.append(summary)

    mutant_text = "\n".join(mutant_summaries)

    prompt = f"""[ System Prompt ]
You are an expert static-analysis engineer who groups reported False Positive (FP) and False Negative (FN) mutants by root cause. Only answer strictly in the following JSON format following the output format instructions.

[ Task / User Prompt ]
Analyze the following {len(raw_reported)} reported mutants (False Positives and False Negatives) and group them by ROOT CAUSE.

Rule Goal: 
{state.get('rule_goal', '')}
Rule Implementation: 
```
{state.get('rule_implementation', '')}
```

MUTANTS TO ANALYZE:
{mutant_text}

GROUP BY ROOT CAUSE based on:
1. **TECHNIQUE**: Mutants requiring the same analysis technique (e.g., constant propagation, taint tracking)
2. **RULE_SPECIFIC**: Rule-specific issues that need individual fixes (e.g., missing specific API variant, missing method override)

[ Do and Do Not ]
Do:
- Reference mutants by their exact indices as listed in MUTANTS TO ANALYZE (e.g., [0], [2, 5]).
- Assign each mutant to exactly one group; every mutant must appear in a group, and no mutant may appear in more than one group.
- State a concrete root cause per group and explain why the grouped mutants belong together.
- Use "group_type": "TECHNIQUE" when the fix requires a shared analysis technique and "RULE_SPECIFIC" when mutants need individual rule-level fixes.
Do Not:
- Do not invent mutant indices or reference indices that do not exist in MUTANTS TO ANALYZE.
- Do not use vague root causes such as "general bug" or "miscellaneous".
- Do not merge unrelated mutants that share no root cause, and do not add fields outside the specified JSON schema.
- Do not output any prose, commentary, or markdown outside the single JSON object.

[ Few-shot Example ]
Mutant 0 | Classification: FN | Predicate: rule.has_constant_propagation
Bug Description: Rule flags a potential integer overflow, but no constant propagation analysis is run, so the value is never inferred as constant.
---
Mutant 2 | Classification: FN | Predicate: rule.has_constant_propagation
Bug Description: Rule requires constant folding of an array index, but the analysis does not track constant assignments across branches.
---
Mutant 4 | Classification: FP | Predicate: rule.missing_method_override
Bug Description: Rule reports a missing override of equals() in a class that never extends the base class; the API-variant check is too broad.

Response:
{{
    "groups": [
        {{
            "root_cause": "Missing constant propagation analysis across branches",
            "group_type": "TECHNIQUE",
            "explanation": "Mutants 0 and 2 both require the analysis to infer and propagate constant values before the rule can evaluate correctly.",
            "mutant_indices": [0, 2]
        }},
        {{
            "root_cause": "Over-broad method-override check for equals()",
            "group_type": "RULE_SPECIFIC",
            "explanation": "Mutant 4 is a rule-specific issue: the override check must require an actual inheritance relationship before reporting a missing override.",
            "mutant_indices": [4]
        }}
    ]
}}

[ Output Format ]
Return a single JSON object with this exact schema:
{{
    "groups": [
        {{
            "root_cause": "Brief description of the root cause or technique",
            "group_type": "TECHNIQUE" or "RULE_SPECIFIC",
            "explanation": "Detailed explanation of why these mutants are grouped",
            "mutant_indices": [list of indices from the mutants above]
        }}
    ]
}}
Be precise with indices and grouping. Each mutant should appear in exactly one group."""

    from langchain_core.messages import HumanMessage
    
    response = llm.invoke([HumanMessage(content=prompt)])
    response_text = response.content

    # Parse LLM response
    try:
        # Try to extract JSON from response
        import re
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            json_str = json_match.group(0)
            result = json.loads(json_str)
        else:
            result = json.loads(response_text)
    except json.JSONDecodeError as e:
        print(f"[pipeline] ERROR: Failed to parse LLM grouping response: {e}")
        # Return all items in a single ungrouped group
        return {
            "root_cause_groups": [
                {
                    "root_cause": "LLM Grouping Failed",
                    "group_type": "RULE_SPECIFIC",
                    "explanation": f"LLM response parsing failed: {str(e)}. Showing all reportable mutants ungrouped.",
                    "indices": list(range(len(raw_reported))),
                    "items": raw_reported,
                }
            ]
        }

    # Build grouped structure from LLM result
    root_cause_groups = []
    seen_indices = set()
    
    for group in result.get("groups", []):
        indices = group.get("mutant_indices", [])
        if not indices:
            continue
        
        # Validate indices
        indices = [i for i in indices if 0 <= i < len(raw_reported)]
        if not indices:
            continue
        
        # Get items for this group
        items = [raw_reported[i] for i in indices]
        
        root_cause_groups.append({
            "root_cause": group.get("root_cause", "Unknown"),
            "group_type": group.get("group_type", "RULE_SPECIFIC"),
            "explanation": group.get("explanation", ""),
            "indices": indices,
            "items": items,
        })
        
        seen_indices.update(indices)
    
    # Add any ungrouped mutants to a default group
    ungrouped_indices = [i for i in range(len(raw_reported)) if i not in seen_indices]
    if ungrouped_indices:
        root_cause_groups.append({
            "root_cause": "Ungrouped / Analysis required",
            "group_type": "RULE_SPECIFIC",
            "explanation": "These mutants need further analysis",
            "indices": ungrouped_indices,
            "items": [raw_reported[i] for i in ungrouped_indices],
        })
    
    return {"root_cause_groups": root_cause_groups}




def group_results_node(
    state: PipelineState,
    llm: BaseChatModel,
) -> Dict[str, Any]:
    """Group reported mutants by root cause using LLM analysis."""
    verified = state.get("verified_results", [])
    raw_reported = [v for v in verified if v.get("should_report") and v.get("report")]
    
    print(f"[pipeline] group_results — {len(raw_reported)} reportable mutant(s)")
    
    if not raw_reported:
        print("[pipeline] group_results done — no reportable mutants")
        return {
            "raw_reported_mutants": raw_reported,
            "grouped_reported_mutants": {"root_cause_groups": []},
        }
    
    # Use LLM to perform root cause grouping
    grouped = _get_root_cause_groups(raw_reported, state, llm)
    
    num_groups = len(grouped.get("root_cause_groups", []))
    print(
        f"[pipeline] group_results done — "
        f"reportable={len(raw_reported)} root_cause_groups={num_groups}"
    )
    
    return {
        "raw_reported_mutants": raw_reported,
        "grouped_reported_mutants": grouped,
    }


def _build_markdown_report(state: PipelineState) -> str:
    raw_reported = state.get("raw_reported_mutants", [])
    grouped = state.get("grouped_reported_mutants", {})
    verified = state.get("verified_results", [])
    
    # Extract root cause groups
    root_cause_groups = grouped.get("root_cause_groups", [])
    
    # Extract FP/FN counts from root cause groups
    fp_reports = []
    fn_reports = []
    for group in root_cause_groups:
        for item in group.get("items", []):
            if item.get("classification") == "FP":
                fp_reports.append(item)
            elif item.get("classification") == "FN":
                fn_reports.append(item)

    lines = [
        f"# Static Rule Testing Report: {state.get('rule_id', '')}",
        "",
        "## Summary",
        "",
        f"- Language: {state.get('language', '')}",
        f"- Rule goal: {state.get('rule_goal', '')}",
        f"- Total generated mutants: {len(state.get('all_mutants', []))}",
        f"- Total verified mutants: {len(verified)}",
        f"- Reportable mutants: {len(raw_reported)}",
        f"- False positives: {len(fp_reports)}",
        f"- False negatives: {len(fn_reports)}",
        "",
        "## Original Rule Implementation",
        "",
        "```",
        state.get("rule_implementation", ""),
        "```",
        "",
        "## Original Seed Test Case",
        "",
        f"```{state.get('language', '')}",
        state.get("current_seed", ""),
        "```",
        "",
        "## All Verified Mutants",
        "",
    ]

    if not verified:
        lines.extend(["No verified mutants.", ""])

    for idx, item in enumerate(verified, 1):
        report = item.get("report") or {}
        lines.extend([
            f"### {idx}. {report.get('score', 'P2')} · {item.get('classification', 'NONE')} · {item.get('predicate', '')}",
            "",
            f"- Should report: {item.get('should_report')}",
            f"- Risk type: {item.get('risk_type', '')}",
            f"- Snippet source: {item.get('snippet_url', '')}",
            f"- Bug description: {report.get('bug_description', '')}",
            f"- Assessment reason: {report.get('assessment_reason', '')}",
            f"- LLM judge says issue: {item.get('llm_has_issue')}",
            f"- Tool says issue: {item.get('tool_has_issue')}",
            "",
            "#### Reproduction Code",
            "",
            f"```{state.get('language', '')}",
            item.get("mutant_code", ""),
            "```",
            "",
            "#### Oracle",
            "",
            "```json",
            json.dumps(item.get("oracle", {}), indent=2),
            "```",
            "",
        ])

    lines.extend([
        "## Grouped Reportable Mutants (by Root Cause)",
        "",
    ])

    if not raw_reported:
        lines.extend(["No reportable mutants.", ""])
        return "\n".join(lines)

    # Display root cause grouping
    for group_idx, group in enumerate(root_cause_groups, 1):
        root_cause = group.get("root_cause", "Unknown")
        group_type = group.get("group_type", "RULE_SPECIFIC")
        explanation = group.get("explanation", "")
        items = group.get("items", [])
        
        lines.extend([
            f"### Group {group_idx}: {root_cause}",
            f"**Type**: {group_type}",
            f"**Count**: {len(items)}",
            "",
        ])
        
        if explanation:
            lines.extend([
                f"**Explanation**: {explanation}",
                "",
            ])
        
        sorted_items = sorted(items, key=_score_order)
        for item_idx, item in enumerate(sorted_items, 1):
            report = item.get("report") or {}
            bug_desc = str(report.get("bug_description", "") or "").strip()
            one_line_bug_desc = " ".join(bug_desc.split())
            if len(one_line_bug_desc) > 240:
                one_line_bug_desc = one_line_bug_desc[:237] + "..."

            lines.extend([
                f"- {item_idx}. {report.get('score', 'P2')} · {item.get('predicate', '')} · {item.get('risk_type', '')} · {item.get('classification', 'NONE')}",
                f"  should_report={item.get('should_report')} llm_issue={item.get('llm_has_issue')} tool_issue={item.get('tool_has_issue')}",
            ])
            if one_line_bug_desc:
                lines.append(f"  bug={one_line_bug_desc}")
        
        lines.append("")

    return "\n".join(lines)


def build_report_node(state: PipelineState) -> Dict[str, Any]:
    """Aggregate verification results into a structured final report."""
    verified = state.get("verified_results", [])
    all_mutants = state.get("all_mutants", [])
    raw_reported = state.get("raw_reported_mutants", [])
    grouped = state.get("grouped_reported_mutants", {})

    disagreements = [v for v in verified if v.get("disagreement")]
    
    # Extract FP/FN counts from root cause groups
    root_cause_groups = grouped.get("root_cause_groups", [])
    fp_reports = []
    fn_reports = []
    for group in root_cause_groups:
        for item in group.get("items", []):
            if item.get("classification") == "FP":
                fp_reports.append(item)
            elif item.get("classification") == "FN":
                fn_reports.append(item)

    summary: Dict[str, Any] = {
        "rule_id": state.get("rule_id", ""),
        "language": state.get("language", ""),
        "rule_goal": state.get("rule_goal", ""),
        "rule_implementation": state.get("rule_implementation", ""),
        "original_seed_test_case": state.get("current_seed", ""),
        "detection_formula": state.get("detection_formula", ""),
        "covered_variants": state.get("covered_variants", []),
        "stats": {
            "total_mutants_generated": len(all_mutants),
            "total_verified": len(verified),
            "total_disagreements": len(disagreements),
            "total_reportable": len(raw_reported),
            # keep legacy fields for compatibility with existing tests/scripts
            "total_reportable_before_dedup": len(raw_reported),
            "total_reportable_after_dedup": len(raw_reported),
            "false_positive_issues": len(fp_reports),
            "false_negative_issues": len(fn_reports),
            "early_exit_reason": state.get("early_exit_reason", ""),
        },
        "all_variants_generated": all_mutants,
        "all_reported_mutants_before_dedup": raw_reported,
        "all_reported_mutants_after_dedup": raw_reported,
        "grouped_reported_mutants": grouped,
        "reports": sorted(raw_reported, key=_score_order),
        "all_verified": verified,
    }
    markdown_report = _build_markdown_report(state)

    print(
        f"[pipeline] build_report done — "
        f"FP={len(fp_reports)} FN={len(fn_reports)} "
        f"total_reportable={len(raw_reported)}"
    )
    return {"pipeline_summary": summary, "markdown_report": markdown_report}


# ---------------------------------------------------------------------------
# Workflow assembly
# ---------------------------------------------------------------------------

def build_pipeline_workflow(
    llm: BaseChatModel,
    analyzer: Analyzer,
) -> StateGraph:
    """Assemble the 5-node pipeline graph.

    Graph:
        START → analyze → generate_mutants → verify_mutants → group_results → build_report → END
    """
    workflow = StateGraph(
        PipelineState,
        input_schema=PipelineInputState,
        output_schema=PipelineOutputState,
    )

    workflow.add_node("analyze",
                      lambda state: analyze_node(state, analyzer, llm))
    workflow.add_node("generate_mutants",
                      lambda state: generate_mutants_node(state, llm))
    workflow.add_node("verify_mutants",
                      lambda state: verify_mutants_node(state, llm, analyzer))
    workflow.add_node("group_results",
                      lambda state: group_results_node(state, llm))
    workflow.add_node("build_report", build_report_node)

    workflow.add_edge(START, "analyze")
    workflow.add_edge("analyze", "generate_mutants")
    workflow.add_edge("generate_mutants", "verify_mutants")
    workflow.add_edge("verify_mutants", "group_results")
    workflow.add_edge("group_results", "build_report")
    workflow.add_edge("build_report", END)

    return workflow


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
class PipelineAgent:
    """End-to-end static rule testing pipeline.

    Usage::

        agent = PipelineAgent(llm=llm, analyzer=analyzer, language="java")
        result = agent.run(rule_id="java/jdbc-sqli")
        print(json.dumps(result["pipeline_summary"], indent=2))
    """

    def __init__(
        self,
        llm: BaseChatModel,
        analyzer: Analyzer,
        language: str = "java",
    ) -> None:
        self.llm = llm
        self.analyzer = analyzer
        self.language = language
        self.checkpointer = InMemorySaver()

        # Optional LLM cost/time tracking (ENABLE_COST_TRACKING=1). When
        # enabled, attach the CostTracker callback to the LLM so every call
        # made through this model accumulates latency + token usage.
        if os.getenv("ENABLE_COST_TRACKING", "0").lower() in ("1", "true", "yes", "on"):
            self.cost_tracker = CostTracker(model=os.getenv("LLM_MODEL", ""))
            set_active_tracker(self.cost_tracker)
            existing_callbacks = list(getattr(self.llm, "callbacks", None) or [])
            self.llm.callbacks = existing_callbacks + [self.cost_tracker]
        else:
            self.cost_tracker = None

        self.agent = build_pipeline_workflow(llm, analyzer).compile()

    def run(self, rule_id: str, config=None) -> Dict[str, Any]:
        """Run the full pipeline for *rule_id* and return the final state."""
        if config is None:
            config = {"configurable": {"thread_id": rule_id}}
            lf_handler = get_callback_handler()
            if lf_handler is not None:
                config["callbacks"] = [lf_handler]
        init: PipelineState = {
            "messages": [],
            "rule_id": rule_id,
            "language": self.language,
            "rule_goal": "",
            "covered_variants": [],
            "logic_tree": {},
            "logic_tree_with_code": {},
            "detection_formula": "",
            "rule_implementation": "",
            "current_seed": "",
            "early_exit_reason": "",
            "all_mutants": [],
            "verified_results": [],
            "raw_reported_mutants": [],
            "grouped_reported_mutants": {},
            "pipeline_summary": {},
            "markdown_report": "",
        }
        result = self.agent.invoke(init, config=config)
        if self.cost_tracker is not None:
            cost_summary = self.cost_tracker.summary()
            result.setdefault("pipeline_summary", {})["cost"] = cost_summary
            print(f"[pipeline] cost: {cost_summary}")
        return result

import argparse

def cli():
    parser = argparse.ArgumentParser(description="Run the PipelineAgent for static rule testing.")
    parser.add_argument("--rule_id", type=str, required=True, help="The ID of the rule to test (e.g., 'jdbc-sqli').")
    parser.add_argument("--language", type=str, required=True, help="Programming language of the rule.")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode with verbose output.")
    parser.add_argument("--analyzer", type=str,required=True, help="Specify which Analyzer implementation to use (semgrep, bandit, codeql, spotbugs).")
    parser.add_argument("--base_dir", type=str, required=True, help="'dataset/semgrep-rules' for example.")
    parser.add_argument("--artifacts_dir", type=str, default="out", help="Directory to save pipeline outputs.")
    args = parser.parse_args()

    from agents.model import llm

    if args.analyzer == "semgrep":
        from analyzers.semgrep_check import SemgrepAnalyzer
        analyzer = SemgrepAnalyzer(dataset_dir=args.base_dir, language=args.language)
    elif args.analyzer == "bandit":
        from analyzers.bandit_check import BanditAnalyzer
        analyzer = BanditAnalyzer(dataset_dir=args.base_dir)
    elif args.analyzer == "codeql":
        from analyzers.codeql_check import CodeQLAnalyzer
        analyzer = CodeQLAnalyzer(dataset_dir=args.base_dir, language=args.language)
    elif args.analyzer == "spotbugs":
        from analyzers.spotbugs_check import SpotBugsAnalyzer
        analyzer = SpotBugsAnalyzer(dataset_dir=args.base_dir)
    else:
        raise ValueError(f"Unsupported analyzer: {args.analyzer}. Must be one of: semgrep, bandit, codeql, spotbugs.")

    agent = PipelineAgent(llm=llm, analyzer=analyzer, language=args.language)

    result = agent.run(rule_id=args.rule_id)

    summary = result.get("pipeline_summary", {})
    
    markdown_report = result.get("markdown_report", "")
    ARTIFACTS_DIR = Path(args.artifacts_dir) / args.rule_id
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = ARTIFACTS_DIR / f"pipeline_summary_{args.rule_id}.json"
    report_path = ARTIFACTS_DIR / f"pipeline_report_{args.rule_id}.md"

    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report_path.write_text(markdown_report, encoding="utf-8")

if __name__ == "__main__":
    cli()
