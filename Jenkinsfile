pipeline {
    agent any

    environment {
        PYTHON_PATH = "python"
        REPORT_DIR = 'reports'
    }

    triggers {
        githubPush()
    }

    stages {

        stage('0. Checkout') {
            steps {
                checkout([
                    $class: 'GitSCM',
                    branches: [[name: '*/vulnerabilities']],
                    userRemoteConfigs: [[url: 'https://github.com/Daniel-Lefevre/Software_Security_Assignment_1.git']]
                ])
                bat 'dir'
            }
        }

        stage('1. Build') {
            steps {
                bat """
                    ${PYTHON_PATH} --version

                    if not exist venv (
                        ${PYTHON_PATH} -m venv venv
                    )

                    call venv\\Scripts\\activate.bat

                    venv\\Scripts\\pip install --upgrade pip
                    venv\\Scripts\\pip install -r requirements.txt
                    venv\\Scripts\\pip install bandit
                """
            }
        }

        stage('2. Security Scan') {
            steps {
                bat 'if not exist reports mkdir reports'

                // Explicitly scan only your application files
                bat 'call venv\\Scripts\\activate.bat && venv\\Scripts\\bandit banking_api.py account_service.py loan_service.py -f json -o reports\\bandit_report.json || exit /b 0'

                bat 'call venv\\Scripts\\activate.bat && venv\\Scripts\\bandit banking_api.py account_service.py loan_service.py -f html -o reports\\bandit_report.html || exit /b 0'
            }
        }

        stage('3. Report Generation') {
            steps {
                archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
            }
        }

        stage('4. Enforce Security Gate') {
            steps {
                script {
                    def report = readFile('reports/bandit_report.json')

                    if (report.contains('"issue_severity": "HIGH"') || report.contains('"issue_severity": "CRITICAL"')) {
                        currentBuild.result = 'FAILURE'
                        echo " Vulnerabilities found → marking build as FAILED"
                    } else {
                        echo " No high vulnerabilities"
                    }
                }
            }
        }
    }

    post {
        always {
            echo "========== PIPELINE COMPLETE =========="
        }
        success {
            echo "[SUCCESS] Secure build passed"
        }
        failure {
            echo "[FAILURE] Build failed due to vulnerabilities (report generated)"
        }
    }
}
