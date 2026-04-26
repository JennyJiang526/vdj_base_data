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

        // =========================
        // API HEALTH CHECK
        // Always runs; saves api_health_results.json for the download stage to read.
        // Stage itself never fails — individual API failures are expected.
        // =========================
        stage('API Health Check') {
            steps {
                echo 'Running API health check on igserver...'
                sshagent(credentials: ['igserver']) {
                    sh '''
                        ssh -o StrictHostKeyChecking=no $IG_SERVER \
                        "cd ${REMOTE_DIR} && python3 ${API_SCRIPT} || true"
                    '''
                }
            }
        }

        // =========================
        // DOWNLOAD
        // Reads api_health_results.json produced above and skips any API
        // whose status is "FAILED" (connection error, timeout, HTTP error, etc.).
        // Fails the pipeline if no healthy APIs remain, no repertoires are found,
        // or the download itself throws an exception.
        // =========================
        stage('Download Study Data') {
            steps {
                echo "Downloading study ${params.STUDY_ID} on igserver (skipping unhealthy APIs)..."
                sshagent(credentials: ['igserver']) {
                    sh """
                        ssh -o StrictHostKeyChecking=no \$IG_SERVER bash -s << 'ENDSSH'
set +e

mkdir -p ${DOWNLOAD_DIR}/${params.STUDY_ID}
chmod -R 777 ${DOWNLOAD_DIR} || true

python3 - << 'PYEOF'
import os, sys, json
import pandas as pd

os.environ['GEVENT_SUPPORT'] = 'True'
sys.path.insert(0, '${REMOTE_DIR}')

from collect import collect_repertoires_and_count_rearrangements, download_study

study_id = '${params.STUDY_ID}'
outdir   = '${DOWNLOAD_DIR}'

health_file = '${REMOTE_DIR}/api_health_results.json'

if os.path.exists(health_file):
    with open(health_file) as f:
        health_data = json.load(f)
    healthy_repos = [r['base_url'] for r in health_data if r.get('status') in ('OK', 'WARNING')]
    failed_repos  = [r['base_url'] for r in health_data if r.get('status') == 'FAILED']
    if failed_repos:
        print(f"Skipping {len(failed_repos)} FAILED API(s):")
        for url in failed_repos:
            print(f"  - {url}")
else:
    print("WARNING: api_health_results.json not found, attempting all known repos")
    healthy_repos = [
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

if not healthy_repos:
    print("ERROR: All APIs are unhealthy — cannot download data")
    sys.exit(1)

print(f"Querying {len(healthy_repos)} healthy repo(s) for study: {study_id}")
repo_df = pd.DataFrame(healthy_repos, columns=['URL'])

results = collect_repertoires_and_count_rearrangements(repo_df, study_id)
repertoires = results.get('Repertoire', [])

if not repertoires:
    print(f"ERROR: No repertoires found for study {study_id}")
    sys.exit(1)

print(f"Found {len(repertoires)} repertoire(s). Starting download...")
resp = download_study(study_id, repertoires, outdir)
print("Download complete:", resp)
PYEOF
ENDSSH
                    """
                }
            }
        }

        // =========================
        // DATA VALIDATION
        // Checks that every downloaded file exists and is non-empty,
        // and that at least one metadata file is present and non-empty.
        // Fails the pipeline immediately if any check fails.
        // =========================
        stage('Validate Downloaded Data') {
            steps {
                echo "Validating downloaded data for study ${params.STUDY_ID}..."
                sshagent(credentials: ['igserver']) {
                    sh """
                        ssh -o StrictHostKeyChecking=no \$IG_SERVER bash -s << 'ENDSSH'
python3 - << 'PYEOF'
import os, sys

study_dir = '${DOWNLOAD_DIR}/${params.STUDY_ID}'
errors = []

if not os.path.isdir(study_dir):
    print(f"FAIL: study directory does not exist: {study_dir}")
    sys.exit(1)

all_files = []
for root, dirs, files in os.walk(study_dir):
    for fname in files:
        all_files.append(os.path.join(root, fname))

if not all_files:
    print(f"FAIL: no files found in {study_dir}")
    sys.exit(1)

for fpath in all_files:
    if os.path.getsize(fpath) == 0:
        errors.append(f"empty file: {fpath}")

meta_keywords = ('metadata', 'manifest')
data_files = [f for f in all_files if not any(k in os.path.basename(f).lower() for k in meta_keywords)]
meta_files = [f for f in all_files if     any(k in os.path.basename(f).lower() for k in meta_keywords)]

if not data_files:
    errors.append("no data/repertoire files found")
if not meta_files:
    errors.append("no metadata files found")

if errors:
    print("VALIDATION FAILED:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)

print(f"OK: {len(all_files)} file(s) validated ({len(data_files)} data, {len(meta_files)} metadata)")
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
                        echo "Fetching API health results from igserver..."
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
