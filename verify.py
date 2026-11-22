#!/usr/bin/env python3
"""
Verification Receipt Skill - Core verification logic
Produces frozen, dual-path verification receipts for AI agent claims.
"""

import json
import hashlib
import hmac
import time
import uuid
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import urllib.request
import urllib.error
import dns.resolver
import dns.exception


@dataclass
class ReadPathResult:
    method: str
    url: str = ""
    query: str = ""
    status: int = 0
    body_hash: str = ""
    answer: str = ""
    record_hash: str = ""
    error: str = ""
    timestamp_utc: str = ""

    def __post_init__(self):
        if not self.timestamp_utc:
            self.timestamp_utc = datetime.now(timezone.utc).isoformat()


@dataclass
class VerificationReceipt:
    claim: str
    timestamp_utc: str
    read_paths: List[ReadPathResult]
    verdict: str  # "verified" | "disputed" | "unverifiable"
    receipt_id: str
    verifier: str = "tallybexro/v1.0"

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    def to_file(self, path: str):
        with open(path, 'w') as f:
            f.write(self.to_json())


class Verifier:
    """Dual-path verification for AI agent claims."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def verify(self, claim: str, target: str, read_paths: List[str]) -> VerificationReceipt:
        """Run verification with two independent read paths."""
        # Freeze claim before any read
        frozen_claim = claim
        timestamp = datetime.now(timezone.utc).isoformat()
        receipt_id = f"vr-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}"

        results = []
        for path in read_paths:
            if path == "http":
                results.append(self._read_http(target))
            elif path == "dns":
                results.append(self._read_dns(target))
            elif path == "api":
                results.append(self._read_api(target))
            elif path == "ledger":
                results.append(self._read_ledger(target))
            else:
                results.append(ReadPathResult(method=path, error=f"Unknown path: {path}"))

        # Verdict from path agreement only
        verdict = self._derive_verdict(results)

        return VerificationReceipt(
            claim=frozen_claim,
            timestamp_utc=timestamp,
            read_paths=results,
            verdict=verdict,
            receipt_id=receipt_id
        )

    def _read_http(self, url: str) -> ReadPathResult:
        """HTTP GET with body hash."""
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'tallybexro-verifier/1.0'})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read()
                body_hash = "sha256:" + hashlib.sha256(body).hexdigest()
                return ReadPathResult(
                    method="http",
                    url=url,
                    status=resp.status,
                    body_hash=body_hash
                )
        except urllib.error.HTTPError as e:
            return ReadPathResult(method="http", url=url, status=e.code, error=str(e))
        except Exception as e:
            return ReadPathResult(method="http", url=url, status=0, error=str(e))

    def _read_dns(self, domain: str) -> ReadPathResult:
        """DNS lookup with record hash."""
        try:
            answers = dns.resolver.resolve(domain, 'A')
            records = [str(r) for r in answers]
            record_hash = "sha256:" + hashlib.sha256(','.join(sorted(records)).encode()).hexdigest()
            return ReadPathResult(
                method="dns",
                query=domain,
                answer=','.join(records),
                record_hash=record_hash,
                status=200
            )
        except dns.exception.DNSException as e:
            return ReadPathResult(method="dns", query=domain, status=0, error=str(e))
        except Exception as e:
            return ReadPathResult(method="dns", query=domain, status=0, error=str(e))

    def _read_api(self, url: str) -> ReadPathResult:
        """API endpoint read (same as HTTP but for explicit API paths)."""
        return self._read_http(url)

    def _read_ledger(self, url: str) -> ReadPathResult:
        """Ledger read path - expects JSON with balance/transactions."""
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'tallybexro-verifier/1.0'})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read()
                body_hash = "sha256:" + hashlib.sha256(body).hexdigest()
                # Try to parse as JSON for ledger-specific fields
                try:
                    data = json.loads(body.decode())
                    # Could extract specific ledger fields here
                except:
                    pass
                return ReadPathResult(
                    method="ledger",
                    url=url,
                    status=resp.status,
                    body_hash=body_hash
                )
        except Exception as e:
            return ReadPathResult(method="ledger", url=url, status=0, error=str(e))

    def _derive_verdict(self, results: List[ReadPathResult]) -> str:
        """Derive verdict from path agreement."""
        successful = [r for r in results if r.status == 200 and not r.error]
        if len(successful) < 2:
            return "unverifiable"
        # For now: if both paths succeed, verified
        # In practice, would compare specific fields
        return "verified"


if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Verify an AI agent claim")
    parser.add_argument("--claim", required=True, help="Claim text to verify")
    parser.add_argument("--target", required=True, help="Target URL or domain")
    parser.add_argument("--paths", nargs=2, default=["http", "dns"], help="Two read paths")
    parser.add_argument("--output", help="Output file for receipt")

    args = parser.parse_args()

    verifier = Verifier()
    receipt = verifier.verify(args.claim, args.target, args.paths)

    print(receipt.to_json())
    if args.output:
        receipt.to_file(args.output)
        print(f"Receipt written to {args.output}", file=sys.stderr)