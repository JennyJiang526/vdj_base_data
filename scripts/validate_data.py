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
import gzip
import json
import os
import sys

# Files smaller than this are likely truncated downloads or error responses
MIN_FILE_BYTES = 100


def check_gzip_readable(fpath, errors):
    """Peek inside a .gz file to confirm it contains actual data."""
    try:
        with gzip.open(fpath, "rb") as gz:
            chunk = gz.read(1024)
            if not chunk:
                errors.append(f"gzip file is valid but empty inside: {fpath}")
    except gzip.BadGzipFile:
        errors.append(f"file is not a valid gzip archive: {fpath}")
    except EOFError:
        errors.append(f"gzip file appears truncated: {fpath}")
    except Exception as e:
        errors.append(f"could not read gzip file {fpath}: {e}")


def check_file_size(fpath, errors):
    """Check a file is non-zero and not suspiciously small."""
    size = os.path.getsize(fpath)
    if size == 0:
        errors.append(f"empty file (0 bytes): {fpath}")
        return False
    if size < MIN_FILE_BYTES:
        errors.append(f"suspiciously small file ({size} bytes), likely a failed download: {fpath}")
        return False
    return True


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
        if check_file_size(fpath, errors):
            check_gzip_readable(fpath, errors)

    # Check metadata.json — try study root, then project_metadata/
    for candidate in [
        os.path.join(study_dir, 'metadata.json'),
        os.path.join(study_dir, 'project_metadata', 'metadata.json'),
    ]:
        if os.path.exists(candidate):
            meta_path = candidate
            break
    else:
        errors.append("metadata.json not found (checked study root and project_metadata/)")
        print(f"  AIRR: {len(tsv_files)} .tsv.gz file(s) found")
        return

    if not check_file_size(meta_path, errors):
        print(f"  AIRR: {len(tsv_files)} .tsv.gz file(s) found")
        return

    try:
        with open(meta_path) as f:
            meta = json.load(f)
        if not meta.get('Repertoire'):
            errors.append("metadata.json contains no Repertoire entries")
    except json.JSONDecodeError as e:
        errors.append(f"metadata.json is not valid JSON: {e}")

    print(f"  AIRR: {len(tsv_files)} .tsv.gz file(s) found, metadata.json OK")


def validate_ena(study_dir, errors):
    raw_seq_dir = os.path.join(study_dir, 'raw_seq')
    if not os.path.isdir(raw_seq_dir):
        errors.append("raw_seq/ directory not found")
        return

    # Check the directory itself isn't just an empty shell (no files anywhere in the tree)
    all_files = [
        os.path.join(r, f)
        for r, _, files in os.walk(raw_seq_dir)
        for f in files
    ]
    if not all_files:
        errors.append("raw_seq/ directory exists but contains no files (checked recursively)")
        return

    fastq_files = [f for f in all_files if f.endswith('.fastq.gz')]
    if not fastq_files:
        errors.append(
            f"raw_seq/ has {len(all_files)} file(s) recursively "
            "but none are .fastq.gz — unexpected format"
        )
        return

    for fpath in fastq_files:
        if check_file_size(fpath, errors):
            check_gzip_readable(fpath, errors)

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