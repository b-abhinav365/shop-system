pipeline {
  agent any
  environment { IMAGE = "shop-system" }
  stages {
    stage('Checkout') { steps { checkout scm } }
    stage('Install')  { steps { sh 'python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt' } }
    stage('Lint')     { steps { sh '. venv/bin/activate && flake8 app.py' } }
    stage('Unit Tests') { steps { sh '. venv/bin/activate && pytest -v' } }
    stage('Docker Build') { steps { sh 'docker build -t $IMAGE:${BUILD_NUMBER} -t $IMAGE:latest .' } }
    stage('Deploy') {
      steps {
        sh 'docker rm -f shop || true'
        sh 'docker run -d --name shop -p 5000:5000 $IMAGE:latest'
        sh 'sleep 5'
      }
    }
    stage('Selenium Tests') {
      steps { sh '. venv/bin/activate && BASE_URL=http://localhost:5000 pytest selenium_tests -v' }
    }
  }
  post { failure { sh 'docker logs shop || true' } }
}
