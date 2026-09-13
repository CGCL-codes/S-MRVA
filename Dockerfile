# ============================================================================
# SMRVA — Docker Image
# ============================================================================
# Build:   docker build -t smrva .
# Run:     docker run -it --env-file .env smrva
#
# With data volumes:
#   docker run -it --env-file .env \
#     -v $PWD/dataset:/workspace/dataset \
#     -v $PWD/output:/workspace/output \
#     smrva bash
# ============================================================================

FROM python:3.13-slim

LABEL description="SMRVA — Static Analysis Rule Verification Agent"
LABEL maintainer="S-MRVA"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# ---- System packages ----
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates git wget unzip xz-utils \
    build-essential \
    openjdk-21-jdk-headless \
    && rm -rf /var/lib/apt/lists/*

# ---- CodeQL CLI ----
ARG CODEQL_VERSION=2.23.9
RUN mkdir -p /opt/codeql && \
    curl -fsSL --retry 5 --retry-delay 5 --retry-all-errors \
      "https://github.com/github/codeql-cli-binaries/releases/download/v${CODEQL_VERSION}/codeql-linux64.zip" -o /tmp/codeql.zip && \
    unzip -q /tmp/codeql.zip -d /opt/codeql && \
    rm /tmp/codeql.zip && \
    /opt/codeql/codeql/codeql --version

ENV CODEQL_PATH=/opt/codeql/codeql/codeql

# ---- SpotBugs ----
ARG SPOTBUGS_VERSION=4.9.3
RUN mkdir -p /opt/spotbugs && \
    curl -fsSL --retry 5 --retry-delay 5 --retry-all-errors \
      "https://repo1.maven.org/maven2/com/github/spotbugs/spotbugs/${SPOTBUGS_VERSION}/spotbugs-${SPOTBUGS_VERSION}.zip" -o /tmp/spotbugs.zip && \
    unzip -q /tmp/spotbugs.zip -d /opt/spotbugs && \
    rm /tmp/spotbugs.zip && \
    chmod +x /opt/spotbugs/spotbugs-${SPOTBUGS_VERSION}/bin/spotbugs

ENV SPOTBUGS_HOME=/opt/spotbugs/spotbugs-${SPOTBUGS_VERSION}

# ---- PATH + Workdir ----
ENV PATH="/opt/codeql/codeql:${SPOTBUGS_HOME}/bin:${PATH}"
WORKDIR /workspace

# ---- Python dependencies (includes semgrep, bandit) ----
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Embedding model baked in (no runtime download; works offline) ----
ENV HF_HOME=/opt/hf_cache
# socksio lets huggingface_hub's httpx client use a SOCKS (ALL_PROXY) proxy, if set
RUN pip install --no-cache-dir socksio && \
    python3 -c "from huggingface_hub import snapshot_download; snapshot_download('Salesforce/codet5p-110m-embedding')" && \
    chmod -R a+rwX "$HF_HOME"

# ---- Project files ----
COPY .env.example .env.example
COPY src/ src/
COPY example/ example/
COPY dataset/ dataset/
COPY reports/ reports/
COPY docs/ docs/
COPY data/setup.sh data/setup.sh

# ---- Analyzer data (clones bandit, codeql, semgrep-rules, spotbugs, etc.) ----
RUN bash data/setup.sh

# ---- Entrypoint (starts code search server) ----
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# ---- Hygiene: never ship VCS / agent-tooling metadata ----
RUN find / -xdev \( -name .git -o -name .claude -o -name .agents -o -name .agent -o -name .opencode -o -name __pycache__ \) \
        -prune -exec rm -rf {} + 2>/dev/null || true

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# ---- Default env ----
ENV SAT_WORK_DIR=/workspace
ENV LLM_MODEL=qwen3.5-plus
ENV DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
ENV EMBED_MODEL=codet5p
ENV HF_HUB_OFFLINE=1

CMD ["bash"]
