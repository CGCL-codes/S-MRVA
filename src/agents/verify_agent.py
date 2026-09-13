"""New Verify Agent - compare LLM judge vs analyzer tool result.

Workflow (LangGraph):
1. llm_judge: LLM decides whether mutant SHOULD have an issue.
2. analyzer_check: run analyzer tool on mutant code.
3. compare: classify disagreement as FP/FN when outcomes differ.
4. assess (conditional): evaluate mutant validity/commonness/criticality.
5. build_report (conditional): generate report when valid and common.
"""

import json
import operator
import re
from pathlib import Path
from typing import Any, Dict, List, Literal
import uuid

from typing_extensions import Annotated, TypedDict
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from analyzers.analyzer import Analyzer
try:
	from utils import parse_json
except ImportError:
	def parse_json(response: str) -> Dict[str, Any]:
		json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
		if json_match:
			try:
				return json.loads(json_match.group(1))
			except json.JSONDecodeError:
				pass

		json_match = re.search(r'\{[\s\S]*\}', response)
		if json_match:
			try:
				return json.loads(json_match.group())
			except json.JSONDecodeError:
				pass

		return {}


JUDGE_SYSTEM_PROMPT = """[ System Prompt ]
You are a {language} code security expert who decides whether a given code snippet contains a described security issue.
Only answer strictly in the following JSON format following the output format instructions.

[ Task / User Prompt ]
Your task is to find out whether the given code has the following security issue:
------------------------------ Issue description -----------------------------
{rule_goal}
-------------------------------- Notes ---------------------------------
The comments are only a reference and may be wrong; base your judgment on the code itself.

[ Do and Do Not ]
Do:
- Give your own judgment based strictly on the given code.
- Focus on the specific code snippet provided, without assuming external context.
- Return STRICT JSON only with exactly the fields in the output format.
Do Not:
- Do not blindly trust comments or any oracle prompt.
- Do not speculate about missing external context.
- Do not add extra JSON fields.

[ Few-shot Example ]
Input code:
```java
String q = "SELECT * FROM users WHERE id=" + userInput;
ResultSet rs = stmt.executeQuery(q);
```
Expected output:
```json
{{"has_issue": true, "reason": "The SQL query is built by directly concatenating the untrusted variable userInput into the query string and then executing it, which allows SQL injection."}}
```

[ Output Format ]
```json
{{
  "has_issue": true or false,
  "reason": "detailed explanation"
}}
```
"""


JUDGE_PROMPT = """[ System Prompt ]
You are a precise code analyzer that applies the given security rule to code snippets.
Only answer strictly in the following JSON format following the output format instructions.

[ Task / User Prompt ]
Please analyze the following code and determine if it has the security issue described in the system prompt.

------------------------------ Code to analyze -----------------------------
{mutant_code}

[ Do and Do Not ]
Do:
- Apply the security rule from the system prompt to this exact snippet.
- Consider how the snippet is actually used within the provided lines.
- Return strict JSON with exactly the output format fields.
Do Not:
- Do not report issues that are not present in the snippet.
- Do not return anything besides the JSON object.

[ Few-shot Example ]
Input code:
```python
import os
os.system("rm -rf " + userInput)
```
Expected output:
```json
{{"has_issue": true, "reason": "os.system executes a shell command that includes the untrusted userInput directly, enabling command injection."}}
```

[ Output Format ]
```json
{{
  "has_issue": true or false,
  "reason": "detailed explanation"
}}
```
"""


ASSESS_SYSTEM_PROMPT = """[ System Prompt ]
You are a security expert and you are familiar with static analysis tools.
Only answer strictly in the following JSON format following the output format instructions.

[ Task / User Prompt ]
Your task is to determine whether it is a valuable false positive or false negative of the static analyzer on a code snippet, when there is a disagreement between the LLM judge and the static analyzer output.
Definitions:
1. A valid issue means the code indeed reveals a false positive or false negative of the static analyzer, regardless of whether it is common or critical.
2. A common issue means it is a realistic code pattern that is likely to appear in real codebases, not some extremely contrived or unrealistic code.
3. A critical issue means it has a high potential to cause real security vulnerabilities or significant problems in practice, not just a minor or theoretical issue.

[ Do and Do Not ]
Do:
- Judge validity independently from commonness and criticality.
- Base the assessment on the provided code, tool output, and LLM judgment.
- Return strict JSON only with exactly the output format fields.
Do Not:
- Do not mark an issue valid only because both sides disagree.
- Do not add extra fields or prose outside the JSON object.

[ Few-shot Example ]
Input scenario:
The static analyzer reports a potential SQL injection in a JDBC statement built by string concatenation, while the LLM judge considers the code safe because the input appears bounded.
```java
String q = "SELECT * FROM products WHERE price > " + priceParam;
stmt.executeQuery(q);
```
Expected output:
```json
{{"is_valid": true, "is_common": true, "is_critical": true, "assessment_reason": "The code concatenates the external priceParam directly into the query and executes it, which is a realistic SQL injection pattern the analyzer should flag; this is a genuine false negative, common in real codebases and critical in impact.", "bug_description": "The SQL query is built by unsanitized string concatenation of external input, allowing SQL injection."}}
```

[ Output Format ]
```json
{{
  "is_valid": true or false,
  "is_common": true or false,
  "is_critical": true or false,
  "assessment_reason": "detailed reasoning",
  "bug_description": "what is wrong and why"
}}
```
"""


ASSESS_PROMPT = """[ System Prompt ]
You are a security expert and you are familiar with static analysis tools. Only answer strictly in the following JSON format following the output format instructions.

[ Task / User Prompt ]
There is a disagreement between the LLM judge and the static analyzer output, classified as {classification}.
Target predicate: {target_predicate}
Rule goal: {rule_goal}
Predicate goal: {predicate_goal}
Mutation reason: {mutant_reason}

------------------------------ Code under analysis -----------------------------
{mutant_code}

------------------------------- Static Analyzer Output -------------------------
{tool_output}

------------------------------- LLM Judge Output --------------------------------
{llm_reason}

Determine whether this disagreement represents a valuable false positive or false negative of the static analyzer.

[ Do and Do Not ]
Do:
- Apply the valid/common/critical definitions from the system prompt to this concrete case.
- Use the static analyzer output and LLM judgment as evidence, not as ground truth.
- Return strict JSON only with exactly the output format fields.
Do Not:
- Do not declare validity without grounding in the shown code.
- Do not add extra JSON fields or explanatory text outside the JSON object.

[ Few-shot Example ]
Input scenario:
The analyzer flags hardcoded credentials in the code below, while the LLM judge says there is no issue because the file looks like a unit test.
```python
API_KEY = "EXAMPLE-NOT-A-REAL-KEY"
requests.get(url, headers={{"Authorization": API_KEY}})
```
Expected output:
```json
{{"is_valid": true, "is_common": true, "is_critical": true, "assessment_reason": "A hardcoded credential in source code is a realistic pattern that real codebases contain and the analyzer correctly flags it; the LLM's dismissal because it resembles a test is not a sufficient reason, so this is a valuable finding.", "bug_description": "A secret API key is hardcoded in the source, which can leak credentials if the code is shared or committed."}}
```

[ Output Format ]
```json
{{
  "is_valid": true or false,
  "is_common": true or false,
  "is_critical": true or false,
  "assessment_reason": "detailed reasoning",
  "bug_description": "what is wrong and why"
}}
```
"""


class VerifyState(TypedDict):
	messages: Annotated[List[AnyMessage], operator.add]

	language: str
	rule_id: str
	target_predicate: str
	rule_goal: str
	predicate_goal: str
	mutant_code: str
	mutant_reason: str
	oracle: Dict[str, Any]

	llm_has_issue: bool
	llm_reason: str

	tool_has_issue: bool
	tool_output: str
	tool_runtime_error: bool

	disagreement: bool
	classification: Literal["FP", "FN", "NONE"]

	is_valid: bool
	is_common: bool
	is_critical: bool
	assessment_reason: str
	bug_description: str

	should_report: bool
	report: Dict[str, Any]


def _to_bool(value: Any) -> bool:
	if isinstance(value, bool):
		return value
	if isinstance(value, str):
		return value.strip().lower() in {"true", "1", "yes", "y"}
	if isinstance(value, (int, float)):
		return value != 0
	return False


def llm_judge_node(state: VerifyState, llm: BaseChatModel) -> Dict[str, Any]:
	prompt = JUDGE_PROMPT.format(
		mutant_code=state.get("mutant_code", ""),
	)
	system_prompt = JUDGE_SYSTEM_PROMPT.format(
		language=state.get("language", "java"),
		rule_goal=state.get("rule_goal", ""),
	)
	response = llm.invoke([
		SystemMessage(content=system_prompt),
		HumanMessage(content=prompt),
	])

	if isinstance(response.content, list):
		response_text = response.content[0]['text']
	else:
		response_text = response.content
	parsed = parse_json(str(response_text))

	return {
		"messages": [response],
		"llm_has_issue": _to_bool(parsed.get("has_issue", False)),
		"llm_reason": str(parsed.get("reason", "")),
	}


def analyzer_check_node(state: VerifyState, analyzer: Analyzer) -> Dict[str, Any]:
	result = analyzer.run_check_in_temp_dir(
		rule_id=state["rule_id"],
		test_code=state.get("mutant_code", ""),
	)
	return {
		"tool_has_issue": bool(result.issues_found),
		"tool_output": result.output,
		"tool_runtime_error": bool(result.runtime_error),
	}


def compare_node(state: VerifyState) -> Dict[str, Any]:
	llm_has_issue = bool(state.get("llm_has_issue", False))
	tool_has_issue = bool(state.get("tool_has_issue", False))
	tool_runtime_error = bool(state.get("tool_runtime_error", False))

	# fix the case when tool has runtime error, we can't trust its output, so we won't classify it as FP or FN, just mark as no disagreement and no classification
	if tool_runtime_error:
		# If the tool had a runtime error, we can't trust its output, so we won't classify it as FP or FN.
		return {
			"disagreement": False,
			"classification": "NONE",
			"should_report": False,
		}

	if llm_has_issue == tool_has_issue:
		return {
			"disagreement": False,
			"classification": "NONE",
			"should_report": False,
		}

	classification: Literal["FP", "FN", "NONE"] = "FP" if (not llm_has_issue and tool_has_issue) else "FN"
	return {
		"disagreement": True,
		"classification": classification,
	}


def route_after_compare(state: VerifyState) -> str:
	return "assess" if state.get("disagreement", False) else END


def assess_node(state: VerifyState, llm: BaseChatModel) -> Dict[str, Any]:
	prompt = ASSESS_PROMPT.format(
		classification=state.get("classification", "NONE"),
		target_predicate=state.get("target_predicate", ""),
		rule_goal=state.get("rule_goal", ""),
		predicate_goal=state.get("predicate_goal", ""),
		mutant_reason=state.get("mutant_reason", ""),
		mutant_code=state.get("mutant_code", ""),
		tool_output=state.get("tool_output", ""),
		llm_reason=state.get("llm_reason", ""),
	)
	response = llm.invoke([
		SystemMessage(content=ASSESS_SYSTEM_PROMPT),
		HumanMessage(content=prompt),
	])
	if isinstance(response.content, list):
		response_text = response.content[0]['text']
	else:
		response_text = response.content
	parsed = parse_json(str(response_text))

	is_valid = _to_bool(parsed.get("is_valid", False))
	is_common = _to_bool(parsed.get("is_common", False))
	is_critical = _to_bool(parsed.get("is_critical", False))

	return {
		"messages": [response],
		"is_valid": is_valid,
		"is_common": is_common,
		"is_critical": is_critical,
		"assessment_reason": str(parsed.get("assessment_reason", "")),
		"bug_description": str(parsed.get("bug_description", "")),
		"should_report": bool(is_valid and is_common),
	}


def route_after_assess(state: VerifyState) -> str:
	return "build_report" if state.get("should_report", False) else END


def _score_label(is_common: bool, is_critical: bool) -> str:
	if is_common and is_critical:
		return "P0"
	if is_common or is_critical:
		return "P1"
	return "P2"


def build_report_node(state: VerifyState) -> Dict[str, Any]:
	score = _score_label(bool(state.get("is_common", False)), bool(state.get("is_critical", False)))
	report = {
		"classification": state.get("classification", "NONE"),
		"score": score,
		"bug_description": state.get("bug_description", ""),
		"reproduce_code_example": state.get("mutant_code", ""),
		"target_predicate": state.get("target_predicate", ""),
		"rule_goal": state.get("rule_goal", ""),
		"predicate_goal": state.get("predicate_goal", ""),
		"assessment_reason": state.get("assessment_reason", ""),
		"llm_judge": {
			"has_issue": state.get("llm_has_issue", False),
			"reason": state.get("llm_reason", ""),
		},
		"analyzer_check": {
			"has_issue": state.get("tool_has_issue", False),
			"runtime_error": state.get("tool_runtime_error", False),
			"output": state.get("tool_output", ""),
		},
	}
	return {"report": report}


def build_new_verify_workflow(llm: BaseChatModel, analyzer: Analyzer) -> StateGraph:
	workflow = StateGraph(VerifyState)

	workflow.add_node("llm_judge", lambda state: llm_judge_node(state, llm))
	workflow.add_node("analyzer_check", lambda state: analyzer_check_node(state, analyzer))
	workflow.add_node("compare", compare_node)
	workflow.add_node("assess", lambda state: assess_node(state, llm))
	workflow.add_node("build_report", build_report_node)

	workflow.add_edge(START, "llm_judge")
	workflow.add_edge("llm_judge", "analyzer_check")
	workflow.add_edge("analyzer_check", "compare")
	workflow.add_conditional_edges("compare", route_after_compare, ["assess", END])
	workflow.add_conditional_edges("assess", route_after_assess, ["build_report", END])
	workflow.add_edge("build_report", END)
	return workflow


class VerifyAgent:
	"""Compare LLM judgment vs analyzer output and emit FP/FN report when warranted."""

	def __init__(self, llm: BaseChatModel, analyzer: Analyzer):
		self.llm = llm
		self.analyzer = analyzer
		self.checkpointer = InMemorySaver()
		self.agent = build_new_verify_workflow(llm, analyzer).compile(checkpointer=self.checkpointer)

	def verify_mutant(
		self,
		rule_id: str,
		mutant_code: str,
		oracle: Dict[str, Any],
		target_predicate: str,
		rule_goal: str,
		predicate_goal: str,
		mutant_reason: str = "",
		language: str = "java",
	) -> Dict[str, Any]:
		initial_state: VerifyState = {
			"messages": [],
			"language": language,
			"rule_id": rule_id,
			"target_predicate": target_predicate,
			"rule_goal": rule_goal,
			"predicate_goal": predicate_goal,
			"mutant_code": mutant_code,
			"mutant_reason": mutant_reason,
			"oracle": oracle,
			"llm_has_issue": False,
			"llm_reason": "",
			"tool_has_issue": False,
			"tool_output": "",
			"tool_runtime_error": False,
			"disagreement": False,
			"classification": "NONE",
			"is_valid": False,
			"is_common": False,
			"is_critical": False,
			"assessment_reason": "",
			"bug_description": "",
			"should_report": False,
			"report": {},
		}
		return self.agent.invoke(initial_state, config={"configurable":{"thread_id":str(uuid.uuid4())}})