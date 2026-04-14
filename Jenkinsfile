pipeline {
    agent any

    parameters {
        string(name: 'STUDY_ID', defaultValue: 'PRJ_TEST', description: 'Study / Project ID to download')
        choice(name: 'TASK', choices: ['download', 'api_test', 'both'], description: 'Select task to run')

        booleanParam(name: 'Refresh', defaultValue: false, description: 'Set to true to force Jenkins to reload the Jenkinsfile and exit.')
    }

    environment {
        IG_SERVER = credentials('igserver_user')

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
                    python3 -m pip install --upgrade pip
                    python3 -m pip install requests pandas
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

                    echo "Downloading data for study: ${params.STUDY_ID}"

                    sh """
                        ${PYTHON} ${DOWNLOAD_SCRIPT} \
                        --study_id ${params.STUDY_ID} \
                        --output_dir ${projectDir}
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
