import json, numpy as np
from sentence_transformers import SentenceTransformer
from collections import defaultdict

# Load datasets
with open('dataset/bylaws_dataset.json', encoding='utf-8') as f:
    grounded_data = json.load(f)['bylaws']
with open('dataset/bylaws_dataset_backup_verbatim2.json', encoding='utf-8') as f:
    fallback_data = json.load(f)['bylaws']

# Load benchmark
with open('tests/retrieval_benchmark.json', encoding='utf-8') as f:
    benchmark = json.load(f)

# Build lookup: section_id -> record text (for both versions)
def build_text_lookup(records, use_grounded=True):
    lookup = {}
    for r in records:
        bid = r.get('official_bylaw_number', '') or r.get('bylaw_number', '')
        if use_grounded:
            text = r.get('official_legal_text', '') or r.get('retrieval_text', '') or ''
        else:
            text = r.get('retrieval_text', '') or r.get('official_legal_text', '') or ''
        if bid:
            lookup[str(bid).strip()] = text
    return lookup

grounded_lookup = build_text_lookup(grounded_data, use_grounded=True)
fallback_lookup = build_text_lookup(fallback_data, use_grounded=False)

# For the fallback version, check if each expected section was grounded or not
fallback_grounding_status = {}
for r in fallback_data:
    bid = r.get('official_bylaw_number', '') or r.get('bylaw_number', '')
    if bid:
        status = r.get('official_grounding_status', '')
        fallback_grounding_status[str(bid).strip()] = status

# Load embedding model
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

# Pre-compute embeddings for all texts in both versions
print("Computing embeddings...")
grounded_texts = [grounded_lookup.get(bid, '') for bid in sorted(grounded_lookup.keys())]
fallback_texts = [fallback_lookup.get(bid, '') for bid in sorted(fallback_lookup.keys())]
all_section_ids = list(sorted(set(list(grounded_lookup.keys()) + list(fallback_lookup.keys()))))

# Filter to only sections present in both
section_ids = [s for s in all_section_ids if s in grounded_lookup and s in fallback_lookup]
print(f"Comparing {len(section_ids)} sections")

g_texts = [grounded_lookup[s] for s in section_ids]
f_texts = [fallback_lookup[s] for s in section_ids]

g_emb = model.encode(g_texts, show_progress_bar=True, convert_to_numpy=True)
f_emb = model.encode(f_texts, show_progress_bar=True, convert_to_numpy=True)

def cosine_sim(a, b):
    a_norm = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-10)
    b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-10)
    return a_norm @ b_norm.T

def run_bench(embeddings, section_ids, queries, label):
    q_emb = model.encode([q['query'] for q in queries], show_progress_bar=False, convert_to_numpy=True)
    sims = cosine_sim(q_emb, embeddings)
    
    results = []
    for i, q in enumerate(queries):
        expected = set(q['expected_sections'])
        scores = sims[i]
        ranked_idx = np.argsort(-scores)
        ranked_sections = [section_ids[idx] for idx in ranked_idx]
        
        top1_correct = ranked_sections[0] in expected if ranked_sections else False
        top3_correct = any(s in expected for s in ranked_sections[:3])
        top5_correct = any(s in expected for s in ranked_sections[:5])
        rr = 0.0
        for rank, sec in enumerate(ranked_sections, 1):
            if sec in expected:
                rr = 1.0 / rank
                break
        
        # Determine if query's expected sections were grounded or fallback in old version
        was_grounded = all(
            fallback_grounding_status.get(es, '') in ('verbatim_sourced', 'verbatim_source_verified')
            for es in expected
        )
        
        results.append({
            'query': q['query'],
            'topic': q.get('topic', ''),
            'expected': list(expected),
            'top1': top1_correct,
            'top3': top3_correct,
            'top5': top5_correct,
            'mrr': rr,
            'was_grounded': was_grounded,
        })
    
    # Aggregate
    total = len(results)
    grounded_q = [r for r in results if r['was_grounded']]
    fallback_q = [r for r in results if not r['was_grounded']]
    
    def agg(qs, name):
        t = len(qs)
        t1 = sum(1 for r in qs if r['top1']); t3 = sum(1 for r in qs if r['top3']); t5 = sum(1 for r in qs if r['top5'])
        mrr = sum(r['mrr'] for r in qs) / max(t, 1)
        return f"{name:15s} n={t:2d}  Top-1={t1:2d}/{t} ({t1/max(t,1)*100:.0f}%)  Top-3={t3:2d}/{t} ({t3/max(t,1)*100:.0f}%)  Top-5={t5:2d}/{t} ({t5/max(t,1)*100:.0f}%)  MRR={mrr:.4f}"
    
    print(f"\n--- {label} ---")
    print(agg(results, "All"))
    print(agg(grounded_q, "Grounded"))
    print(agg(fallback_q, "Fallback"))
    
    # Weakest clusters
    topic_stats = defaultdict(lambda: {'n':0, 't1':0, 't3':0, 't5':0, 'rrs':[]})
    for r in results:
        topic_stats[r['topic']]['n'] += 1
        topic_stats[r['topic']]['t1'] += 1 if r['top1'] else 0
        topic_stats[r['topic']]['t3'] += 1 if r['top3'] else 0
        topic_stats[r['topic']]['t5'] += 1 if r['top5'] else 0
        topic_stats[r['topic']]['rrs'].append(r['mrr'])
    
    print("\nPer-topic (worst first by Top-1):")
    for topic in sorted(topic_stats, key=lambda t: topic_stats[t]['t1'] / max(topic_stats[t]['n'],1)):
        ts = topic_stats[topic]
        mrr = sum(ts['rrs']) / max(ts['n'],1)
        t1p = ts['t1']/max(ts['n'],1)*100
        print(f"  {topic:20s} n={ts['n']:2d} Top-1={t1p:5.1f}% MRR={mrr:.4f}")
    
    return results

print("\nBenchmark queries:", len(benchmark))
g_res = run_bench(g_emb, section_ids, benchmark, "GROUNDED TEXT")
f_res = run_bench(f_emb, section_ids, benchmark, "FALLBACK TEXT")

# Also count how many queries had grounded vs fallback expected sections
n_g = sum(1 for r in g_res if r['was_grounded'])
n_f = sum(1 for r in g_res if not r['was_grounded'])
print(f"\nQueries referencing grounded sections: {n_g}")
print(f"Queries referencing fallback sections: {n_f}")
