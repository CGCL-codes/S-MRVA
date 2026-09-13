"""Prompts for the Main Agent."""

SYSTEM_PROMPT = """[ System Prompt ]
You are an expert static analysis engineer.
You have extensive knowledge of:
- Static analysis techniques (pattern matching, data flow, taint analysis)
- Popular static analysis tools and their rule formats (CodeQL, Semgrep, Bandit, etc.)
- Security vulnerabilities and code quality issues
- Code patterns and programming idioms
Only answer strictly in the following JSON format following the output format instructions.
"""

ANALYZE_RULE_PROMPT = """[ Task / User Prompt ]
Please read the rule description and test cases below (rule: {rule_id}). Answer exactly these TWO questions:

Q1: What vulnerability or security problem is this rule expected to match?
    Describe the underlying vulnerability class (e.g., SQL injection, path traversal,
    hardcoded credentials, TOCTOU), including the concrete code patterns and data-flow
    relationships that constitute the vulnerability. Be specific about API calls,
    argument patterns, and the threat model.

Q2: What variant patterns are already covered by the existing seed test cases?
    Examine each test case and list the concrete code patterns, API variants,
    and structural variations that the rule currently handles. For each covered
    variant, note which aspect of the rule logic it exercises.

You can use the `web_search` tool to inspect unfamiliar terms, CWE references,
and hyperlinks mentioned in the rule metadata.

Note: The rule content may be in a domain-specific language (CodeQL, Semgrep YAML,
Bandit YAML, etc.) and may contain complex logic. Try to understand it thoroughly.

# Rule Content
```
{rule_content}
```

# Test Cases
```
{test_cases}
```

[ Do and Do Not ]
Do:
- Thoroughly understand the rule even when it is written in a DSL (CodeQL, Semgrep/Bandit YAML, SpotBugs annotations).
- Be specific about API calls, argument patterns, data-flow relationships, and the threat model in Q1.
- In Q2, enumerate each seed test case's concrete patterns/variants and which part of the rule logic each exercises.
- Use web_search for unfamiliar terms, CWE references, or rule-metadata links.
Do Not:
- Do not return anything other than the specified JSON format.
- Do not give vague, high-level descriptions without concrete code patterns.

[ Few-shot Example ]
Example (rule: anonymous-ldap-bind, a Semgrep Java rule):

Rule content (abridged):
  pattern: |
    $ENV.put($CTX.SECURITY_AUTHENTICATION, "none");
    ...
    $DCTX = new InitialDirContext($ENV, ...);

Test cases:
  anonymous-ldap-bind_0.java:
    Hashtable env = new Hashtable();
    env.put(Context.SECURITY_AUTHENTICATION, "none");
    DirContext ctx = new InitialDirContext(env);

Expected output:
{{
  "rule_specification": "Detects anonymous LDAP binds: code that sets the JNDI SECURITY_AUTHENTICATION context property to \\"none\\" and then creates an InitialDirContext with that environment, allowing unauthenticated LDAP operations (CWE-287).",
  "covered_variant_patterns": [
    "Hashtable-based environment with Context.SECURITY_AUTHENTICATION set to \\"none\\" followed by new InitialDirContext(env)"
  ]
}}

[ Output Format ]
```json
{{
    "rule_specification": "Q1 answer: detailed description of the vulnerability this rule detects",
    "covered_variant_patterns": ["Q2 answer: list of code patterns/variants the rule currently covers"],
}}
```
"""


_LOGIC_TREE_PASS1 = """----------------------------------- PASS 1: LINE-TO-LINE PARSE -----------------------------------
Review the rule implementation from top to bottom. For each logical check or
condition you encounter, produce a line-to-line abstraction entry:
- Identify the concrete code region (line numbers or pattern names) in the rule.
- Describe in one sentence what this check does semantically.
- Note whether it is a positive match condition, a negative exclusion (NOT),
  or part of a larger conjunction/disjunction.

This pass ensures no part of the detection logic is overlooked."""

_LOGIC_TREE_PASS2_GROUPED = """----------------------------------- PASS 2: CONSTRUCT HIGH-LEVEL PREDICATES -----------------------
From the line-to-line parse, group related low-level checks into {b_low}-{b_high} high-level
semantic predicates that capture independent detection concerns. Each predicate
should represent a distinct sub-pattern of the vulnerability (e.g., an API usage
pattern, a data-flow constraint, or a structural code property).

Rules:
- Combine checks that serve the same semantic goal into one predicate.
- Do NOT drop any detection logic — every check from Pass 1 must be accounted for.
- If the rule is very simple, as few as {b_low} predicates is fine; for complex rules, at most {b_high}.
- Include the actual implementation source code or key checking logic in the
  "impl" field, NOT just a high-level description.
- The "detection_formula" must express the full boolean logic among predicates.

Organize the final predicates into a logic tree reflecting their AND/OR/NOT
relationships."""

_LOGIC_TREE_PASS2_RAW = """----------------------------------- PASS 2: CONSTRUCT LINE-LEVEL PREDICATES --------------------------
From the line-to-line parse, keep every check at its original granularity:
EACH line-level check from Pass 1 becomes ONE predicate node. Do NOT group or
merge related checks into higher-level predicates.

Rules:
- Do NOT drop any detection logic — every check from Pass 1 must be accounted for.
- There is no predicate-count limit; mirror the rule's real structure.
- Preserve the AND/OR/NOT relationships among checks.
- Include the actual implementation source code or key checking logic in the
  "impl" field, NOT just a high-level description.
- The "detection_formula" must express the full boolean logic among predicates.

Organize the final predicates into a logic tree reflecting their AND/OR/NOT
relationships."""

_LOGIC_TREE_DO_DO_NOT = """[ Do and Do Not ]
Do:
- Account for every check from Pass 1 in the final tree.
- Include the actual implementation source code in each predicate's "impl" field.
- Express the full boolean logic among predicates in "detection_formula".
Do Not:
- Do not drop or merge away any detection logic.
- Do not return anything other than the specified JSON format."""

_LOGIC_TREE_FEW_SHOT = """[ Few-shot Example ]
Example (rule: anonymous-ldap-bind, a Semgrep Java rule):

Rule implementation (abridged):
  pattern: |
    $ENV.put($CTX.SECURITY_AUTHENTICATION, "none");
    ...
    $DCTX = new InitialDirContext($ENV, ...);

Expected output:
{
  "logic_tree": {
    "operator": "AND",
    "children": [
      {
        "predicate": "anonymous_auth_config",
        "description": "Sets the SECURITY_AUTHENTICATION context property to 'none'",
        "impl": "$ENV.put($CTX.SECURITY_AUTHENTICATION, \"none\");"
      },
      {
        "predicate": "initial_dir_context_creation",
        "description": "Creates an InitialDirContext using the configured environment",
        "impl": "$DCTX = new InitialDirContext($ENV, ...);"
      }
    ]
  },
  "detection_formula": "anonymous_auth_config AND initial_dir_context_creation",
  "line_by_line_parse": [
    {"region": "pattern line 1", "check": "anonymous authentication is configured", "role": "match"},
    {"region": "pattern line 2", "check": "an LDAP context is created with that environment", "role": "match"}
  ]
}"""

_LOGIC_TREE_OUTPUT_FORMAT = """[ Output Format ]
```json
{
    "logic_tree": {
        "operator": "AND",
        "children": [
            {
                "predicate": "predicate_name",
                "description": "What this predicate semantically matches",
                "impl": "The actual rule implementation for this predicate"
            },
            {
                "operator": "OR",
                "children": [
                    {
                        "predicate": "alternative_a",
                        "description": "First alternative pattern",
                        "impl": "..."
                    },
                    {
                        "predicate": "alternative_b",
                        "description": "Second alternative pattern",
                        "impl": "..."
                    }
                ]
            }
        ]
    },
    "detection_formula": "predicate_name AND (alternative_a OR alternative_b)",
    "line_by_line_parse": [
        {"region": "line/pattern reference", "check": "what it checks", "role": "match|exclude|conjunction"},
        ...
    ]
}
```"""


def _logic_tree_prompt(pass2: str, b_low: int, b_high: int) -> str:
    """Assemble the logic-tree prompt from the shared PASS-1 / Do-DoNot / few-shot /
    output-format sections and the given PASS-2 instruction. The two variants (grouped vs
    line-level) differ only in the PASS-2 section — PASS 1, Do/Do Not, the few-shot
    example, and the output format are byte-identical — so an ablation of the compression
    step is not confounded by prompt-wording changes."""
    return (
        "[ Task / User Prompt ]\n"
        "You will decompose the rule in TWO passes.\n\n"
        + _LOGIC_TREE_PASS1
        + "\n\n"
        + pass2.format(b_low=b_low, b_high=b_high)
        + "\n\n"
        + _LOGIC_TREE_DO_DO_NOT
        + "\n\n"
        + _LOGIC_TREE_FEW_SHOT
        + "\n\n"
        + _LOGIC_TREE_OUTPUT_FORMAT
    )


def logic_tree_prompt(b_low: int, b_high: int) -> str:
    """Assemble the grouped (count-bounded) logic-tree prompt for the given
    predicate-count bounds (B_low, B_high) from §4.1."""
    return _logic_tree_prompt(_LOGIC_TREE_PASS2_GROUPED, b_low, b_high)


LOGIC_TREE_PROMPT_RAW = _logic_tree_prompt(_LOGIC_TREE_PASS2_RAW, 1, 1)


ANALYZE_PREDICATE_MAPPING_PROMPT = """[ Task / User Prompt ]
Analyze what the following predicate maps to in the test case code.

Predicate:
{predicate_name}

Description:
{predicate_description}

Implementation:
```
{predicate_impl}
```

Test Case Code:
```
{code}
```

Analyzer Report:
```
{dynamic_analysis_report}
```

Your task: identify all code snippets in the test case that match this predicate.
Return ONLY matched code snippets, and wrap each snippet with <match> and </match>.

[ Do and Do Not ]
Do:
- Return only matched code snippets, each wrapped in <match>...</match>.
- Return multiple <match> blocks if there are multiple matches.
Do Not:
- Do not return explanations.
- Do not return anything other than the matched snippets or NO_MATCH.

[ Output Format ]
<match>socket.connect(host, port)</match>
<match>
user_input = request.args.get("url")
os.system("ping " + user_input)
</match>

If there is no match, return exactly: NO_MATCH
"""