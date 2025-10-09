# scanner/project_detector.py
# Determines project boundaries and metadata.
# - Identify project type (individual vs collaborative)
# - Detect config files: requirements.txt, package.json, pom.xml, etc.
# - Classify coding vs document vs media projects