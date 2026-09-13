# S-MRVA — Artifact

**S-MRVA**: *Divide and Conquer: Exposing SAST Rule Flaws via Realistic Variant
Synthesis from Millions of Repositories* (CCS '26).

S-MRVA is an LLM-agent pipeline that automatically finds **false positives (FP)**
and **false negatives (FN)** in static-analysis security rules (Semgrep, CodeQL,
Bandit, SpotBugs).

# Quick start for functional evaluation

Build the image, add a **DeepSeek** key and a GitHub token, and run one example
rule with **default settings** (~20–35 minutes for one rule).

### 1. Build the image

```bash
docker build -t smrva .
```

### 2. Configure (DeepSeek, defaults)

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
unless you switch to LLM-only synthesis (`-e LLM_DIRECT_MUTATION=1`).

### 3. Run the example

```bash
mkdir -p example/run_output
docker run --rm -i --network=host --env-file .env \
  --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -v "$PWD/example/run_output:/workspace/example/run_output" \
  smrva bash example/run_semgrep_example.sh
```

> **Behind a proxy?** We ran these from mainland China. For the build use
> `--network=host --build-arg HTTP_PROXY=$HTTP_PROXY --build-arg HTTPS_PROXY=$HTTPS_PROXY --build-arg ALL_PROXY=$ALL_PROXY --build-arg NO_PROXY=$NO_PROXY`;
> for `docker run` add
> `--env HTTP_PROXY --env HTTPS_PROXY --env http_proxy --env https_proxy`. If
> those variables are unset this is a no-op.

It ends with a `Pipeline complete!` block and writes
`example/run_output/anonymous-ldap-bind/pipeline_report_anonymous-ldap-bind.md` plus
`pipeline_summary_anonymous-ldap-bind.json`.
