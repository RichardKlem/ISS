pipeline {
  agent {
    node {
      label 'pc322'
    }

  }
  stages {
    stage('Build') {
      steps {
        dir(path: 'mastermind') {
          git(url: 'git@gitlab.codasip.com:continuous-integration/mastermind.git', branch: 'release-8.4')
        }

        dir(path: 'jenkins') {
          git(url: 'git@gitlab.codasip.com:continuous-integration/jenkins.git', branch: 'release-8.4')
        }

        sh '''chmod -R a+x jenkins/*



chmod -R a+x jenkins/*
                python2 jenkins/jenkins.py -m build.tools -w $WORKSPACE -b $REVISION -d $DISTRO -i $INSERT_ARTIFACT -t $BUILD_TYPE'''
        archiveArtifacts(artifacts: 'codasip-tools*.tar.gz', allowEmptyArchive: true)
      }
    }

    stage('Test') {
      parallel {
        stage('Test') {
          steps {
            input(message: 'Huh?', id: 'HUH', ok: 'OHOHOH')
            echo 'Testing is done...'
          }
        }

        stage('') {
          steps {
            echo 'Parallel testung, Hooray'
            timestamps()
          }
        }

      }
    }

    stage('Finish') {
      steps {
        sleep 10
        echo 'Waited 10s'
      }
    }

  }
  environment {
    SPCEIAL_NODE_VAR = 'test_value'
  }
}