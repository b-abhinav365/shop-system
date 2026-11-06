
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

        stage('Install Dependencies') {
            steps {
                echo 'Installing Python dependencies...'

                bat '"%PYTHON_EXE%" --version'
                bat '"%PYTHON_EXE%" -m venv venv'
                bat 'venv\\Scripts\\python.exe -m pip install --upgrade pip'
                bat 'venv\\Scripts\\python.exe -m pip install -r requirements.txt'
                bat 'venv\\Scripts\\python.exe -m pip install flake8 pytest'
            }
        }

        stage('Lint') {
            steps {
                echo 'Running Flake8 code quality checks...'

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
                echo 'Building Shop System Docker image...'

                bat 'docker build -t %IMAGE%:%BUILD_NUMBER% -t %IMAGE%:latest .'
            }
        }

        stage('Deploy') {
            steps {
                echo 'Removing previous Shop container and deploying new version...'

                powershell '''
                    $ErrorActionPreference = "Stop"

                    $maxAttempts = 10
                    $removed = $false

                    for ($i = 1; $i -le $maxAttempts; $i++) {

                        $existing = docker ps -aq --filter "name=^shop$"

                        if (-not $existing) {
                            $removed = $true
                            break
                        }

                        Write-Host "Attempt $i : Removing existing shop container..."

                        docker rm -f shop 2>&1 | Out-Host

                        Start-Sleep -Seconds 3
                    }

                    $remaining = docker ps -aq --filter "name=^shop$"

                    if ($remaining) {
                        throw "Could not remove the previous shop container. Check Docker Desktop."
                    }

                    Write-Host "Previous container removed successfully."
                '''

                bat 'docker run -d --name %CONTAINER% -p %PORT%:5000 %IMAGE%:latest'

                powershell '''
                    Start-Sleep -Seconds 10

                    $running = docker inspect shop --format "{{.State.Running}}"

                    if ($running -ne "true") {
                        docker logs shop
                        throw "Shop container failed to start."
                    }

                    Write-Host "Shop application is running."
                '''

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
            echo 'Pipeline failed. Checking Docker container logs...'

            bat 'docker logs shop 2>NUL || exit /b 0'
        }

        always {
            echo 'Shop System pipeline execution finished.'
        }
    }
}
