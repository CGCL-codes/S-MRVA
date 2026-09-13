# S-MRVA — Artifact

**S-MRVA**: *Divide and Conquer: Exposing SAST Rule Flaws via Realistic Variant
Synthesis from Millions of Repositories* (CCS '26).

S-MRVA is an LLM-agent pipeline that automatically finds **false positives (FP)**
and **false negatives (FN)** in static-analysis security rules (Semgrep, CodeQL,
Bandit, SpotBugs). Given a rule it:

1. **Analyses** the rule's detection logic into a predicate-logic tree;
2. **Searches** real GitHub code for structurally different variants of the
   rule's matched patterns;
3. **Synthesises** realistic mutant test cases that may bypass or falsely
   trigger the rule;
4. **Verifies** every mutant against the real analyzer and an LLM judge, and
   classifies the disagreements;
5. **Groups** the confirmed defects by root cause and writes a report.

This artifact is submitted for **two badges**. [Quick start](#quick-start-for-functional-evaluation) is a
short setup that runs the example; Parts 1 and 2 map to the badges:

| Part | Badge | What it shows | Entry point |
|---|---|---|---|
| [Quick start](#quick-start-for-functional-evaluation) | — (quick start) | pull image, DeepSeek key, run the example | `docker pull 9iang22/smrva:latest` |
| [Part 1](#part-1--functional-badge) | Functional | documented / consistent / complete / exercisable | Docker example |
| [Part 2](#part-2--reusable-badge) | Reusable | backend swap, ablation, sensitivity, time & cost | `example/run_reuse_demo.sh` |

**Archival.** Permanently archived on Zenodo:
[10.5281/zenodo.22830827](https://doi.org/10.5281/zenodo.22830827). The prebuilt
image is pinned by digest in [Quick start, §0.1](#01-pull-the-image).

---

# Quick start for functional evaluation

The fastest way to exercise the artifact: pull the prebuilt image, add a
**DeepSeek** key, and run one example rule with **default settings** (~20–35 min
for one rule). Parts 1–2 are the detail behind this.

> The published image was built **exactly** with `docker build -t smrva .` — the
> same command as [Part 1, Step 1](#step-1--get-the-image-recommended-pull) — and can be rebuilt locally
> at any time. The pull is only a convenience.

### 0.1 Pull the image

```bash
docker pull 9iang22/smrva:latest
docker tag  9iang22/smrva:latest smrva      # so the commands below stay simple
```

> For a reproducible pin, pull by digest instead of the mutable `latest` tag:
> `docker pull 9iang22/smrva@sha256:3e5508744ac380ede53aea84d194c2b3cbeb47cc2abb0eb111c2ab512318c581`.

### 0.2 Configure (DeepSeek, defaults)

Create `.env` with your DeepSeek key and a GitHub token; everything else stays
at its default:

```bash
cat > .env <<'EOF'
# Comments must be on their own line: `docker --env-file` keeps trailing text
# as part of the value, so an inline `# ...` would corrupt the key.
LLM_API_KEY=sk-...
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-flash
EMBED_MODEL=codet5p
GITHUB_TOKENS=ghp_...
SAT_WORK_DIR=/workspace
EOF
```

Two credentials are needed:

- **DeepSeek API key** (`LLM_API_KEY`) — sign in at
  <https://platform.deepseek.com/api_keys> and copy a key (`sk-…`).
- **GitHub token** (`GITHUB_TOKENS`) — the retrieval stage searches real code via
  the GitHub Code Search API, which requires a token. Easiest if the GitHub CLI
  is already logged in:
  ```bash
  gh auth token
  ```
  Otherwise create one at *Settings → Developer settings → Personal access
  tokens*: a **classic** token with the `public_repo` scope, or a **fine-grained**
  token with *Public Repositories (read-only)*. Multiple tokens can be passed
  comma-separated and are rotated to survive rate limits.

Without a GitHub token no snippets are fetched, so the run produces **no mutants**
unless you switch to LLM-only synthesis (`-e LLM_DIRECT_MUTATION=1`). More detail
in [Part 1, Step 2](#step-2--configure-keys).

### 0.3 Run the example

```bash
mkdir -p example/run_output
docker run --rm -i --network=host --env-file .env \
  --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -v "$PWD/example/run_output:/workspace/example/run_output" \
  smrva bash example/run_semgrep_example.sh
```

> **Behind a proxy?** The commands in this README are shown without one. We ran
> them from mainland China and added
> `--env HTTP_PROXY --env HTTPS_PROXY --env http_proxy --env https_proxy` to
> every `docker run`; if those variables are unset this is a no-op, and if you
> are not behind a proxy you need nothing extra.

It ends with a `Pipeline complete!` block and writes
`example/run_output/anonymous-ldap-bind/pipeline_report_anonymous-ldap-bind.md` plus
`pipeline_summary_anonymous-ldap-bind.json` — the exact tail and the output
schema are in [Part 1, Step 3](#step-3--run-the-example).

---

# Part 1 — Functional badge

## (i) Documented

> *Are the artifacts sufficiently documented to enable them to be exercised by
> readers of the paper?*

This README is organised around the three functional criteria, so a reviewer can
walk them in order:

| Criterion | Section |
|---|---|
| (i) Documented | this section |
| (ii) Consistent & complete | [(ii) Consistent and Complete](#ii-consistent-and-complete) — repo layout + paper→artifact map + components |
| (iii) Exercisable | [(iii) Exercisable](#iii-exercisable) — the Docker quickstart |

Supporting documents and scripts:

- `example/run_semgrep_example.sh` — the quickstart run script;
- `example/run_reuse_demo.sh` — the reusable-badge demo (Part 2);
- `src/agents/check_env.py` — one-shot LLM/embedding configuration check;
- [`docs/query_agent_reuse.md`](docs/query_agent_reuse.md) — reuse the retrieval
  stage (QueryAgent) standalone;
- [`docs/adding_an_analyzer.md`](docs/adding_an_analyzer.md) — add a new SAST
  analyzer to the framework.

## (ii) Consistent and Complete

> *Are the artifacts relevant to the paper, and do they contribute in some
> inherent way to the generation of its main results?*
> *Do the submitted artifacts include all of the key components described in the
> paper?*

Every component that **generates** the paper's results is included: the five
pipeline stages, the four analyzer wrappers, the 220-rule dataset, the retrieval
and embedding layer, and the default-model cached outputs.

### Repository layout

```
ae/
├── src/
│   ├── agents/            # 5-stage pipeline: analysis, query, synthesis, verify, report
│   ├── analyzers/         # SAST wrappers: semgrep, codeql, bandit, spotbugs
│   ├── tools/             # GitHub code search, embeddings, rate-limit server
│   ├── prompts/           # LLM prompt templates
│   └── resources/
├── dataset/               # 220 rules: Bandit 31, CodeQL 48, Semgrep-Java 79, Semgrep-C 48, SpotBugs 14 (+ sampled/ = 20-rule subset)
├── reports/               # filed maintainer bug reports
├── example/               # quickstart + reusable demo + cached example output
├── docs/                  # reuse guides (QueryAgent, adding an analyzer)
├── data/setup.sh          # downloads analyzer runtime data (CodeQL, SpotBugs, rules)
├── Dockerfile, docker-entrypoint.sh, requirements.txt
└── start_*.sh             # batch launchers for a full 220-rule run
```

| Component | Location |
|---|---|
| Five-stage LLM-agent pipeline | `src/agents/pipeline_agent.py` + `analysis_agent.py`, `query_agent_*.py`, `synthesis_agent*.py`, `verify_agent.py` |
| Analyzer framework + four analyzers | `src/analyzers/` (`impl_semgrep_check.py`, `impl_codeql_check.py`, `impl_bandit_check.py`, `impl_spotbugs_check.py`, base `analyzer.py`) |
| Retrieval / QueryAgent | `src/agents/query_agent_api.py` (pipeline entry; `query_agent_gh.py` is an optional gh-CLI variant); `src/tools/` + code-search server |
| Embedding-based dedup (τ) | `src/tools/impl_code_search.py` |
| Rule dataset (220; 20-rule sample) | `dataset/`, `dataset/sampled/` |
| Time / cost tracking | `src/agents/cost_tracker.py` |
| Reuse documentation | `docs/` |


## (iii) Exercisable

> *Do the submitted artifacts include the scripts and data needed to run the
> experiments described in the paper, and can the software be successfully
> executed?*

The image bundles all four analyzers (Semgrep, Bandit, CodeQL, SpotBugs) and
their runtime data, so no host tooling is required beyond Docker.

**Time budget**

| Step | Human | Compute |
|---|---|---|
| 1. Get the image (pull, or build) | ~1 min | ~2–3 min (~4.6 GB pull) |
| 2. Configure `.env` | ~5 min | — |
| 3. Run the example | ~5 min | ~20–35 min (one rule) |

### Step 1 — Get the image (recommended: pull)

**Recommended — pull the prebuilt image.** It is the same image that the build
below produces, so pulling is equivalent and skips a long build:

```bash
docker pull 9iang22/smrva:latest
docker tag  9iang22/smrva:latest smrva      # so the commands below stay simple
```

**Alternative — build from source** (identical result):

```bash
docker build -t smrva .
```

> **Behind a proxy?** (needed in mainland China, optional elsewhere.) Build with
> `--network=host` and pass
> `--build-arg HTTP_PROXY=$HTTP_PROXY --build-arg HTTPS_PROXY=$HTTPS_PROXY
> --build-arg ALL_PROXY=$ALL_PROXY --build-arg NO_PROXY=$NO_PROXY`. Without the
> proxy arguments the `data/setup.sh` clone step fails in a proxied network.

Either way the resulting image bundles the CodeQL CLI, SpotBugs, and analyzer
data (the build fetches them via `data/setup.sh`; the pull already contains
them). It ships **no VCS or agent-tooling metadata** — `.git`, `.claude`,
`.agents` are removed during the build (cloned analyzer data has its `.git`
stripped too).

### Step 2 — Configure keys

```bash
cp .env.example .env
```

Fill in `.env`. The **LLM** is provider-agnostic (any OpenAI-compatible API);
the code-search **embedding** is configured separately.

```ini
# --- LLM (required) ---
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen3.5-plus

# --- Embedding for snippet dedup: qwen (DashScope API) or codet5p (local) ---
EMBED_MODEL=codet5p

# --- GitHub code-search tokens (comma-separated) — required for the full pipeline ---
GITHUB_TOKENS=ghp_xxx,ghp_yyy

SAT_WORK_DIR=/workspace
```

#### Getting an API key

- **Qwen (Model Studio / DashScope):** sign in, open the API-Keys page, and copy
  a key (`sk-…`). Keys are **region-bound** — choose the **Singapore** region for
  overseas use. <https://modelstudio.console.alibabacloud.com/>
- **DeepSeek:** <https://platform.deepseek.com/api_keys>
- **OpenAI:** <https://platform.openai.com/api-keys>

Put the key in `.env` as `DASHSCOPE_API_KEY=…` (Qwen) or `LLM_API_KEY=…` (any
provider).

#### Getting a GitHub token

The retrieval stage (QueryAgent) searches real code through the **GitHub Code
Search API**, which requires a token. Without one no snippets are fetched, so the
run produces **no mutants** unless you explicitly switch to LLM-only synthesis:
set `ABLATION=no-code-search` in Part 2, or add `-e LLM_DIRECT_MUTATION=1` to the
run command below.

Two ways to get a token, easiest first:

- **GitHub CLI:** if you have `gh` and are logged in, it prints a ready-to-use
  token:
  ```bash
  gh auth token
  ```
- **Personal access token (manual):** GitHub → *Settings → Developer settings →
  Personal access tokens*. A **classic** token needs the `public_repo` scope for
  public code search (`repo` also covers private repos); a **fine-grained**
  token needs *Public Repositories (read-only)*.

Set it (comma-separated multiple tokens are rotated to survive rate limits):

```ini
GITHUB_TOKENS=ghp_xxx
# GITHUB_TOKENS=ghp_xxx,ghp_yyy
```

> GitHub's Code Search API has an aggressive **secondary rate limit**; a tripped
> request can wait ~2 h if there are too many concurrency tasks, please only start
> ONE test per time.

#### Verify your configuration

Confirm the LLM and embedding actually work before a long run — run it inside
the image (the Python dependencies are guaranteed to be there):

```bash
docker run --rm --network=host --env-file .env -e HOME=/tmp \
  smrva python3 src/agents/check_env.py
```

It prints the resolved model/endpoint (keys masked), sends one tiny LLM request,
and runs the configured embedding — ending with `RESULT: PASS` (exit code 0) on
success. The **CodeT5p** embedding model (~0.5 GB) is baked into the image, so
nothing is downloaded at run time and this works offline; on a machine
**without a GPU the local embedding runs on CPU** (slower). Re-run it after
switching providers.

### Step 3 — Run the example

The example runs the pipeline on the Semgrep Java rule `anonymous-ldap-bind`
(**~20–35 minutes**). It writes into `example/run_output/`, which we bind-mount
from the host and run as **your** UID so the files are readable/editable by you —
not root. (Your runs go to `example/run_output/`; the read-only cached runs
shipped with the artifact stay in `example/output/`.)

```bash
mkdir -p example/run_output
docker run --rm -i --network=host --env-file .env \
  --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -v "$PWD/example/run_output:/workspace/example/run_output" \
  smrva bash example/run_semgrep_example.sh
```

- `--user "$(id -u):$(id -g)"` makes every file written to the bind mount owned
  by your host account; `-e HOME=/tmp` gives that UID a writable home.
- **Proxy:** we ran this from mainland China and added
  `--env HTTP_PROXY --env HTTPS_PROXY --env http_proxy --env https_proxy` to
  reach GitHub. If you are **not** behind a proxy, the command works as shown
  (unset variables are ignored).
- The **CodeT5p** embedding model (~0.5 GB) is baked into the image, so there is
  no download step and no model-cache volume to mount.
- **Side effects:** creates `example/run_output/anonymous-ldap-bind/` and overwrites
  it on re-runs (idempotent); uses the network (LLM + GitHub). The run may take
  >20 min if GitHub's code-search rate limit stalls it.
- If you prefer to run as root (the image default), the output files will be
  root-owned; afterwards run
  `sudo chown -R "$(id -u):$(id -g)" example/run_output` to make them yours.

The command runs `src/agents/pipeline_agent.py` (see
`example/run_semgrep_example.sh`).

**Expected output.** Exit code `0` and a `Pipeline complete!` block. The exact
counts **vary between runs** (LLM sampling + live GitHub search): two of our runs
took ~28 min and ~31 min and reported `reportable=8/21` and `reportable=13/31`
respectively. One run's tail:

```
[pipeline] verify_mutants done — reportable=13/31
[pipeline] group_results done — reportable=13 root_cause_groups=5
[pipeline] build_report done — FP=4 FN=9 total_reportable=13

============================================
 Pipeline complete!
 Report:  example/run_output/anonymous-ldap-bind/pipeline_report_anonymous-ldap-bind.md
 Summary: example/run_output/anonymous-ldap-bind/pipeline_summary_anonymous-ldap-bind.json
============================================
```

> A different run is **not** a failure: any `Pipeline complete!` with exit code
> `0` is a success. Do not compare your mutant counts against these — they vary.

### Example input

The rule is a small Semgrep YAML
(`dataset/semgrep-rules/anonymous-ldap-bind/anonymous-ldap-bind.yaml`); S-MRVA
reads its `pattern`, `message`, `severity`, and `metadata`
(analyzer = Semgrep, language = Java):

```yaml
rules:
- id: anonymous-ldap-bind
  metadata:
    cwe: ['CWE-287: Improper Authentication']
  message: Detected anonymous LDAP bind. ...
  severity: WARNING
  pattern: |
    $ENV.put($CTX.SECURITY_AUTHENTICATION, "none");
    ...
    $DCTX = new InitialDirContext($ENV, ...);
  languages:
  - java
```

### Example output (`example/output/anonymous-ldap-bind/`)

| File | What it is |
|---|---|
| `pipeline_report_<rule>.md` | Human-readable report: rule goal, seed, per root-cause group, verdict, code snippet. |
| `pipeline_summary_<rule>.json` | Structured results; carries the time/cost data (R4) when `ENABLE_COST_TRACKING=1`. |

Key `pipeline_summary_*.json` fields:

- `stats.total_mutants_generated` — mutants synthesised;
- `stats.total_verified` — mutants checked by the analyzer + LLM judge;
- `stats.total_disagreements` / `false_positive_issues` / `false_negative_issues`
  — the FP/FN counts;
- `grouped_reported_mutants.root_cause_groups` — confirmed defects grouped by
  root cause;
- `reports[]` — one entry per confirmed defect (predicate, risk type, snippet,
  oracle verdict).

`example/output/` already contains cached runs for `anonymous-ldap-bind` and
`BindToAllInterfaces` so you can read the schema without running anything.

> S-MRVA is **non-deterministic** (LLM sampling + live GitHub search), so a
> fresh run will not be byte-identical to the cached one; the *shape* of the
> output and the qualitative conclusions are stable.

---

# Part 2 — Reusable badge

This part shows how to reuse S-MRVA beyond the paper. The four reuse items
(R1–R4) are exercised by one script — see [§R5 One-command demo](#r5-one-command-demo);
[§R6](#r6-extending-s-mrva) covers extending S-MRVA with a new rule-set or a new
analyzer.

## R1. Use a different LLM backend

The LLM is any OpenAI-compatible endpoint; only three variables matter:

| Variable | Meaning |
|---|---|
| `LLM_BASE_URL` | API base URL (overrides `DASHSCOPE_BASE_URL`) |
| `LLM_API_KEY` | API key (overrides `DASHSCOPE_API_KEY`) |
| `LLM_MODEL` | model id |

The **embedding** is separate: `EMBED_MODEL=qwen` (DashScope API, reads
`DASHSCOPE_*` **directly** — no `LLM_*` fallback) or `EMBED_MODEL=codet5p`
(local, no external call). Pairing a non-DashScope LLM with `codet5p` keeps
everything off the China endpoint.

**Example — DeepSeek** (no DashScope involvement):

```ini
LLM_API_KEY=sk-...
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-flash
EMBED_MODEL=codet5p
```

> `deepseek-flash` was the id tested; DeepSeek renames ids over time. Keep
> comments on their own line — `docker --env-file` does not strip inline `#`.

**Example — DashScope from overseas (Singapore).** Use the international
endpoint with a **Singapore-region** key (DashScope keys are region-bound and
rejected by the wrong region):

```ini
DASHSCOPE_API_KEY=sk-ws-...
DASHSCOPE_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen3.5-plus
EMBED_MODEL=codet5p
```

**Other OpenAI-compatible providers** (set the three `LLM_*` vars):

| Provider | `LLM_BASE_URL` | Notes |
|---|---|---|
| OpenAI | `https://api.openai.com/v1` | |
| OpenRouter | `https://openrouter.ai/api/v1` | aggregator; model ids are `vendor/model` |
| SiliconFlow (intl) | `https://api.siliconflow.com/v1` | hosts DeepSeek/Qwen, plus embeddings |
| Moonshot / Kimi | `https://api.moonshot.ai/v1` | |

After switching, run `python3 src/agents/check_env.py` to confirm the new
provider answers before a long run. Model ids drift over time (notably
DeepSeek's); take the current id from the provider's docs.

## R2. Run ablation settings

Ablation switches the pipeline's optional stages via two environment variables:

| Setting | Ablation | Variables |
|---|---|---|
| `full` (default) | — | `LLM_DIRECT_MUTATION=0`, `ENABLE_LOGIC_TREE_REFINEMENT=1` |
| `no-code-search` | skip GitHub retrieval; synthesise from the LLM only | `LLM_DIRECT_MUTATION=1` |
| `no-refine` | skip the logic-tree refinement pass | `ENABLE_LOGIC_TREE_REFINEMENT=0` |

The demo maps these to `ABLATION=full|no-code-search|no-refine` (→ paper
**Table 7**) and can run repeats over the 20-rule subset
(`dataset/sampled/`).

## R3. Run parameter-sensitivity analysis

The two parameters the paper sweeps are environment variables:

| Knob | Variable | Default | Range |
|---|---|---|---|
| Predicate branching | `LOGIC_TREE_B_HIGH` (`B_low=2` via `LOGIC_TREE_B_LOW`) | 5 | e.g. 1,3,5,7,9 → paper **Figure 5** |
| Snippet-dedup τ | `EMBED_SIM_THRESHOLD` | 0.60 | 0.2,0.4,0.6,0.8,1.0 → paper **Figure 6** |

The demo maps these to `B_HIGH=<int>` and `TAU=<0..1>`.

## R4. Get time & cost information

Set `ENABLE_COST_TRACKING=1` (the demo enables it by default). The run then
prints a line and stores the same dict under `pipeline_summary["cost"]`:

```
[pipeline] cost: {'model': 'deepseek-flash', 'num_llm_calls': 143,
 'input_tokens': 812345, 'output_tokens': 98765, 'total_tokens': 911110,
 'total_time_seconds': 1234.5, 'estimated_cost_usd': 0.244}
```

It counts every LLM call, its latency, and prompt/completion tokens
(`src/agents/cost_tracker.py`); `estimated_cost_usd` uses a built-in price table
and reports `0.0` for models it does not know. Numbers above are illustrative.

## R5. One-command demo

`example/run_reuse_demo.sh` puts R1–R4 into one run. **Preview** the resolved
configuration without spending an LLM call:

```bash
DRY_RUN=1 bash example/run_reuse_demo.sh
```

**Run** the demo (backend + ablation + sensitivity + cost in one command):

```bash
# default backend, no ablation, default sensitivity, cost tracking on
bash example/run_reuse_demo.sh

# everything changed at once (no-code-search is the fastest)
BACKEND=deepseek ABLATION=no-code-search B_HIGH=3 TAU=0.4 bash example/run_reuse_demo.sh
```

`BACKEND` presets fill `LLM_BASE_URL`/`LLM_MODEL` for that provider; an explicit
`LLM_*` variable passed on the command line wins over the preset, which wins over
`.env`. `ABLATION`, `B_HIGH` and `TAU` take the values from R2/R3. The target
defaults to `RULE_ID=anonymous-ldap-bind`, `RULE_LANGUAGE=java`,
`ANALYZER=semgrep`, `BASE_DIR=dataset/semgrep-rules`,
`ARTIFACTS_DIR=example/run_output`.

Inside Docker:

```bash
docker run --rm -i --network=host --env-file .env \
  --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -v "$PWD/example/run_output:/workspace/example/run_output" \
  -e BACKEND=deepseek -e ABLATION=no-code-search -e B_HIGH=3 -e TAU=0.4 \
  smrva bash example/run_reuse_demo.sh
```

> Behind a proxy? Add the `--env HTTP_PROXY …` flags as in
> [Quick start](#quick-start-for-functional-evaluation).

The script prints the resolved configuration (key masked) before running, then
the pipeline, then where the time/cost summary was written.

## R6. Extending S-MRVA

There are two independent axes of extension: **rule-sets** (a new set of rules
for an analyzer you already have — no code change) and **analyzers** (wrapping a
different SAST tool).

### R6.1 Add a rule-set — Semgrep example

A rule-set is just a directory of rule folders. The artifact ships two Semgrep
rule-sets, and they differ **only in configuration**:

| Rule-set | Upstream | Language | Rules | Launcher |
|---|---|---|---|---|
| `dataset/semgrep-rules` | `semgrep/semgrep-rules` | Java | 79 | `start_semgrep.sh` |
| `dataset/semgrep-rules-0xdea` | `0xdea/semgrep-rules` | C | 48 | `start_semgrep-0xdea.sh` |

Layout — one folder per rule id, holding the rule file plus the seed tests the
analyzer reads through `load_rule` / `load_test_cases`:

```
dataset/semgrep-rules/                 dataset/semgrep-rules-0xdea/
└── anonymous-ldap-bind/               └── argv-envp-access/
    ├── anonymous-ldap-bind.yaml           ├── argv-envp-access.yaml
    ├── anonymous-ldap-bind_0.java         └── argv-envp-access.c
    └── anonymous-ldap-bind_1.java
```

The two launchers are otherwise identical — only these three variables change:

```bash
# start_semgrep.sh                         # start_semgrep-0xdea.sh
BASE_DIR=dataset/semgrep-rules             BASE_DIR=dataset/semgrep-rules-0xdea
RULE_LANGUAGE=java                         RULE_LANGUAGE=c
OUTPUT_DIR=output/semgrep-rules            OUTPUT_DIR=output/semgrep-rules-0xdea
```

**To add your own rule-set, no code changes are needed:**

1. Drop one folder per rule under `dataset/<your-ruleset>/`
   (`<rule_id>/<rule_id>.yaml` + seed files). To fetch an upstream rule-set
   instead, add a pinned clone to `data/setup.sh`
   (`clone_at <repo> <commit> <dir>` — this is how the two Semgrep sets are
   obtained).
2. Run the existing analyzer against it:
   ```bash
   python3 src/agents/pipeline_agent.py \
     --rule_id <rule_id> --language c --analyzer semgrep \
     --base_dir dataset/<your-ruleset> \
     --artifacts_dir output/<your-ruleset>
   ```
   For a batch run, copy `start_semgrep-0xdea.sh` and change the same three
   variables.

The analyzer discovers rules by listing `base_dir`, so any rule-set in a
supported language works as-is.

### R6.2 Adapt a new analyzer — Bandit example

To wrap a different SAST tool, implement the small `Analyzer` interface in two
files, then register it by name. Bandit (Python) is a complete, compact example:

```
src/analyzers/
├── analyzer.py            # Analyzer base class + CheckResult   (shared)
├── impl_bandit_check.py   # BanditCheckRunner: run the tool, parse its output
└── bandit_check.py        # BanditAnalyzer(Analyzer): dataset + runner
src/agents/pipeline_agent.py   # cli(): the `--analyzer bandit` branch
```

**The contract** — the pipeline needs six methods and a
`CheckResult(test_id, issues_found, output, runtime_error)`:

| Method | Purpose |
|---|---|
| `get_all_rule_ids()` | rule ids = subdirectories of `dataset_dir` |
| `get_rule_description(rule_id)` | text handed to the LLM |
| `load_rule(rule_id)` | `{path: text}` for the rule definition |
| `load_test_cases(rule_id)` | `{path: text}` for the seed tests |
| `run_check(rule_id, test_path)` | run the tool on a file → `CheckResult` |
| `run_check_in_temp_dir(rule_id, test_code)` | same, on a synthesized snippet |

The same shape works for any CLI tool:

1. **Runner** (`impl_bandit_check.py`) — invoke the binary and parse its verdict:
   ```python
   cmd = ["bandit", "-r", str(file_path)]
   result = subprocess.run(cmd, capture_output=True, text=True)
   issues_found = bool(re.search(r">>\s+Issue:\s+\[[A-Z]\d+:", result.stdout))
   # -> {"success": True, "issues_found": issues_found, "output": result.stdout}
   ```
   A missing binary or crash returns `success=False`; the analyzer maps that to
   `runtime_error=True` so the case is dropped rather than read as a clean pass.

2. **Analyzer** (`bandit_check.py`) — map the dataset to the runner:
   ```python
   class BanditAnalyzer(Analyzer):
       def __init__(self, dataset_dir):
           super().__init__("bandit", dataset_dir)
           self.runner = BanditCheckRunner()

       def get_all_rule_ids(self):
           return os.listdir(self.dataset_dir)

       def load_rule(self, rule_id):          # .py plugin in dataset/bandit/<rule_id>/
           d = self.dataset_dir / rule_id
           return {d / f: (d / f).read_text()
                   for f in os.listdir(d) if f.endswith(".py")}

       def run_check_in_temp_dir(self, rule_id, test_code):
           # Bandit is Python-only, so the snippet is always written as .py
           ...
   ```

3. **Register** it in `src/agents/pipeline_agent.py` → `cli()`:
   ```python
   elif args.analyzer == "bandit":
       from analyzers.bandit_check import BanditAnalyzer
       analyzer = BanditAnalyzer(dataset_dir=args.base_dir)
   ```
   Update the `--analyzer` help string and the final `raise ValueError(...)` list.

4. **Dataset layout** follows the built-ins — one folder per rule, plus seed
   tests. Bandit keeps the plugin, metadata, and seeds like this:
   ```
   dataset/bandit/
   └── B101/
       ├── asserts.py         # load_rule   (plugin / rule source)
       ├── metadata.json
       └── test_files/        # load_test_cases
   ```

5. **Docker + test** — install the tool and put it on `PATH` in the `Dockerfile`
   (see the CodeQL / SpotBugs blocks); `dataset/` is already copied. Then run
   one rule as in R6.1, or unit-test the wrapper by mirroring
   `src/analyzers/test_semgrep_check.py`.

A full walk-through (skeleton, registration, Docker, unit test, and gotchas such
as the exact `run_check_in_temp_dir(rule_id=…, test_code=…)` keyword names) is in
[`docs/adding_an_analyzer.md`](docs/adding_an_analyzer.md).

## License

See [LICENSE](LICENSE).
