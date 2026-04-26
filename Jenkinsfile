pipeline {
    agent any

    parameters {
        string(name: 'STUDY_ID', defaultValue: 'PRJNA349143', description: 'Study / Project ID')
        booleanParam(name: 'Refresh', defaultValue: false, description: 'Reload Jenkinsfile and exit')
    }

    environment {
        IG_SERVER    = credentials('igserver_user')
        REMOTE_DIR   = '/mnt/data9/projects/Yaari_lab/code'
        DOWNLOAD_DIR = '/mnt/data9/projects/Yaari_lab/test'

        API_SCRIPT      = 'api_test.py'
        DOWNLOAD_SCRIPT = 'download_repertoires_and_metadata.py'
    }

    stages {

        stage('Refresh Jenkinsfile') {
            when { expression { return params.Refresh } }
            steps {
                echo "Refreshing Jenkinsfile and exiting"
                script { currentBuild.result = 'SUCCESS' }
            }
        }

        stage('Checkout Code') {
            steps {
                echo 'Cloning repository...'
                git url: 'https://github.com/JennyJiang526/vdj_base_data.git', branch: 'main'
            }
        }

        stage('Sync Code to IG Server') {
            steps {
                sshagent(credentials: ['igserver']) {
                    sh '''
                        ssh -o StrictHostKeyChecking=no $IG_SERVER "mkdir -p ${REMOTE_DIR}"
                        scp -r -o StrictHostKeyChecking=no * $IG_SERVER:${REMOTE_DIR}/
                    '''
                }
            }
        }

        stage('Setup Python on IG Server') {
            steps {
                sshagent(credentials: ['igserver']) {
                    sh '''
                        ssh -o StrictHostKeyChecking=no $IG_SERVER \
                        "python3 --version && \
                         python3 -m pip install --user --upgrade pip && \
                         python3 -m pip install --user -r ${REMOTE_DIR}/requirements.txt"
                    '''
                }
            }
        }

        // =========================================================
        // MERGED: API HEALTH CHECK + DOWNLOAD
        //   1) Run api_test.py to produce api_health_results.json
        //   2) Parse the result and drop APIs with connection error /
        //      timeout / unreachable status
        //   3) Only query / download from the remaining healthy APIs
        // =========================================================
        stage('API Health Check & Download') {
            steps {
                echo "Running API health check + download for study ${params.STUDY_ID} on igserver..."
                sshagent(credentials: ['igserver']) {
                    sh """
                        ssh -o StrictHostKeyChecking=no \$IG_SERVER bash -s << 'ENDSSH'
                        set -e   # Surface real failures (api_test.py itself is allowed to partially fail)

                        mkdir -p ${DOWNLOAD_DIR}/${params.STUDY_ID}
                        chmod -R 777 ${DOWNLOAD_DIR} || true

                        cd ${REMOTE_DIR}

                        # ---------------------------------------------------------
                        # Step 1: API health check -> api_health_results.json
                        # ---------------------------------------------------------
                        echo ">>> [1/2] API health check"
                        python3 ${API_SCRIPT} || true   # Health check itself may have partial failures; do not fail the pipeline here

                        # ---------------------------------------------------------
                        # Step 2: Filter out unhealthy APIs and download from the rest
                        # ---------------------------------------------------------
                        echo ">>> [2/2] Filtered download based on healthy APIs"

                        python3 - << 'PYEOF'
                        import os, sys, json
                        import pandas as pd

                        os.environ['GEVENT_SUPPORT'] = 'True'
                        sys.path.insert(0, '${REMOTE_DIR}')

                        from collect import collect_repertoires_and_count_rearrangements, download_study

                        study_id   = '${params.STUDY_ID}'
                        outdir     = '${DOWNLOAD_DIR}'
                        study_dir  = os.path.join(outdir, study_id)
                        remote_dir = '${REMOTE_DIR}'

                        # Full candidate repository list
                        all_repos = [
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
                        ]

                        def _norm(u):
                            return (u or '').rstrip('/').lower()

                        def _is_unhealthy(info):
                            '''Return True if the health-check result for an API indicates it is
                            unreachable / has a connection error / is otherwise unusable.'''
                            if info is None:
                                return True
                            if isinstance(info, bool):
                                return not info
                            if isinstance(info, str):
                                s = info.lower()
                                return any(k in s for k in (
                                    'connection error', 'connection refused', 'timeout',
                                    'unreachable', 'fail', 'error', 'down',
                                ))
                            if isinstance(info, dict):
                                status = str(info.get('status', info.get('state', ''))).lower()
                                error  = str(info.get('error',  info.get('message', ''))).lower()
                                ok_flag = info.get('ok', info.get('healthy', info.get('success')))
                                if ok_flag is False:
                                    return True
                                text = f"{status} {error}"
                                return any(k in text for k in (
                                    'connection error', 'connection refused', 'timeout',
                                    'unreachable', 'fail', 'error', 'down',
                                ))
                            return False

                        # Read api_health_results.json
                        results_path = os.path.join(remote_dir, 'api_health_results.json')
                        bad = set()
                        if os.path.exists(results_path):
                            try:
                                with open(results_path) as f:
                                    data = json.load(f)
                            except Exception as e:
                                print(f"WARN: cannot parse {results_path}: {e}; treating all APIs as healthy.")
                                data = None

                            iter_items = []
                            if isinstance(data, dict):
                                iter_items = list(data.items())
                            elif isinstance(data, list):
                                for d in data:
                                    if isinstance(d, dict):
                                        url = d.get('url') or d.get('URL') or d.get('repo') or d.get('host')
                                        iter_items.append((url, d))

                            for url, info in iter_items:
                                if not url:
                                    continue
                                if _is_unhealthy(info):
                                    bad.add(_norm(url))
                        else:
                            print(f"WARN: {results_path} not found, will query all repos.")

                        healthy = [u for u in all_repos if _norm(u) not in bad]
                        skipped = [u for u in all_repos if _norm(u) in bad]

                        if skipped:
                            print(f"Skipping {len(skipped)} unhealthy APIs:")
                            for u in skipped:
                                print(f"  - {u}")

                        if not healthy:
                            print("ERROR: no healthy APIs available, abort.")
                            sys.exit(1)

                        print(f"Using {len(healthy)} healthy APIs.")

                        repo_df = pd.DataFrame(healthy, columns=['URL'])

                        print(f"Searching {len(repo_df)} repositories for study: {study_id}")

                        try:
                            results = collect_repertoires_and_count_rearrangements(repo_df, study_id)
                            repertoires = results.get('Repertoire', [])
                        except Exception as e:
                            print(f"ERROR during search: {e}")
                            sys.exit(1)

                        if not repertoires:
                            print(f"No repertoires found for study: {study_id}")
                            sys.exit(1)

                        print(f"Found {len(repertoires)} repertoires. Downloading...")

                        try:
                            resp = download_study(study_id, repertoires, outdir)
                            print("Download response:", resp)
                        except Exception as e:
                            print(f"Download failed: {e}")
                            sys.exit(1)

                        # Persist a sample manifest for the downstream validation stage
                        os.makedirs(study_dir, exist_ok=True)
                        sample_ids = []
                        for r in repertoires:
                            rid = None
                            if isinstance(r, dict):
                                rid = (r.get('repertoire_id')
                                    or (r.get('repertoire') or {}).get('repertoire_id')
                                    or r.get('sample_id'))
                            if rid:
                                sample_ids.append(str(rid))

                        with open(os.path.join(study_dir, 'samples_manifest.json'), 'w') as f:
                            json.dump(sample_ids, f, indent=2)
                        print(f"Manifest written: {len(sample_ids)} samples -> samples_manifest.json")

                        PYEOF
                        ENDSSH
                    """
                }
            }
        }

        // =========================================================
        // DATA VALIDATION (new)
        //   - Each sample's data file must exist and be non-empty
        //   - Each sample's metadata file must exist and be non-empty
        //   - On any failure: fail the Jenkins pipeline immediately
        // =========================================================
        stage('Validate Downloaded Data') {
            steps {
                echo "Validating downloaded data for study ${params.STUDY_ID}..."
                sshagent(credentials: ['igserver']) {
                    sh """
                        ssh -o StrictHostKeyChecking=no \$IG_SERVER bash -s << 'ENDSSH'
                        set -e

                        python3 - << 'PYEOF'
                        import os, sys, glob, json

                        study_id  = '${params.STUDY_ID}'
                        study_dir = os.path.join('${DOWNLOAD_DIR}', study_id)

                        # Common file extensions: AIRR-seq rearrangement data + metadata
                        DATA_EXTS = ('.tsv.gz', '.tsv', '.airr.tsv.gz', '.airr.tsv', '.airr')
                        META_EXTS = ('.metadata.json', '_metadata.json', '.metadata.yaml',
                                    '_metadata.yaml', '.json', '.yaml', '.yml')

                        if not os.path.isdir(study_dir):
                            print(f"FAIL: study dir does not exist: {study_dir}")
                            sys.exit(1)

                        # 1. Resolve sample list (prefer manifest written by the previous stage)
                        manifest_path = os.path.join(study_dir, 'samples_manifest.json')
                        samples = []
                        if os.path.exists(manifest_path):
                            try:
                                with open(manifest_path) as f:
                                    samples = [str(s) for s in json.load(f) if s]
                            except Exception as e:
                                print(f"WARN: cannot read manifest: {e}")

                        # Fallback: derive sample names from data files in the directory
                        if not samples:
                            derived = set()
                            for fname in os.listdir(study_dir):
                                for ext in DATA_EXTS:
                                    if fname.endswith(ext):
                                        derived.add(fname[: -len(ext)])
                                        break
                            samples = sorted(derived)

                        if not samples:
                            print(f"FAIL: no samples found to validate under {study_dir}")
                            sys.exit(1)

                        print(f"Validating {len(samples)} samples in {study_dir}")

                        errors = []

                        def find_one(sample, exts):
                            """Find a real file matching `sample` prefix and one of the candidate extensions."""
                            for ext in exts:
                                # Exact match
                                exact = os.path.join(study_dir, f"{sample}{ext}")
                                if os.path.isfile(exact):
                                    return exact
                                # Fuzzy match (prefix + anything + ext)
                                for c in glob.glob(os.path.join(study_dir, f"{sample}*{ext}")):
                                    if os.path.isfile(c):
                                        return c
                            return None

                        for s in samples:
                            # ---- Data file ----
                            data_file = find_one(s, DATA_EXTS)
                            if not data_file:
                                errors.append(f"[MISSING data] sample={s}")
                            elif os.path.getsize(data_file) == 0:
                                errors.append(f"[EMPTY data]   {data_file}")

                            # ---- Metadata file ----
                            meta_file = find_one(s, META_EXTS)
                            if not meta_file:
                                errors.append(f"[MISSING meta] sample={s}")
                            elif os.path.getsize(meta_file) == 0:
                                errors.append(f"[EMPTY meta]   {meta_file}")

                        if errors:
                            print("=== Data validation FAILED ===")
                            for e in errors:
                                print("  -", e)
                            print(f"Total errors: {len(errors)}")
                            sys.exit(1)   # Fail the Jenkins pipeline so problems are not hidden

                        print(f"=== Data validation PASSED for {len(samples)} samples ===")
                        PYEOF
                        ENDSSH
                    """
                }
            }
        }

        stage('Fetch Results') {
            steps {
                sshagent(credentials: ['igserver']) {
                    sh '''
                        echo "Fetching results from igserver..."
                        scp -o StrictHostKeyChecking=no \
                        $IG_SERVER:${REMOTE_DIR}/api_health_results.json . || true
                    '''
                }
            }
        }
    }

    post {
        success {
            echo 'Pipeline succeeded!'
        }

        failure {
            echo 'Pipeline failed!'
            sh '''
                echo "---- API RESULTS ----"
                if [ -f api_health_results.json ]; then
                    cat api_health_results.json
                else
                    echo "No API results found"
                fi
            '''
        }

        always {
            echo 'Pipeline finished.'
        }
    }
}
