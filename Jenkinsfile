pipeline {
    agent any

    parameters {
        string(name: 'STUDY_ID', defaultValue: 'PRJ_TEST', description: 'Study / Project ID to download')
        choice(name: 'TASK', choices: ['download', 'api_test', 'both'], description: 'Select task to run')
    }

    environment {
        PYTHON = 'python3'
        BASE_DIR = '/mnt/data9/projects/Yaari_lab/test' 
        API_SCRIPT = 'api_test.py'
        DOWNLOAD_SCRIPT = 'download_repertoires_and_metadata.py' 
    }

    options {
        timestamps()
    }


    stages {
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
                    pip3 install --upgrade pip
                    pip3 install requests pandas
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

                    echo "Downloading data for study: ${params.STUDY_ID}"

                    sh """
                        ${PYTHON} ${DOWNLOAD_SCRIPT} \
                        --study_id ${params.STUDY_ID} \
                        --output_dir ${projectDir}
                    """
                }
            }
        }
}