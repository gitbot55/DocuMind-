| Setting | Value |
|---|---|
| chunk_words | 500 |
| chunk_overlap | 80 |
| top_k | 5 |
| threshold | 0.45 |
| embedder | fastembed:BAAI/bge-small-en-v1.5 |
| chunks_indexed | 7 |
| llm_used | True |

| Metric | Value |
|---|---|
| n_answerable | 23 |
| n_unanswerable | 5 |
| hit_rate_at_1 | 0.957 |
| hit_rate_at_3 | 1.000 |
| hit_rate_at_k | 1.000 |
| mrr | 0.978 |
| correct_refusal_rate | 1.000 |
| false_refusal_rate | 0.000 |
| judge_correctness | n/a |
| judge_faithfulness | n/a |
| avg_latency_ms | 7154.500 |
