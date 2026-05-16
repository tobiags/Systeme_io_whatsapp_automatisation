from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "templates_wati_final.json"


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def build_payload(meta: dict, template: dict) -> dict:
    return {
        "type": "template",
        "category": meta["category"],
        "subCategory": meta["subCategory"],
        "language": meta["language"],
        "elementName": template["name"],
        "header": {"type": "none"},
        "body": template["body"],
        "buttonsType": "none",
        "customParams": [
            {"paramName": var["name"], "paramValue": var["sample"]}
            for var in template["variables"]
        ],
        "creationMethod": 0,
    }


def get_existing(base_url: str, token: str) -> dict[str, dict]:
    response = requests.get(
        f"{base_url.rstrip('/')}/api/v2/getMessageTemplates",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=30,
    )
    response.raise_for_status()
    body = response.json()
    templates = body.get("messageTemplates", [])
    return {item["elementName"]: item for item in templates if "elementName" in item}


def submit(base_url: str, token: str, payload: dict) -> requests.Response:
    return requests.post(
        f"{base_url.rstrip('/')}/api/v1/whatsapp/templates",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit final Wati templates from manifest.")
    parser.add_argument("--apply", action="store_true", help="Actually submit to Wati.")
    parser.add_argument("--base-url", default=os.getenv("WATI_API_URL", ""))
    parser.add_argument("--token", default=os.getenv("WATI_API_TOKEN", ""))
    args = parser.parse_args()

    if not args.base_url or not args.token:
        print("Missing WATI_API_URL or WATI_API_TOKEN.", file=sys.stderr)
        return 2

    manifest = load_manifest()
    templates = manifest["templates"]
    meta = manifest["meta"]

    print(f"Checking existing templates on {args.base_url} ...")
    try:
        existing = get_existing(args.base_url, args.token)
    except requests.HTTPError as exc:
        print(f"Unable to list templates: {exc.response.status_code} {exc.response.text}", file=sys.stderr)
        return 3

    to_create: list[dict] = []
    for template in templates:
        payload = build_payload(meta, template)
        current = existing.get(template["name"])
        if current:
            current_body = (current.get("bodyOriginal") or current.get("body") or "").strip()
            if current_body == template["body"].strip():
                print(f"SKIP {template['name']} (already present with same body)")
                continue
            print(f"CONFLICT {template['name']} (already exists with different content)")
            continue
        to_create.append(payload)

    print(f"{len(to_create)} template(s) ready to create.")
    for payload in to_create:
        print(f"- {payload['elementName']}")

    if not args.apply:
        print("Dry-run complete. Re-run with --apply to submit.")
        return 0

    failures = 0
    for payload in to_create:
        response = submit(args.base_url, args.token, payload)
        if response.ok:
            print(f"CREATED {payload['elementName']}: {response.text}")
        else:
            failures += 1
            print(
                f"FAILED {payload['elementName']}: {response.status_code} {response.text}",
                file=sys.stderr,
            )

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
