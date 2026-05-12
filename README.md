# VDJ Base Data Pipeline

## Overview

This repository contains a Jenkins-based data pipeline for retrieving immune repertoire sequencing data from AIRR-compliant repositories.

The pipeline performs:

1. API health checks across multiple AIRR data repositories
2. Selective querying of healthy endpoints
3. Download of study-specific repertoire and metadata
4. Validation of downloaded data integrity

---

## Pipeline Workflow

### 1. Checkout Code

Clones the repository from GitHub into the Jenkins workspace.

### 2. Sync to Remote Server

All files are copied to a remote compute server (IG Server) for execution.

### 3. Environment Setup

* Verifies Python installation
* Installs dependencies from `requirements.txt`

---

### 4. API Health Check

Runs:

```
python3 api_test.py
```

* Tests connectivity and responsiveness of AIRR APIs
* Outputs:

  ```
  api_health_results.json
  ```
* APIs are categorized as:

  * `OK`
  * `WARNING`
  * `FAILED`

⚠️ This stage never fails the pipeline — failures are handled downstream.

---

### 5. Download Study Data

* Uses only **healthy APIs** from the previous stage
* Queries repositories for the specified study ID
* Downloads:

  * Repertoire data files
  * Metadata / manifest files

Core functions:

```
collect_repertoires_and_count_rearrangements
download_study
```

Pipeline fails if:

* No healthy APIs available
* No repertoires found
* Download process fails

---

### 6. Data Validation

Ensures:

* Study directory exists
* Files are non-empty
* Both data and metadata files are present

Pipeline fails if:

* Any file is empty
* No repertoire data found
* No metadata files found

---

### 7. Fetch Results

Copies `api_health_results.json` back to Jenkins workspace for inspection.

---

## Parameters

| Parameter  | Description                                  |
| ---------- | -------------------------------------------- |
| `STUDY_ID` | AIRR study/project ID (default: PRJNA349143) |
| `Refresh`  | If true, reloads Jenkinsfile and exits       |

---

## Required Files

The pipeline depends on:

* `api_test.py` — API health checking
* `collect.py` (or module) — data querying & download logic
* `requirements.txt` — Python dependencies

---

## Outputs

* Downloaded data:

  ```
  ${DOWNLOAD_DIR}/${STUDY_ID}/
  ```
* API health report:

  ```
  api_health_results.json
  ```

---

## Notes

* The pipeline executes on a remote server via SSH
* Failed APIs are automatically skipped
* Validation ensures data integrity before completion

