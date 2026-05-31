"""Public package API for AI Nutritionist."""

from ai_nutritionist.recommender import RecommendationResult, WeeklyRecommendationResult, recommend, recommend_week

__all__ = ["RecommendationResult", "WeeklyRecommendationResult", "recommend", "recommend_week"]
