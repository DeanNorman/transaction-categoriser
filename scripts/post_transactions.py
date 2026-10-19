#!/usr/bin/env python3
"""Feed a CSV of transactions through the public API, one POST /transactions per row, the way an integration would.

    python3 scripts/post_transactions.py --base-url http://localhost:8000 data/transaction_history.csv

Standard library only. Prints created, conflicts (the ID was already there) and rejected rows (with the field errors
the API returned). The server does the validating and the categorising; this script only posts.
"""

import argparse
import csv
import json
import sys
import urllib.error
import urllib.request

COLUMNS = {
    "Transaction ID": "id",
    "Amount": "amount",
    "Timestamp": "timestamp",
    "Description": "description",
    "Transaction Type": "transaction_type",
    "Account Number": "account_number",
}


def rows_from(path):
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = [name for name in COLUMNS if name not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(f"missing columns: {', '.join(missing)}")
        for number, raw in enumerate(reader, start=2):
            yield number, {field: (raw.get(name) or "").strip() for name, field in COLUMNS.items()}


def post(base_url, body, timeout):
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/transactions",
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json", "accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        payload = error.read()
        try:
            return error.code, json.loads(payload or b"{}")
        except json.JSONDecodeError:
            return error.code, {"detail": payload.decode(errors="replace")[:200]}


def post_file(path, base_url, limit=None, timeout=10.0, log=None):
    report = {"created": 0, "conflicts": 0, "rejected": 0, "failed": 0, "rejected_rows": []}
    for count, (number, body) in enumerate(rows_from(path), start=1):
        if limit is not None and count > limit:
            break
        status, answer = post(base_url, body, timeout)
        if status == 201:
            report["created"] += 1
            if log:
                log(f"row {number}: {answer['id']} -> {answer['category']} ({answer['method']}, {answer['confidence']})")
        elif status == 409:
            report["conflicts"] += 1
        elif status == 400:
            report["rejected"] += 1
            if len(report["rejected_rows"]) < 20:
                report["rejected_rows"].append({"row": number, "errors": answer})
        else:
            report["failed"] += 1
            if log:
                log(f"row {number}: HTTP {status} {answer}")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("csv")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--limit", type=int, default=None, help="Post only the first N rows.")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--quiet", action="store_true", help="Only the summary.")
    args = parser.parse_args(argv)
    try:
        report = post_file(args.csv, args.base_url, args.limit, args.timeout, log=None if args.quiet else print)
    except urllib.error.URLError as error:
        raise SystemExit(f"could not reach {args.base_url}: {error.reason}")
    print(json.dumps(report, indent=2))
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
