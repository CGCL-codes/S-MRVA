"""Main Agent - Plans and coordinates the testing process.

Memory access: FULL
- Reads/writes: rule, analysis, test cases, mappings, strategies
"""

from dataclasses import dataclass
import json
import operator
import re
from typing import Dict, Any, List, Optional, TYPE_CHECKING, Literal
from typing_extensions import Annotated, TypedDict
import sys
import os
import uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, AnyMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START, END

from prompts.analysis_agent import (
    SYSTEM_PROMPT,
    ANALYZE_RULE_PROMPT,
    logic_tree_prompt,
    LOGIC_TREE_PROMPT_RAW,
)
from analyzers.analyzer import Analyzer
from .utils import env_int, parse_json
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchResults

@tool("web_search", return_direct=True)
def web_search(query: str) -> str:
    """Tool for general web search to find additional information about rules, predicates, code patterns, etc"""
    search = DuckDuckGoSearchResults()
    return search.invoke(query)


def extract_predicates_from_tree(tree: Dict[str, Any], predicates: list = None) -> list:
    """Recursively extract all predicates from the logic tree.
    
    Args:
        tree: The logic tree node (can be a dict with 'predicate' or 'operator' keys)
        predicates: List to accumulate predicates
        
    Returns:
        List of predicate dictionaries with 'predicate', 'description', and 'impl' keys
    """
    if predicates is None:
        predicates = []
    
    if isinstance(tree, dict):
        # If this node has a predicate, add it
        if "predicate" in tree:
            predicates.append({
                "predicate": tree.get("predicate", ""),
                "description": tree.get("description", ""),
                "impl": tree.get("impl", "")
            })
        
        # If this node has children, recurse
        if "children" in tree and isinstance(tree["children"], list):
            for child in tree["children"]:
                extract_predicates_from_tree(child, predicates)
    
    return predicates


def parse_predicate_mapping_output(response: str) -> List[str]:
    """Parse matched code snippets wrapped by <match>...</match>.
    
    Args:
        response: The LLM response containing match tags
        
    Returns:
        List of matched code snippets
    """
    if not response:
        return []

    if response.strip() == "NO_MATCH":
        return []

    matches = re.findall(r'<match>(.*?)</match>', response, flags=re.DOTALL)
    cleaned = [m.strip() for m in matches if m.strip()]
    return cleaned


def rebuild_logic_tree_with_mappings(tree: Dict[str, Any], predicate_mappings: Dict[str, List[str]]) -> Dict[str, Any]:
    """Rebuild the logic tree structure with predicate code coverage added.
    
    Args:
        tree: The original logic tree
        predicate_mappings: Dict mapping predicate names to matched code snippets
        
    Returns:
        Updated tree with 'covered' field added to each predicate
    """
    if isinstance(tree, dict):
        # If this is a predicate node, add matched code snippets.
        if "predicate" in tree:
            predicate_name = tree["predicate"]
            tree = dict(tree)  # Create a copy
            tree["covered"] = predicate_mappings.get(predicate_name, [])
        
        # If this node has children, recurse
        if "children" in tree and isinstance(tree["children"], list):
            new_children = []
            for child in tree["children"]:
                new_children.append(rebuild_logic_tree_with_mappings(child, predicate_mappings))
            tree = dict(tree) if isinstance(tree, dict) else tree
            tree["children"] = new_children
    
    return tree


class AnalysisState(TypedDict):
    """State for the multi-step analysis workflow."""
    messages: Annotated[List[AnyMessage], operator.add]
    rule_id: str
    rule_content: str
    test_cases: Dict[str, str]
    dynamic_analysis_report: Dict[str, str]
    current_seed: str
    language: str 
    rule_goal: str
    covered_variants: List[str]
    logic_tree: Dict[str, Any]
    detection_formula: str
    logic_tree_with_code: Dict[str, Any]
    logic_tree_with_code_before_refine: Dict[str, Any]
    predicates: List[Dict[str, Any]]
    predicate_mappings: Dict[str, List[str]]
    refine_operations: List[Dict[str, Any]]
    refine_notes: str
    early_exit_reason: str


def _response_text(response: Any) -> str:
    content = getattr(response, "content", "")
    if isinstance(content, list):
        first = content[0] if content else ""
        if isinstance(first, dict):
            return str(first.get("text", ""))
        return str(first)
    return str(content)


def _invoke_with_context(
    state: AnalysisState,
    llm: BaseChatModel,
    prompt: str,
    system_prompt: Optional[str] = None,
) -> tuple[Any, List[AnyMessage]]:
    history = list(state.get("messages", []))

    if system_prompt and not any(isinstance(m, SystemMessage) for m in history):
        history.append(SystemMessage(content=system_prompt))

    user_msg = HumanMessage(content=prompt)
    response = llm.invoke([*history, user_msg])
    return response, [user_msg, response]


def _find_predicate_node(
    node: Dict[str, Any],
    target: str,
    parent: Optional[Dict[str, Any]] = None,
    child_index: int = -1,
) -> Optional[Dict[str, Any]]:
    if not isinstance(node, dict):
        return None

    if node.get("predicate") == target:
        return {"node": node, "parent": parent, "child_index": child_index}

    children = node.get("children", [])
    if isinstance(children, list):
        for idx, child in enumerate(children):
            found = _find_predicate_node(child, target, node, idx)
            if found:
                return found
    return None


def _build_predicate_node(template: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "predicate": template.get("predicate", fallback.get("predicate", "")),
        "description": template.get("description", fallback.get("description", "")),
        "impl": template.get("impl", fallback.get("impl", "")),
        "covered": template.get("covered", fallback.get("covered", [])),
    }


def _apply_split_operation(tree: Dict[str, Any], op: Dict[str, Any]) -> tuple[Dict[str, Any], str, bool]:
    target = op.get("target") or op.get("target_predicate") or ""
    new_preds = op.get("new_predicates", [])
    connector = str(op.get("connector", "AND")).upper()

    if not target or not isinstance(new_preds, list) or len(new_preds) < 2:
        return tree, f"split skipped: invalid target/new_predicates for '{target}'", False

    found = _find_predicate_node(tree, target)
    if not found:
        return tree, f"split skipped: target predicate '{target}' not found", False

    target_node = found["node"]
    parent = found["parent"]
    idx = found["child_index"]
    fallback = {
        "predicate": target,
        "description": target_node.get("description", ""),
        "impl": target_node.get("impl", ""),
        "covered": target_node.get("covered", []),
    }

    children = []
    for entry in new_preds:
        if isinstance(entry, str):
            entry = {"predicate": entry}
        if not isinstance(entry, dict) or not entry.get("predicate"):
            continue
        children.append(_build_predicate_node(entry, fallback))

    if len(children) < 2:
        return tree, f"split skipped: insufficient valid split children for '{target}'", False

    split_node = {
        "operator": connector if connector in {"AND", "OR"} else "AND",
        "description": op.get("description", f"Refined split of {target}"),
        "children": children,
    }

    if parent is None:
        return split_node, f"split applied on root predicate '{target}'", True

    parent_children = parent.get("children", [])
    if not isinstance(parent_children, list) or idx < 0 or idx >= len(parent_children):
        return tree, f"split skipped: invalid parent linkage for '{target}'", False

    parent_children[idx] = split_node
    return tree, f"split applied for predicate '{target}'", True


def _apply_merge_operation(tree: Dict[str, Any], op: Dict[str, Any]) -> tuple[Dict[str, Any], str, bool]:
    targets = op.get("targets", [])
    new_pred = op.get("new_predicate", {})

    if not isinstance(targets, list) or len(targets) < 2:
        return tree, "merge skipped: invalid targets", False

    locations = []
    for target in targets:
        if not isinstance(target, str) or not target:
            continue
        found = _find_predicate_node(tree, target)
        if not found:
            return tree, f"merge skipped: target predicate '{target}' not found", False
        locations.append(found)

    if len(locations) < 2:
        return tree, "merge skipped: fewer than two valid target predicates", False

    parents = {id(loc["parent"]) for loc in locations}
    if len(parents) != 1:
        return tree, "merge skipped: targets are not siblings under same parent", False

    parent = locations[0]["parent"]
    if parent is None:
        return tree, "merge skipped: cannot merge root node directly", False

    covered: List[str] = []
    impl_parts: List[str] = []
    desc_parts: List[str] = []
    for loc in locations:
        node = loc["node"]
        for s in node.get("covered", []) if isinstance(node.get("covered", []), list) else []:
            if s not in covered:
                covered.append(s)
        if node.get("impl"):
            impl_parts.append(str(node.get("impl")))
        if node.get("description"):
            desc_parts.append(str(node.get("description")))

    merged_name = new_pred.get("predicate") or "_and_".join(targets)
    merged_node = {
        "predicate": merged_name,
        "description": new_pred.get("description") or " + ".join(desc_parts),
        "impl": new_pred.get("impl") or "\n".join(impl_parts),
        "covered": new_pred.get("covered") or covered,
    }

    children = parent.get("children", [])
    if not isinstance(children, list):
        return tree, "merge skipped: parent has no children list", False

    indices = sorted(loc["child_index"] for loc in locations if isinstance(loc["child_index"], int))
    if len(indices) < 2:
        return tree, "merge skipped: invalid child indices", False

    first = indices[0]
    children[first] = merged_node
    for i in reversed(indices[1:]):
        if 0 <= i < len(children):
            del children[i]

    return tree, f"merge applied for targets={targets}", True


def _extract_predicate_mappings_from_tree(tree: Dict[str, Any]) -> Dict[str, List[str]]:
    mappings: Dict[str, List[str]] = {}

    def _walk(node: Any):
        if not isinstance(node, dict):
            return

        name = node.get("predicate", "")
        if name:
            covered = node.get("covered", [])
            mappings[name] = covered if isinstance(covered, list) else []

        children = node.get("children", [])
        if isinstance(children, list):
            for child in children:
                _walk(child)

    _walk(tree)
    return mappings


def _tree_bounds() -> tuple[int, int]:
    """Predicate-count bounds (B_low, B_high) for tree refinement.

    Configurable via ``LOGIC_TREE_B_LOW`` / ``LOGIC_TREE_B_HIGH`` env vars
    (defaults 2 and 5, matching §4.1 of the paper). Bounds are sanitized so
    B_low >= 1 and B_high >= B_low.
    """
    low = env_int("LOGIC_TREE_B_LOW", 2)
    high = env_int("LOGIC_TREE_B_HIGH", 5)
    low = max(low, 1)
    return low, max(high, low)


def refine_logic_tree(state: AnalysisState, llm: BaseChatModel) -> dict:
    """Step 5: Refine mapped logic tree with cautious LLM-guided split/merge operations."""
    tree = state.get("logic_tree_with_code", {})
    if not isinstance(tree, dict) or not tree:
        return {
            "messages": [
                HumanMessage(content="Refinement skipped due to empty logic_tree_with_code."),
                AIMessage(content='{"should_change": false, "operations": []}'),
            ],
            "logic_tree_with_code_before_refine": tree,
            "refine_operations": [],
            "refine_notes": "Skipped: empty logic tree.",
        }

    current_predicates = extract_predicates_from_tree(tree)
    current_predicate_count = len(current_predicates)
    rule_goal = state.get("rule_goal", "")
    covered = state.get("covered_variants", [])
    b_low, b_high = _tree_bounds()

    # Hard-gate early exit: when enabled and the tree exceeds B_high, stop with
    # an empty logic tree (0 mutants downstream) and record the reason.
    if os.getenv("LOGIC_TREE_EARLY_EXIT", "0").lower() in ("1", "true", "yes", "on") \
            and current_predicate_count > b_high:
        reason = f"predicate_count={current_predicate_count} > b_high={b_high}"
        return {
            "messages": [
                HumanMessage(content="Refinement skipped: early exit (predicate count exceeds B_high)."),
                AIMessage(content='{"should_change": false, "operations": []}'),
            ],
            "logic_tree_with_code": {},
            "logic_tree_with_code_before_refine": tree,
            "refine_operations": [],
            "refine_notes": reason,
            "early_exit_reason": reason,
        }

    hard_limit_instruction = ""
    if current_predicate_count > b_high:
        hard_limit_instruction = (
            f"\nHARD CONSTRAINT: current predicate count is {current_predicate_count} (>{b_high}). "
            f"You MUST propose merge operations to reduce to at most {b_high} predicates. "
            "Do not return should_change=false in this case."
        )

    prompt = (
        "[ System Prompt ]\n"
        "You are an expert static analysis engineer specializing in rule decomposition.\n"
        "You refine predicate logic trees to achieve balanced decomposition granularity.\n"
        "Only answer strictly in the following JSON format following the output format instructions.\n\n"
        "[ Task / User Prompt ]\n"
        "Review the mapped predicate logic tree and apply the following refinement policies "
        "to achieve balanced decomposition granularity (§4.1):\n\n"
        "--- AND-Merge Policy ---\n"
        "If two sibling nodes under an AND clause consistently map to the same tightly "
        "coupled code region (they always activate together across seeds), MERGE them "
        "into one node. This removes artificial fragmentation of what is semantically "
        "one unit.\n\n"
        "--- OR-Merge Policy ---\n"
        "If two sibling leaves under an OR clause are trivial variants of the same "
        "choice (e.g., different API names for the same function), MERGE them into "
        "one alternatives node. This preserves a single semantic choice point.\n\n"
        "--- Split Policy ---\n"
        "If one node maps to code that spans multiple basic blocks or function "
        "boundaries, SPLIT it into smaller, more focused nodes. Overly broad "
        "predicates weaken downstream retrieval.\n\n"
        "--- Bounds ---\n"
        f"Target predicate count: {b_low}–{b_high}. "
        f"Current: {current_predicate_count}.\n"
        f"- If count > {b_high}, prioritize merges.\n"
        f"- If count < {b_low}, prioritize splits.\n"
        f"- Conservative: if the tree already works well within bounds, do not change.\n\n"
        f"{hard_limit_instruction}\n\n"
        "[ Do and Do Not ]\n"
        "Do:\n"
        "- Apply the merge/split policies conservatively and only when justified.\n"
        "- Preserve each predicate's 'covered' code when merging or splitting.\n"
        "- Respect the predicate-count bounds.\n"
        "Do Not:\n"
        "- Do not change the tree if it already works well within bounds.\n"
        "- Do not return anything other than the specified JSON format.\n\n"
        "[ Few-shot Example ]\n"
        "Example: two sibling leaves under an OR clause are trivial API variants of the same choice.\n\n"
        "Input tree (abridged):\n"
        "{\n"
        '  "operator": "OR",\n'
        '  "children": [\n'
        '    {"predicate": "md5_via_hashlib", "description": "hashlib.md5() call", "impl": "...", "covered": ["hashlib.md5(pw)"]},\n'
        '    {"predicate": "md5_via_crypto", "description": "Crypto.Hash.MD5 call", "impl": "...", "covered": ["MD5.new(pw)"]}\n'
        "  ]\n"
        "}\n\n"
        "Expected output:\n"
        "{\n"
        '  "should_change": true,\n'
        '  "notes": "OR-Merge policy: the two leaves are trivial API variants of the same choice; merged into one alternatives node.",\n'
        '  "operations": [\n'
        '    {"op": "merge", "targets": ["md5_via_hashlib", "md5_via_crypto"], "new_predicate": {"predicate": "md5_usage", "description": "MD5 hashing via any API", "impl": "..."}}\n'
        "  ]\n"
        "}\n\n"
        "[ Output Format ]\n"
        "You may propose operations:\n"
        '- split: {"op":"split","target":"name","connector":"AND|OR",'
        '"new_predicates":[{"predicate":"...","description":"...","impl":"..."}]}\n'
        '- merge: {"op":"merge","targets":["a","b"],'
        '"new_predicate":{"predicate":"...","description":"...","impl":"..."}}\n\n'
        "Return strict JSON only:\n"
        "{\n"
        '  "should_change": true|false,\n'
        '  "notes": "which policy was applied and why",\n'
        '  "operations": [ ... ]\n'
        "}\n\n"
        f"Current mapped logic tree:\n{json.dumps(tree, indent=2)}"
    )

    response, new_messages = _invoke_with_context(state, llm, prompt)
    parsed = parse_json(_response_text(response))
    should_change = bool(parsed.get("should_change", False))
    operations = parsed.get("operations", [])
    notes = str(parsed.get("notes", ""))

    if not should_change or not isinstance(operations, list) or not operations:
        return {
            "messages": new_messages,
            "logic_tree_with_code_before_refine": tree,
            "refine_operations": [],
            "refine_notes": notes or "No change requested by LLM.",
        }

    refined_tree = json.loads(json.dumps(tree))
    applied_logs: List[Dict[str, Any]] = []

    for op in operations:
        if not isinstance(op, dict):
            applied_logs.append({"op": "invalid", "applied": False, "message": "operation is not dict"})
            continue

        op_type = str(op.get("op", "")).lower().strip()
        if op_type == "split":
            refined_tree, msg, ok = _apply_split_operation(refined_tree, op)
        elif op_type == "merge":
            refined_tree, msg, ok = _apply_merge_operation(refined_tree, op)
        else:
            msg, ok = f"unsupported op '{op_type}'", False

        applied_logs.append({"op": op_type, "applied": ok, "message": msg, "detail": op})

    refined_predicates = extract_predicates_from_tree(refined_tree)
    refined_mappings = _extract_predicate_mappings_from_tree(refined_tree)

    return {
        "messages": new_messages,
        "logic_tree_with_code_before_refine": tree,
        "logic_tree_with_code": refined_tree,
        "predicates": refined_predicates,
        "predicate_mappings": refined_mappings,
        "refine_operations": applied_logs,
        "refine_notes": notes,
    }

def analyze_rule(state: AnalysisState, analyzer: Analyzer, llm: BaseChatModel) -> dict:
    """Step 1: Analyze the rule and test cases to extract rule goal and covered variants."""
    rule_id = state["rule_id"]
    
    # Load rule content
    rule_content = ""
    for rn, rc in analyzer.load_rule(rule_id=rule_id).items():
        rule_content += f"# File: {rn}\n"
        rule_content += rc + "\n"

    # Load test cases
    test_cases_raw = analyzer.load_test_cases(rule_id=rule_id)
    if not test_cases_raw:
        raise ValueError(f"Failed to get test cases for rule {rule_id}")

    # Convert Path keys to strings for serialization
    test_cases = {str(k): v for k, v in test_cases_raw.items()}

    test_cases_str = ""
    for tn, tc in test_cases.items():
        test_cases_str += f"# Test case: {tn}\n"
        test_cases_str += tc + "\n"

    # Create prompt for step 1
    prompt = ANALYZE_RULE_PROMPT.format(
        rule_id=rule_id,
        rule_content=rule_content,
        test_cases=test_cases_str
    )
    
    # Call LLM with persisted conversation context.
    response, new_messages = _invoke_with_context(
        state,
        llm,
        prompt,
        system_prompt=SYSTEM_PROMPT,
    )
    
    # Parse response
    json_content = parse_json(_response_text(response))

    return {
        "messages": new_messages,
        "rule_content": rule_content,
        "test_cases": test_cases,
        "rule_goal": json_content.get("rule_specification", ""),
        "covered_variants": json_content.get("covered_variant_patterns", []),
    }


def decompose_rule(state: AnalysisState, llm: BaseChatModel) -> dict:
    """Step 2: Decompose the rule into logical components (logic tree and detection formula)."""
    raw_mode = os.getenv("ENABLE_LOGIC_TREE_REFINEMENT", "1").lower() in ("0", "false", "no")
    b_low, b_high = _tree_bounds()
    tree_prompt = LOGIC_TREE_PROMPT_RAW if raw_mode else logic_tree_prompt(b_low, b_high)

    # Keep prompt concise and rely on prior conversation context from step 1.
    prompt = (
        f"{tree_prompt}\n\n"
        "Use previous conversation context for the full rule and test-case details. "
        "Do not restate them.\n\n"
        f"Rule goal:\n{state.get('rule_goal', '')}\n\n"
        f"Covered variants:\n{json.dumps(state.get('covered_variants', []), indent=2)}"
    )
    
    # Call LLM with accumulated messages.
    response, new_messages = _invoke_with_context(state, llm, prompt)
    
    # Parse response
    json_content = parse_json(_response_text(response))
    
    logic_tree = json_content.get("logic_tree", {})
    
    # Extract all predicates from the logic tree for parallel mapping
    predicates = extract_predicates_from_tree(logic_tree)

    return {
        "messages": new_messages,
        "logic_tree": logic_tree,
        "detection_formula": json_content.get("detection_formula", ""),
        "predicates": predicates,
    }

def dynamic_analysis(state: AnalysisState, analyzer: Analyzer) -> dict:
    """Run dynamic analysis by executing the rule's check on the test case code snippet."""
    test_cases = state["test_cases"]
    rule_id = state["rule_id"]

    # Run the check using the analyzer's tool
    current_seed = ""

    for tn, tc in test_cases.items():
        if "seed" in tn.lower() or "positive" in tn.lower():
            check_result = analyzer.run_check_in_temp_dir(rule_id=rule_id, test_code=tc)
            if check_result.issues_found:
                current_seed = tn
                break
    
    if not current_seed:
        for tn, tc in test_cases.items():
            check_result = analyzer.run_check_in_temp_dir(rule_id=rule_id, test_code=tc)
            if not check_result.issues_found:
                continue
            else:
                current_seed = tn
    
    if not current_seed:
        raise ValueError(f"No issues found for any positive test case of rule {rule_id}")

    return {
        "current_seed": current_seed,
        "current_seed_content": test_cases[current_seed],
        "dynamic_analysis_report": {
            current_seed: {
                "issues_found": check_result.issues_found,
                "output": check_result.output,
                "runtime_error": check_result.runtime_error
            }
        }
    }

def analyze_predicate_mappings(state: AnalysisState, llm: BaseChatModel) -> dict:
    """Step 4: Analyze mapping for each predicate with match-tag snippets.
    
    For each predicate, ask the LLM to return matched code snippets in <match>...</match> blocks.
    """
    predicates = state.get("predicates", [])
    current_seed = state.get("current_seed", "")
    test_cases = state.get("test_cases", {})
    current_seed_content = test_cases.get(current_seed, "")
    dynamic_analysis_reports = state.get("dynamic_analysis_report", {})
    dynamic_analysis_report = dynamic_analysis_reports.get(current_seed, {})
    
    predicate_mappings: Dict[str, List[str]] = {}
    
    # Reuse cross-step context, but keep each predicate request concise.
    base_history = list(state.get("messages", []))

    for predicate in predicates:
        predicate_name = predicate.get("predicate", "")
        predicate_desc = predicate.get("description", "")
        predicate_impl = predicate.get("impl", "")
        
        if not predicate_name:
            continue
        
        prompt = (
            "Find concrete code snippets in the current seed that match this predicate.\n"
            "Use previous context for rule/test details and return <match>...</match> tags only.\n\n"
            f"Predicate name: {predicate_name}\n"
            f"Predicate description: {predicate_desc}\n"
            f"Predicate impl: {predicate_impl}\n"
            f"Current seed code:\n{current_seed_content}\n\n"
            f"Dynamic analysis report:\n{json.dumps(dynamic_analysis_report, indent=2)}"
        )

        response = llm.invoke([*base_history, HumanMessage(content=prompt)])
        response_text = _response_text(response)
        
        # Parse matched code snippets
        matched_snippets = parse_predicate_mapping_output(response_text)
        predicate_mappings[predicate_name] = matched_snippets
    
    # Rebuild logic tree with mappings
    logic_tree = state.get("logic_tree", {})
    logic_tree_with_mappings = rebuild_logic_tree_with_mappings(logic_tree, predicate_mappings)

    # Do not append messages from per-predicate mapping stage.
    # This stage only passes structural mapping outputs to the refine step.
    return {
        "predicate_mappings": predicate_mappings,
        "logic_tree_with_code": logic_tree_with_mappings,
    }


def build_analysis_workflow(analyzer: Analyzer, llm: BaseChatModel) -> StateGraph:
    """Build the five-step analysis workflow graph.
    
    Workflow:
    1. analyze_rule: Extract rule goal and covered variants
    2. decompose_rule: Build logic tree and detection formula (also extracts predicates)
    3. dynamic_analysis: Run analyzer check on current test case
    4. analyze_predicate_mappings: Map each predicate independently using match-tag snippets
    5. refine_logic_tree: Cautiously refine mapped tree with split/merge operations

    Step 5 can be disabled for the ablation variant via the
    ``ENABLE_LOGIC_TREE_REFINEMENT`` environment variable (default ``1``).
    When set to ``0``/``false``/``no``, the workflow ends after predicate
    mapping and the initial (unrefined) tree is used downstream; the
    decompose step then also skips PASS-2 compression (one predicate per
    line-level rule check, no count cap).
    """
    enable_refine = os.getenv("ENABLE_LOGIC_TREE_REFINEMENT", "1").lower() not in ("0", "false", "no")

    # Build workflow
    workflow = StateGraph(AnalysisState)
    
    # Create node functions with analyzer and llm bound
    def analyze_rule_node(state: AnalysisState) -> dict:
        return analyze_rule(state, analyzer, llm)
    
    def decompose_rule_node(state: AnalysisState) -> dict:
        return decompose_rule(state, llm)
    
    def dynamic_analysis_node(state: AnalysisState) -> dict:
        return dynamic_analysis(state, analyzer)
    
    def analyze_predicate_mappings_node(state: AnalysisState) -> dict:
        return analyze_predicate_mappings(state, llm)

    def refine_logic_tree_node(state: AnalysisState) -> dict:
        return refine_logic_tree(state, llm)
    
    # Add nodes
    workflow.add_node("analyze_rule", analyze_rule_node)
    workflow.add_node("decompose_rule", decompose_rule_node)
    workflow.add_node("dynamic_analysis", dynamic_analysis_node)
    workflow.add_node("analyze_predicate_mappings", analyze_predicate_mappings_node)
    if enable_refine:
        workflow.add_node("refine_logic_tree", refine_logic_tree_node)
    
    # Add edges to create five-step workflow
    workflow.add_edge(START, "analyze_rule")
    workflow.add_edge("analyze_rule", "decompose_rule")
    workflow.add_edge("decompose_rule", "dynamic_analysis")
    workflow.add_edge("dynamic_analysis", "analyze_predicate_mappings")
    if enable_refine:
        workflow.add_edge("analyze_predicate_mappings", "refine_logic_tree")
        workflow.add_edge("refine_logic_tree", END)
    else:
        workflow.add_edge("analyze_predicate_mappings", END)
    
    return workflow


class MainAgent:
    """Main agent that coordinates the five-step analysis workflow."""
    
    def __init__(
        self, 
        llm: BaseChatModel, 
        analyzer: Analyzer,
        lang: str,
        rule_id: str
    ):
        self.llm = llm
        self.analyzer = analyzer
        self.lang = lang
        self.rule_id = rule_id
        self.checkpointer = InMemorySaver()
        # Build and compile the workflow
        workflow = build_analysis_workflow(analyzer, llm)
        self.agent = workflow.compile(checkpointer=self.checkpointer)
    
    def run_analysis(self) -> dict:
        """Run the complete five-step analysis workflow.
        
        Returns:
            Final state containing rule analysis, logic tree, dynamic analysis, and mappings
        """
        initial_state = {
            "messages": [],
            "rule_id": self.rule_id,
            "rule_content": "",
            "test_cases": {},
            "dynamic_analysis_report": {},
            "current_seed": "",
            "language": self.lang,
            "rule_goal": "",
            "covered_variants": [],
            "logic_tree": {},
            "detection_formula": "",
            "logic_tree_with_code": {},
            "logic_tree_with_code_before_refine": {},
            "predicates": [],
            "predicate_mappings": {},
            "refine_operations": [],
            "refine_notes": "",
        }
        
        import langfuse_debug as ld
        from langfuse.langchain import CallbackHandler
        lf_handler = CallbackHandler()
        
        result = self.agent.invoke(
            input=initial_state,
            config={
                "configurable": {"thread_id": str(uuid.uuid4())},
                "callbacks": [lf_handler]
                }
        )
        return result
    
if __name__ == "__main__":
    # Example usage
    from analyzers.bandit_check import BanditAnalyzer

    dataset_dir = Path(os.getenv("SAT_WORK_DIR", ".")) / "dataset/bandit"
    analyzer = BanditAnalyzer(dataset_dir=str(dataset_dir))
    from agents.model import llm
    
    agent = MainAgent(
        llm=llm, 
        analyzer=analyzer, 
        lang="python", 
        rule_id="B501"
    )
    
    analysis_result = agent.run_analysis()
    
    # Display results
    print("\n" + "="*80)
    print("FIVE-STEP ANALYSIS WORKFLOW RESULTS")
    print("="*80)
    print(f"\nRule ID: {analysis_result['rule_id']}")
    print(f"Language: {analysis_result['language']}")
    
    print("\n--- Step 1: Rule Analysis ---")
    print(f"Rule Goal: {analysis_result.get('rule_goal', 'N/A')}")
    print(f"Covered Variants: {analysis_result.get('covered_variants', [])}")
    
    print("\n--- Step 2: Logic Tree Decomposition ---")
    print(f"Detection Formula: {analysis_result.get('detection_formula', 'N/A')}")
    print(f"Logic Tree: {json.dumps(analysis_result.get('logic_tree', {}), indent=2)}")
    
    print("\n--- Step 3: Dynamic Analysis ---")
    print(f"Current Seed: {analysis_result.get('current_seed', 'N/A')}")
    print(f"Dynamic Analysis Report: {json.dumps(analysis_result.get('dynamic_analysis_report', {}), indent=2)}")
    
    print("\n--- Step 4: Parallel Predicate Mapping ---")
    print("Predicate Mappings (covered snippets):")
    for pred_name, snippets in analysis_result.get('predicate_mappings', {}).items():
        print(f"  {pred_name}:")
        if snippets:
            for snippet in snippets:
                print(f"    - {snippet}")
        else:
            print("    - NO_MATCH")
    
    print(f"\nLogic Tree with Mappings: {json.dumps(analysis_result.get('logic_tree_with_code_before_refine', {}), indent=2)}")

    print("\n--- Step 5: Tree Refinement ---")
    print(f"Refine Notes: {analysis_result.get('refine_notes', '')}")
    print(f"Refine Operations: {json.dumps(analysis_result.get('refine_operations', []), indent=2)}")
    print(f"Refined Logic Tree with Mappings: {json.dumps(analysis_result.get('logic_tree_with_code', {}), indent=2)}")


