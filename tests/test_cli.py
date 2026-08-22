from orbit.cli import build_parser, main


def test_parser_exposes_developer_commands() -> None:
    parser = build_parser()
    assert parser.parse_args(["health"]).command == "health"
    assert parser.parse_args(["models", "--json"]).json is True


def test_models_command_supports_json(capsys, monkeypatch, tmp_path) -> None:
    from orbit.core import config as config_module

    monkeypatch.setattr(config_module.OrbitConfig, "default", lambda: config_module.OrbitConfig(home=tmp_path))
    assert main(["models", "--json"]) == 0
    assert capsys.readouterr().out.strip() == "[]"


def test_health_command_returns_success(capsys, monkeypatch, tmp_path) -> None:
    from orbit.core import config as config_module

    monkeypatch.setattr(config_module.OrbitConfig, "default", lambda: config_module.OrbitConfig(home=tmp_path))
    assert main(["health"]) == 0
    assert "healthy" in capsys.readouterr().out
