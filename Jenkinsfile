@Library('lib')_

pythonPipeline {
  package_name          = 'terra-stac-api'
  test_module_name      = 'terra_stac_api'
  python_version        = '3.10'
  create_tag_job        = true
  build_container_image = true
  dev_hosts             = 'docker-services-dev-01.vgt.vito.be'
  prod_hosts            = 'docker-services-prod-02.vgt.vito.be'
  docker_deploy         = true
  docker_registry_prod  = 'vito-docker.artifactory.vgt.vito.be'
  extras_require        = 'dev'
  pre_test_script       = 'pre_test.sh'
}