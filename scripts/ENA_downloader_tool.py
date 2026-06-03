#!/usr/bin/env python3
"""
CLI entry point for the ENA FASTQ downloader.

Downloads FASTQ (or originally-submitted) files from ENA for a project.
Requires that the AIRR metadata has already been downloaded and structured
(i.e. {outdir}/{project_id}/project_metadata/metadata.json must exist).

Usage:
    python3 scripts/ENA_downloader_tool.py \\
        --project-name PRJNA349143 \\
        --outdir /path/to/data \\
        [--use-original]
"""
import argparse
import sys
import os

from ENA_Downloader import ENA_Downloader


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--project-name', required=True,
                        help='ENA/SRA project accession (e.g. PRJNA349143)')
    parser.add_argument('--outdir', required=True,
                        help='Root directory where project folders live '
                             '(same value passed to download_repertoires.py)')
    parser.add_argument('--use-submitted', action='store_true',
                        help='Download originally-submitted files instead of ENA-processed FASTQ')
    args = parser.parse_args()

    obj = ENA_Downloader(args.project_name, args.use_submitted, projects_path=args.outdir)
    obj.start_downloading()


if __name__ == "__main__":
    main()