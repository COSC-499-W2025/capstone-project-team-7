"""Rule-based skill gap analyzer with role profiles.

Compares a project's detected skills against expected skills for common
software engineering roles and returns matched, missing, and extra skills
with a weighted coverage percentage.

Each expected skill carries an importance level:
  - "critical"    — must-have for the role  (weight 3)
  - "recommended" — strongly expected       (weight 2)
  - "nice_to_have" — beneficial but optional (weight 1)
"""

from typing import Dict, List, Any

# Importance weights used in coverage calculation
IMPORTANCE_WEIGHTS: Dict[str, int] = {
    "critical": 3,
    "recommended": 2,
    "nice_to_have": 1,
}

ROLE_PROFILES: Dict[str, Dict[str, Any]] = {
    "backend_developer": {
        "label": "Backend Developer",
        "description": "Server-side APIs, databases, and business logic",
        "expected_skills": {
            "RESTful API Design": "critical",
            "SQL Database Queries": "critical",
            "Error Handling": "critical",
            "Automated Testing": "recommended",
            "Logging": "recommended",
            "Authentication & Authorization": "recommended",
            "Object-Relational Mapping (ORM)": "nice_to_have",
            "Input Validation": "recommended",
            "Middleware Pattern": "nice_to_have",
        },
    },
    "frontend_developer": {
        "label": "Frontend Developer",
        "description": "User interfaces, client-side logic, and web frameworks",
        "expected_skills": {
            "React Framework": "critical",
            "Automated Testing": "recommended",
            "Asynchronous Programming": "recommended",
            "Static Typing": "recommended",
            "Error Handling": "critical",
            "Next.js Framework": "nice_to_have",
            "Code Documentation": "nice_to_have",
        },
    },
    "fullstack_developer": {
        "label": "Full-Stack Developer",
        "description": "End-to-end development across frontend and backend",
        "expected_skills": {
            "RESTful API Design": "critical",
            "SQL Database Queries": "recommended",
            "Error Handling": "critical",
            "Automated Testing": "recommended",
            "Authentication & Authorization": "recommended",
            "React Framework": "critical",
            "Asynchronous Programming": "recommended",
            "Static Typing": "nice_to_have",
            "Logging": "nice_to_have",
            "Input Validation": "nice_to_have",
        },
    },
    "data_scientist": {
        "label": "Data Scientist",
        "description": "Data analysis, machine learning, and statistical modelling",
        "expected_skills": {
            "Data Analysis (pandas)": "critical",
            "Numerical Computing (NumPy)": "critical",
            "Machine Learning (scikit-learn)": "recommended",
            "Dynamic Programming": "nice_to_have",
            "Hash-based Data Structures": "recommended",
            "Automated Testing": "recommended",
            "Code Documentation": "nice_to_have",
            "SQL Database Queries": "recommended",
        },
    },
    "devops_engineer": {
        "label": "DevOps Engineer",
        "description": "CI/CD pipelines, containers, and infrastructure automation",
        "expected_skills": {
            "CI/CD Practices": "critical",
            "Containerization": "critical",
            "Version Control (Git)": "critical",
            "Logging": "recommended",
            "Error Handling": "recommended",
            "Automated Testing": "recommended",
        },
    },
    "ml_engineer": {
        "label": "ML Engineer",
        "description": "Production machine learning systems and model deployment",
        "expected_skills": {
            "Machine Learning (scikit-learn)": "critical",
            "Data Analysis (pandas)": "critical",
            "Numerical Computing (NumPy)": "critical",
            "Deep Learning (PyTorch)": "recommended",
            "Deep Learning (TensorFlow)": "recommended",
            "Automated Testing": "recommended",
            "SQL Database Queries": "recommended",
            "Data Visualization (matplotlib)": "nice_to_have",
            "Version Control (Git)": "nice_to_have",
            "Logging": "nice_to_have",
        },
    },
    "security_engineer": {
        "label": "Security Engineer",
        "description": "Application security, authentication, and secure coding practices",
        "expected_skills": {
            "Authentication & Authorization": "critical",
            "Input Validation": "critical",
            "Error Handling": "critical",
            "Automated Testing": "recommended",
            "Logging": "recommended",
            "Middleware Pattern": "recommended",
            "Static Typing": "nice_to_have",
            "Code Documentation": "nice_to_have",
        },
    },
}


def get_available_roles() -> List[Dict[str, str]]:
    """Return list of available role profiles."""
    return [
        {"key": key, "label": profile["label"], "description": profile["description"]}
        for key, profile in ROLE_PROFILES.items()
    ]


def analyze_gaps(detected_skills: List[str], role: str) -> Dict[str, Any]:
    """Compare detected skills against a role profile with importance weighting.

    Args:
        detected_skills: List of skill names found in the project.
        role: Role profile key (e.g. ``"backend_developer"``).

    Returns:
        Dict with ``role``, ``role_label``, ``matched``, ``missing``,
        ``extra``, ``coverage_percent``, and ``weighted_coverage_percent`` keys.
        Matched and missing entries include importance levels.

    Raises:
        ValueError: If the role key is not recognised.
    """
    profile = ROLE_PROFILES.get(role)
    if profile is None:
        raise ValueError(f"Unknown role: {role}. Available: {list(ROLE_PROFILES.keys())}")

    expected_skills = profile["expected_skills"]
    detected = set(detected_skills)

    matched = []
    missing = []
    weighted_matched = 0
    weighted_total = 0

    for skill_name, importance in expected_skills.items():
        weight = IMPORTANCE_WEIGHTS.get(importance, 1)
        weighted_total += weight

        if skill_name in detected:
            matched.append({"name": skill_name, "importance": importance})
            weighted_matched += weight
        else:
            missing.append({"name": skill_name, "importance": importance})

    # Sort: critical first, then recommended, then nice_to_have
    importance_order = {"critical": 0, "recommended": 1, "nice_to_have": 2}
    matched.sort(key=lambda s: (importance_order.get(s["importance"], 9), s["name"]))
    missing.sort(key=lambda s: (importance_order.get(s["importance"], 9), s["name"]))

    extra = sorted(detected - set(expected_skills.keys()))

    flat_coverage = round(len(matched) / len(expected_skills) * 100, 1) if expected_skills else 0.0
    weighted_coverage = round(weighted_matched / weighted_total * 100, 1) if weighted_total else 0.0

    return {
        "role": role,
        "role_label": profile["label"],
        "matched": matched,
        "missing": missing,
        "extra": extra,
        "coverage_percent": flat_coverage,
        "weighted_coverage_percent": weighted_coverage,
    }
