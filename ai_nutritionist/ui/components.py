import pandas as pd
import streamlit as st

from ai_nutritionist.data import load_food_catalog
from ai_nutritionist.ui.state import main_feedback_terms


def hide_streamlit_chrome() -> None:
    st.markdown(
        """
        <style>
          #MainMenu,
          footer,
          header,
          [data-testid="stDeployButton"],
          [data-testid="stToolbar"],
          [data-testid="stDecoration"],
          [data-testid="stStatusWidget"],
          .stDeployButton {
            display: none !important;
          }
          .block-container {
            padding-top: 3rem;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data
def catalog() -> pd.DataFrame:
    return load_food_catalog()


def progress_value(current: float, target: float) -> float:
    if target <= 0:
        return 0.0
    return min(float(current) / float(target), 1.0)


def progress_row(label: str, current: float, target: float, unit: str, *, limit: bool = False) -> None:
    pct = 0 if target <= 0 else (current / target) * 100
    status = "limit" if limit else "target"
    st.write(f"**{label}**")
    st.progress(progress_value(current, target))
    st.caption(f"{current:.1f}{unit} / {target:.1f}{unit} {status} ({pct:.0f}%)")


def items_frame(items: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(items)[
        [
            "food_name",
            "food_group",
            "serving_grams",
            "calories",
            "protein_g",
            "carbohydrate_g",
            "fiber_g",
            "sugars_g",
            "sodium_mg",
            "saturated_fat_g",
            "vegetarian",
            "vegan",
        ]
    ]


def feedback_widget(
    *,
    scope: str,
    label: str,
    items: list[dict[str, object]],
    context: dict[str, object],
) -> None:
    st.caption(f"Was this {scope} useful?")
    key = f"feedback_{scope}_{label}".lower().replace(" ", "_").replace("/", "_")
    value = st.feedback("thumbs", key=key)
    marker_key = f"{key}_recorded"
    if value is None or st.session_state.get(marker_key) == value:
        return

    sentiment = "liked" if value == 1 else "not_liked"
    st.session_state.feedback_log.append(
        {
            "timestamp_utc": pd.Timestamp.utcnow().isoformat(),
            "scope": scope,
            "label": label,
            "sentiment": sentiment,
            "avoid_terms": main_feedback_terms(items) if sentiment == "not_liked" else [],
            **context,
        }
    )
    st.session_state[marker_key] = value
    if sentiment == "not_liked":
        st.caption("Feedback saved locally. Use Regenerate with feedback to try a different version.")

