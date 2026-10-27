"""
Inkloom AI Brand Checker
Combines deterministic rule checks with AI-assisted analysis.
"""
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class CheckResult:
    category: str
    severity: str
    title: str
    explanation: str
    original_text: str
    suggested_text: Optional[str]
    guideline_id: Optional[int]
    is_rule_based: bool
    confidence: float


# Sample brand knowledge for demo (can be overridden by workspace guidelines)
DEFAULT_PROHIBITED = [
    (r"\bguaranteed\b", "Avoid absolute guarantees unless approved.", "high"),
    (r"\bbest\s+in\s+(the\s+)?world\b", "Avoid unsubstantiated superlatives.", "high"),
    (r"\b#1\b|\bnumber\s+one\b", "Ranking claims require approved evidence.", "high"),
    (r"\bfree\s+forever\b", "Pricing claims must match approved offers.", "medium"),
    (r"\b100%\s+safe\b|\bcompletely\s+safe\b", "Safety claims require supporting evidence.", "critical"),
]

DEFAULT_PREFERRED = {
    "AI": "artificial intelligence",
    "ML": "machine learning",
    "customers": "clients",  # example brand preference
}

DEFAULT_TONE_KEYWORDS = {
    "professional": ["innovative", "reliable", "trusted", "expert", "proven"],
    "casual": ["awesome", "cool", "super", "amazing", "wow"],
}


def check_prohibited_phrases(text: str, guidelines: List[Dict]) -> List[CheckResult]:
    results = []
    text_lower = text.lower()
    
    # From workspace guidelines
    for g in guidelines:
        if g.get("category") in ("prohibited", "claim") and g.get("is_exact_match"):
            pattern = re.escape(g["content"].lower())
            if re.search(rf"\b{pattern}\b", text_lower):
                results.append(CheckResult(
                    category=g["category"],
                    severity=g.get("severity", "high"),
                    title=f"Prohibited or restricted phrase: '{g['content']}'",
                    explanation=f"This text matches the restricted guideline: {g['title']}. {g['content']}",
                    original_text=g["content"],
                    suggested_text=None,
                    guideline_id=g.get("id"),
                    is_rule_based=True,
                    confidence=1.0
                ))
    
    # Built-in patterns
    for pattern, msg, severity in DEFAULT_PROHIBITED:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for m in matches:
            original = m.group(0)
            results.append(CheckResult(
                category="claim",
                severity=severity,
                title=f"Potentially unsupported claim: '{original}'",
                explanation=msg + " Link this to an approved claim or remove the absolute language.",
                original_text=original,
                suggested_text=_suggest_softer(original),
                guideline_id=None,
                is_rule_based=True,
                confidence=0.95
            ))
    return results


def check_terminology(text: str, guidelines: List[Dict]) -> List[CheckResult]:
    results = []
    # Preferred terms from guidelines
    preferred = {}
    for g in guidelines:
        if g.get("category") == "terminology":
            # Expect content like "Use X instead of Y" or simple preferred term
            preferred[g["title"].lower()] = g["content"]
    
    # Also use defaults
    for wrong, right in DEFAULT_PREFERRED.items():
        if wrong.lower() in text.lower() and right.lower() not in text.lower():
            # Simple presence check
            results.append(CheckResult(
                category="terminology",
                severity="low",
                title=f"Preferred terminology suggestion",
                explanation=f"Brand prefers '{right}' over '{wrong}' in customer-facing content.",
                original_text=wrong,
                suggested_text=right,
                guideline_id=None,
                is_rule_based=True,
                confidence=0.85
            ))
    return results


def check_tone_and_alignment(text: str, guidelines: List[Dict], channel: str = "social") -> List[CheckResult]:
    """AI-assisted style checks (rule-heuristic simulation for reliability)."""
    results = []
    text_lower = text.lower()
    word_count = len(text.split())
    
    # Tone mismatch heuristics
    casual_hits = sum(1 for w in DEFAULT_TONE_KEYWORDS["casual"] if w in text_lower)
    if casual_hits >= 2 and channel in ("ad", "campaign", "email"):
        results.append(CheckResult(
            category="tone",
            severity="medium",
            title="Tone may be too casual for this channel",
            explanation=f"Detected informal language that may not match a professional brand voice for {channel} content. Consider more measured wording.",
            original_text="",
            suggested_text=None,
            guideline_id=None,
            is_rule_based=False,  # AI-assisted judgement
            confidence=0.7
        ))
    
    # Length / clarity
    if word_count > 80 and channel == "social":
        results.append(CheckResult(
            category="message",
            severity="low",
            title="Social posts are often more effective when concise",
            explanation="This draft is relatively long for typical social platforms. Consider shortening while keeping the core message.",
            original_text="",
            suggested_text=None,
            guideline_id=None,
            is_rule_based=False,
            confidence=0.65
        ))
    
    # Missing brand values (simple)
    positive_signals = ["trust", "reliable", "quality", "innovation", "customer", "client"]
    if not any(s in text_lower for s in positive_signals) and word_count > 30:
        results.append(CheckResult(
            category="message",
            severity="low",
            title="Consider reinforcing brand value language",
            explanation="The draft does not clearly surface common brand themes (trust, quality, reliability). This is a soft suggestion only.",
            original_text="",
            suggested_text=None,
            guideline_id=None,
            is_rule_based=False,
            confidence=0.55
        ))
    
    return results


def check_accessibility_and_clarity(text: str) -> List[CheckResult]:
    results = []
    # All-caps shouting
    if re.search(r"\b[A-Z]{5,}\b", text):
        results.append(CheckResult(
            category="accessibility",
            severity="medium",
            title="Excessive capitalisation detected",
            explanation="Large blocks of capital letters can reduce readability and appear aggressive. Prefer sentence case.",
            original_text="",
            suggested_text=None,
            guideline_id=None,
            is_rule_based=True,
            confidence=0.9
        ))
    
    # Very long sentences
    sentences = re.split(r"[.!?]+", text)
    long_sents = [s.strip() for s in sentences if len(s.split()) > 40]
    if long_sents:
        results.append(CheckResult(
            category="clarity",
            severity="low",
            title="Long sentence detected",
            explanation="One or more sentences exceed 40 words. Shorter sentences improve clarity and scannability.",
            original_text=long_sents[0][:120] + ("..." if len(long_sents[0]) > 120 else ""),
            suggested_text=None,
            guideline_id=None,
            is_rule_based=True,
            confidence=0.8
        ))
    return results


def _suggest_softer(phrase: str) -> str:
    softer = {
        "guaranteed": "designed to deliver",
        "best in the world": "among the leading",
        "best in world": "among the leading",
        "#1": "a leading",
        "number one": "a leading",
        "free forever": "free for a limited time",
        "100% safe": "built with safety in mind",
        "completely safe": "designed with safety as a priority",
    }
    return softer.get(phrase.lower(), f"[rephrase: {phrase}]")


def run_full_check(text: str, guidelines: List[Dict], channel: str = "social") -> List[CheckResult]:
    """Main entry point – combines all checkers."""
    all_results: List[CheckResult] = []
    
    all_results.extend(check_prohibited_phrases(text, guidelines))
    all_results.extend(check_terminology(text, guidelines))
    all_results.extend(check_tone_and_alignment(text, guidelines, channel))
    all_results.extend(check_accessibility_and_clarity(text))
    
    # Deduplicate by title + original roughly
    seen = set()
    unique = []
    for r in all_results:
        key = (r.title, r.original_text[:50] if r.original_text else "")
        if key not in seen:
            seen.add(key)
            unique.append(r)
    
    # Sort by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    unique.sort(key=lambda x: severity_order.get(x.severity, 4))
    
    return unique


def generate_suggestion_rewrite(original: str, findings: List[CheckResult]) -> str:
    """Simple rewrite helper that softens flagged phrases."""
    rewritten = original
    for f in findings:
        if f.suggested_text and f.original_text and f.original_text in rewritten:
            rewritten = rewritten.replace(f.original_text, f.suggested_text, 1)
    return rewritten