#!/usr/bin/env python3
"""
Validate downloaded study data before downstream processing.

Auto-detects what was downloaded and validates accordingly:
  - AIRR rearrangement data (.tsv.gz + metadata.json) if present
  - ENA FASTQ data (.fastq.gz files under raw_seq/) if present

At least one of the two must be present.
Exits with code 1 on any failure so Jenkins terminates the pipeline immediately.

Usage:
    python3 scripts/validate_data.py --study-dir /path/to/data/PRJNA349143
"""
import argparse
import json
import os
import sys


def validate_airr(study_dir, errors):
    tsv_files = [
        os.path.join(r, f)
        for r, _, files in os.walk(study_dir)
        for f in files
        if f.endswith('.tsv.gz') and 'raw_seq' not in r
    ]
    if not tsv_files:
        errors.append("no .tsv.gz rearrangement files found")
        return

    for fpath in tsv_files:
        if os.path.getsize(fpath) == 0:
            errors.append(f"empty file: {fpath}")

    meta_path = os.path.join(study_dir, 'metadata.json')
    if not os.path.exists(meta_path):
        # metadata may have been moved to project_metadata/ by create_projects_structure
        meta_path = os.path.join(study_dir, 'project_metadata', 'metadata.json')
    if not os.path.exists(meta_path):
        errors.append("metadata.json not found (checked study root and project_metadata/)")
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

    print(f"  AIRR: {len(tsv_files)} .tsv.gz file(s) found")


def validate_ena(study_dir, errors):
    raw_seq_dir = os.path.join(study_dir, 'raw_seq')
    if not os.path.isdir(raw_seq_dir):
        errors.append("raw_seq/ directory not found")
        return

    fastq_files = [
        os.path.join(r, f)
        for r, _, files in os.walk(raw_seq_dir)
        for f in files
        if f.endswith('.fastq.gz')
    ]
    if not fastq_files:
        errors.append("no .fastq.gz files found under raw_seq/")
        return

    for fpath in fastq_files:
        if os.path.getsize(fpath) == 0:
            errors.append(f"empty file: {fpath}")

    print(f"  ENA:  {len(fastq_files)} .fastq.gz file(s) found")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--study-dir', required=True,
                        help='Downloaded study directory to validate')
    args = parser.parse_args()

    study_dir = args.study_dir
    if not os.path.isdir(study_dir):
        print(f"FAIL: study directory does not exist: {study_dir}")
        sys.exit(1)

    # Detect what is present
    has_tsv = any(
        f.endswith('.tsv.gz')
        for r, _, files in os.walk(study_dir)
        for f in files
        if 'raw_seq' not in r
    )
    has_fastq = os.path.isdir(os.path.join(study_dir, 'raw_seq'))

    if not has_tsv and not has_fastq:
        print("FAIL: no AIRR (.tsv.gz) or ENA (raw_seq/) data found")
        sys.exit(1)

    errors = []
    if has_tsv:
        validate_airr(study_dir, errors)
    if has_fastq:
        validate_ena(study_dir, errors)

    if errors:
        print("VALIDATION FAILED:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print(f"OK: validation passed for {study_dir}")


if __name__ == '__main__':
    main()
