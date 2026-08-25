# Reproduction helper: single multi-hop question smoke test with INFO logging
# and dependency graph decomposition history output
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
logging.basicConfig(level=logging.INFO, format="%(message)s")

from src.main import create_rag_model

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_PATH = os.path.join(PROJECT_ROOT, "dataset", "hotpotqa_corpus.json")

QUESTION = "In which county is the town in which Raymond Robertsen was born ?"

model = create_rag_model("logic-rag", DATASET_PATH, max_rounds=3, top_k=3)
answer, contexts, rounds = model.answer_question(QUESTION)

print("\n==== 最终答案 ====")
print("Q:", QUESTION)
print("A:", answer)
print("检索轮数:", rounds)

print("\n==== 逻辑依赖图分解历史 (论文核心) ====")
import json
print(json.dumps(model.last_dependency_analysis, ensure_ascii=False, indent=2))
