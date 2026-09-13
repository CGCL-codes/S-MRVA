"""REST API query agent with generate-search-evaluate loop.

This module uses GitHub REST code search via `tools.api_code_search.github_code_search`
and generates queries based on `prompts/code_search_api.md` guidance.
"""

import json
import operator
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from typing_extensions import Annotated, TypedDict

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.api_code_search import github_code_search, peek as github_code_peek
from .utils import parse_json


checkpointer = InMemorySaver()


class QueryAgentState(TypedDict):
    messages: Annotated[List[AnyMessage], operator.add]
    target_predicate: str
    logic_tree_with_code: Dict[str, Any]
    target_cnt: int
    max_iterations: int
    iteration_count: int
    search_iterations: int
    language: str

    fn_last_query: List[str]
    fn_saved_examples: List[Dict[str, Any]]
    fn_seen_ids: List[str]
    fn_seen_patterns: List[str]

    fp_last_query: List[str]
    fp_saved_examples: List[Dict[str, Any]]
    fp_seen_ids: List[str]
    fp_seen_patterns: List[str]

    query_refine_turn: int
    query_refine_max_turns: int
    fn_refine_done: bool
    fp_refine_done: bool

    result: Dict[str, Any]


CODE_SEARCH_SKILL = Path(__file__).parent.parent / "prompts" / "code_search_api.md"
CODE_SEARCH_SKILL_TEXT = CODE_SEARCH_SKILL.read_text(encoding="utf-8")

GENERATOR_SYSTEM_PROMPT = """[ System Prompt ]
You are a GitHub Code Search query generation expert with deep expertise in static analysis and code search.
Only answer strictly in the following JSON format following the output format instructions.

[ Task / User Prompt ]
Strictly follow the skill document below when generating queries.

---------------- SKILL: code_search_api.md ----------------
{code_search_skill}
----------------------------------------------------------

[ Do and Do Not ]
Do:
- Keep queries valid for GitHub code search.
- Use `language:{language}` in each query.
- Keep query complexity moderate (avoid over-complex expressions).
Do Not:
- Do not return anything other than strict JSON.

[ Output Format ]
Return JSON:
{{
    "queries": [
        "query 1",
        "query 2",
    ],
    "focus": "short reason why this set helps"
}}
"""

QUERY_PROMPT = """[ System Prompt ]
You are a GitHub Code Search query generation expert with deep expertise in static analysis and code search.
Only answer strictly in the following JSON format following the output format instructions.

[ Task / User Prompt ]
Generate up to 3 GitHub code search queries to search for code examples relevant to the target predicate. You can find all already covered code snippets in the logic tree with code.
We say a code snippet is relevant if it can be indeed used when implementing the code for the target predicate.
So your query should include the features of the target predicate, but avoid including all features which will lead to overly strict queries and miss many relevant examples.

For example, if you want to search for code of get username from a request,
you can use query like "username request language:java" to see diverse examples of how to get username from a request,
instead of "request.getParameter(\"username\") language:java" which is too strict and only returns examples using getParameter method.

Your goal is:
{goal}

Search direction:
{direction}

------------------------------------- Target Information -------------------------------------
Target predicate:
{target_predicate}

Current implementation:
{logic_tree_with_code}

[ Do and Do Not ]
Do:
- Include the features of the target predicate in your queries.
- Use `language:{language}` in each query.
- Use prior context to avoid repeated queries and improve diversity.
Do Not:
- Do not include all features of the target predicate, which leads to overly strict queries and misses relevant examples.
- Do not return anything other than strict JSON.

[ Output Format ]
Return JSON:
{{
    "queries": [
        "query 1",
        "query 2",
    ],
    "focus": "short reason why this set helps"
}}
"""

EVALUATOR_SYSTEM_PROMPT = """[ System Prompt ]
You are an expert of static analysis with deep expertise in code pattern detection and rule coverage analysis.
Only answer strictly in the following JSON format following the output format instructions.

[ Task / User Prompt ]
Your task is to find potentially uncovered patterns for the given target predicate from a batch of code snippets returned by GitHub code search.
You should examine them one by one and select the most insightful and representative ones.
You should focus on the code snippets that can bypass the detection logic and help identify potential blind spots in the rule.

[ Do and Do Not ]
Do:
- Prefer snippets that are relevant, structurally diverse, and add coverage beyond already seen patterns.
- Select the 2-3 most insightful and representative snippets for this search step. If no good snippet is found, you can select fewer or even none. If many good snippets are found, you can select up to 3, but be CAREFUL and make sure each one is high-quality and unique.
- Simplify the code snippets, but keep the key pattern and insight that matters for detection.
- Pay attention to the conversation context to avoid repeated patterns.
Do Not:
- Do not select snippets that are duplicate, already covered, too common, or weakly related.
- Do not return anything other than strict JSON.

[ Output Format ]
Return JSON:
{{
    "selected": [
        {{
            "snippet": "simplified code snippet",
            "reason": "short reason label",
            "pattern": "short pattern summary"
        }},
        {{
            "snippet": "another code snippet",
            "reason": "short reason label",
            "pattern": "short pattern summary"
        }}
    ]
}}
"""

EVALUATOR_PROMPT = """[ System Prompt ]
You are an expert of static analysis with deep expertise in code pattern detection and rule coverage analysis.
Only answer strictly in the following JSON format following the output format instructions.

[ Task / User Prompt ]
Evaluate this batch of snippets.
Snippet candidates:
{snippets}

Already seen patterns:
{seen_patterns}

[ Do and Do Not ]
Do:
- Prefer snippets that are relevant, structurally diverse, and add coverage beyond already seen patterns.
- Select the 2-3 most insightful and representative snippets for this search step. If no good snippet is found, you can select fewer or even none.
- Simplify the code snippets, but keep the key pattern and insight that matters for detection.
Do Not:
- Do not select snippets that are duplicate, already covered, too common, or weakly related.
- Do not return anything other than strict JSON.

[ Output Format ]
Return JSON:
{{
    "selected": [
        {{
            "snippet": "simplified code snippet",
            "reason": "short reason label",
            "pattern": "short pattern summary"
        }}
    ]
}}
"""

QUERY_REFINE_PROMPT = """[ System Prompt ]
You are a GitHub Code Search query refinement expert with deep expertise in static analysis and code search.
Only answer strictly in the following JSON format following the output format instructions.

[ Task / User Prompt ]
You are refining GitHub code search queries.

Goal:
{goal}

Target predicate:
{target_predicate}

Current query list:
{current_queries}

We performed a lightweight peek search using these queries.
You should judge whether results seem relevant/diverse enough to continue.

Top results for the search:
{peek_results}

[ Do and Do Not ]
Do:
- If current queries are already good, set is_ok=true and keep queries stable.
- If not good, set is_ok=false and provide improved queries by add/remove/edit.
- Keep at most 3 queries.
- Include `language:{language}` in each query.
Do Not:
- Do not return anything other than strict JSON.

[ Output Format ]
Return JSON:
{{
    "is_ok": true or false,
    "reason": "short explanation",
    "actions": ["add ...", "remove ...", "edit ..."],
    "queries": ["q1", "q2", "q3"]
}}
"""

QUERY_REFINE_MAX_TURNS = int(os.getenv("QUERY_REFINE_MAX_TURNS", "0"))


def _snippet_identity(snippet: Dict[str, Any]) -> str:
    return snippet.get("url") or f"{snippet.get('repo', '')}:{snippet.get('path', '')}"


def _normalize_result(result: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(result)
    normalized["repo"] = result.get("repo") or result.get("repository") or ""
    normalized["url"] = result.get("url") or result.get("html_url") or ""
    normalized["path"] = result.get("path") or ""
    normalized["snippet"] = result.get("snippet") or result.get("code") or ""
    normalized["code"] = normalized["snippet"]
    return normalized


def _normalize_queries(parsed: Dict[str, Any], language: str) -> List[str]:
    raw_queries = parsed.get("queries")
    if not isinstance(raw_queries, list):
        single = str(parsed.get("query", "")).strip()
        raw_queries = [single] if single else []

    deduped: List[str] = []
    seen = set()
    for item in raw_queries:
        query = str(item).strip()
        if not query:
            continue
        if f"language:{language}" not in query:
            query = f"{query} language:{language}"
        if query in seen:
            continue
        seen.add(query)
        deduped.append(query)
        if len(deduped) >= 3:
            break
    return deduped


def _make_query(
    llm: BaseChatModel,
    generator_system: SystemMessage,
    language: str,
    target_predicate: str,
    logic_tree_with_code: Dict[str, Any],
    direction: str,
    goal: str,
    context_messages: List[AnyMessage],
) -> List[str]:
    prompt = QUERY_PROMPT.format(
        target_predicate=target_predicate,
        logic_tree_with_code=json.dumps(logic_tree_with_code, indent=2),
        direction=direction,
        goal=goal,
        language=language,
    )
    human_msg = HumanMessage(content=prompt)
    response = llm.invoke([generator_system] + context_messages + [human_msg])
    if isinstance(response.content, list):
        response_text = response.content[0]['text']
    else:
        response_text = response.content
    parsed = parse_json(response_text)
    queries = _normalize_queries(parsed, language)
    if not queries:
        print(
            f"[query_agent_api] WARNING: query generation returned NO queries "
            f"predicate='{target_predicate}' direction='{direction}' "
            f"raw={response_text[:400]!r}"
        )
    else:
        print(
            f"[query_agent_api] generated queries predicate='{target_predicate}' "
            f"direction='{direction}': {queries}"
        )
    return queries


def _evaluate_search_results_batch(
    llm: BaseChatModel,
    evaluator_system: SystemMessage,
    snippets: List[Dict[str, Any]],
    seen_patterns: List[str],
) -> List[Dict[str, str]]:

    prompt = EVALUATOR_PROMPT.format(
        snippets=json.dumps(snippets, indent=2),
        seen_patterns="\n".join(f"- {p}" for p in seen_patterns) or "(none)",
    )
    human_msg = HumanMessage(content=prompt)
    response = llm.invoke(input=[evaluator_system, human_msg])
    if isinstance(response.content, list):
        response_text = response.content[0]['text']
    else:
        response_text = response.content
    parsed = parse_json(response_text)
    selected = parsed.get("selected", [])
    if not isinstance(selected, list):
        return []

    normalized: List[Dict[str, str]] = []
    for item in selected[:3]:
        if not isinstance(item, dict):
            continue
        snippet = str(item.get("snippet", "")).strip()
        if not snippet:
            continue
        normalized.append(
            {
                "snippet": snippet,
                "reason": str(item.get("reason", "unknown")),
                "pattern": str(item.get("pattern", "")),
            }
        )
    return normalized


def _search_with_api(query: str, target_cnt: int) -> List[Dict[str, Any]]:
    print(f"[query_agent_api] github_search query={query!r} target_cnt={target_cnt}")
    parsed = github_code_search(
        query=query,
        target_results=max(target_cnt, 1),
        context_lines=5,
    )

    if isinstance(parsed, dict) and parsed.get("error"):
        print(f"[query_agent_api] search error: {parsed.get('error')}")
        return []

    if not isinstance(parsed, list):
        print(f"[query_agent_api] search returned non-list: {type(parsed).__name__}")
        return []

    items = [item for item in parsed if isinstance(item, dict)]
    print(f"[query_agent_api] github_search query={query!r} returned {len(items)} result(s)")
    return items


def _peek_search_results(queries: List[str]) -> List[Dict[str, Any]]:
    per_query_peek: List[Dict[str, Any]] = []
    for query in queries:
        raw_items = github_code_peek(query=query)
        per_query_peek.append(
            {
                "query": query,
                "top_results": raw_items,
            }
        )
    return per_query_peek


def _refine_queries_once(
    llm: BaseChatModel,
    generator_system: SystemMessage,
    language: str,
    target_predicate: str,
    goal: str,
    current_queries: List[str],
    peek_results: List[Dict[str, Any]],
    context_messages: List[AnyMessage],
) -> Dict[str, Any]:
    prompt = QUERY_REFINE_PROMPT.format(
        goal=goal,
        target_predicate=target_predicate,
        current_queries=json.dumps(current_queries, indent=2),
        peek_results=json.dumps(peek_results, indent=2),
        language=language,
    )
    response = llm.invoke([generator_system] + context_messages + [HumanMessage(content=prompt)])
    if isinstance(response.content, list):
        response_text = response.content[0]["text"]
    else:
        response_text = response.content

    parsed = parse_json(response_text)
    refined = _normalize_queries(parsed, language)
    is_ok = bool(parsed.get("is_ok", False))
    reason = str(parsed.get("reason", ""))
    actions = parsed.get("actions", [])
    if not isinstance(actions, list):
        actions = []

    return {
        "is_ok": is_ok,
        "reason": reason,
        "actions": [str(a) for a in actions],
        "queries": refined if refined else list(current_queries),
    }


def _new_candidate_snippets(raw_items: List[Dict[str, Any]], seen_ids: set) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    for item in raw_items:
        snippet = _normalize_result(item)
        snippet_id = _snippet_identity(snippet)
        if snippet_id in seen_ids:
            continue
        seen_ids.add(snippet_id)
        if not snippet.get("snippet", "").strip():
            continue
        candidates.append(snippet)
    return candidates


def _search_and_evaluate_direction(
    llm: BaseChatModel,
    evaluator_system: SystemMessage,
    queries: List[str],
    target_cnt: int,
    seen_ids: List[str],
    seen_patterns: List[str],
) -> Dict[str, Any]:
    if not queries:
        return {
            "selected_examples": [],
            "seen_ids": list(seen_ids),
            "seen_patterns": list(seen_patterns),
            "search_count": 0,
        }

    merged_raw_items: List[Dict[str, Any]] = []
    for query in queries:
        merged_raw_items.extend(_search_with_api(query, target_cnt))

    mutable_seen_ids = set(seen_ids)
    candidates = _new_candidate_snippets(merged_raw_items, mutable_seen_ids)
    if not candidates:
        print(
            f"[query_agent_api] search produced 0 new candidates "
            f"(raw={len(merged_raw_items)}, queries={len(queries)})"
        )
        return {
            "selected_examples": [],
            "seen_ids": list(mutable_seen_ids),
            "seen_patterns": list(seen_patterns),
            "search_count": len(queries),
        }

    serialized_candidates = [
        {
            "repo": snippet.get("repo", ""),
            "path": snippet.get("path", ""),
            "url": snippet.get("url", ""),
            "snippet": snippet.get("snippet", ""),
        }
        for snippet in candidates
    ]

    print(f"[query_agent_api] evaluating {len(serialized_candidates)} candidate(s) from {len(queries)} query(ies)")

    selections = _evaluate_search_results_batch(
        llm=llm,
        evaluator_system=evaluator_system,
        snippets=serialized_candidates,
        seen_patterns=seen_patterns,
    )
    print(f"[query_agent_api] evaluator selected {len(selections)} example(s) from {len(serialized_candidates)} candidate(s)")

    kept_items: List[Dict[str, Any]] = []
    next_seen_patterns = list(seen_patterns)
    for item in selections:
        kept = {
            "snippet": item.get("snippet", ""),
            "code": item.get("snippet", ""),
            "reason": item.get("reason", ""),
            "pattern": item.get("pattern", ""),
        }
        kept_items.append(kept)

        pattern = str(item.get("pattern", "")).strip()
        if pattern:
            next_seen_patterns.append(pattern)

    return {
        "selected_examples": kept_items[:3],
        "seen_ids": list(mutable_seen_ids),
        "seen_patterns": next_seen_patterns,
        "search_count": len(queries),
    }


def build_workflow(llm: BaseChatModel, language: str, skip_refine_pipeline: bool = True):
    generator_system = SystemMessage(
        content=GENERATOR_SYSTEM_PROMPT.format(
            code_search_skill=CODE_SEARCH_SKILL_TEXT,
            language=language,
        )
    )
    evaluator_system = SystemMessage(content=EVALUATOR_SYSTEM_PROMPT)

    def generate_queries_node(state: QueryAgentState) -> Dict[str, Any]:
        context_messages = list(state.get("messages", []))
        target_predicate = state["target_predicate"]
        logic_tree_with_code = state["logic_tree_with_code"]

        fn_goal = (
            "Find risky implementations related to the predicate but structurally different from current coverage. "
            "These may become false negatives if missed."
        )
        fp_goal = (
            "Find secure remediation/mitigation patterns related to the predicate. "
            "These may become false positives if not excluded."
        )

        # Execute sequentially to avoid rate limiting
        fn_queries = _make_query(
            llm=llm,
            generator_system=generator_system,
            language=language,
            target_predicate=target_predicate,
            logic_tree_with_code=logic_tree_with_code,
            direction="alternative_pattern_false_negative",
            goal=fn_goal,
            context_messages=list(context_messages),
        )

        fp_queries = _make_query(
            llm=llm,
            generator_system=generator_system,
            language=language,
            target_predicate=target_predicate,
            logic_tree_with_code=logic_tree_with_code,
            direction="mitigation_pattern_false_positive",
            goal=fp_goal,
            context_messages=list(context_messages),
        )

        return {
            "fn_last_query": fn_queries,
            "fp_last_query": fp_queries,
            "query_refine_turn": 0,
            "query_refine_max_turns": QUERY_REFINE_MAX_TURNS,
            "fn_refine_done": False,
            "fp_refine_done": False,
            "iteration_count": state.get("iteration_count", 0) + 1,
            "skip_refine_pipeline": skip_refine_pipeline,
        }

    def refine_queries_node(state: QueryAgentState) -> Dict[str, Any]:
        context_messages = state.get("messages", [])
        target_predicate = state["target_predicate"]

        fn_goal = (
            "Find risky implementations related to the predicate but structurally different from current coverage. "
            "These may become false negatives if missed."
        )
        fp_goal = (
            "Find secure remediation/mitigation patterns related to the predicate. "
            "These may become false positives if not excluded."
        )

        def _refine_one_direction(
            current_queries: List[str],
            goal: str,
            already_done: bool,
        ) -> Dict[str, Any]:
            if already_done or not current_queries:
                return {
                    "queries": list(current_queries),
                    "done": True,
                    "reason": "already_done_or_empty",
                }

            peek_results = _peek_search_results(current_queries)
            refine_result = _refine_queries_once(
                llm=llm,
                generator_system=generator_system,
                language=language,
                target_predicate=target_predicate,
                goal=goal,
                current_queries=current_queries,
                peek_results=peek_results,
                context_messages=list(context_messages),
            )

            next_queries = refine_result.get("queries", [])
            is_ok = bool(refine_result.get("is_ok", False))
            done = is_ok or next_queries == current_queries
            return {
                "queries": next_queries if next_queries else list(current_queries),
                "done": done,
                "reason": refine_result.get("reason", ""),
            }

        # Execute sequentially to avoid rate limiting
        fn_res = _refine_one_direction(
            list(state.get("fn_last_query", [])),
            fn_goal,
            bool(state.get("fn_refine_done", False)),
        )
        fp_res = _refine_one_direction(
            list(state.get("fp_last_query", [])),
            fp_goal,
            bool(state.get("fp_refine_done", False)),
        )

        return {
            "fn_last_query": fn_res.get("queries", list(state.get("fn_last_query", []))),
            "fp_last_query": fp_res.get("queries", list(state.get("fp_last_query", []))),
            "fn_refine_done": bool(fn_res.get("done", False)),
            "fp_refine_done": bool(fp_res.get("done", False)),
            "query_refine_turn": state.get("query_refine_turn", 0) + 1,
        }

    def should_continue_refine(state: QueryAgentState) -> str:
        if bool(state.get("skip_refine_pipeline", False)):
            return "search_and_evaluate"
        if bool(state.get("fn_refine_done", False)) and bool(state.get("fp_refine_done", False)):
            return "search_and_evaluate"
        if state.get("query_refine_turn", 0) >= state.get("query_refine_max_turns", QUERY_REFINE_MAX_TURNS):
            return "search_and_evaluate"
        return "refine_queries"

    def search_and_evaluate_node(state: QueryAgentState) -> Dict[str, Any]:
        fn_queries = state.get("fn_last_query", [])
        fp_queries = state.get("fp_last_query", [])
        target_cnt = state["target_cnt"]
        fn_seen_patterns = list(state.get("fn_seen_patterns", []))
        fp_seen_patterns = list(state.get("fp_seen_patterns", []))
        fn_saved_examples = list(state.get("fn_saved_examples", []))
        fp_saved_examples = list(state.get("fp_saved_examples", []))

        def _search_eval_direction(
            queries: List[str],
            seen_ids: List[str],
            seen_patterns: List[str],
        ) -> Dict[str, Any]:
            return _search_and_evaluate_direction(
                llm=llm,
                evaluator_system=evaluator_system,
                queries=queries,
                target_cnt=target_cnt,
                seen_ids=seen_ids,
                seen_patterns=seen_patterns,
            )

        # Execute sequentially to avoid rate limiting
        fn_result = _search_eval_direction(
            fn_queries,
            list(state.get("fn_seen_ids", [])),
            fn_seen_patterns,
        )
        fp_result = _search_eval_direction(
            fp_queries,
            list(state.get("fp_seen_ids", [])),
            fp_seen_patterns,
        )

        for kept in fn_result["selected_examples"]:
            fn_saved_examples.append(kept)
            if len(fn_saved_examples) >= state["target_cnt"]:
                break

        for kept in fp_result["selected_examples"]:
            fp_saved_examples.append(kept)
            if len(fp_saved_examples) >= state["target_cnt"]:
                break

        return {
            "fn_saved_examples": fn_saved_examples,
            "fn_seen_ids": fn_result["seen_ids"],
            "fn_seen_patterns": fn_result["seen_patterns"],
            "fp_saved_examples": fp_saved_examples,
            "fp_seen_ids": fp_result["seen_ids"],
            "fp_seen_patterns": fp_result["seen_patterns"],
            "search_iterations": state.get("search_iterations", 0)
            + fn_result["search_count"]
            + fp_result["search_count"],
        }

    def should_continue(state: QueryAgentState) -> str:
        fn_saved = len(state.get("fn_saved_examples", []))
        fp_saved = len(state.get("fp_saved_examples", []))
        target_cnt = state.get("target_cnt", 0)

        if fn_saved >= target_cnt and fp_saved >= target_cnt:
            return "build_output"
        if state.get("iteration_count", 0) >= state.get("max_iterations", 0):
            return "build_output"
        return "generate_queries"

    def build_output_node(state: QueryAgentState) -> Dict[str, Any]:
        fn_examples = state.get("fn_saved_examples", [])
        fp_examples = state.get("fp_saved_examples", [])
        all_examples = fn_examples + fp_examples

        result = {
            "target_predicate": state.get("target_predicate", ""),
            "language": state.get("language", language),
            "logic_tree_with_code": state.get("logic_tree_with_code", {}),
            "current_cnt": len(all_examples),
            "target_cnt": state.get("target_cnt", 0) * 2,
            "saved_code_snippets": all_examples,
            "false_negative_examples": fn_examples,
            "false_positive_examples": fp_examples,
            "search_iterations": state.get("search_iterations", 0),
            "max_iterations": state.get("max_iterations", 0),
            "last_query": {
                "false_negative": state.get("fn_last_query", []),
                "false_positive": state.get("fp_last_query", []),
            },
        }
        return {"result": result}

    workflow = StateGraph(QueryAgentState)
    workflow.add_node("generate_queries", generate_queries_node)
    workflow.add_node("refine_queries", refine_queries_node)
    workflow.add_node("search_and_evaluate", search_and_evaluate_node)
    workflow.add_node("build_output", build_output_node)

    workflow.add_edge(START, "generate_queries")
    workflow.add_conditional_edges(
        "generate_queries",
        lambda state: "search_and_evaluate" if bool(state.get("skip_refine_pipeline", False)) else "refine_queries",
        ["refine_queries", "search_and_evaluate"],
    )
    workflow.add_conditional_edges(
        "refine_queries",
        should_continue_refine,
        ["refine_queries", "search_and_evaluate"],
    )
    workflow.add_conditional_edges(
        "search_and_evaluate",
        should_continue,
        ["generate_queries", "build_output"],
    )
    workflow.add_edge("build_output", END)

    return workflow.compile(checkpointer=checkpointer)


def find_code_snippets(
    llm: BaseChatModel,
    language: str,
    target_predicate: str,
    logic_tree_with_code: Dict[str, Any],
    target_cnt: int = 5,
    max_iterations: int = 5,
    callback_handler: Any = None,
    skip_refine_pipeline: Optional[bool] = None,
) -> Dict[str, Any]:
    if skip_refine_pipeline is None:
        skip_refine_pipeline = os.getenv("QUERY_AGENT_SKIP_REFINE_PIPELINE", "1").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    agent = build_workflow(llm=llm, language=language, skip_refine_pipeline=skip_refine_pipeline)
    initial_state: QueryAgentState = {
        "messages": [],
        "target_predicate": target_predicate,
        "logic_tree_with_code": logic_tree_with_code,
        "target_cnt": target_cnt,
        "max_iterations": max_iterations,
        "iteration_count": 0,
        "search_iterations": 0,
        "language": language,
        "fn_last_query": [],
        "fn_saved_examples": [],
        "fn_seen_ids": [],
        "fn_seen_patterns": [],
        "fp_last_query": [],
        "fp_saved_examples": [],
        "fp_seen_ids": [],
        "fp_seen_patterns": [],
        "query_refine_turn": 0,
        "query_refine_max_turns": QUERY_REFINE_MAX_TURNS,
        "fn_refine_done": False,
        "fp_refine_done": False,
        "skip_refine_pipeline": skip_refine_pipeline,
        "result": {},
    }

    print(
        f"[query_agent_api] find_code_snippets START target_predicate={target_predicate!r} "
        f"language={language} target_cnt={target_cnt} max_iterations={max_iterations} "
        f"skip_refine_pipeline={skip_refine_pipeline} tree={json.dumps(logic_tree_with_code)[:300]!r}"
    )

    final_state = agent.invoke(
        initial_state,
        config={
            "configurable": {"thread_id": str(uuid.uuid4())},
            "callbacks": callback_handler,
            },
    )
    result = final_state.get("result", {})
    print(
        f"[query_agent_api] find_code_snippets DONE target_predicate={target_predicate!r} "
        f"fn={len(result.get('false_negative_examples', []))} "
        f"fp={len(result.get('false_positive_examples', []))} "
        f"search_iterations={result.get('search_iterations', 0)} "
        f"last_query={json.dumps(result.get('last_query', {}))}"
    )
    return result


if __name__ == "__main__":

    from agents.model import llm
    import langfuse_debug
    from langfuse.langchain import CallbackHandler

    lf_handler = CallbackHandler()

    target_predicate = "Use of insecure MD5 hashing"
    logic_tree = {
        "condition": "MD5 hash usage",
        "patterns": ["hashlib.md5", "Crypto.Hash.MD5"],
    }

    result = find_code_snippets(
        llm=llm,
        language="java",
        target_predicate=target_predicate,
        logic_tree_with_code=logic_tree,
        target_cnt=3,
        max_iterations=1,
        callback_handler=[lf_handler]
    )

    print(
        json.dumps(
            {
                "current_cnt": result.get("current_cnt"),
                "false_negative_count": len(result.get("false_negative_examples", [])),
                "false_positive_count": len(result.get("false_positive_examples", [])),
                "search_iterations": result.get("search_iterations"),
                "last_query": result.get("last_query"),
            },
            indent=2,
        )
    )
