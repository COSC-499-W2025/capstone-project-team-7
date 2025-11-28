from backend.src.cli.screens import SignupSubmitted

def test_signup_submitted_event_fields():
    event = SignupSubmitted("test@example.com", "password123")
    assert event.email == "test@example.com"
    assert event.password == "password123"