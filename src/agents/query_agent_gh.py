"""Query agent using gh CLI code search in a generator-evaluator multi-agent loop.

This module provides a QueryAgent-style interface and output shape, and executes
search with `gh search code` via a wrapper tool.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.chat_models.tongyi import ChatTongyi

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.gh_code_search import gh_code_search
from .utils import parse_json


GENERATOR_SYSTEM_PROMPT = """[ System Prompt ]
You are an {language} engineer who is skilled at all aspects of code development.
Only answer strictly in the following JSON format following the output format instructions.

[ Task / User Prompt ]
You help find diverse code examples with GitHub code search.

[ Do and Do Not ]
Do:
- Generate queries that retrieve diverse, relevant code examples.
- Use previous conversation context to avoid repeating ideas and improve diversity.
Do Not:
- Do not return anything other than strict JSON.

[ Output Format ]
Return JSON:
{{
  "query": "compact gh search code query",
  "focus": "why this query should retrieve diverse useful snippets"
}}
"""

QUERY_PROMPT = """[ System Prompt ]
You are an {language} engineer who is skilled at all aspects of code development.
Only answer strictly in the following JSON format following the output format instructions.

[ Task / User Prompt ]
Here is some {language} code snippets that can be caught by a static analysis predicate.
Please analyze what they are doing and extract the keywords to generate a search query to find more diverse code snippets
that are relevant to the given code snippets.
When you generate the search query, you can think from two directions:
1. Alternative patterns that the current predicate may miss, which may become false negatives.
2. Mitigation or remediation patterns that the current predicate should exclude, which may become false positives.

Here is the target predicate you want to find code snippets for:
{target_predicate}

And here is the current implementation of the predicate in a logic tree format with code examples:
{logic_tree_with_code}

Search direction:
{direction}

Your goal is:
{goal}

[ Do and Do Not ]
Do:
- Generate multiple queries, each query is a list of keywords, and each keyword can be a term or a short pattern.
- Use previous conversation context to avoid repeating ideas and improve diversity.
Do Not:
- Do not return anything other than strict JSON.

[ Output Format ]
Return JSON:
{{
  "query": "compact gh search code query",
  "focus": "why this query should retrieve diverse useful snippets"
}}
"""


EVALUATOR_SYSTEM_PROMPT = """[ System Prompt ]
You are a strict snippet evaluator for static-analysis dataset expansion with deep expertise in {language} code patterns.
Only answer strictly in the following JSON format following the output format instructions.

[ Task / User Prompt ]
Decide whether each snippet should be kept.

[ Do and Do Not ]
Do:
- KEEP a snippet if it is relevant and likely exposes an alternative vulnerable pattern (FN direction) or a secure mitigation/remediation pattern (FP direction), and is meaningfully different.
- IGNORE a snippet if it is duplicate, too common, already covered, or not related.
Do Not:
- Do not return anything other than strict JSON.

[ Output Format ]
Return JSON:
{{
  "decision": "keep" | "ignore",
  "reason": "short reason label",
  "pattern": "short pattern name when keep, else empty"
}}
"""

EVALUATOR_PROMPT = """[ System Prompt ]
You are a strict snippet evaluator for static-analysis dataset expansion with deep expertise in code pattern detection.
Only answer strictly in the following JSON format following the output format instructions.

[ Task / User Prompt ]
Evaluate this snippet candidate.

Target predicate:
{target_predicate}

Predicate implementation:
{logic_tree_with_code}

Direction:
{direction}

Snippet candidate:
{snippet}

Seen patterns:
{seen_patterns}

[ Do and Do Not ]
Do:
- KEEP if it is relevant and likely exposes an alternative vulnerable pattern (FN direction) or a secure mitigation/remediation pattern (FP direction), and is meaningfully different.
- IGNORE if duplicate, too common, already covered, or not related.
Do Not:
- Do not return anything other than strict JSON.

[ Output Format ]
Return JSON:
{{
  "decision": "keep" | "ignore",
  "reason": "short reason label",
  "pattern": "short pattern name when keep, else empty"
}}
"""


def _snippet_identity(snippet: Dict[str, Any]) -> str:
    return snippet.get("url") or f"{snippet.get('repo', '')}:{snippet.get('path', '')}"


def _normalize_result(result: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(result)
    normalized["repo"] = result.get("repo") or ""
    normalized["url"] = result.get("url") or ""
    normalized["path"] = result.get("path") or ""
    normalized["snippet"] = result.get("snippet") or result.get("code") or ""
    normalized["code"] = normalized["snippet"]
    return normalized


class QueryAgentGH:
    def __init__(self, llm: BaseChatModel, language: str):
        self.llm = llm
        self.language = language
        self.generator_system = SystemMessage(content=GENERATOR_SYSTEM_PROMPT.format(language=language))
        self.evaluator_system = SystemMessage(content=EVALUATOR_SYSTEM_PROMPT.format(language=language))

    def _make_query(
        self,
        target_predicate: str,
        logic_tree_with_code: Dict[str, Any],
        direction: str,
        goal: str,
        context_messages: List[Any],
    ) -> str:
        prompt = QUERY_PROMPT.format(
            target_predicate=target_predicate,
            logic_tree_with_code=json.dumps(logic_tree_with_code, indent=2),
            direction=direction,
            language=self.language,
            goal=goal,
        )
        human_msg = HumanMessage(content=prompt)
        response = self.llm.invoke([self.generator_system] + context_messages + [human_msg])
        context_messages.extend([human_msg, response])
        return parse_json(response.content).get("query", "")

    def _evaluate_snippet(
        self,
        target_predicate: str,
        logic_tree_with_code: Dict[str, Any],
        direction: str,
        snippet: Dict[str, Any],
        seen_patterns: List[str],
        context_messages: List[Any],
    ) -> Dict[str, str]:
        prompt = EVALUATOR_PROMPT.format(
            target_predicate=target_predicate,
            logic_tree_with_code=json.dumps(logic_tree_with_code, indent=2),
            direction=direction,
            snippet=json.dumps(snippet, indent=2),
            seen_patterns="\n".join(f"- {p}" for p in seen_patterns) or "(none)",
        )
        human_msg = HumanMessage(content=prompt)
        response = self.llm.invoke([self.evaluator_system] + context_messages + [human_msg])
        context_messages.extend([human_msg, response])
        parsed = parse_json(response.content)
        return {
            "decision": str(parsed.get("decision", "ignore")).lower(),
            "reason": str(parsed.get("reason", "unknown")),
            "pattern": str(parsed.get("pattern", "")),
        }

    def _search_with_gh(self, query: str, target_cnt: int) -> List[Dict[str, Any]]:
        result = gh_code_search.invoke(
            {
                "query": query,
                "language": self.language,
                "target_results": max(target_cnt, 1),
            }
        )
        try:
            parsed = json.loads(result)
        except json.JSONDecodeError:
            return []

        if isinstance(parsed, dict) and parsed.get("error"):
            print(f"[QueryAgentGH] search error: {parsed.get('error')}")
            return []

        if not isinstance(parsed, list):
            return []

        return [item for item in parsed if isinstance(item, dict)]

    def _new_candidate_snippets(
        self,
        raw_items: List[Dict[str, Any]],
        seen_ids: set,
    ) -> List[Dict[str, Any]]:
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

    def _evaluate_and_keep(
        self,
        target_predicate: str,
        logic_tree_with_code: Dict[str, Any],
        direction: str,
        snippet: Dict[str, Any],
        seen_patterns: List[str],
        evaluator_context: List[Any],
        saved: List[Dict[str, Any]],
    ) -> bool:
        decision = self._evaluate_snippet(
            target_predicate=target_predicate,
            logic_tree_with_code=logic_tree_with_code,
            direction=direction,
            snippet=snippet,
            seen_patterns=seen_patterns,
            context_messages=evaluator_context,
        )

        if decision.get("decision") != "keep":
            return False

        kept = dict(snippet)
        kept["reason"] = decision.get("reason", "")
        kept["pattern"] = decision.get("pattern", "")
        kept["search_direction"] = direction
        saved.append(kept)

        pattern = decision.get("pattern", "").strip()
        if pattern:
            seen_patterns.append(pattern)
        return True

    def _run_direction(
        self,
        target_predicate: str,
        logic_tree_with_code: Dict[str, Any],
        direction: str,
        goal: str,
        target_cnt: int,
        max_iterations: int,
    ) -> Dict[str, Any]:
        saved: List[Dict[str, Any]] = []
        seen_ids = set()
        seen_patterns: List[str] = []

        generator_context: List[Any] = []
        evaluator_context: List[Any] = []

        last_query = ""
        last_search_results = "[]"
        search_iterations = 0

        for _ in range(max_iterations):
            if len(saved) >= target_cnt:
                break

            last_query = self._make_query(
                target_predicate=target_predicate,
                logic_tree_with_code=logic_tree_with_code,
                direction=direction,
                goal=goal,
                context_messages=generator_context,
            )
            if not last_query:
                continue

            search_iterations += 1
            raw_items = self._search_with_gh(last_query, target_cnt)
            last_search_results = json.dumps(raw_items)
            candidates = self._new_candidate_snippets(raw_items, seen_ids)

            for snippet in candidates:
                self._evaluate_and_keep(
                    target_predicate=target_predicate,
                    logic_tree_with_code=logic_tree_with_code,
                    direction=direction,
                    snippet=snippet,
                    seen_patterns=seen_patterns,
                    evaluator_context=evaluator_context,
                    saved=saved,
                )

                if len(saved) >= target_cnt:
                    break

        return {
            "examples": saved,
            "count": len(saved),
            "search_iterations": search_iterations,
            "last_query": last_query,
            "last_search_results": last_search_results,
        }

    def find_code_snippets(
        self,
        target_predicate: str,
        logic_tree_with_code: Dict[str, Any],
        target_cnt: int = 5,
        max_iterations: int = 5,
    ) -> Dict[str, Any]:
        """Find code snippets for FN/FP directions with QueryAgent-compatible output."""
        alternative_goal = (
            "Find vulnerable or risky implementations related to the predicate but structurally different from the current implementation. "
            "These may become false negative cases if the predicate does not cover them. "
            f"Only return {self.language} examples. "
            "Focus on diversity across frameworks, repositories, APIs, and coding styles."
        )
        mitigation_goal = (
            "Find secure remediation, mitigation, sanitization, parameterization, validation, or safe-wrapper implementations related to the predicate. "
            "These may become false positive cases if the predicate cannot exclude them. "
            f"Only return {self.language} examples. "
            "Focus on diversity across frameworks, repositories, APIs, and coding styles."
        )

        false_negative = self._run_direction(
            target_predicate,
            logic_tree_with_code,
            "alternative_pattern_false_negative",
            alternative_goal,
            target_cnt,
            max_iterations,
        )
        false_positive = self._run_direction(
            target_predicate,
            logic_tree_with_code,
            "mitigation_pattern_false_positive",
            mitigation_goal,
            target_cnt,
            max_iterations,
        )

        all_examples = false_negative["examples"] + false_positive["examples"]
        return {
            "target_predicate": target_predicate,
            "language": self.language,
            "logic_tree_with_code": logic_tree_with_code,
            "current_cnt": len(all_examples),
            "target_cnt": target_cnt * 2,
            "saved_code_snippets": all_examples,
            "false_negative_examples": false_negative["examples"],
            "false_positive_examples": false_positive["examples"],
            "search_iterations": false_negative["search_iterations"] + false_positive["search_iterations"],
            "max_iterations": max_iterations,
            "last_query": {
                "false_negative": false_negative["last_query"],
                "false_positive": false_positive["last_query"],
            },
            "last_search_results": {
                "false_negative": false_negative["last_search_results"],
                "false_positive": false_positive["last_search_results"],
            },
        }



