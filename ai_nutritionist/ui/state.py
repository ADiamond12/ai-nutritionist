import pandas as pd
import streamlit as st

from ai_nutritionist.ui.config import FEEDBACK_AVOID_TERMS, PLAN_VARIATIONS


def ensure_session_state() -> None:
    st.session_state.setdefault("feedback_log", [])
    st.session_state.setdefault("last_plan", None)
    st.session_state.setdefault("plan_variant", 0)


def merge_terms(*values: str | list[str] | tuple[str, ...] | None) -> list[str]:
    merged: list[str] = []
    for value in values:
        if not value:
            continue
        if isinstance(value, str):
            terms = value.replace(";", ",").replace("\n", ",").split(",")
        else:
            terms = list(value)
        for term in terms:
            cleaned = str(term).strip().lower()
            if cleaned and cleaned not in merged:
                merged.append(cleaned)
    return merged


def variation_terms(dietary_pattern: str, variant: int) -> tuple[str, ...]:
    options = PLAN_VARIATIONS.get(dietary_pattern, ())
    if not options or variant <= 0:
        return ()
    return options[(variant - 1) % len(options)]


def compatible_variation_terms(dietary_pattern: str, variant: int, avoid_terms: list[str]) -> tuple[str, ...]:
    terms = variation_terms(dietary_pattern, variant)
    avoided = merge_terms(avoid_terms)
    if any(_terms_overlap(term, avoided) for term in terms):
        return ()
    return terms


def _terms_overlap(term: str, avoided: list[str]) -> bool:
    cleaned = term.strip().lower()
    return any(cleaned in avoided_term or avoided_term in cleaned for avoided_term in avoided)


def feedback_avoid_terms() -> list[str]:
    terms: list[str] = []
    for entry in st.session_state.feedback_log:
        if not isinstance(entry, dict):
            continue
        if entry.get("sentiment") != "not_liked":
            continue
        avoid_terms = entry.get("avoid_terms", [])
        if not isinstance(avoid_terms, (list, tuple, set)):
            continue
        for term in avoid_terms:
            if term not in terms:
                terms.append(str(term))
    return terms


def main_feedback_terms(items: list[dict[str, object]]) -> list[str]:
    names = " ".join(str(item.get("food_name", "")).lower() for item in items)
    return [term for term in FEEDBACK_AVOID_TERMS if term in names][:3]


def feedback_csv() -> str:
    if not st.session_state.feedback_log:
        return "timestamp_utc,scope,label,sentiment,avoid_terms\n"
    frame = pd.DataFrame(st.session_state.feedback_log).copy()
    if "avoid_terms" in frame.columns:
        frame["avoid_terms"] = frame["avoid_terms"].apply(lambda terms: ", ".join(terms or []))
    return frame.to_csv(index=False)
