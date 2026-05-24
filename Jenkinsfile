pipeline {
    agent any

    parameters {
        string(name: 'STUDY_ID', defaultValue: 'PRJNA349143', description: 'Study / Project ID')
        booleanParam(name: 'Refresh', defaultValue: false, description: 'Reload Jenkinsfile and exit')
        choice(name: 'DOWNLOAD_MODE', choices: ['api', 'ena', 'api-then-ena'], description: 'api: AIRR API only | ena: ENA FASTQ only | api-then-ena: AIRR API then ENA FASTQ')
        booleanParam(name: 'USE_SUBMITTED', defaultValue: false, description: 'Use originally-submitted files instead of ENA-processed FASTQ (ENA modes only)')
    }

    environment {
        IG_SERVER    = credentials('igserver_user')
        REMOTE_DIR   = '/mnt/data9/projects/Yaari_lab/code'
        DOWNLOAD_DIR = '/mnt/data9/projects/Yaari_lab/test'
    }

    stages {

        stage('Refresh Jenkinsfile') {
            when { expression { return params.Refresh } }
            steps {
                echo 'Refreshing Jenkinsfile and exiting'
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

        // Tests every API endpoint and writes api_health_results.json.
        // The stage itself never fails — individual endpoint failures are expected
        // and are handled downstream in the Download stage.
        stage('API Health Check') {
            when { expression { return params.DOWNLOAD_MODE in ['api', 'api-then-ena'] } }
            steps {
                echo 'Running API health check on igserver...'
                sshagent(credentials: ['igserver']) {
                    sh '''
                        ssh -o StrictHostKeyChecking=no $IG_SERVER \
                        "cd ${REMOTE_DIR} && python3 scripts/api_test.py || true"
                    '''
                }
            }
        }

        // Reads api_health_results.json, skips FAILED endpoints, then downloads
        // repertoire + metadata for the requested study.
        // Fails the pipeline if no healthy APIs remain or no data is found.
        stage('Download Study Data') {
            when { expression { return params.DOWNLOAD_MODE in ['api', 'api-then-ena'] } }
            steps {
                echo "Downloading study ${params.STUDY_ID} from healthy APIs..."
                sshagent(credentials: ['igserver']) {
                    sh """
                        ssh -o StrictHostKeyChecking=no \$IG_SERVER \
                        "mkdir -p ${DOWNLOAD_DIR} && \
                         cd ${REMOTE_DIR} && \
                         python3 scripts/download_repertoires.py \
                           --study-id ${params.STUDY_ID} \
                           --outdir   ${DOWNLOAD_DIR}"
                    """
                }
            }
        }

        // Verifies that every downloaded file exists and is non-empty,
        // and that metadata.json is present and valid.
        // Fails the pipeline immediately if anything is wrong.
        stage('Validate Downloaded Data') {
            when { expression { return params.DOWNLOAD_MODE in ['api', 'api-then-ena'] } }
            steps {
                echo "Validating downloaded data for study ${params.STUDY_ID}..."
                sshagent(credentials: ['igserver']) {
                    sh """
                        ssh -o StrictHostKeyChecking=no \$IG_SERVER \
                        "python3 ${REMOTE_DIR}/scripts/validate_data.py \
                           --study-dir ${DOWNLOAD_DIR}/${params.STUDY_ID}"
                    """
                }
            }
        }

        // Downloads FASTQ files from ENA into {DOWNLOAD_DIR}/{STUDY_ID}/raw_seq/.
        // In api-then-ena mode, requires the AIRR metadata download to have run first.
        stage('Download FASTQ from ENA') {
            when { expression { return params.DOWNLOAD_MODE in ['ena', 'api-then-ena'] } }
            steps {
                echo "Downloading FASTQ files from ENA for study ${params.STUDY_ID}..."
                sshagent(credentials: ['igserver']) {
                    sh """
                        ssh -o StrictHostKeyChecking=no \$IG_SERVER \
                        "cd ${REMOTE_DIR} && \
                         python3 scripts/ENA_downloader_tool.py \
                           --project-name ${params.STUDY_ID} \
                           --outdir       ${DOWNLOAD_DIR} \
                           ${params.USE_SUBMITTED ? '--use-submitted' : ''}"
                    """
                }
            }
        }

        stage('Fetch Results') {
            steps {
                echo 'Fetching API health results from igserver...'
                sshagent(credentials: ['igserver']) {
                    sh '''
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
