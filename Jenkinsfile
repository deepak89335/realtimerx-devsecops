pipeline {
    agent any

    environment {
        IMAGE_NAME   = "realtimerx"
        IMAGE_TAG    = "${env.BUILD_NUMBER}"
        COMPOSE_FILE = "docker-compose.yml"
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.CURRENT_BRANCH = sh(
                        script: "git rev-parse --abbrev-ref HEAD | sed 's#origin/##'",
                        returnStdout: true
                    ).trim()

                    echo "Branch: ${env.CURRENT_BRANCH} | Build: ${env.BUILD_NUMBER}"
                }
            }
        }

        stage('Install & Test') {
            steps {
                sh '''
                    python3 -m pip install --break-system-packages -r requirements.txt
                    python3 -m pytest tests/ -v --tb=short
                '''
            }
            post {
                failure {
                    error "Pipeline blocked: tests failed."
                }
            }
        }

        stage('SAST Scan') {
            steps {
                sh '''
                    pip3 install --break-system-packages bandit || true
                    bandit -r app/ -f txt -o bandit_report.txt || true
                    cat bandit_report.txt

                    if grep -E "Severity: (HIGH|CRITICAL)" bandit_report.txt; then
                        echo "SAST FAILED"
                        exit 1
                    fi

                    echo "SAST PASSED"
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'bandit_report.txt', allowEmptyArchive: true
                }
            }
        }

        stage('Dependency Scan') {
            steps {
                sh '''
                    pip3 install --break-system-packages pip-audit || true

                    pip-audit -r requirements.txt -f plain > pip_audit_report.txt 2>&1 || true
                    cat pip_audit_report.txt

                    if grep -i "critical" pip_audit_report.txt; then
                        echo "DEPENDENCY SCAN FAILED"
                        exit 1
                    fi

                    echo "DEPENDENCY SCAN PASSED"
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'pip_audit_report.txt', allowEmptyArchive: true
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                sh '''
                    docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .
                    docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_NAME}:latest
                    docker images | grep ${IMAGE_NAME}
                '''
            }
        }

        stage('Container Image Scan') {
            steps {
                sh '''
                    trivy image --exit-code 0 --severity HIGH,CRITICAL \
                        --format table ${IMAGE_NAME}:${IMAGE_TAG} | tee trivy_report.txt
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'trivy_report.txt', allowEmptyArchive: true
                }
            }
        }

        stage('Security Gate') {
            steps {
                script {
                    def vulnCount = sh(
                        script: "grep -E 'CRITICAL|HIGH' trivy_report.txt | wc -l",
                        returnStdout: true
                    ).trim()

                    if (vulnCount.toInteger() > 0) {
                        error "SECURITY GATE FAILED: ${vulnCount} vulnerabilities found."
                    } else {
                        echo "Security Gate Passed"
                    }
                }
            }
        }

        stage('Deploy to Staging') {
            when {
                expression { env.CURRENT_BRANCH ==~ /develop|staging/ }
            }
            steps {
                withCredentials([file(credentialsId: 'realtimerx-env', variable: 'ENV_FILE')]) {
                    sh '''
                        cp $ENV_FILE .env
                        sed -i "s/APP_PORT=.*/APP_PORT=5001/" .env

                        docker-compose down || true
                        docker-compose up -d --build

                        sleep 20
                        docker-compose ps
                    '''
                }
            }
        }

        stage('Smoke Test') {
            when {
                expression { env.CURRENT_BRANCH ==~ /develop|staging/ }
            }
            steps {
                sh '''
                    for i in $(seq 1 12); do
                        STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5001/health)
                        if [ "$STATUS" = "200" ]; then
                            echo "App is up"
                            break
                        fi
                        sleep 5
                        if [ "$i" = "12" ]; then
                            echo "SMOKE TEST FAILED"
                            exit 1
                        fi
                    done
                '''
            }
        }

        stage('Deploy to Production') {
            when {
                allOf {
                    expression { env.CURRENT_BRANCH == 'main' }
                    expression { currentBuild.result == null || currentBuild.result == 'SUCCESS' }
                }
            }
            steps {
                input message: "Approve Production Deploy?", ok: "Deploy"

                withCredentials([file(credentialsId: 'realtimerx-env', variable: 'ENV_FILE')]) {
                    sh '''
                        cp $ENV_FILE .env
                        sed -i "s/APP_PORT=.*/APP_PORT=5000/" .env

                        docker-compose down || true
                        docker-compose up -d

                        sleep 20

                        STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/health)
                        if [ "$STATUS" != "200" ]; then
                            echo "PROD FAILED"
                            exit 1
                        fi

                        echo "Production Deploy Success"
                    '''
                }
            }
        }
    }

    post {
        failure {
            echo "BUILD FAILED — ${env.BUILD_NUMBER}"
        }
        success {
            echo "BUILD SUCCESS — ${IMAGE_NAME}:${IMAGE_TAG}"
        }
        always {
            sh "docker image prune -f || true"
        }
    }
}
