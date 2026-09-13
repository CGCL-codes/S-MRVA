from analysis_agent import MainAgent
from langchain_community.chat_models import ChatTongyi
from pathlib import Path
import os

from analyzers.bandit_check import BanditAnalyzer
from analyzers.semgrep_check import SemgrepAnalyzer

llm = ChatTongyi(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url=os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    model="qwen-plus",
    )

def test_bandit():
    # Setup
    dataset_dir = Path(os.getenv("SAT_WORK_DIR", ".")) / "dataset/bandit"

    # Create agent with two-step workflow
    agent = MainAgent(
        llm=llm, 
        analyzer=BanditAnalyzer(dataset_dir=str(dataset_dir)), 
        lang="python", 
        rule_id="B501"
    )

    # Run the two-step analysis workflow
    print("Starting two-step analysis workflow...")
    result = agent.run_analysis()

    # Display results
    print("\n" + "="*80)
    print("ANALYSIS RESULTS")
    print("="*80)
    print(f"\nRule ID: {result['rule_id']}")
    print(f"Language: {result['language']}")

    print("\n--- Step 1: Rule Analysis ---")
    print(f"Rule Goal: {result.get('rule_goal', 'N/A')}")
    print(f"Covered Variants: {result.get('covered_variants', [])}")

    print("\n--- Step 2: Logic Tree Decomposition ---")
    print(f"Detection Formula: {result.get('detection_formula', 'N/A')}")
    print(f"Logic Tree: {json.dumps(result.get('logic_tree', {}), indent=2)}")