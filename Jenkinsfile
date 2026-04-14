pipeline {
    agent any

    parameters {
        string(name: 'STUDY_ID', defaultValue: 'PRJ_TEST', description: 'Study / Project ID')
        choice(name: 'TASK', choices: ['download', 'api_test', 'both'], description: 'Task to run')
        booleanParam(name: 'Refresh', defaultValue: false, description: 'Reload Jenkinsfile and exit')
    }

    environment {
        IG_SERVER = credentials('igserver_user')  
        REMOTE_DIR = '/mnt/data9/projects/Yaari_lab/vdjbase_data/'           

        API_SCRIPT = 'api_test.py'
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
        // =========================
        stage('Setup Python on IG Server') {
            steps {
                sshagent(credentials: ['igserver']) {
                    sh '''
                    ssh -o StrictHostKeyChecking=no $IG_SERVER "
                        cd ${REMOTE_DIR}

                        python3 --version

                        # create venv if not exists
                        if [ ! -d venv ]; then
                            python3 -m venv venv
                        fi

                        source venv/bin/activate

                        pip install --upgrade pip

                        if [ -f requirements.txt ]; then
                            pip install -r requirements.txt
                        fi
                    "
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
                    ssh -o StrictHostKeyChecking=no $IG_SERVER "
                        cd ${REMOTE_DIR}
                        source venv/bin/activate
                        python3 ${API_SCRIPT}
                    "
                    '''
                }
            }
        }

        // =========================
        // DOWNLOAD TASK (REMOTE)
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
                    ssh -o StrictHostKeyChecking=no $IG_SERVER "
                        cd ${REMOTE_DIR}
                        source venv/bin/activate
                        python3 ${DOWNLOAD_SCRIPT} --study ${params.STUDY_ID}
                    "
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