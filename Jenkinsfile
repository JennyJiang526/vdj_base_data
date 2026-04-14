pipeline {
    agent any

    parameters {
        string(name: 'STUDY_ID', defaultValue: 'PRJ_TEST', description: 'Study / Project ID to download')
        choice(name: 'TASK', choices: ['download', 'api_test', 'both'], description: 'Select task to run')

        booleanParam(name: 'Refresh', defaultValue: false, description: 'Set to true to force Jenkins to reload the Jenkinsfile and exit.')
    }

    environment {
        IG_SERVER = credentials('igserver_user')
        IG_SERVER_URL = 'http://127.0.0.1:5000'   // Update to your igserver's actual URL

        PYTHON = 'python3'
        BASE_DIR = '/mnt/data9/projects/Yaari_lab/test'
        API_SCRIPT = 'api_test.py'
        DOWNLOAD_SCRIPT = 'download_repertoires_and_metadata.py'
    }


    stages {
        stage('Refresh Jenkinsfile') {
            when { expression { return params.Refresh == true } }
            steps {
                echo "Refreshing Jenkinsfile and exiting pipeline - Setting Build to SUCCESS"
                script { currentBuild.result = 'SUCCESS' }
            }
        }


        stage('Checkout Code') {
            steps {
                echo 'Cloning repository...'
                git url: 'https://github.com/JennyJiang526/vdj_base_data.git', branch: 'main'
            }
        }

        stage('Setup Python') {
            steps {
                sh '''
                    python3 --version
                    if ! python3 -m pip --version > /dev/null 2>&1; then
                        echo "pip not found, installing..."
                        sudo apt-get update
                        sudo apt-get install -y python3-pip
                    fi

                    python3 -m pip install --upgrade pip
                    python3 -m pip install --upgrade pip
                    python3 -m pip install -r requirements.txt
                '''
            }
        }

        // =========================
        // (1) API TEST TASK
        // =========================
        stage('API Health Check') {
            when {
                anyOf {
                    expression { params.TASK == 'api_test' }
                    expression { params.TASK == 'both' }
                }
            }
            steps {
                echo 'Running API health check...'
                sh """
                    ${PYTHON} ${API_SCRIPT}
                """
            }
        }

        // =========================
        // (2) DOWNLOAD TASK
        // =========================
        stage('Download Study Data') {
            when {
                anyOf {
                    expression { params.TASK == 'download' }
                    expression { params.TASK == 'both' }
                }
            }
            steps {
                script {
                    def projectDir = "${BASE_DIR}/${params.STUDY_ID}"

                    echo "Creating project directory: ${projectDir}"

                    sh """
                        mkdir -p ${projectDir}/metadata
                        mkdir -p ${projectDir}/sequences
                        mkdir -p ${projectDir}/runs
                    """

                    echo "Downloading data for study: ${params.STUDY_ID} from ${IG_SERVER_URL} to ${projectDir}"

                    sh """
                        ${PYTHON} -c "
                        import os, sys
                        os.environ['GEVENT_SUPPORT'] = 'True'
                        sys.path.insert(0, '.')
                        from collect import collect_repertoires_and_count_rearrangements, download_study
                        import pandas as pd

                        study_id = '${params.STUDY_ID}'
                        outdir   = '${projectDir}'
                        repo_url = '${IG_SERVER_URL}'

                        repo_df = pd.DataFrame([repo_url], columns=['URL'])
                        print(f'Querying {repo_url} for study: {study_id}')
                        results = collect_repertoires_and_count_rearrangements(repo_df, study_id)

                        repertoires = results.get('Repertoire', [])
                        if repertoires:
                            print(f'Found {len(repertoires)} repertoire(s). Starting download...')
                            resp = download_study(study_id, repertoires, outdir)
                            if resp:
                                print(f'Download initiated. Downloader ID: {resp.get(\\\"downloader_id\\\")}')
                            else:
                                print('Download failed: ' + str(resp))
                            sys.exit(0 if resp else 1)
                        else:
                            print(f'No repertoires found for study: {study_id}')
                            sys.exit(1)
                        "
                    """
                }
            }
        }

        stage('Archive Results') {
            steps {
                archiveArtifacts artifacts: '**/*.json', fingerprint: true
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
                cat api_health_results.json || true
            '''
        }
        always {
            echo 'Pipeline finished.'
        }
    }
}
