"""Curated learning resource map keyed by skill names from skills_extractor.py.

Each skill maps to a list of resources at various proficiency levels so the
resource suggestions service can recommend the *next-level* material for a
user who is currently at beginner or intermediate tier.
"""

from typing import Any, Dict, List

ResourceEntry = Dict[str, str]  # title, url, type, level

RESOURCE_MAP: Dict[str, List[ResourceEntry]] = {
    # ── Frameworks ────────────────────────────────────────────────────
    "React Framework": [
        {"title": "React Official Tutorial", "url": "https://react.dev/learn", "type": "docs", "level": "beginner"},
        {"title": "React Hooks In Depth", "url": "https://www.youtube.com/watch?v=TNhaISOUy6Q", "type": "video", "level": "intermediate"},
        {"title": "Advanced React Patterns", "url": "https://www.patterns.dev/react", "type": "article", "level": "advanced"},
    ],
    "Next.js Framework": [
        {"title": "Next.js Learn Course", "url": "https://nextjs.org/learn", "type": "course", "level": "beginner"},
        {"title": "Next.js App Router Deep Dive", "url": "https://nextjs.org/docs/app", "type": "docs", "level": "intermediate"},
        {"title": "Advanced Next.js (Vercel)", "url": "https://nextjs.org/docs/app/building-your-application", "type": "docs", "level": "advanced"},
    ],
    "Angular Framework": [
        {"title": "Angular Getting Started", "url": "https://angular.dev/tutorials", "type": "docs", "level": "beginner"},
        {"title": "Angular University Courses", "url": "https://angular-university.io/", "type": "course", "level": "intermediate"},
    ],
    "Vue.js Framework": [
        {"title": "Vue.js Guide", "url": "https://vuejs.org/guide/introduction.html", "type": "docs", "level": "beginner"},
        {"title": "Vue Mastery Free Courses", "url": "https://www.vuemastery.com/courses", "type": "course", "level": "intermediate"},
    ],
    "Django Framework": [
        {"title": "Django Official Tutorial", "url": "https://docs.djangoproject.com/en/stable/intro/tutorial01/", "type": "docs", "level": "beginner"},
        {"title": "Django REST Framework Guide", "url": "https://www.django-rest-framework.org/tutorial/quickstart/", "type": "docs", "level": "intermediate"},
        {"title": "Two Scoops of Django (Book)", "url": "https://www.feldroy.com/books/two-scoops-of-django-3-x", "type": "course", "level": "advanced"},
    ],
    "Flask Framework": [
        {"title": "Flask Mega-Tutorial", "url": "https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world", "type": "article", "level": "beginner"},
        {"title": "Flask REST API Patterns", "url": "https://flask.palletsprojects.com/en/stable/patterns/", "type": "docs", "level": "intermediate"},
    ],
    "Express.js Framework": [
        {"title": "Express Getting Started", "url": "https://expressjs.com/en/starter/installing.html", "type": "docs", "level": "beginner"},
        {"title": "Express Best Practices", "url": "https://expressjs.com/en/advanced/best-practice-performance.html", "type": "docs", "level": "intermediate"},
    ],
    "Spring Framework": [
        {"title": "Spring Quickstart", "url": "https://spring.io/quickstart", "type": "docs", "level": "beginner"},
        {"title": "Spring Boot Reference", "url": "https://docs.spring.io/spring-boot/reference/", "type": "docs", "level": "intermediate"},
    ],

    # ── Practices ─────────────────────────────────────────────────────
    "Error Handling": [
        {"title": "Error Handling Best Practices", "url": "https://docs.python.org/3/tutorial/errors.html", "type": "docs", "level": "beginner"},
        {"title": "Robust Error Handling Patterns", "url": "https://www.youtube.com/watch?v=ZsvftkbbrR0", "type": "video", "level": "intermediate"},
    ],
    "Automated Testing": [
        {"title": "Real Python – Testing Intro", "url": "https://realpython.com/python-testing/", "type": "article", "level": "beginner"},
        {"title": "Testing JavaScript (Kent C. Dodds)", "url": "https://testingjavascript.com/", "type": "course", "level": "intermediate"},
        {"title": "Advanced Testing Strategies", "url": "https://martinfowler.com/articles/practical-test-pyramid.html", "type": "article", "level": "advanced"},
    ],
    "Logging": [
        {"title": "Python Logging HOWTO", "url": "https://docs.python.org/3/howto/logging.html", "type": "docs", "level": "beginner"},
        {"title": "Structured Logging Best Practices", "url": "https://www.structlog.org/en/stable/", "type": "docs", "level": "intermediate"},
    ],
    "Static Typing": [
        {"title": "TypeScript Handbook", "url": "https://www.typescriptlang.org/docs/handbook/intro.html", "type": "docs", "level": "beginner"},
        {"title": "Python Type Hints (mypy)", "url": "https://mypy.readthedocs.io/en/stable/getting_started.html", "type": "docs", "level": "intermediate"},
        {"title": "Advanced TypeScript Patterns", "url": "https://www.totaltypescript.com/tutorials", "type": "course", "level": "advanced"},
    ],
    "Asynchronous Programming": [
        {"title": "JavaScript Promises & Async/Await", "url": "https://javascript.info/async", "type": "article", "level": "beginner"},
        {"title": "Python asyncio Guide", "url": "https://docs.python.org/3/library/asyncio.html", "type": "docs", "level": "intermediate"},
        {"title": "Concurrency Patterns in Depth", "url": "https://www.youtube.com/watch?v=olYdb0DdGtM", "type": "video", "level": "advanced"},
    ],
    "Code Documentation": [
        {"title": "Write the Docs Guide", "url": "https://www.writethedocs.org/guide/writing/beginners-guide-to-docs/", "type": "article", "level": "beginner"},
        {"title": "Documenting Python Code (Real Python)", "url": "https://realpython.com/documenting-python-code/", "type": "article", "level": "intermediate"},
    ],

    # ── Architecture & APIs ───────────────────────────────────────────
    "RESTful API Design": [
        {"title": "REST API Tutorial", "url": "https://restfulapi.net/", "type": "article", "level": "beginner"},
        {"title": "API Design Patterns (Google)", "url": "https://cloud.google.com/apis/design", "type": "docs", "level": "intermediate"},
        {"title": "Building Hypermedia APIs", "url": "https://www.oreilly.com/library/view/restful-web-apis/9781449359713/", "type": "course", "level": "advanced"},
    ],
    "Authentication & Authorization": [
        {"title": "OAuth 2.0 Simplified", "url": "https://aaronparecki.com/oauth-2-simplified/", "type": "article", "level": "beginner"},
        {"title": "JWT Handbook", "url": "https://auth0.com/resources/ebooks/jwt-handbook", "type": "article", "level": "intermediate"},
        {"title": "OWASP Authentication Cheatsheet", "url": "https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html", "type": "docs", "level": "advanced"},
    ],
    "Input Validation": [
        {"title": "OWASP Input Validation Cheatsheet", "url": "https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html", "type": "docs", "level": "beginner"},
        {"title": "Pydantic Validation Patterns", "url": "https://docs.pydantic.dev/latest/concepts/validators/", "type": "docs", "level": "intermediate"},
    ],
    "Middleware Pattern": [
        {"title": "Express Middleware Guide", "url": "https://expressjs.com/en/guide/using-middleware.html", "type": "docs", "level": "beginner"},
        {"title": "FastAPI Middleware", "url": "https://fastapi.tiangolo.com/tutorial/middleware/", "type": "docs", "level": "intermediate"},
    ],
    "Microservices Architecture": [
        {"title": "Microservices.io Patterns", "url": "https://microservices.io/patterns/index.html", "type": "article", "level": "intermediate"},
        {"title": "Building Microservices (Sam Newman)", "url": "https://samnewman.io/books/building_microservices_2nd_edition/", "type": "course", "level": "advanced"},
    ],
    "Model-View-Controller (MVC)": [
        {"title": "MVC Pattern Explained", "url": "https://developer.mozilla.org/en-US/docs/Glossary/MVC", "type": "article", "level": "beginner"},
    ],
    "CI/CD Practices": [
        {"title": "GitHub Actions Quickstart", "url": "https://docs.github.com/en/actions/quickstart", "type": "docs", "level": "beginner"},
        {"title": "CI/CD Best Practices", "url": "https://www.atlassian.com/continuous-delivery/principles/continuous-integration-vs-delivery-vs-deployment", "type": "article", "level": "intermediate"},
    ],
    "Containerization": [
        {"title": "Docker Getting Started", "url": "https://docs.docker.com/get-started/", "type": "docs", "level": "beginner"},
        {"title": "Dockerfile Best Practices", "url": "https://docs.docker.com/build/building/best-practices/", "type": "docs", "level": "intermediate"},
        {"title": "Kubernetes Basics", "url": "https://kubernetes.io/docs/tutorials/kubernetes-basics/", "type": "course", "level": "advanced"},
    ],
    "Version Control (Git)": [
        {"title": "Git Handbook (GitHub)", "url": "https://docs.github.com/en/get-started/using-git/about-git", "type": "docs", "level": "beginner"},
        {"title": "Pro Git Book", "url": "https://git-scm.com/book/en/v2", "type": "course", "level": "intermediate"},
    ],

    # ── Database ──────────────────────────────────────────────────────
    "SQL Database Queries": [
        {"title": "SQLBolt Interactive Tutorial", "url": "https://sqlbolt.com/", "type": "course", "level": "beginner"},
        {"title": "Advanced SQL (Mode Analytics)", "url": "https://mode.com/sql-tutorial/", "type": "course", "level": "intermediate"},
        {"title": "Use the Index, Luke (SQL Performance)", "url": "https://use-the-index-luke.com/", "type": "article", "level": "advanced"},
    ],
    "Object-Relational Mapping (ORM)": [
        {"title": "SQLAlchemy Tutorial", "url": "https://docs.sqlalchemy.org/en/20/tutorial/index.html", "type": "docs", "level": "beginner"},
        {"title": "Prisma Getting Started", "url": "https://www.prisma.io/docs/getting-started", "type": "docs", "level": "intermediate"},
    ],

    # ── Data Structures & Algorithms ──────────────────────────────────
    "Hash-based Data Structures": [
        {"title": "Hash Tables Explained (CS50)", "url": "https://www.youtube.com/watch?v=nvzVHwrrub0", "type": "video", "level": "beginner"},
        {"title": "Hashing Strategies & Collision Resolution", "url": "https://www.geeksforgeeks.org/hashing-set-2-separate-chaining/", "type": "article", "level": "intermediate"},
    ],
    "Tree Data Structures": [
        {"title": "Binary Trees (Visualgo)", "url": "https://visualgo.net/en/bst", "type": "course", "level": "beginner"},
        {"title": "Balanced BSTs & Red-Black Trees", "url": "https://www.cs.usfca.edu/~galles/visualization/RedBlack.html", "type": "course", "level": "advanced"},
    ],
    "Dynamic Programming": [
        {"title": "Dynamic Programming (MIT OCW)", "url": "https://www.youtube.com/watch?v=OQ5jsbhAv_M", "type": "video", "level": "intermediate"},
        {"title": "Competitive Programmer's Handbook (DP chapter)", "url": "https://cses.fi/book/book.pdf", "type": "course", "level": "advanced"},
    ],
    "Recursion": [
        {"title": "Recursion Explained (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=IJDJ0kBx2LM", "type": "video", "level": "beginner"},
        {"title": "Thinking Recursively in Python", "url": "https://realpython.com/python-thinking-recursively/", "type": "article", "level": "intermediate"},
    ],
    "Sorting Algorithms": [
        {"title": "Sorting Visualizations", "url": "https://visualgo.net/en/sorting", "type": "course", "level": "beginner"},
        {"title": "Sorting Algorithm Comparison", "url": "https://www.toptal.com/developers/sorting-algorithms", "type": "article", "level": "intermediate"},
    ],

    # ── Design Patterns ───────────────────────────────────────────────
    "Singleton Pattern": [
        {"title": "Refactoring Guru – Singleton", "url": "https://refactoring.guru/design-patterns/singleton", "type": "article", "level": "intermediate"},
    ],
    "Factory Pattern": [
        {"title": "Refactoring Guru – Factory Method", "url": "https://refactoring.guru/design-patterns/factory-method", "type": "article", "level": "intermediate"},
    ],
    "Observer Pattern": [
        {"title": "Refactoring Guru – Observer", "url": "https://refactoring.guru/design-patterns/observer", "type": "article", "level": "intermediate"},
    ],
    "Decorator Pattern": [
        {"title": "Refactoring Guru – Decorator", "url": "https://refactoring.guru/design-patterns/decorator", "type": "article", "level": "intermediate"},
        {"title": "Python Decorators (Real Python)", "url": "https://realpython.com/primer-on-python-decorators/", "type": "article", "level": "advanced"},
    ],
    "Strategy Pattern": [
        {"title": "Refactoring Guru – Strategy", "url": "https://refactoring.guru/design-patterns/strategy", "type": "article", "level": "intermediate"},
    ],

    # ── OOP ───────────────────────────────────────────────────────────
    "Inheritance": [
        {"title": "OOP in Python (Real Python)", "url": "https://realpython.com/inheritance-composition-python/", "type": "article", "level": "beginner"},
    ],
    "Polymorphism": [
        {"title": "Polymorphism in Python", "url": "https://realpython.com/python-classes/#polymorphism", "type": "article", "level": "intermediate"},
    ],
    "Encapsulation": [
        {"title": "Encapsulation in OOP", "url": "https://realpython.com/python-classes/#encapsulation", "type": "article", "level": "beginner"},
    ],

    # ── ML & Data Science ─────────────────────────────────────────────
    "Data Analysis (pandas)": [
        {"title": "10 Minutes to pandas", "url": "https://pandas.pydata.org/docs/user_guide/10min.html", "type": "docs", "level": "beginner"},
        {"title": "Pandas Cookbook", "url": "https://pandas.pydata.org/docs/user_guide/cookbook.html", "type": "docs", "level": "intermediate"},
    ],
    "Numerical Computing (NumPy)": [
        {"title": "NumPy Quickstart", "url": "https://numpy.org/doc/stable/user/quickstart.html", "type": "docs", "level": "beginner"},
        {"title": "NumPy for Data Science", "url": "https://numpy.org/doc/stable/user/absolute_beginners.html", "type": "docs", "level": "intermediate"},
    ],
    "Machine Learning (scikit-learn)": [
        {"title": "scikit-learn Tutorials", "url": "https://scikit-learn.org/stable/tutorial/index.html", "type": "docs", "level": "beginner"},
        {"title": "Hands-On ML (Aurélien Géron)", "url": "https://www.oreilly.com/library/view/hands-on-machine-learning/9781098125974/", "type": "course", "level": "intermediate"},
    ],
    "Deep Learning (PyTorch)": [
        {"title": "PyTorch Tutorials", "url": "https://pytorch.org/tutorials/", "type": "docs", "level": "intermediate"},
        {"title": "fast.ai Practical Deep Learning", "url": "https://course.fast.ai/", "type": "course", "level": "advanced"},
    ],
    "Deep Learning (TensorFlow)": [
        {"title": "TensorFlow Tutorials", "url": "https://www.tensorflow.org/tutorials", "type": "docs", "level": "intermediate"},
        {"title": "DeepLearning.AI TensorFlow Specialization", "url": "https://www.coursera.org/professional-certificates/tensorflow-in-practice", "type": "course", "level": "advanced"},
    ],
    "Data Visualization (matplotlib)": [
        {"title": "Matplotlib Tutorials", "url": "https://matplotlib.org/stable/tutorials/index.html", "type": "docs", "level": "beginner"},
        {"title": "Python Data Visualization Guide", "url": "https://realpython.com/python-matplotlib-guide/", "type": "article", "level": "intermediate"},
    ],
}


TIER_ORDER = ["beginner", "intermediate", "advanced"]


def get_next_tier(current_tier: str) -> str | None:
    """Return the tier above the current one, or None if already advanced."""
    try:
        idx = TIER_ORDER.index(current_tier)
    except ValueError:
        return "intermediate"
    if idx >= len(TIER_ORDER) - 1:
        return None
    return TIER_ORDER[idx + 1]


def get_resources_for_skill(skill_name: str, target_tier: str) -> list[ResourceEntry]:
    """Return resources for a skill at or above the target tier."""
    entries = RESOURCE_MAP.get(skill_name, [])
    if not entries:
        return []
    try:
        target_idx = TIER_ORDER.index(target_tier)
    except ValueError:
        target_idx = 0
    return [e for e in entries if TIER_ORDER.index(e.get("level", "beginner")) >= target_idx]
