import requests
import time
from typing import Dict, List
import json

# =========================
# CONFIG: APIs to test
# =========================
API_ENDPOINTS = [
        'https://covid19-1.ireceptor.org',
        'https://covid19-2.ireceptor.org',
        'https://covid19-3.ireceptor.org',
        'https://covid19-4.ireceptor.org', #Connection Error
        'https://ipa1.ireceptor.org',
        'https://ipa2.ireceptor.org',
        'https://ipa3.ireceptor.org',
        'https://ipa4.ireceptor.org',
        'https://ipa5.ireceptor.org', # Connection Error
        'https://ipa6.ireceptor.org',
        'https://vdjserver.org',
        'https://scireptor.dkfz.de', # HTTP 503
        'https://airr-seq.vdjbase.org', # Connection Error
        'https://roche-airr.ireceptor.org', # Connection Error
        'https://t1d-1.ireceptor.org',
        'https://agschwab.uni-muenster.de',
        'http://127.0.0.1:5000' # HTTP 403
]

TIMEOUT = 10  # seconds


# =========================
# AIRR API test
# =========================
def test_airr_api(base_url):
    result = {
        "base_url": base_url,
        "status": "UNKNOWN",
        "status_code": None,
        "response_time": None,
        "error": None
    }

    # endpoint
    test_url = f"{base_url}/airr/v1/repertoire"

    payload = {
        "size": 1 
    }

    try:
        start = time.time()

        response = requests.post(
            test_url,
            json=payload,
            timeout=TIMEOUT
        )

        end = time.time()

        result["status_code"] = response.status_code
        result["response_time"] = round(end - start, 3)

        if response.status_code == 200:
            try:
                data = response.json()

                if "Repertoire" in data or "repertoire" in data:
                    result["status"] = "OK"
                else:
                    result["status"] = "WARNING"
                    result["error"] = "Invalid AIRR response format"

            except Exception:
                result["status"] = "FAILED"
                result["error"] = "Invalid JSON"

        else:
            result["status"] = "FAILED"
            result["error"] = f"HTTP {response.status_code}"

    except requests.exceptions.Timeout:
        result["status"] = "FAILED"
        result["error"] = "Timeout"

    except requests.exceptions.ConnectionError:
        result["status"] = "FAILED"
        result["error"] = "Connection Error"

    except Exception as e:
        result["status"] = "FAILED"
        result["error"] = str(e)

    return result


# =========================
# Run all tests
# =========================
def run_tests():
    results = []

    print("\n=== AIRR API Health Check ===\n")

    for api in API_ENDPOINTS:
        print(f"Testing: {api}")

        res = test_airr_api(api)
        results.append(res)

        print(f"  Status: {res['status']}")
        print(f"  Code: {res['status_code']}")
        print(f"  Time: {res['response_time']}s")

        if res["error"]:
            print(f"  Error: {res['error']}")

        print("-" * 40)

    return results


# =========================
# Summary (for Jenkins)
# =========================
def summarize(results):
    failed = [r for r in results if r["status"] == "FAILED"]
    warning = [r for r in results if r["status"] == "WARNING"]

    print("\n=== SUMMARY ===")
    print(f"Total APIs: {len(results)}")
    print(f"Failed: {len(failed)}")
    print(f"Warning: {len(warning)}")

    if failed:
        print("\n❌ Failed APIs:")
        for r in failed:
            print(f"- {r['base_url']} ({r['error']})")

    if warning:
        print("\n⚠️ Warning APIs:")
        for r in warning:
            print(f"- {r['base_url']} ({r['error']})")

    with open("api_health_results.json", "w") as f:
        json.dump(results, f, indent=2)

    if failed:
        exit(1)
    else:
        exit(0)


# =========================
# Main
# =========================
if __name__ == "__main__":
    results = run_tests()
    summarize(results)