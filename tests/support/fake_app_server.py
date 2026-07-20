from __future__ import annotations

import json
import sys
import time


MODE = sys.argv[1]

for line in sys.stdin:
    message = json.loads(line)
    method = message.get("method")
    request_id = message.get("id")

    if method == "initialize":
        print(json.dumps({"id": request_id, "result": {"userAgent": "fake"}}), flush=True)
    elif method == "initialized":
        continue
    elif method == "account/read":
        if MODE == "account-error":
            print(
                json.dumps(
                    {
                        "id": request_id,
                        "error": {"code": -32001, "message": "account unavailable"},
                    }
                ),
                flush=True,
            )
        else:
            print(
                json.dumps(
                    {
                        "id": request_id,
                        "result": {
                            "account": {
                                "email": "codex@example.com",
                                "planType": "plus",
                            }
                        },
                    }
                ),
                flush=True,
            )
    elif method == "account/rateLimits/read":
        if MODE == "silent":
            time.sleep(5)
        elif MODE == "error":
            print(
                json.dumps(
                    {
                        "id": request_id,
                        "error": {"code": -32001, "message": "not authenticated"},
                    }
                ),
                flush=True,
            )
        else:
            print(
                json.dumps(
                    {"method": "account/rateLimits/updated", "params": {"ignored": True}}
                ),
                flush=True,
            )
            print(
                json.dumps(
                    {
                        "id": request_id,
                        "result": {
                            "rateLimits": {
                                "primary": {
                                    "usedPercent": 26,
                                    "windowDurationMins": 10080,
                                    "resetsAt": 1784545373,
                                },
                                "secondary": {
                                    "usedPercent": 62,
                                    "windowDurationMins": 300,
                                    "resetsAt": 1784520000,
                                },
                            }
                        },
                    }
                ),
                flush=True,
            )
