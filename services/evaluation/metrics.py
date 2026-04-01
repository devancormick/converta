from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

try:
    from rouge_score import rouge_scorer
    _ROUGE = rouge_scorer.RougeScorer(["rouge1", "rougeL"], use_stemmer=True)
except ImportError:
    _ROUGE = None

try:
    from bert_score import score as _bert_score_fn
    _BERTSCORE = True
except ImportError:
    _BERTSCORE = False

try:
    import textstat
    _TEXTSTAT = True
except ImportError:
    _TEXTSTAT = False

try:
    from transformers import GPT2LMHeadModel, GPT2TokenizerFast
    import torch
    _tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")
    _lm = GPT2LMHeadModel.from_pretrained("gpt2")
    _lm.eval()
    _PERPLEXITY = True
except Exception:
    _PERPLEXITY = False


@dataclass
class MetricResult:
    rouge1: float
    rouge_l: float
    bertscore_f1: float
    perplexity: float


def compute_rouge(reference: str, hypothesis: str) -> tuple[float, float]:
    if _ROUGE is None:
        return 0.0, 0.0
    scores = _ROUGE.score(reference, hypothesis)
    return scores["rouge1"].fmeasure, scores["rougeL"].fmeasure


def compute_bertscore(reference: str, hypothesis: str) -> float:
    if not _BERTSCORE:
        return 0.0
    try:
        _, _, F = _bert_score_fn([hypothesis], [reference], lang="en", verbose=False)
        return float(F[0])
    except Exception:
        return 0.0


def compute_perplexity(text: str) -> float:
    if not _PERPLEXITY:
        return 0.0
    try:
        import torch
        inputs = _tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            outputs = _lm(**inputs, labels=inputs["input_ids"])
        loss = outputs.loss.item()
        return math.exp(loss)
    except Exception:
        return 0.0


def compute_all(reference: str, hypothesis: str) -> MetricResult:
    rouge1, rouge_l = compute_rouge(reference, hypothesis)
    bertscore_f1 = compute_bertscore(reference, hypothesis)
    perplexity = compute_perplexity(hypothesis)
    return MetricResult(
        rouge1=rouge1,
        rouge_l=rouge_l,
        bertscore_f1=bertscore_f1,
        perplexity=perplexity,
    )
