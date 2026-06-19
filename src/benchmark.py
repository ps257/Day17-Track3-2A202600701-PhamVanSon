from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_advanced import AdvancedAgent
from agent_baseline import BaselineAgent
from config import load_config


@dataclass
class BenchmarkRow:
    agent_name: str
    agent_tokens_only: int
    prompt_tokens_processed: int
    recall_score: float
    response_quality: float
    memory_growth_bytes: int
    compactions: int


def load_conversations(path: Path) -> list[dict[str, Any]]:
    """Student TODO: read JSON conversations from disk."""
    import json
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def recall_points(answer: str, expected: list[str]) -> float:
    """Student TODO: return 0 / 0.5 / 1 depending on how many expected facts appear."""
    score = 0.0
    import unicodedata
    def normalize(s):
        return unicodedata.normalize('NFC', s.lower())
    
    normalized_answer = normalize(answer)
    for e in expected:
        if normalize(e) in normalized_answer:
            score += 1.0
    if not expected:
        return 1.0
    return score / len(expected)


def heuristic_quality(answer: str, expected: list[str]) -> float:
    """Student TODO: add a lightweight quality score for offline mode."""
    if not answer:
        return 0.0
    score = recall_points(answer, expected)
    if score > 0:
        return min(1.0, score + 0.1)
    return 0.5 if "Đã nhận" not in answer else 0.0


def run_agent_benchmark(agent_name: str, agent, conversations: list[dict[str, Any]], config) -> BenchmarkRow:
    """Student TODO: evaluate one agent over many conversations."""
    total_agent_tokens = 0
    total_prompt_tokens = 0
    total_recall = 0.0
    total_quality = 0.0
    total_compactions = 0
    total_growth = 0
    
    num_recall_questions = 0

    for conv in conversations:
        conv_id = conv["id"]
        user_id = conv["user_id"]
        
        # Feed all turns
        for turn in conv["turns"]:
            agent.reply(user_id, conv_id, turn)
        
        total_agent_tokens += agent.token_usage(conv_id)
        total_prompt_tokens += agent.prompt_token_usage(conv_id)
        total_compactions += agent.compaction_count(conv_id)
        
        # Cross-session recall in a fresh thread
        fresh_thread_id = f"{conv_id}-recall"
        for q in conv["recall_questions"]:
            question = q["question"]
            expected = q["expected_contains"]
            
            num_recall_questions += 1
            
            # Ask agent
            reply = agent.reply(user_id, fresh_thread_id, question)
                
            answer = reply.get("content", "")
            total_recall += recall_points(answer, expected)
            total_quality += heuristic_quality(answer, expected)
            
        if hasattr(agent, "memory_file_size"):
            # keep max growth or cumulative?
            # actually we can just take the latest file size for that user
            growth = agent.memory_file_size(user_id)
            total_growth = max(total_growth, growth)
            
    avg_recall = total_recall / num_recall_questions if num_recall_questions > 0 else 0.0
    avg_quality = total_quality / num_recall_questions if num_recall_questions > 0 else 0.0
            
    return BenchmarkRow(
        agent_name=agent_name,
        agent_tokens_only=total_agent_tokens,
        prompt_tokens_processed=total_prompt_tokens,
        recall_score=avg_recall,
        response_quality=avg_quality,
        memory_growth_bytes=total_growth,
        compactions=total_compactions
    )


def format_rows(rows: list[BenchmarkRow]) -> str:
    """Student TODO: print a markdown table or tabulated output."""
    from tabulate import tabulate
    
    headers = [
        "Agent", 
        "Agent tokens only", 
        "Prompt tokens processed", 
        "Cross-session recall", 
        "Response quality", 
        "Memory growth (bytes)", 
        "Compactions"
    ]
    
    table_data = []
    for r in rows:
        table_data.append([
            r.agent_name,
            r.agent_tokens_only,
            r.prompt_tokens_processed,
            f"{r.recall_score:.2f}",
            f"{r.response_quality:.2f}",
            r.memory_growth_bytes,
            r.compactions
        ])
        
    return tabulate(table_data, headers=headers, tablefmt="pipe")


def main() -> None:
    """Student TODO: run both benchmark suites."""
    config = load_config(Path(__file__).resolve().parent.parent)
    
    data_dir = config.data_dir
    
    std_convs = load_conversations(data_dir / "conversations.json")
    stress_convs = load_conversations(data_dir / "advanced_long_context.json")
    
    print("=== Standard Benchmark ===")
    baseline = BaselineAgent(config, force_offline=True)
    advanced = AdvancedAgent(config, force_offline=True)
    
    std_baseline_row = run_agent_benchmark("Baseline", baseline, std_convs, config)
    std_advanced_row = run_agent_benchmark("Advanced", advanced, std_convs, config)
    
    print(format_rows([std_baseline_row, std_advanced_row]))
    
    print("\n=== Long-Context Stress Benchmark ===")
    baseline_stress = BaselineAgent(config, force_offline=True)
    advanced_stress = AdvancedAgent(config, force_offline=True)
    
    stress_baseline_row = run_agent_benchmark("Baseline", baseline_stress, stress_convs, config)
    stress_advanced_row = run_agent_benchmark("Advanced", advanced_stress, stress_convs, config)
    
    print(format_rows([stress_baseline_row, stress_advanced_row]))


if __name__ == "__main__":
    main()
