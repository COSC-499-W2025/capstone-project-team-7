from backend.src.cli.services.portfolio_timeline_service import PortfolioTimelineService


class FakeProjectsService:
    def __init__(self, projects, projects_with_scan):
        self._projects = projects
        self._projects_with_scan = projects_with_scan

    def get_user_projects(self, user_id):
        return list(self._projects)

    def get_user_projects_with_scan_data(self, user_id):
        return list(self._projects_with_scan)


def test_projects_timeline_ordering_is_deterministic():
    projects = [
        {
            "id": "b",
            "project_name": "Beta",
            "scan_timestamp": "2024-02-01T00:00:00Z",
            "project_end_date": None,
            "created_at": None,
        },
        {
            "id": "a",
            "project_name": "Alpha",
            "scan_timestamp": "2024-02-01T00:00:00Z",
            "project_end_date": None,
            "created_at": None,
        },
        {
            "id": "c",
            "project_name": "Gamma",
            "scan_timestamp": "2024-01-15T00:00:00Z",
            "project_end_date": None,
            "created_at": None,
        },
    ]
    service = PortfolioTimelineService(
        projects_service=FakeProjectsService(projects, [])
    )
    items = service.get_projects_timeline("user-1")
    assert [item["project_id"] for item in items] == ["c", "a", "b"]


def test_skills_timeline_ordering_and_aggregation():
    projects_with_scan = [
        {
            "id": "1",
            "project_name": "Alpha",
            "scan_data": {
                "skills_progress": {
                    "timeline": [
                        {
                            "period_label": "2024-02",
                            "commits": 5,
                            "top_skills": ["B", "A"],
                        },
                        {
                            "period_label": "2024-01",
                            "commits": 2,
                            "top_skills": ["C"],
                        },
                    ]
                }
            },
        },
        {
            "id": "2",
            "project_name": "Beta",
            "scan_data": {
                "skills_analysis": {
                    "chronological_overview": [
                        {
                            "period": "2024-01",
                            "skills_exercised": ["D", "A"],
                        }
                    ]
                }
            },
        },
    ]
    service = PortfolioTimelineService(
        projects_service=FakeProjectsService([], projects_with_scan)
    )
    items = service.get_skills_timeline("user-1")
    assert [item["period_label"] for item in items] == ["2024-01", "2024-02"]
    assert items[0]["skills"] == ["A", "C", "D"]
    assert items[0]["commits"] == 2
    assert items[0]["projects"] == ["Alpha", "Beta"]
    assert items[1]["skills"] == ["A", "B"]
    assert items[1]["commits"] == 5
    assert items[1]["projects"] == ["Alpha"]
