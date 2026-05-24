pipeline {
    agent any

    parameters {
        string(name: 'STUDY_ID', defaultValue: 'PRJNA338795', description: 'Study / Project ID')
        choice(name: 'DOWNLOAD_MODE', choices: ['api', 'ena', 'api-then-ena'], description: 'api: AIRR API only | ena: ENA FASTQ only | api-then-ena: AIRR API then ENA FASTQ')
        // booleanParam(name: 'USE_SUBMITTED', defaultValue: false, description: 'Use originally-submitted files instead of ENA-processed FASTQ (ENA modes only)')
        booleanParam(name: 'Refresh', defaultValue: false, description: 'Reload Jenkinsfile and exit')
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
        // Exit codes from download_repertoires.py:
        //   0 = data found and downloaded
        //   2 = no repertoires found (soft failure — triggers ENA fallback in api-then-ena mode)
        //   1 = hard error (always fails the pipeline)
        stage('Download Study Data') {
            when { expression { return params.DOWNLOAD_MODE in ['api', 'api-then-ena'] } }
            steps {
                echo "Downloading study ${params.STUDY_ID} from healthy APIs..."
                script {
                    sshagent(credentials: ['igserver']) {
                        def cmd = """
                            ssh -o StrictHostKeyChecking=no \$IG_SERVER \
                            "mkdir -p ${DOWNLOAD_DIR} && \
                             cd ${REMOTE_DIR} && \
                             python3 scripts/download_repertoires.py \
                               --study-id ${params.STUDY_ID} \
                               --outdir   ${DOWNLOAD_DIR}"
                        """
                        if (params.DOWNLOAD_MODE == 'api-then-ena') {
                            def exitCode = sh(script: cmd, returnStatus: true)
                            if (exitCode == 1) {
                                error("API download failed with a hard error — aborting")
                            }
                            env.API_FOUND_DATA = (exitCode == 0) ? 'true' : 'false'
                            if (exitCode != 0) {
                                echo "No repertoires found via API — will fall back to ENA"
                            }
                        } else {
                            sh cmd
                            env.API_FOUND_DATA = 'true'
                        }
                    }
                }
            }
        }


        stage('Download FASTQ from ENA') {
            when {
                expression {
                    return params.DOWNLOAD_MODE == 'ena' ||
                           (params.DOWNLOAD_MODE == 'api-then-ena' && env.API_FOUND_DATA != 'true')
                }
            }
            steps {
                echo "Downloading FASTQ files from ENA for study ${params.STUDY_ID}..."
                sshagent(credentials: ['igserver']) {
                    sh """
                        ssh -o StrictHostKeyChecking=no \$IG_SERVER \
                        "cd ${REMOTE_DIR} && \
                         python3 scripts/ENA_downloader_tool.py \
                           --project-name ${params.STUDY_ID} \
                           --outdir       ${DOWNLOAD_DIR}"
                    """
                }
            }
        }

        // Runs after all downloads complete regardless of mode.
        // Auto-detects what was downloaded (AIRR TSVs, ENA FASTQs, or both) and validates each.
        stage('Validate Downloaded Data') {
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
