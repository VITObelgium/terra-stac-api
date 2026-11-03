@Library('lib')_

pythonPipeline {
  package_name          = 'terra-stac-api'
  test_module_name      = 'terra_stac_api'
  python_version        = ['3.14']
  create_tag_job        = true
  build_container_image = true
  dev_hosts             = 'docker-services-dev-01.vgt.vito.be'
  prod_hosts            = 'docker-services-prod-02.vgt.vito.be'
  docker_deploy         = true
  artifactory_server    = 'sas'
  wheel_repo            = 'team-rise-pypi-local-prod'
  wheel_repo_dev        = 'team-rise-pypi-local-dev'
  docker_registry_dev   = 'team-rise-docker-local-dev.repo.vito.be'
  docker_registry_prod  = 'team-rise-docker-local-prod.repo.vito.be'
  extras_require        = 'dev'
  pre_test_script       = 'pre_test.sh'
  extra_env_variables   = [
    "TEST_IN_JENKINS=True"
  ]
  enable_uv             = true
  enable_caching        = true
}