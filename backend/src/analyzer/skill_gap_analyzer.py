"""Rule-based skill gap analyzer with role profiles.

Compares a project's detected skills against expected skills for common
software engineering roles and returns matched, missing, and extra skills
with a coverage percentage.
"""

from typing import Dict, List, Any

ROLE_PROFILES: Dict[str, Dict[str, Any]] = {
    "backend_developer": {
        "label": "Backend Developer",
        "description": "Server-side APIs, databases, and business logic",
        "expected_skills": [
            "RESTful API Design",
            "SQL Database Queries",
            "Error Handling",
            "Automated Testing",
            "Logging",
            "Authentication & Authorization",
            "Object-Relational Mapping (ORM)",
            "Input Validation",
            "Middleware Pattern",
        ],
    },
    "frontend_developer": {
        "label": "Frontend Developer",
        "description": "User interfaces, client-side logic, and web frameworks",
        "expected_skills": [
            "React Framework",
            "Vue.js Framework",
            "Angular Framework",
            "Automated Testing",
            "Asynchronous Programming",
            "Static Typing",
            "Error Handling",
        ],
    },
    "fullstack_developer": {
        "label": "Full-Stack Developer",
        "description": "End-to-end development across frontend and backend",
        "expected_skills": [
            "RESTful API Design",
            "SQL Database Queries",
            "Error Handling",
            "Automated Testing",
            "Authentication & Authorization",
            "React Framework",
            "Asynchronous Programming",
            "Static Typing",
            "Logging",
            "Input Validation",
        ],
    },
    "data_scientist": {
        "label": "Data Scientist",
        "description": "Data analysis, algorithms, and statistical modelling",
        "expected_skills": [
            "Dynamic Programming",
            "Sorting Algorithms",
            "Search Algorithms",
            "Hash-based Data Structures",
            "Recursive Problem Solving",
            "Automated Testing",
            "Code Documentation",
            "SQL Database Queries",
        ],
    },
    "devops_engineer": {
        "label": "DevOps Engineer",
        "description": "CI/CD pipelines, containers, and infrastructure automation",
        "expected_skills": [
            "CI/CD Practices",
            "Containerization",
            "Version Control (Git)",
            "Logging",
            "Error Handling",
            "Automated Testing",
        ],
    },
}


def get_available_roles() -> List[Dict[str, str]]:
    """Return list of available role profiles."""
    return [
        {"key": key, "label": profile["label"], "description": profile["description"]}
        for key, profile in ROLE_PROFILES.items()
    ]


def analyze_gaps(detected_skills: List[str], role: str) -> Dict[str, Any]:
    """Compare detected skills against a role profile.

    Args:
        detected_skills: List of skill names found in the project.
        role: Role profile key (e.g. ``"backend_developer"``).

    Returns:
        Dict with ``role``, ``role_label``, ``matched``, ``missing``,
        ``extra``, and ``coverage_percent`` keys.

    Raises:
        ValueError: If the role key is not recognised.
    """
    profile = ROLE_PROFILES.get(role)
    if profile is None:
        raise ValueError(f"Unknown role: {role}. Available: {list(ROLE_PROFILES.keys())}")

    expected = set(profile["expected_skills"])
    detected = set(detected_skills)

    matched = sorted(expected & detected)
    missing = sorted(expected - detected)
    extra = sorted(detected - expected)

    coverage = round(len(matched) / len(expected) * 100, 1) if expected else 0.0

    return {
        "role": role,
        "role_label": profile["label"],
        "matched": matched,
        "missing": missing,
        "extra": extra,
        "coverage_percent": coverage,
    }
