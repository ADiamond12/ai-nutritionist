DIETARY_PATTERNS = {
    "Mediterranean / Greek": "mediterranean",
    "Omnivore": "omnivore",
    "Vegetarian": "vegetarian",
    "Vegan": "vegan",
    "Keto-style / low carb": "keto_style",
}

GOAL_FOCUS = {
    "Balanced": "balanced",
    "Higher protein": "higher_protein",
    "Higher fiber": "higher_fiber",
    "Lighter meals": "lighter_meals",
    "Lower sodium": "lower_sodium",
}

WEIGHT_GOALS = {
    "Auto from BMI": "auto",
    "Maintain weight": "maintain",
    "Lose weight": "lose",
    "Gain weight": "gain",
}

PLAN_VARIATIONS = {
    "mediterranean": [
        ("chicken", "souvlaki"),
        ("salmon", "fish"),
        ("lentil", "fasolada"),
        ("cod", "plaki"),
        ("chickpea", "gigantes"),
        ("tuna", "white bean"),
    ],
    "omnivore": [("chicken",), ("salmon", "fish"), ("beans", "lentil"), ("turkey",)],
    "vegetarian": [("egg", "yogurt"), ("lentil", "beans"), ("chickpea", "hummus"), ("tofu",)],
    "vegan": [("lentil", "beans"), ("tofu", "soy"), ("chickpea", "hummus"), ("quinoa", "beans")],
    "keto_style": [("chicken",), ("salmon", "fish"), ("egg",), ("turkey",)],
}

FEEDBACK_AVOID_TERMS = (
    "chicken",
    "souvlaki",
    "salmon",
    "cod",
    "tuna",
    "lentil",
    "fasolada",
    "chickpea",
    "gigantes",
    "beans",
    "yogurt",
    "egg",
    "turkey",
    "tofu",
)

