"""
research_engine/writer/similarity_estimator.py
Tier 3 — Turnitin-style similarity estimator

Scans generated chapter text for suspiciously generic sentences and
estimates likely plagiarism similarity scores before submission.

How it works:
  1. Splits text into sentences
  2. Scores each sentence on "genericity" — common academic phrases,
     boilerplate, and formulaic structures score high
  3. Checks for overly common transition phrases
  4. Flags sentences that read like they came from Wikipedia or a
     textbook introduction
  5. Estimates an overall similarity percentage

This is NOT a real plagiarism checker — it's a heuristic warning
system. It tells the student "these sentences are likely to trigger
high similarity on Turnitin because they're generic."

Public API
----------
    estimate_similarity(text)           → SimilarityReport
    estimate_session(session)           → dict[int, SimilarityReport]
    flag_generic_sentences(text)        → list[SentenceFlag]
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from collections import Counter


@dataclass
class SentenceFlag:
    """A single flagged sentence."""
    text:           str
    score:          float     # 0–1 (higher = more generic)
    reason:         str
    start_char:     int = 0

    def __repr__(self): return f"[{self.score:.2f}] {self.text[:60]}"


@dataclass
class SimilarityReport:
    """Similarity estimate for a chapter or text block."""
    estimated_similarity:   float = 0.0     # 0–100%
    total_sentences:         int   = 0
    flagged_sentences:       int   = 0
    high_risk_sentences:     int   = 0       # score > 0.7
    flags:                   list[SentenceFlag] = field(default_factory=list)
    average_sentence_score:  float = 0.0
    grade:                   str   = "—"
    recommendation:          str   = ""

    def summary(self) -> str:
        lines = [
            f"Estimated similarity: ~{self.estimated_similarity:.0f}%",
            f"Sentences: {self.total_sentences} | Flagged: {self.flagged_sentences} | High risk: {self.high_risk_sentences}",
            f"Average genericity: {self.average_sentence_score:.2f}",
            f"Grade: {self.grade}",
            f"Recommendation: {self.recommendation}",
        ]
        if self.flags:
            lines.append("\nTop flagged sentences:")
            for f in self.flags[:5]:
                lines.append(f"  [{f.score:.2f}] {f.text[:70]}")
                lines.append(f"        Reason: {f.reason}")
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# Generic phrase patterns (score-weighted)
# ══════════════════════════════════════════════════════════════

_GENERIC_PATTERNS = [
    # Very common academic boilerplate (high weight)
    (r"(?i)it is (widely|generally|commonly) (known|accepted|recognized|acknowledged)", 0.85, "Common academic boilerplate"),
    (r"(?i)plays a (vital|crucial|pivotal|significant|important) role", 0.80, "Overused phrase: 'plays a vital/crucial role'"),
    (r"(?i)(has|have) become (increasingly|more and more) important", 0.80, "Overused phrase: 'has become increasingly important'"),
    (r"(?i)in today'?s (world|society|modern society)", 0.85, "Generic opener: 'in today's world/society'"),
    (r"(?i)(therefore|thus|hence|consequently), it can be (concluded|inferred|seen)", 0.75, "Formulaic conclusion phrase"),
    (r"(?i)the (purpose|aim|objective) of this (study|research) is to", 0.70, "Standard purpose statement — consider rephrasing"),
    (r"(?i)according to the (world health organization|who|unicef)", 0.65, "Frequently copied WHO/UNICEF statement"),
    (r"(?i)this (study|research) (aimed|sought) to (examine|investigate|determine|assess|explore)", 0.70, "Standard research aim statement"),
    (r"(?i)several (studies|researchers|authors) have (shown|demonstrated|indicated|reported)", 0.70, "Overused literature transition"),
    (r"(?i)it is (important|essential|crucial|necessary) to (note|understand|recognize|highlight)", 0.75, "Filler phrase"),
    (r"(?i)(on the other hand|in contrast|conversely), (other|some|many) (studies|researchers)", 0.65, "Overused contrast transition"),
    (r"(?i)the (results|findings) of this (study|research) (show|demonstrate|reveal|indicate)", 0.70, "Standard results opener"),
    (r"(?i)in (conclusion|summary), (the|this) (study|research) (has|have)", 0.75, "Formulaic conclusion opener"),
    (r"(?i)(data|information) were (collected|gathered|obtained) (using|through|via|by means of)", 0.65, "Standard methods phrase"),
    (r"(?i)a (structured|self-administered|well-structured) questionnaire was (used|administered|employed)", 0.70, "Standard instrument description"),
    (r"(?i)the (target|study) population (consisted of|comprised|included)", 0.65, "Standard population description"),
    (r"(?i)(simple|purposive|stratified|random) (random )?sampling (technique|method) was (used|employed|adopted)", 0.70, "Standard sampling description"),
    (r"(?i)(cronbach'?s )?alpha (of|value|coefficient) (0\.\d+|>\s*0\.7)", 0.60, "Standard reliability statement"),
    (r"(?i)(chi-square|chi square|χ²) (test|analysis) was (used|conducted|performed|employed)", 0.65, "Standard analysis phrase"),
    (r"(?i)at (a|the) (0\.05|p\s*[<≤]\s*0\.05) (level of significance|significance level)", 0.65, "Standard significance phrase"),
    (r"(?i)the (null hypothesis|H0) (was|is) (rejected|accepted|not rejected)", 0.70, "Standard hypothesis conclusion"),
    (r"(?i)(in|with) (line|accordance) (with|to) (previous|earlier|prior) (studies|research)", 0.65, "Overused comparison phrase"),
    (r"(?i)this (finding|result) is (consistent with|in agreement with|supported by)", 0.65, "Overused finding comparison"),
    (r"(?i)the (table|figure|chart) (above|below) (shows|illustrates|depicts|presents|displays)", 0.60, "Standard table reference"),
    (r"(?i)as (shown|presented|indicated|depicted) in (table|figure) \d+", 0.60, "Standard table reference"),
    (r"(?i)the majority of (respondents|participants|the respondents)", 0.55, "Common frequency phrase"),
    (r"(?i)more than half of (the )?(respondents|participants)", 0.55, "Common frequency phrase"),
    (r"(?i)based on the (findings|results|data|analysis) of this (study|research)", 0.65, "Standard findings reference"),

    # Wikipedia/textbook style
    (r"(?i)is defined as (the|a) ", 0.70, "Dictionary-style definition"),
    (r"(?i)refers to (the|a) ", 0.65, "Dictionary-style definition"),
    (r"(?i)can be (defined|described) as ", 0.65, "Dictionary-style definition"),
    (r"(?i)is (a|an) (method|technique|process|approach|system) (used|designed|that)", 0.60, "Textbook-style definition"),

    # Very short sentences with no substance
    (r"(?i)^(this|that|it) (is|was|has|had) (very|quite|really|extremely) ", 0.60, "Empty intensifier sentence"),
]

# Common transition words that signal generic writing
_TRANSITION_OVERUSE = re.compile(
    r"(?i)\b(furthermore|moreover|additionally|in addition|consequently|nevertheless|nonetheless)\b",
    re.IGNORECASE
)


# ══════════════════════════════════════════════════════════════
# Sentence splitter
# ══════════════════════════════════════════════════════════════

def _split_sentences(text: str) -> list[tuple[str, int]]:
    """
    Split text into sentences, returning (sentence, start_char) tuples.
    """
    # Remove markdown headings for sentence analysis
    clean = re.sub(r'^#+\s+.*$', '', text, flags=re.MULTILINE)
    # Split on sentence endings
    sentences = []
    pos = 0
    for m in re.finditer(r'([^.!?]+[.!?]+(?:\s|$))', clean):
        s = m.group(0).strip()
        if len(s) > 15:  # skip very short fragments
            sentences.append((s, m.start()))
    return sentences


# ══════════════════════════════════════════════════════════════
# Sentence scoring
# ══════════════════════════════════════════════════════════════

def _score_sentence(sentence: str) -> tuple[float, str]:
    """
    Score a sentence for genericity. Returns (score, reason).
    """
    max_score = 0.0
    reason = ""

    for pattern, weight, desc in _GENERIC_PATTERNS:
        if re.search(pattern, sentence):
            if weight > max_score:
                max_score = weight
                reason = desc

    # Check for transition word overuse
    transitions = _TRANSITION_OVERUSE.findall(sentence)
    if len(transitions) >= 2:
        score = max(max_score, 0.55)
        if score > max_score:
            max_score = score
            reason = f"Multiple transition words in one sentence ({', '.join(transitions)})"

    # Very short sentences are often filler
    words = sentence.split()
    if len(words) < 8 and max_score < 0.5:
        max_score = max(max_score, 0.35)
        reason = reason or "Very short sentence — may be filler"

    # Sentences with no citations and high length are lower risk
    if "(" not in sentence and max_score < 0.4 and len(words) > 25:
        max_score = min(max_score, 0.3)  # specific long sentences are probably fine

    return (max_score, reason) if max_score > 0 else (0.0, "")


# ══════════════════════════════════════════════════════════════
# Main functions
# ══════════════════════════════════════════════════════════════

def flag_generic_sentences(text: str) -> list[SentenceFlag]:
    """
    Flag individual sentences that are likely to trigger high similarity.
    """
    flags = []
    for sentence, start in _split_sentences(text):
        score, reason = _score_sentence(sentence)
        if score > 0.4:
            flags.append(SentenceFlag(
                text=sentence, score=score, reason=reason,
                start_char=start
            ))
    return flags


def estimate_similarity(text: str) -> SimilarityReport:
    """
    Estimate likely Turnitin similarity for a text block.

    Returns a SimilarityReport with estimated percentage, flagged
    sentences, and recommendations.
    """
    sentences = _split_sentences(text)
    report = SimilarityReport(total_sentences=len(sentences))

    if not sentences:
        return report

    all_flags = flag_generic_sentences(text)
    report.flags = sorted(all_flags, key=lambda x: -x.score)
    report.flagged_sentences = len(all_flags)
    report.high_risk_sentences = sum(1 for f in all_flags if f.score > 0.7)

    # Average genericity across all sentences
    all_scores = []
    for sentence, _ in sentences:
        s, _ = _score_sentence(sentence)
        all_scores.append(s)
    report.average_sentence_score = sum(all_scores) / len(all_scores) if all_scores else 0

    # Estimated similarity: weighted combination
    # - flagged ratio
    # - high-risk ratio (weighted 2x)
    # - average genericity
    flagged_ratio = report.flagged_sentences / report.total_sentences
    high_risk_ratio = report.high_risk_sentences / report.total_sentences
    raw = (flagged_ratio * 30) + (high_risk_ratio * 25) + (report.average_sentence_score * 45)
    report.estimated_similarity = min(round(raw, 1), 95.0)

    # Grade
    sim = report.estimated_similarity
    if sim < 15: report.grade = "A"
    elif sim < 25: report.grade = "B"
    elif sim < 35: report.grade = "C"
    elif sim < 50: report.grade = "D"
    else: report.grade = "F"

    # Recommendation
    if sim < 15:
        report.recommendation = "Low similarity risk. Text appears original and specific."
    elif sim < 25:
        report.recommendation = "Moderate risk. A few generic phrases — consider rephrasing flagged sentences."
    elif sim < 35:
        report.recommendation = "Elevated risk. Rephrase all flagged sentences and add more specific examples."
    elif sim < 50:
        report.recommendation = "High risk. Major revision needed — text contains too much generic academic phrasing."
    else:
        report.recommendation = "Critical risk. Rewrite flagged sentences entirely with specific, original language."

    return report


def estimate_session(session) -> dict[int, SimilarityReport]:
    """
    Estimate similarity for all chapters in a session.
    """
    reports = {}
    for n, ch in session.chapters.items():
        reports[n] = estimate_similarity(ch.content)
    return reports
