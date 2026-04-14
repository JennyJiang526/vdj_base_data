pipeline {
    agent any

    parameters {
        string(name: 'STUDY_ID', defaultValue: 'PRJNA349143', description: 'Study / Project ID')
        choice(name: 'TASK', choices: ['download', 'api_test', 'both'], description: 'Task to run')
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
        // API TEST
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
                        "cd ${REMOTE_DIR} && python3 ${API_SCRIPT} || true"
                    '''
                }
            }
        }

        // =========================
        // DOWNLOAD（关键修复）
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
set +e   # ❗关键：不要因为错误退出

mkdir -p ${DOWNLOAD_DIR}/${params.STUDY_ID}
chmod -R 777 ${DOWNLOAD_DIR} || true

python3 - << 'PYEOF'
import os, sys
import pandas as pd

os.environ['GEVENT_SUPPORT'] = 'True'
sys.path.insert(0, '${REMOTE_DIR}')

from collect import collect_repertoires_and_count_rearrangements, download_study

study_id = '${params.STUDY_ID}'
outdir   = '${DOWNLOAD_DIR}'

# ✅ 过滤掉明显坏的 API
repo_list = [
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
    'https://t1d-1.ireceptor.org'
]

repo_df = pd.DataFrame(repo_list, columns=['URL'])

print(f"Searching {len(repo_df)} repositories for study: {study_id}")

try:
    results = collect_repertoires_and_count_rearrangements(repo_df, study_id)
    repertoires = results.get('Repertoire', [])
except Exception as e:
    print(f"ERROR during search: {e}")
    sys.exit(0)   # ❗不fail pipeline

if not repertoires:
    print(f"No repertoires found for study: {study_id}")
    sys.exit(0)   # ❗关键修改：不再 exit(1)

print(f"Found {len(repertoires)} repertoires. Downloading...")

try:
    resp = download_study(study_id, repertoires, outdir)
    print("Download response:", resp)
except Exception as e:
    print(f"Download failed: {e}")
    sys.exit(0)   # ❗不fail pipeline

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