import re
from typing import List, Tuple
from rapidfuzz.distance import Levenshtein
from collections import Counter

def split_sentences(text: str) -> List[str]:
    # Simple splitter with English punctuation; replace/extend for multilingual.
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [p.strip() for p in parts if p.strip()]

def grade_dictation(expected: str, text: str) -> Tuple[float, List[str]]:
    e = re.sub(r"[^a-zA-Z'\s]", '', expected.lower()).split()
    t = re.sub(r"[^a-zA-Z'\s]", '', text.lower()).split()
    # word-level alignment via Levenshtein distance
    max_len = max(len(e), len(t))
    dist = Levenshtein.distance(' '.join(e), ' '.join(t))
    score = max(0.0, 100.0 * (1 - dist / max(1, len(' '.join(e)))))
    # naive diff list
    diffs = []
    for i in range(max_len):
        ew = e[i] if i < len(e) else '(缺)'
        tw = t[i] if i < len(t) else '(缺)'
        if ew != tw:
            diffs.append(f"{tw} → {ew}")
    return round(score, 2), diffs

def keyword_overlap(a: str, b: str) -> float:
    tok = lambda s: [w for w in re.findall(r"[a-zA-Z']+", s.lower()) if len(w)>2]
    A, B = Counter(tok(a)), Counter(tok(b))
    common = sum((A & B).values())
    total = sum(A.values())
    return 0.0 if total == 0 else 100.0 * common / total

def grade_retell(reference: str, text: str) -> float:
    # coverage by keywords
    return round(keyword_overlap(reference, text), 2)

def grade_summary(reference: str, text: str) -> float:
    # coverage + brevity heuristic
    cov = keyword_overlap(reference, text)
    length_penalty = 0.0
    if len(text.split()) < 10: length_penalty = 10.0
    return max(0.0, min(100.0, cov - length_penalty))