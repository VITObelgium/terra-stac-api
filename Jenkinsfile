@Library('lib')_

pythonPipeline {
  package_name          = 'terra-stac-api'
  python_version        = '3.10'
  create_tag_job        = true
  build_container_image = true
  dev_hosts             = 'docker-services-dev-01.vgt.vito.be'
  prod_hosts            = 'docker-services-prod-01.vgt.vito.be'
  docker_deploy         = true
  extras_require        = 'dev'
}