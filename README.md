# S-MRVA — Artifact

**S-MRVA**: *Divide and Conquer: Exposing SAST Rule Flaws via Realistic Variant
Synthesis from Millions of Repositories* (CCS '26).

S-MRVA is an LLM-agent pipeline that automatically finds **false positives (FP)**
and **false negatives (FN)** in static-analysis security rules (Semgrep, CodeQL,
Bandit, SpotBugs).

> Full artifact documentation — dataset layout, functional-badge details, and the
> reuse guide (backend swap, ablation, sensitivity, cost, extension) — is in the
> [`artifact`](https://github.com/CGCL-codes/S-MRVA/blob/artifact/README.md) branch.
> Archived on Zenodo: [10.5281/zenodo.22830827](https://doi.org/10.5281/zenodo.22830827).

# Quick start for functional evaluation

The fastest way to exercise the artifact: pull the prebuilt image, add a
**DeepSeek** key, and run one example rule with **default settings** (~20–35 min
for one rule).

> The published image was built **exactly** with `docker build -t smrva .` and can
> be rebuilt locally at any time. The pull is only a convenience.

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
in the [full artifact README](https://github.com/CGCL-codes/S-MRVA/blob/artifact/README.md).

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
schema are in the [full artifact README](https://github.com/CGCL-codes/S-MRVA/blob/artifact/README.md).
