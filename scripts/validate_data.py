#!/usr/bin/env python3
"""
Validate downloaded study data before downstream processing.

Checks performed:
  1. Study directory exists
  2. At least one .tsv.gz rearrangement file is present and non-empty
  3. metadata.json is present, non-empty, and contains Repertoire entries

Exits with code 1 on any failure so Jenkins terminates the pipeline immediately.

Usage:
    python3 scripts/validate_data.py --study-dir /path/to/data/PRJNA349143
"""
import argparse
import json
import os
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study-dir', required=True, help='Downloaded study directory to validate')
    args = parser.parse_args()

    study_dir = args.study_dir
    errors = []

    if not os.path.isdir(study_dir):
        print(f"FAIL: study directory does not exist: {study_dir}")
        sys.exit(1)

    all_files = []
    for root, _, files in os.walk(study_dir):
        for fname in files:
            all_files.append(os.path.join(root, fname))

    if not all_files:
        print(f"FAIL: no files found in {study_dir}")
        sys.exit(1)

    # Every file must be non-empty
    for fpath in all_files:
        if os.path.getsize(fpath) == 0:
            errors.append(f"empty file: {fpath}")

    # Rearrangement data files
    data_files = [f for f in all_files if f.endswith('.tsv.gz')]
    if not data_files:
        errors.append("no .tsv.gz rearrangement files found")

    # metadata.json
    meta_path = os.path.join(study_dir, 'metadata.json')
    if not os.path.exists(meta_path):
        errors.append("metadata.json not found")
    elif os.path.getsize(meta_path) == 0:
        errors.append("metadata.json is empty")
    else:
        try:
            with open(meta_path) as f:
                meta = json.load(f)
            if not meta.get('Repertoire'):
                errors.append("metadata.json contains no Repertoire entries")
        except json.JSONDecodeError as e:
            errors.append(f"metadata.json is not valid JSON: {e}")

    if errors:
        print("VALIDATION FAILED:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print(f"OK: {len(data_files)} .tsv.gz file(s) + metadata.json validated in {study_dir}")


if __name__ == '__main__':
    main()
