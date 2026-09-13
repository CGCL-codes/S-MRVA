#!/usr/bin/env python3
import os
import sys
import time
import logging
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.api_code_search import github_code_search

logging.basicConfig(level=logging.INFO, format='[%(processName)s] %(message)s')

def worker_task(worker_id: int, query: str):
    logging.info(f"Worker {worker_id} starting search for: {query}")
    start = time.time()
    
    results = github_code_search(query, target_results=5, context_lines=3)
    
    elapsed = time.time() - start
    logging.info(f"Worker {worker_id} completed in {elapsed:.2f}s, got {len(results)} results")
    
    return worker_id, len(results), elapsed

def main():
    queries = [
        "useState react",
        "async function express",
        "class Component extends",
        "import tensorflow",
    ]
    
    logging.info("Starting multi-process test with %d workers", len(queries))
    
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(worker_task, i, query)
            for i, query in enumerate(queries)
        ]
        
        results = [f.result() for f in futures]
    
    logging.info("\n=== Test Results ===")
    for worker_id, count, elapsed in results:
        logging.info(f"Worker {worker_id}: {count} results in {elapsed:.2f}s")
    
    total_time = sum(r[2] for r in results)
    avg_time = total_time / len(results)
    logging.info(f"\nTotal time: {total_time:.2f}s")
    logging.info(f"Average time per worker: {avg_time:.2f}s")
    logging.info("Test completed successfully!")

if __name__ == "__main__":
    main()
