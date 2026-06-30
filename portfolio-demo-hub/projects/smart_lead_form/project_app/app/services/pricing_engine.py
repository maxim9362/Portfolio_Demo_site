# Loads client pricing rules and calculates generic estimate responses.

import json
from json import JSONDecodeError
from pathlib import Path


CLIENTS_DIR = Path(__file__).resolve().parents[1] / "clients"


def load_pricing_rules(client_id: str) -> dict:
    """Load pricing rules for a client."""
    path = CLIENTS_DIR / client_id / "pricing_rules.json"

    if not path.exists():
        raise FileNotFoundError(f"Pricing rules file not found: {path}")

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in pricing rules file: {path}") from exc


def rule_matches(rule: dict, answers: dict) -> bool:
    """Check whether all rule conditions match the current answers."""
    conditions = rule.get("when", {})
    return all(answers.get(key) == value for key, value in conditions.items())


def find_best_rule(rules: list[dict], answers: dict) -> dict | None:
    """Return the matching rule with the highest priority."""
    matching_rules = [rule for rule in rules if rule_matches(rule, answers)]

    if not matching_rules:
        return None

    return sorted(matching_rules, key=lambda rule: rule.get("priority", 0), reverse=True)[0]


def calculate_estimate(client_id: str, answers: dict) -> dict:
    """Calculate an estimate response from configured pricing rules."""
    pricing_config = load_pricing_rules(client_id)
    best_rule = find_best_rule(pricing_config.get("rules", []), answers)

    if best_rule:
        return {
            "estimated_price_min": best_rule.get("price_min"),
            "estimated_price_max": best_rule.get("price_max"),
            "currency": pricing_config.get("currency"),
            "estimate_message": best_rule.get("estimate_message"),
            "disclaimer": pricing_config.get("disclaimer"),
        }

    return {
        "estimated_price_min": None,
        "estimated_price_max": None,
        "currency": pricing_config.get("currency"),
        "estimate_message": pricing_config.get("default_estimate_message"),
        "disclaimer": pricing_config.get("disclaimer"),
    }
