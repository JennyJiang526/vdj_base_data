pipeline {
    agent any

    parameters {
        string(name: 'STUDY_ID', defaultValue: 'PRJ_TEST', description: 'Study / Project ID')
        choice(name: 'TASK', choices: ['download', 'api_test', 'both'], description: 'Task to run')
        booleanParam(name: 'Refresh', defaultValue: false, description: 'Reload Jenkinsfile and exit')
    }

    environment {
        IG_SERVER    = credentials('igserver_user')
        REMOTE_DIR   = '/mnt/data9/projects/Yaari_lab/vdjbase_data'
        DOWNLOAD_DIR = '/mnt/data9/projects/Yaari_lab/test'

        API_SCRIPT      = 'api_test.py'
        DOWNLOAD_SCRIPT = 'download_repertoires_and_metadata.py'
    }

    stages {

        // =========================
        // Refresh
        // =========================
        stage('Refresh Jenkinsfile') {
            when { expression { return params.Refresh == true } }
            steps {
                echo "Refreshing Jenkinsfile and exiting"
                script { currentBuild.result = 'SUCCESS' }
            }
        }

        // =========================
        // Checkout (local copy)
        // =========================
        stage('Checkout Code') {
            steps {
                echo 'Cloning repository...'
                git url: 'https://github.com/JennyJiang526/vdj_base_data.git', branch: 'main'
            }
        }

        // =========================
        // Sync code to igserver
        // =========================
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

        // =========================
        // Setup Python (REMOTE)
        // Packages install to ~/.local — no venv needed.
        // =========================
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
        // API TEST (REMOTE)
        // =========================
        stage('API Health Check') {
            when {
                anyOf {
                    expression { params.TASK == 'api_test' }
                    expression { params.TASK == 'both' }
                }
            }
            steps {
                echo 'Running API test on igserver...'
                sshagent(credentials: ['igserver']) {
                    sh '''
                        ssh -o StrictHostKeyChecking=no $IG_SERVER \
                            "cd ${REMOTE_DIR} && python3 ${API_SCRIPT}"
                    '''
                }
            }
        }

        // =========================
        // DOWNLOAD TASK (REMOTE)
        // Calls collect.py functions directly to bypass the interactive
        // main() loop and the hardcoded /test/ output path.
        // =========================
        stage('Download Study Data') {
            when {
                anyOf {
                    expression { params.TASK == 'download' }
                    expression { params.TASK == 'both' }
                }
            }
            steps {
                echo "Downloading study ${params.STUDY_ID} on igserver..."
                sshagent(credentials: ['igserver']) {
                    sh """
                        ssh -o StrictHostKeyChecking=no \$IG_SERVER bash -s << 'ENDSSH'
set -e
mkdir -p ${DOWNLOAD_DIR}/${params.STUDY_ID}/metadata
mkdir -p ${DOWNLOAD_DIR}/${params.STUDY_ID}/sequences
mkdir -p ${DOWNLOAD_DIR}/${params.STUDY_ID}/runs

python3 - << 'PYEOF'
import os, sys
os.environ['GEVENT_SUPPORT'] = 'True'
sys.path.insert(0, '${REMOTE_DIR}')
from collect import collect_repertoires_and_count_rearrangements, download_study
import pandas as pd

study_id = '${params.STUDY_ID}'
outdir   = '${DOWNLOAD_DIR}'

repo_df = pd.DataFrame([
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
    'http://127.0.0.1:5000',
], columns=['URL'])

print(f'Searching {len(repo_df)} repositories for study: {study_id}')
results = collect_repertoires_and_count_rearrangements(repo_df, study_id)

repertoires = results.get('Repertoire', [])
if not repertoires:
    print(f'No repertoires found for study: {study_id}')
    sys.exit(1)

print(f'Found {len(repertoires)} repertoire(s). Downloading to {outdir}...')
resp = download_study(study_id, repertoires, outdir)
if resp:
    print(f'Download initiated. Downloader ID: {resp.get("downloader_id")}')
else:
    print('Download request failed: ' + str(resp))
    sys.exit(1)
PYEOF
ENDSSH
                    """
                }
            }
        }

        // =========================
        // Fetch Results
        // =========================
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
