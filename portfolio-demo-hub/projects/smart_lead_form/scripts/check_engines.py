# Runs a manual check for the form and pricing engines.

import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.form_engine import get_visible_steps, load_form_config
from app.services.pricing_engine import calculate_estimate


def print_step_keys(title: str, steps: list[dict]) -> None:
    print(title)
    print(f"count: {len(steps)}")
    print("keys:", ", ".join(step["key"] for step in steps))
    print()


def main() -> None:
    client_id = "notary_demo"
    form_config = load_form_config(client_id)

    print(f"all_steps: {len(form_config['steps'])}")
    print()

    print_step_keys("visible_steps_empty_answers", get_visible_steps(client_id, {}))
    print_step_keys(
        "visible_steps_notary_translation",
        get_visible_steps(client_id, {"service_type": "notary_translation"}),
    )

    translation_estimate = calculate_estimate(
        client_id,
        {
            "service_type": "notary_translation",
            "page_count": "1",
        },
    )
    print("estimate_notary_translation_page_1")
    print(json.dumps(translation_estimate, ensure_ascii=True, indent=2))
    print()

    apostille_estimate = calculate_estimate(client_id, {"service_type": "apostille"})
    print("estimate_apostille")
    print(json.dumps(apostille_estimate, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
