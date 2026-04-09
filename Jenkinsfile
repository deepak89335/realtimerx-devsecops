pipeline {
    agent any

    environment {
        IMAGE_NAME    = "realtimerx"
        IMAGE_TAG     = "${env.BUILD_NUMBER}"
        COMPOSE_FILE  = "docker-compose.yml"
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
                echo "Branch: ${env.BRANCH_NAME} | Build: ${env.BUILD_NUMBER}"
            }
        }

        stage('Install & Test') {
            steps {
                sh '''
                    pip install --quiet -r app/requirements.txt
                    python -m pytest tests/ -v --tb=short
                '''
            }
            post {
                always {
                    echo "Tests complete — check output above for failures"
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                sh "docker build -t ${IMAGE_NAME}:${IMAGE_TAG} ."
                sh "docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_NAME}:latest"
            }
        }

        stage('Deploy to Staging') {
            when {
                anyOf {
                    branch 'develop'
                    branch 'staging'
                }
            }
            steps {
                echo "Deploying build ${IMAGE_TAG} to staging..."
                sh '''
                    docker compose down --remove-orphans || true
                    docker compose up -d --build
                    sleep 10
                    docker compose ps
                '''
            }
        }

        stage('Smoke Test') {
            when {
                anyOf {
                    branch 'develop'
                    branch 'staging'
                }
            }
            steps {
                sh '''
                    # Wait for app to be healthy
                    for i in $(seq 1 10); do
                        STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/health)
                        if [ "$STATUS" = "200" ]; then
                            echo "App is up!"
                            break
                        fi
                        echo "Waiting... attempt $i"
                        sleep 5
                    done

                    # Validate response
                    curl -sf http://localhost:5000/health | grep "ok"
                    curl -sf http://localhost:5000/api/drugs
                    echo "Smoke tests passed."
                '''
            }
        }

        stage('Deploy to Production') {
            when {
                branch 'main'
            }
            input {
                message "Deploy build ${env.BUILD_NUMBER} to production?"
                ok "Yes, deploy"
            }
            steps {
                echo "Production deploy approved — deploying ${IMAGE_TAG}..."
                sh '''
                    docker compose down --remove-orphans || true
                    docker compose up -d
                    sleep 10
                    curl -sf http://localhost:5000/health | grep "ok"
                    echo "Production deploy successful."
                '''
            }
        }
    }

    post {
        failure {
            echo "BUILD FAILED on branch ${env.BRANCH_NAME} — build ${env.BUILD_NUMBER}"
        }
        success {
            echo "BUILD PASSED — ${IMAGE_NAME}:${IMAGE_TAG}"
        }
        always {
            sh "docker image prune -f || true"
        }
    }
}
