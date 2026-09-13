import json
import importlib
import os
import subprocess
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool
import numpy as np


_CODEBERT_TOKENIZER = None
_CODEBERT_MODEL = None
_CODEBERT_TORCH = None
_SENTENCE_EMBEDDER = None


def _repo_name(repository: Any) -> str:
    if isinstance(repository, dict):
        return repository.get("nameWithOwner") or repository.get("fullName") or ""
    if isinstance(repository, str):
        return repository
    return ""


def _extract_snippet(item: Dict[str, Any]) -> str:
    text_matches = item.get("textMatches") or []
    if not isinstance(text_matches, list) or not text_matches:
        return ""

    fragments = [m.get("fragment", "") for m in text_matches if isinstance(m, dict)]
    return "\n\n".join(f.strip() for f in fragments if f and f.strip())


def _identity_key(item: Dict[str, Any]) -> str:
    return item.get("url") or f"{item.get('repo', '')}:{item.get('path', '')}"


def _normalize_items(raw_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    seen = set()

    for item in raw_items:
        if not isinstance(item, dict):
            continue

        snippet = _extract_snippet(item)
        normalized_item = {
            "repo": _repo_name(item.get("repository")),
            "path": item.get("path", ""),
            "url": item.get("url", ""),
            "snippet": snippet,
            "score": 1.0,
            "context_enriched": bool(snippet),
        }

        key = _identity_key(normalized_item)
        if key in seen:
            continue
        seen.add(key)
        normalized.append(normalized_item)

    return normalized


def _select_cluster_representatives(
    candidates: List[Dict[str, Any]],
    target_results: int,
) -> List[Dict[str, Any]]:
    non_empty = [c for c in candidates if (c.get("snippet") or "").strip()]
    if len(non_empty) <= target_results:
        return non_empty

    texts = [c.get("snippet", "") for c in non_empty]

    dense_x = _embed_texts(texts)
    if dense_x is None:
        return non_empty[:target_results]

    try:
        sklearn_cluster = importlib.import_module("sklearn.cluster")
        kmeans_cls = getattr(sklearn_cluster, "KMeans")
    except Exception:
        return non_empty[:target_results]

    k = min(target_results, len(non_empty))
    if k <= 0:
        return []

    try:
        kmeans = kmeans_cls(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(dense_x)
    except Exception:
        return non_empty[:target_results]

    representatives: List[int] = []
    for i in range(k):
        cluster_indices = np.nonzero(labels == i)[0]
        if cluster_indices.size == 0:
            continue
        distances = kmeans.transform(dense_x[cluster_indices])[:, i]
        rep_idx = int(cluster_indices[np.argmin(distances)])
        representatives.append(rep_idx)

    selected_indices = sorted(set(representatives))
    selected = [non_empty[i] for i in selected_indices]

    if len(selected) >= target_results:
        return selected[:target_results]

    selected_set = set(selected_indices)
    for idx, item in enumerate(non_empty):
        if idx in selected_set:
            continue
        selected.append(item)
        if len(selected) >= target_results:
            break

    return selected


def _embed_texts(texts: List[str]) -> Optional[np.ndarray]:
    embeddings = _embed_with_codebert(texts)
    if embeddings is not None:
        return embeddings

    embeddings = _embed_with_sentence_transformers(texts)
    if embeddings is not None:
        return embeddings

    return None


def _embed_with_codebert(texts: List[str]) -> Optional[np.ndarray]:
    global _CODEBERT_TOKENIZER
    global _CODEBERT_MODEL
    global _CODEBERT_TORCH

    try:
        transformers = importlib.import_module("transformers")
        torch = importlib.import_module("torch")
        auto_tokenizer = getattr(transformers, "AutoTokenizer")
        auto_model = getattr(transformers, "AutoModel")
    except Exception:
        return None

    model_name = os.getenv("CODE_EMBED_MODEL", "microsoft/codebert-base")

    try:
        if _CODEBERT_TOKENIZER is None or _CODEBERT_MODEL is None:
            _CODEBERT_TOKENIZER = auto_tokenizer.from_pretrained(model_name)
            _CODEBERT_MODEL = auto_model.from_pretrained(model_name)
            _CODEBERT_MODEL.eval()
            _CODEBERT_TORCH = torch

        encoded = _CODEBERT_TOKENIZER(
            texts,
            padding=True,
            truncation=True,
            max_length=256,
            return_tensors="pt",
        )

        with _CODEBERT_TORCH.no_grad():
            output = _CODEBERT_MODEL(**encoded)

        hidden = output.last_hidden_state
        attention = encoded["attention_mask"].unsqueeze(-1).type_as(hidden)
        pooled = (hidden * attention).sum(dim=1) / attention.sum(dim=1).clamp(min=1e-9)
        normalized = _CODEBERT_TORCH.nn.functional.normalize(pooled, p=2, dim=1)
        return normalized.detach().cpu().numpy()
    except Exception:
        return None


def _embed_with_sentence_transformers(texts: List[str]) -> Optional[np.ndarray]:
    global _SENTENCE_EMBEDDER

    try:
        sentence_transformers = importlib.import_module("sentence_transformers")
        sentence_transformer_cls = getattr(sentence_transformers, "SentenceTransformer")
    except Exception:
        return None

    model_name = os.getenv("FALLBACK_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

    try:
        if _SENTENCE_EMBEDDER is None:
            _SENTENCE_EMBEDDER = sentence_transformer_cls(model_name)

        vectors = _SENTENCE_EMBEDDER.encode(
            texts,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return np.asarray(vectors)
    except Exception:
        return None


@tool("gh_code_search")
def gh_code_search(
    query: str,
    language: str = "",
    target_results: int = 10,
) -> str:
    """Search GitHub code with gh CLI and return normalized snippet results as JSON list.

    Args:
        query: Natural language or GitHub code query text.
        language: Optional language filter (e.g., python, java).
        target_results: Maximum results to fetch.

    Returns:
        JSON string for a list of normalized snippet objects:
        [{"repo","path","url","snippet","score","context_enriched"}, ...]
    """
    fetch_limit = max(int(target_results) * 20, int(target_results), 1)

    cmd = [
        "gh",
        "search",
        "code",
        query,
        "--json",
        "path,repository,url,textMatches",
        "-L",
        str(fetch_limit),
    ]

    if language:
        cmd.extend(["--language", language])

    env = os.environ.copy()
    env["PAGER"] = "cat"
    env["GH_PAGER"] = "cat"

    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            check=False,
            timeout=45,
        )
    except Exception as exc:
        return json.dumps({"error": f"Failed to execute gh: {exc}"})

    if completed.returncode != 0:
        return json.dumps(
            {
                "error": "gh search code failed",
                "stderr": completed.stderr.strip(),
                "stdout": completed.stdout.strip(),
                "returncode": completed.returncode,
            }
        )

    try:
        raw_items = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return json.dumps({"error": f"Invalid gh JSON output: {exc}"})

    if not isinstance(raw_items, list):
        return json.dumps({"error": f"Unexpected gh output type: {type(raw_items).__name__}"})

    normalized = _normalize_items(raw_items)
    selected = _select_cluster_representatives(normalized, max(int(target_results), 1))
    return json.dumps(selected, indent=2)
