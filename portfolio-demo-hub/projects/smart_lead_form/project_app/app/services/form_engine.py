# Loads client form configuration and resolves visible form steps.

import json
from json import JSONDecodeError
from pathlib import Path


CLIENTS_DIR = Path(__file__).resolve().parents[1] / "clients"


def _load_json_file(path: Path) -> dict:
    """Load a JSON file and raise a clear error if it cannot be read."""
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in config file: {path}") from exc


def load_form_config(client_id: str) -> dict:
    """Load the form configuration for a client."""
    return _load_json_file(CLIENTS_DIR / client_id / "form_config.json")


def load_ui_texts(client_id: str) -> dict:
    """Load UI texts for a client."""
    return _load_json_file(CLIENTS_DIR / client_id / "ui_texts.json")


def condition_matches(condition: dict, answers: dict) -> bool:
    """Check whether one condition matches the current answers."""
    key = condition.get("key")
    expected_value = condition.get("equals")

    if key not in answers:
        return False

    return answers[key] == expected_value


def step_is_visible(step: dict, answers: dict) -> bool:
    """Check whether a form step should be visible for the current answers."""
    show_if = step.get("show_if")
    show_if_any = step.get("show_if_any")

    if not show_if and not show_if_any:
        return True

    if show_if:
        return condition_matches(show_if, answers)

    if show_if_any:
        return any(condition_matches(condition, answers) for condition in show_if_any)

    return False


def get_visible_steps(client_id: str, answers: dict) -> list[dict]:
    """Return form steps visible for the current answers."""
    form_config = load_form_config(client_id)
    return [step for step in form_config.get("steps", []) if step_is_visible(step, answers)]


def get_form_config_response(client_id: str) -> dict:
    """Return form configuration, UI texts, and initially visible steps."""
    form_config = load_form_config(client_id)
    ui_texts = load_ui_texts(client_id)

    return {
        **form_config,
        "ui_texts": ui_texts,
        "visible_steps": get_visible_steps(client_id, {}),
    }
