#!/usr/bin/env python3
"""
Download repertoire data for a study from healthy AIRR APIs.

Reads api_health_results.json (written by api_test.py) from the repo root
to skip any endpoint that returned FAILED status (connection error, timeout,
HTTP error, etc.).  Exits non-zero on fatal errors so Jenkins fails fast.

Usage:
    python3 scripts/download_study.py --study-id PRJNA349143 --outdir /path/to/data
"""
import argparse
import json
import os
import sys

os.environ['GEVENT_SUPPORT'] = 'True'

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import pandas as pd
from collect import collect_repertoires_and_count_rearrangements, download_study


def load_healthy_repos():
    health_file = os.path.join(REPO_ROOT, 'api_health_results.json')
    if not os.path.exists(health_file):
        print(f"WARNING: {health_file} not found — using full repo list")
        return None  # caller will use fallback

    with open(health_file) as f:
        health_data = json.load(f)

    healthy = [r['base_url'] for r in health_data if r.get('status') in ('OK', 'WARNING')]
    failed  = [r['base_url'] for r in health_data if r.get('status') == 'FAILED']

    if failed:
        print(f"Skipping {len(failed)} FAILED API(s):")
        for url in failed:
            print(f"  - {url}")

    return healthy


FALLBACK_REPOS = [
    'https://covid19-1.ireceptor.org',
    'https://covid19-2.ireceptor.org',
    'https://covid19-3.ireceptor.org',
    'https://covid19-4.ireceptor.org',
    'https://ipa1.ireceptor.org',
    'https://ipa2.ireceptor.org',
    'https://ipa3.ireceptor.org',
    'https://ipa4.ireceptor.org',
    'https://ipa5.ireceptor.org',
    'https://ipa6.ireceptor.org',
    'https://vdjserver.org',
    'https://scireptor.dkfz.de',
    'https://airr-seq.vdjbase.org',
    'https://roche-airr.ireceptor.org',
    'https://t1d-1.ireceptor.org',
    'https://agschwab.uni-muenster.de',
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study-id', required=True, help='AIRR study / project ID')
    parser.add_argument('--outdir',   required=True, help='Parent download directory')
    args = parser.parse_args()

    healthy_repos = load_healthy_repos() or FALLBACK_REPOS

    if not healthy_repos:
        print("ERROR: All APIs are unhealthy — cannot download data")
        sys.exit(1)

    print(f"Querying {len(healthy_repos)} healthy repo(s) for study: {args.study_id}")
    repo_df = pd.DataFrame(healthy_repos, columns=['URL'])

    results = collect_repertoires_and_count_rearrangements(repo_df, args.study_id)
    repertoires = results.get('Repertoire', [])

    if not repertoires:
        print(f"ERROR: No repertoires found for study {args.study_id}")
        sys.exit(1)

    print(f"Found {len(repertoires)} repertoire(s). Starting download...")
    resp = download_study(args.study_id, repertoires, args.outdir)
    print("Download complete:", resp)


if __name__ == '__main__':
    main()
