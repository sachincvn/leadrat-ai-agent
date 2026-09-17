"""Probe the live Leadrat API and print the response shape.

Run it once against a real tenant so the field mapping in
app/integrations/crm/leadrat/endpoints/get_all_leads.py can be tightened
to the actual response.

    set LEADRAT_JWT=<your token>        # PowerShell: $env:LEADRAT_JWT="..."
    python scripts/probe_leadrat.py

The token is read from the environment and never written to disk.
"""

import json
import os
import sys

import httpx

BASE_URL = os.getenv("LEADRAT_BASE_URL", "https://connect.leadrat.info")
PATH = "/api/v1/mcp/lead/new/all"


def main() -> int:
    jwt = os.getenv("LEADRAT_JWT", "").strip()
    if not jwt:
        print("Set LEADRAT_JWT first.")
        return 1

    sys.path.insert(0, os.getcwd())
    from app.core.jwt_claims import decode_claims

    claims = decode_claims(jwt)
    tenant = os.getenv("LEADRAT_TENANT") or claims.get("custom:tenant_id")
    print(f"tenant : {tenant}")
    print(f"user   : {claims.get('custom:user_id')}")

    resp = httpx.post(
        f"{BASE_URL}{PATH}",
        json={"pageNumber": 1, "pageSize": 3},
        headers={
            "Authorization": f"Bearer {jwt}",
            "tenant": tenant or "",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        timeout=60,
    )
    print(f"status : {resp.status_code}")
    if resp.status_code >= 400:
        print(resp.text[:600])
        return 1

    data = resp.json()
    print(f"envelope keys: {list(data) if isinstance(data, dict) else type(data).__name__}")

    from app.integrations.crm.leadrat.endpoints.get_all_leads import extract_rows

    rows = extract_rows(data)
    print(f"rows   : {len(rows)}")
    if rows:
        print("\nfields on the first row:")
        for key, value in rows[0].items():
            preview = str(value)
            if len(preview) > 60:
                preview = preview[:57] + "..."
            print(f"  {key:35} {preview}")
        print("\nfirst row as JSON:")
        print(json.dumps(rows[0], indent=2, default=str)[:3000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
