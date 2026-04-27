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
                    if (env.BRANCH_NAME) {
                        env.CURRENT_BRANCH = env.BRANCH_NAME
                    } else {
                        env.CURRENT_BRANCH = sh(
                            script: "git rev-parse --abbrev-ref HEAD | sed 's#origin/##'",
                            returnStdout: true
                        ).trim()
                    }
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
                always {
                    echo "Tests complete."
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
                        echo "SAST FAILED: High/Critical issue found."
                        exit 1
                    fi
                    echo "SAST PASSED."
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
                    # FIX: correct format flag is "text" not "plain"
                    pip-audit -r requirements.txt --format=text > pip_audit_report.txt 2>&1 || true
                    cat pip_audit_report.txt
                    if grep -i "critical" pip_audit_report.txt; then
                        echo "DEPENDENCY SCAN FAILED: Critical CVE found."
                        exit 1
                    fi
                    echo "DEPENDENCY SCAN PASSED."
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
                    trivy image \
                        --exit-code 0 \
                        --severity HIGH,CRITICAL \
                        --format table \
                        ${IMAGE_NAME}:${IMAGE_TAG} | tee trivy_report.txt
                    echo "Trivy scan complete."
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
                    def criticalFixable = sh(
                        script: """
                            grep 'CVE-' trivy_report.txt | \
                            grep 'CRITICAL' | \
                            grep -v 'will_not_fix' | \
                            grep -v '│ affected' | \
                            wc -l || true
                        """,
                        returnStdout: true
                    ).trim().toInteger()

                    def highFixable = sh(
                        script: """
                            grep 'CVE-' trivy_report.txt | \
                            grep 'HIGH' | \
                            grep -v 'will_not_fix' | \
                            grep -v '│ affected' | \
                            wc -l || true
                        """,
                        returnStdout: true
                    ).trim().toInteger()

                    def criticalTotal = sh(
                        script: "grep 'CVE-' trivy_report.txt | grep -c 'CRITICAL' || true",
                        returnStdout: true
                    ).trim().toInteger()

                    def highTotal = sh(
                        script: "grep 'CVE-' trivy_report.txt | grep -c 'HIGH' || true",
                        returnStdout: true
                    ).trim().toInteger()

                    echo "=== Security Gate Report ==="
                    echo "CRITICAL — Total: ${criticalTotal} | Fixable: ${criticalFixable}"
                    echo "HIGH     — Total: ${highTotal} | Fixable: ${highFixable}"
                    echo "============================"
                    echo "Note: Unfixable CVEs (will_not_fix/no Debian patch) reported but do not block."

                    if (criticalFixable > 0) {
                        error "SECURITY GATE FAILED: ${criticalFixable} CRITICAL CVEs have patches. Update Dockerfile."
                    }

                    if (env.CURRENT_BRANCH == 'main' && highFixable > 0) {
                        error "SECURITY GATE FAILED: ${highFixable} HIGH CVEs have patches. Fix before production."
                    }

                    echo "Security Gate PASSED for branch: ${env.CURRENT_BRANCH}"
                }
            }
        }

        stage('Deploy to Staging') {
            when {
                expression { env.CURRENT_BRANCH ==~ /develop|staging/ }
            }
            steps {
                echo "Deploying build ${IMAGE_TAG} to staging (port 5001)..."
                withCredentials([file(credentialsId: 'realtimerx-env', variable: 'ENV_FILE')]) {
                    sh '''
                        cp $ENV_FILE .env
                        sed -i "s/APP_PORT=.*/APP_PORT=5001/" .env
                        docker compose down || true
                        docker compose up -d --build
                        sleep 20
                        docker compose ps
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
                    echo "Running smoke tests against staging port 5001..."
                    for i in $(seq 1 12); do
                        STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5001/health)
                        if [ "$STATUS" = "200" ]; then
                            echo "App is up after $i attempts."
                            break
                        fi
                        echo "Attempt $i: HTTP $STATUS — waiting 5s..."
                        sleep 5
                        if [ "$i" = "12" ]; then
                            echo "SMOKE TEST FAILED: /health never returned 200"
                            exit 1
                        fi
                    done
                    curl -sf http://localhost:5001/health | grep "ok"
                    curl -sf http://localhost:5001/api/drugs | python3 -c "import sys,json; json.load(sys.stdin); print('drugs endpoint OK')"
                    echo "All smoke tests PASSED."
                '''
            }
        }

        stage('Deploy to Production') {
            when {
                expression { env.CURRENT_BRANCH == 'main' }
            }
            steps {
                input(
                    message: "Deploy build ${env.BUILD_NUMBER} to PRODUCTION (port 5000)?",
                    ok: "Approve and Deploy"
                )
                withCredentials([file(credentialsId: 'realtimerx-env', variable: 'ENV_FILE')]) {
                    sh '''
                        echo "Production deploy approved..."
                        cp $ENV_FILE .env
                        sed -i "s/APP_PORT=.*/APP_PORT=5000/" .env
                        docker compose down || true
                        docker compose up -d
                        sleep 20
                        STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/health)
                        if [ "$STATUS" != "200" ]; then
                            echo "PRODUCTION HEALTH CHECK FAILED: got $STATUS"
                            exit 1
                        fi
                        echo "Production deploy SUCCESSFUL."
                    '''
                }
            }
        }
    }

    post {
        failure {
            echo "BUILD FAILED — branch: ${env.CURRENT_BRANCH} | build: ${env.BUILD_NUMBER}"
        }
        success {
            echo "BUILD PASSED — ${IMAGE_NAME}:${IMAGE_TAG} on ${env.CURRENT_BRANCH}"
        }
        always {
            sh "docker image prune -f || true"
        }
    }
}
