from utils.automation_profiles import AutomationProfiles, TriggerType, ActionType


def test_validate_rule_invalid_trigger():
    rule = {
        "name": "Bad Trigger",
        "trigger": "nope",
        "action": ActionType.SET_POWER_PROFILE.value,
        "action_params": {"profile": "balanced"},
        "enabled": True,
    }
    result = AutomationProfiles.validate_rule(rule)
    assert result["success"] is False
    assert "Invalid trigger" in " ".join(result["errors"])


def test_validate_rule_missing_command():
    rule = {
        "name": "Run Command",
        "trigger": TriggerType.ON_STARTUP.value,
        "action": ActionType.RUN_COMMAND.value,
        "action_params": {},
        "enabled": True,
    }
    result = AutomationProfiles.validate_rule(rule)
    assert result["success"] is False
    assert "command" in " ".join(result["errors"])


def test_simulate_rules_returns_results(tmp_path, monkeypatch):
    # Use temp config file
    AutomationProfiles.CONFIG_DIR = tmp_path
    AutomationProfiles.CONFIG_FILE = tmp_path / "automation.json"
    AutomationProfiles.save_config({
        "enabled": True,
        "rules": [
            {
                "id": "t1",
                "name": "Battery Saver",
                "trigger": TriggerType.ON_BATTERY.value,
                "action": ActionType.SET_POWER_PROFILE.value,
                "action_params": {"profile": "power-saver"},
                "enabled": True,
            }
        ]
    })

    result = AutomationProfiles.simulate_rules_for_trigger(TriggerType.ON_BATTERY.value)
    assert result["success"] is True
    assert len(result["results"]) == 1
