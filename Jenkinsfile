
pipeline {
    agent any

    environment {
        IMAGE = "shop-system"
        CONTAINER = "shop"
        PORT = "5000"
        PYTHON_EXE = "C:\\Users\\basar\\AppData\\Local\\Programs\\Python\\Python312\\python.exe"
    }

    stages {

        stage('Checkout') {
            steps {
                echo 'Checking out Shop System source code...'
                checkout scm
            }
        }

        stage('Install') {
            steps {
                echo 'Installing Python dependencies...'

                bat '"%PYTHON_EXE%" --version'

                bat '"%PYTHON_EXE%" -m venv venv'

                bat 'venv\\Scripts\\python.exe -m pip install --upgrade pip'

                bat 'venv\\Scripts\\python.exe -m pip install -r requirements.txt flake8 pytest'
            }
        }

        stage('Lint') {
            steps {
                echo 'Running Flake8...'

                bat 'venv\\Scripts\\python.exe -m flake8 app.py'
            }
        }

        stage('Unit Tests') {
            steps {
                echo 'Running unit tests...'

                bat 'venv\\Scripts\\python.exe -m pytest -v'
            }
        }

        stage('Docker Build') {
            steps {
                echo 'Building Docker image...'

                bat 'docker build -t %IMAGE%:%BUILD_NUMBER% -t %IMAGE%:latest .'
            }
        }

        stage('Deploy') {
            steps {
                echo 'Deploying Shop System...'

                // Remove existing container if present
                powershell '''
                    $existing = docker ps -aq --filter "name=^shop$"
        
                    if ($existing) {
                        docker rm -f shop
                    }
                '''
        
                // Start new container
                bat 'docker run -d --name shop -p 5000:5000 shop-system:latest'
        
                // Wait for application startup
                powershell 'Start-Sleep -Seconds 10'
        
                // Verify container is running
                bat 'docker ps --filter "name=shop"'
            }
        }

        stage('Selenium Tests') {
            steps {
                echo 'Running Selenium UI tests...'

                bat 'set "BASE_URL=http://localhost:%PORT%" && venv\\Scripts\\python.exe -m pytest selenium_tests -v'
            }
        }
    }

    post {
        success {
            echo 'Shop System CI/CD pipeline completed successfully!'
        }

        failure {
            echo 'Pipeline failed! Checking Docker logs...'

            bat 'docker logs %CONTAINER% 2>NUL || exit /b 0'
        }

        always {
            echo 'Shop System pipeline execution finished.'
        }
    }
}
