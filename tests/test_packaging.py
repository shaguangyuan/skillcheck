from pathlib import Path


def test_project_distribution_and_primary_command_are_skillcheck():
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert 'name = "skillcheck"' in pyproject
    assert 'skillcheck = "skill_health.cli:main"' in pyproject


def test_legacy_skill_health_command_remains_as_alias():
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert 'skill-health = "skill_health.cli:main"' in pyproject
