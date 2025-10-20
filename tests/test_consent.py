from src.auth import consent

def test_request_consent_structure():
    result = consent.request_consent("user123", "LLM")
    assert result["service"] == "LLM"
    assert "privacy_notice" in result
    assert "agree" in result["options"]
    assert "decline" in result["options"]

def test_save_consent_yes():
    user_id = "user_yes"
    service = "LLM"
    consent.save_consent(user_id, service, True)

    stored = consent.get_consent(user_id, service)
    assert stored["consent_given"] is True
    assert stored["privacy_notice_version"] == "v1.0"
    assert consent.has_consent(user_id, service) is True
    assert "external services" in stored["privacy_notice"]

def test_save_consent_no():
    user_id = "user_no"
    service = "LLM"
    consent.save_consent(user_id, service, False)

    stored = consent.get_consent(user_id, service)
    assert stored["consent_given"] is False
    assert consent.has_consent(user_id, service) is False

def test_withdraw_consent():
    user_id = "user_withdraw"
    service = "LLM"
    consent.save_consent(user_id, service, True)
    assert consent.has_consent(user_id, service) is True

    consent.withdraw_consent(user_id, service)
    assert consent.has_consent(user_id, service) is False

def test_no_entry_defaults_to_false():
    assert consent.has_consent("unknown_user", "LLM") is False
