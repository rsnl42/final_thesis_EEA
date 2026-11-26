#!/usr/bin/env python3
"""
scripts/verify_dpg_urls.py
==========================
Automated health-check and verification script for the Vetted Resilient Solutions Directory.

Capabilities:
1. Pings all registered URLs with browser-realistic headers.
2. Follows redirects and detects permanent 301 domain shifts.
3. Performs content-signature verification to ensure domains are not parked or squatted.
4. Updates data/resources_registry.json with verified status, HTTP code, latency, and real timestamp.
5. Generates a structured markdown verification audit report.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
import ssl
from datetime import datetime, timezone

REGISTRY_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'resources_registry.json')
REPORT_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'last_link_verification_report.md')

MAX_RETRIES = 2
INITIAL_BACKOFF = 3.0
INTER_REQUEST_DELAY = 1.0
MAX_CONSECUTIVE_FAILURES = 3

PARKED_DOMAIN_INDICATORS = [
    "domain for sale",
    "buy this domain",
    "parked domain",
    "hugedomains",
    "godaddy parked",
    "namecheap parking",
    "under construction"
]

def create_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def check_url(url, signature_keywords=None, timeout=12, max_retries=MAX_RETRIES):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }
    ctx = create_ssl_context()
    
    start_time = time.time()
    last_error = None
    last_status = 0
    last_latency = 0

    for attempt in range(max_retries + 1):
        req = urllib.request.Request(url, headers=headers)
        attempt_start = time.time()
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
                latency_ms = int((time.time() - start_time) * 1000)
                status_code = response.status
                final_url = response.url
                
                # Read first 128KB of page to check signature / parking
                html_snippet = response.read(131072).decode('utf-8', errors='ignore').lower()
                
                # Check for domain squatter / parking indicators
                is_parked = any(indicator in html_snippet for indicator in PARKED_DOMAIN_INDICATORS)
                
                # Check for signature keywords if provided
                signature_matched = True
                if signature_keywords:
                    signature_matched = any(kw.lower() in html_snippet for kw in signature_keywords)
                
                is_healthy = (status_code == 200) and not is_parked and signature_matched
                
                warning = None
                if is_parked:
                    warning = "Warning: Page text matched domain parking keywords."
                elif not signature_matched and signature_keywords:
                    warning = f"Warning: Content did not contain expected signature keywords ({signature_keywords})."
                elif final_url.rstrip('/') != url.rstrip('/'):
                    warning = f"Notice: Permanent redirect to {final_url}"

                return {
                    "accessible": is_healthy,
                    "status_code": status_code,
                    "latency_ms": latency_ms,
                    "final_url": final_url,
                    "redirected": (final_url.rstrip('/') != url.rstrip('/')),
                    "warning": warning,
                    "error": None
                }
        except urllib.error.HTTPError as e:
            last_latency = int((time.time() - attempt_start) * 1000)
            last_status = e.code
            last_error = f"HTTP Error {e.code}: {e.reason}"
            # Only retry server errors or rate limiting (429)
            if e.code in (429, 500, 502, 503, 504) and attempt < max_retries:
                retry_after = INITIAL_BACKOFF * (attempt + 1)
                retry_header = e.headers.get("Retry-After") if hasattr(e, "headers") else None
                if retry_header:
                    try:
                        retry_after = min(float(retry_header), 15.0)
                    except (ValueError, TypeError):
                        pass
                time.sleep(retry_after)
                continue
            # For 4xx (404, 401, 403), fail immediately without bombarding
            break
        except urllib.error.URLError as e:
            last_latency = int((time.time() - attempt_start) * 1000)
            last_status = 0
            last_error = f"Network Error: {e.reason}"
            if attempt < max_retries:
                time.sleep(INITIAL_BACKOFF * (attempt + 1))
                continue
            break
        except Exception as e:
            last_latency = int((time.time() - attempt_start) * 1000)
            last_status = 0
            last_error = str(e)
            if attempt < max_retries:
                time.sleep(INITIAL_BACKOFF * (attempt + 1))
                continue
            break

    total_latency_ms = int((time.time() - start_time) * 1000)
    return {
        "accessible": False,
        "status_code": last_status,
        "latency_ms": total_latency_ms or last_latency,
        "final_url": url,
        "redirected": False,
        "warning": None,
        "error": last_error or "Unknown failure after retries"
    }

def run_verification():
    if not os.path.exists(REGISTRY_PATH):
        print(f"Registry not found at {REGISTRY_PATH}")
        sys.exit(1)

    with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
        registry = json.load(f)

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"Starting verification of {len(registry)} educational resources on {today_str}...\n")

    results = []
    has_critical_failures = False
    has_transient_warnings = False

    for item in registry:
        name = item.get("title")
        url = item.get("url")
        sig_kw = item.get("signature_keywords", [])
        consecutive = item.get("consecutive_failures", 0)
        
        print(f"Testing [{item.get('id')}]: {name} -> {url}")
        res = check_url(url, signature_keywords=sig_kw)
        
        item["last_verified_date"] = today_str
        item["http_status"] = res["status_code"]
        item["latency_ms"] = res["latency_ms"]

        if res["accessible"]:
            item["consecutive_failures"] = 0
            item["status"] = "active"
            if res["warning"]:
                item["verification_note"] = res["warning"]
            else:
                item["verification_note"] = "Fully verified active."
        else:
            consecutive += 1
            item["consecutive_failures"] = consecutive
            item["verification_note"] = res["error"]
            if consecutive >= MAX_CONSECUTIVE_FAILURES:
                item["status"] = "offline"
                has_critical_failures = True
                print(f"::error title=Persistent Resource Failure::{name} ({url}) has failed {consecutive} consecutive checks! Manual debugging required.")
            else:
                item["status"] = "degraded"
                has_transient_warnings = True
                print(f"::warning title=Temporary Resource Hiccup::{name} ({url}) failed check ({consecutive}/{MAX_CONSECUTIVE_FAILURES} runs). Will retry on next scheduled run.")

        if res["redirected"] and res["accessible"]:
            item["suggested_canonical_url"] = res["final_url"]

        results.append({
            "item": item,
            "check": res
        })
        print(f"  -> Status {res['status_code']} ({res['latency_ms']}ms) - Active: {res['accessible']} (Consecutive fails: {item.get('consecutive_failures', 0)})\n")

        # Polite delay between items to avoid hammering servers or being flagged
        time.sleep(INTER_REQUEST_DELAY)

    # Save updated registry
    with open(REGISTRY_PATH, 'w', encoding='utf-8') as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)
    print(f"Updated registry saved to {REGISTRY_PATH}")

    # Generate Markdown Report
    run_timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')
    report_lines = [
        f"# Automated Resource Verification Audit Report",
        f"**Run Timestamp:** {run_timestamp}",
        f"**Total Resources Tested:** {len(registry)}",
        f"**Health Summary:** {'🔴 Critical Outages Detected' if has_critical_failures else ('🟡 Transient Glitches Noted (Retrying)' if has_transient_warnings else '🟢 All Systems Healthy')}\n",
        f"| Resource | Scope | URL | HTTP Status | Latency | Health Status | Consecutive Fails | Notes |",
        f"| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |"
    ]

    for r in results:
        it = r["item"]
        ch = r["check"]
        fails = it.get("consecutive_failures", 0)
        if ch["accessible"]:
            status_icon = "🟢 Active"
        elif fails >= MAX_CONSECUTIVE_FAILURES:
            status_icon = f"🔴 Offline ({fails}/{MAX_CONSECUTIVE_FAILURES})"
        else:
            status_icon = f"🟡 Degraded ({fails}/{MAX_CONSECUTIVE_FAILURES})"

        notes = ch["warning"] or ch["error"] or "Verified OK"
        report_lines.append(
            f"| **{it['title']}** | {it.get('scope', 'Global')} | [`{it['url']}`]({it['url']}) | `{ch['status_code']}` | `{ch['latency_ms']}ms` | {status_icon} | `{fails}` | {notes} |"
        )

    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines) + '\n')
    print(f"Audit report generated at {REPORT_PATH}\n")

    return not has_critical_failures

if __name__ == '__main__':
    success = run_verification()
    sys.exit(0 if success else 1)
