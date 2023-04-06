#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License").
#    You may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import logging
import os

import pytest
from _test_cli_helper_functions import _test_command

from seedfarmer import config
from seedfarmer.__main__ import apply, bootstrap, destroy, init
from seedfarmer.__main__ import list as list
from seedfarmer.__main__ import projectpolicy, remove, store, version
from seedfarmer.services._service_utils import boto3_client
from seedfarmer.services.session_manager import SessionManager
from seedfarmer.models.manifests import DeploymentManifest, ModulesManifest
from seedfarmer.models._deploy_spec import DeploySpec
import mock_manifests

from moto import mock_sts


# Override OPS_ROOT to reflect path of resource policy needed for some testing #
_OPS_ROOT = config.OPS_ROOT
_TEST_ROOT = os.path.join(config.OPS_ROOT, "test/unit-test/mock_data")
_PROJECT = config.PROJECT

_logger: logging.Logger = logging.getLogger(__name__)


@pytest.fixture(scope="function")
def patch_command_methods(mocker):
    mocker.patch("seedfarmer.commands.apply", return_value=None)
    mocker.patch("seedfarmer.commands.destroy", return_value=None)
    mocker.patch("seedfarmer.commands._bootstrap_commands.bootstrap_target_account", return_value=None)
    mocker.patch("seedfarmer.commands._bootstrap_commands.bootstrap_toolchain_account", return_value=None)
    mocker.patch("seedfarmer.commands._bootstrap_commands.apply_deploy_logic", return_value=None)


@pytest.fixture(scope="function")
def patch_mgmt_methods(mocker):
    mocker.patch("seedfarmer.mgmt.module_info.write_module_md5", return_value=None)
    mocker.patch("seedfarmer.mgmt.module_info.remove_module_info", return_value=None)
    mocker.patch("seedfarmer.mgmt.module_info.get_all_deployments", return_value=None)
    mocker.patch("seedfarmer.mgmt.deploy_utils.update_deployspec", return_value=None)
    mocker.patch("seedfarmer.mgmt.module_init.create_project", return_value=None)
    mocker.patch("seedfarmer.mgmt.module_init.create_module_dir", return_value=None)
    mocker.patch("seedfarmer.output_utils.print_deployment_inventory", return_value=None)

@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["MOTO_ACCOUNT_ID"] = "123456789012"

@pytest.fixture(scope="function")
def sts_client(aws_credentials):
    with mock_sts():
        yield boto3_client(service_name="sts", session=None)

@pytest.fixture(scope="function")       
def session_manager(sts_client):
    SessionManager._instances={}
    SessionManager().get_or_create(
        project_name="test",
        region_name="us-east-1",
        toolchain_region="us-east-1",
        enable_reaper=False,
    )



# -------------------------------------------
# -----   Test the sub-command `init`   -----
# -------------------------------------------


# @pytest.mark.init
# def test_init_create_module():
#     module_name = "test-module"
#     expected_module_path = os.path.join(_OPS_ROOT, "modules")

#     # Creates a new module
#     _test_command(sub_command=init, options=["module", "-m", module_name], exit_code=0, return_result=False)

#     # Creates a module that already exist
#     result = _test_command(sub_command=init, options=["module", "-m", module_name], exit_code=1, return_result=True)
#     print(result.exception.args[0])
#     assert result.exception.args[0] == f"The module {module_name} already exists under {expected_module_path}."

#     # Checks if file exists from the project template
#     assert os.path.exists(os.path.join(expected_module_path, module_name, "deployspec.yaml"))


@pytest.mark.init
def test_init_create_group_module(patch_mgmt_methods):

    module_name = "test-module"
    group_name = "group"
    expected_module_path = os.path.join(_OPS_ROOT, "modules", group_name, module_name)

    # Creates a group and a module within the group
    _test_command(sub_command=init, options=["module", "-g", group_name, "-m", module_name], exit_code=0)
    # assert os.path.exists(expected_module_path)

    # Creates a group and a module that already exists within the group
    # result = _test_command(
    #     sub_command=init, options=["module", "-g", group_name, "-m", module_name], exit_code=1, return_result=True
    # )
    # assert (
    #     result.exception.args[0] == f"The module {module_name} already exists under {_OPS_ROOT}/modules/{group_name}."
    # )

    # Checks if a file from the project template was created within the new module
    # assert os.path.exists(os.path.join(expected_module_path, "deployspec.yaml"))


@pytest.mark.init
def test_init_create_project(patch_mgmt_methods):

    expected_project_path = os.path.join(_OPS_ROOT, _PROJECT)
    # mocker.patch("seedfarmer.mgmt.module_init.create_project", return_value=None)
    # Creates a new project
    _test_command(sub_command=init, options=["project"], exit_code=0, return_result=False)

    # Checks if file exists from the project template
    # assert os.path.exists(os.path.join(expected_project_path, "seedfarmer.yaml"))


# # -------------------------------------------
# # -----  Test the sub-command `apply`   -----
# # -------------------------------------------


@pytest.mark.version
def test_version():
    _test_command(
        sub_command=version,
        options=None,
        exit_code=0,
        expected_output="seed-farmer",
    )


@pytest.mark.apply
def test_apply_help(patch_command_methods):
    _test_command(
        sub_command=apply,
        options=["--help"],
        exit_code=0,
        expected_output="Apply manifests to a SeedFarmer managed deployment",
    )


@pytest.mark.apply
def test_apply_debug(patch_command_methods):
    _test_command(
        sub_command=apply,
        options=["--help", "--debug"],
        exit_code=0,
        expected_output="Apply manifests to a SeedFarmer managed deployment",
    )


@pytest.mark.first
@pytest.mark.apply_working_module
def test_apply_deployment_dry_run(patch_command_methods):
    # Deploys a functioning module
    deployment_manifest = f"{_TEST_ROOT}/manifests/module-test/deployment.yaml"

    command_output = _test_command(sub_command=apply, options=[deployment_manifest, "--dry-run"], exit_code=0)
    print(command_output)


@pytest.mark.first
@pytest.mark.apply_working_module
def test_apply_deployment(patch_command_methods):
    # Deploys a functioning module
    deployment_manifest = f"{_TEST_ROOT}/manifests/module-test/deployment.yaml"
    command_output = _test_command(sub_command=apply, options=[deployment_manifest, "--debug"], exit_code=0)


@pytest.mark.destroy
def test_destroy_deployment_dry_run(patch_command_methods):
    # Destroy a functioning module
    command_output = _test_command(sub_command=destroy, options=["myapp", "--debug", "--dry-run"], exit_code=0)


@pytest.mark.destroy
def test_destroy_deployment(patch_command_methods):
    # Destroy a functioning module
    command_output = _test_command(sub_command=destroy, options=["myapp", "--debug"], exit_code=0)


# @pytest.mark.bootstrap
# def test_bootstrap_toolchain_and_target(patch_command_methods):
#     # Bootstrap an Account As Target
#     _test_command(sub_command=bootstrap,
#                                    options=["toolchain",
#                                             "--trusted-principal","arn:aws:iam::123456789012:role/AdminRole",
#                                             "--as-target","--debug"],
#                                    exit_code=0)


@pytest.mark.bootstrap
def test_bootstrap_toolchain_only(patch_command_methods):
    # Bootstrap an Account As Target
    _test_command(
        sub_command=bootstrap,
        options=["toolchain", "--trusted-principal", "arn:aws:iam::123456789012:role/AdminRole", "--debug"],
        exit_code=0,
    )


@pytest.mark.bootstrap
def test_bootstrap_target_account(patch_command_methods):
    # Bootstrap an Account As Target
    _test_command(
        sub_command=bootstrap, options=["target", "--toolchain-account", "123456789012", "--debug"], exit_code=0
    )


# @pytest.mark.apply
# def test_apply_missing_deployment():
#     deployment_manifest = f"{_TEST_ROOT}/manifests/test-missing-deployment-manifest/deployment.yaml"

#     result = _test_command(sub_command=apply, options=deployment_manifest, exit_code=1, return_result=True)
#     assert result.exception.args[1] == "No such file or directory"


# @pytest.mark.apply
# def test_apply_missing_group_manifest():
#     deployment_manifest = f"{_TEST_ROOT}/manifests/test-missing-group-manifest/deployment.yaml"

#     result = _test_command(sub_command=apply, options=deployment_manifest, exit_code=1, return_result=True)
#     assert result.exception.args[1] == "No such file or directory"


# @pytest.mark.apply
# def test_apply_missing_deployment_group_name():
#     deployment_manifest = f"{_TEST_ROOT}/manifests/test-missing-deployment-group-name/deployment.yaml"

#     result = _test_command(sub_command=apply, options=deployment_manifest, exit_code=1, return_result=True)
#     assert result.exception.args[0][0][0].exc.errors()[0]["msg"] == "none is not an allowed value"


# @pytest.mark.apply
# def test_apply_missing_deployment_group_path():
#     deployment_manifest = f"{_TEST_ROOT}/manifests/test-missing-deployment-group-path/deployment.yaml"

#     result = _test_command(sub_command=apply, options=deployment_manifest, exit_code=1, return_result=True)
#     assert result.exception.args[0] == "One of the `path` or `modules` attributes must be defined on a Group"


# @pytest.mark.apply
# def test_apply_missing_deployment_name():
#     deployment_manifest = f"{_TEST_ROOT}/manifests/test-missing-deployment-name/deployment.yaml"

#     result = _test_command(sub_command=apply, options=deployment_manifest, exit_code=1, return_result=True)
#     assert result.exception.args[0] == "One of 'name' or 'name_generator' is required"


# @pytest.mark.apply
# def test_apply_broken_deploy_phase():
#     deployment_manifest = f"{_TEST_ROOT}/manifests/test-broken-deployspec-deploy/deployment.yaml"

#     _test_command(sub_command=apply, options=deployment_manifest, exit_code=1, return_result=True)
#     # assert result.exception.args[0][0].exc.errors()[0]["msg"] == "none is not an allowed value"


# # # TODO add test for broken destroy phase
# # @pytest.mark.destroy
# # def test_destroy_broken_deploy_phase():
# #     deployment_manifest = f"{_TEST_ROOT}/manifests/test-broken-deployspec-destroy/deployment.yaml"

# #     result = _test_command(sub_command=destroy, options=deployment_manifest, exit_code=1, return_result=True)
# #     assert result.exception.args[0][0].exc.errors()[0]['msg'] == "none is not an allowed value"

# -------------------------------------------
# -----  Test the sub-command `list`    -----
# -------------------------------------------

# Test Deployspec

@pytest.mark.list
def test_error_messaging():
    import seedfarmer.cli_groups._list_group as lg
    
    lg._error_messaging(deployment='test-dep',group='test-group',module='test-module')

@pytest.mark.list
def test_list_help():
    _test_command(
        list,
        options=["--help"],
        exit_code=0,
        expected_output="List the relative data (module or deployment",
    )

@pytest.mark.list
@pytest.mark.list_deployspec
@pytest.mark.parametrize("session", [None, boto3_client])
def test_list_deployspec_deployed_error(session,mocker):
    mocker.patch("seedfarmer.cli_groups._list_group.mi.get_deployspec", return_value=None)
    mocker.patch("seedfarmer.cli_groups._list_group.du.generate_deployed_manifest", return_value=None)
    _test_command(
        list,
        options=["deployspec",
                "-d","test",
                "-g","test-group",
                "-m","test-module",
                "-p","myapp",
                "--debug",
                ],
        exit_code=1
    )


@pytest.mark.list
@pytest.mark.list_deployspec
def test_list_deployspec_deployed_none(session_manager,mocker):
    mocker.patch("seedfarmer.cli_groups._list_group.mi.get_deployspec", return_value=None)
    mocker.patch("seedfarmer.cli_groups._list_group.du.generate_deployed_manifest", return_value=None)
    _test_command(
        list,
        options=["deployspec",
                 "-d","test",
                 "-g","test-group",
                 "-m","test-module",
                 "-p","myapp",
                 "--debug",
                 ],
        exit_code=0
    )

@pytest.mark.list
@pytest.mark.list_deployspec
def test_list_deployspec_missing_session(session_manager,mocker):
    mocker.patch("seedfarmer.cli_groups._list_group.mi.get_deployspec", return_value={"deploy":{"commands":"echo"}})
    mocker.patch("seedfarmer.cli_groups._list_group.du.generate_deployed_manifest", return_value=(DeploymentManifest(**mock_manifests.deployment_manifest)))
    mocker.patch("seedfarmer.cli_groups._list_group.mi.get_deployspec",return_value=DeploySpec(**mock_manifests.deployspec))
    _test_command(
        list,
        options=["deployspec",
                 "-d","myapp",
                 "-g","messsedup",
                 "-m","networking",
                 "-p","myapp",
                 "--debug",
                 ],
        exit_code=0
    )

@pytest.mark.list
@pytest.mark.list_deployspec
def test_list_deployspec(session_manager,mocker):
    mocker.patch("seedfarmer.cli_groups._list_group.mi.get_deployspec", return_value={"deploy":{"commands":"echo"}})
    mocker.patch("seedfarmer.cli_groups._list_group.du.generate_deployed_manifest", return_value=(DeploymentManifest(**mock_manifests.deployment_manifest)))
    mocker.patch("seedfarmer.cli_groups._list_group.mi.get_deployspec",return_value=DeploySpec(**mock_manifests.deployspec))
    _test_command(
        list,
        options=["deployspec",
                 "-d","myapp",
                 "-g","optionals",
                 "-m","networking",
                 "-p","myapp",
                 "--debug",
                 ],
        exit_code=0
    )
    
# Test list dependencies
@pytest.mark.list
@pytest.mark.list_dependencies
def test_list_dependencies_no_deployed_manifest(session_manager,mocker):
    mocker.patch("seedfarmer.cli_groups._list_group.du.generate_deployed_manifest", return_value=None)
    mocker.patch("seedfarmer.cli_groups._list_group.du.generate_dependency_maps", return_value=None)
    _test_command(
        list,
        options=["dependencies",
                 "-d","test",
                 "-g","test-group",
                 "-m","test-module",
                 "-p","myapp",
                 "--debug",
                 ],
         exit_code=0
    )

@pytest.mark.list
@pytest.mark.list_dependencies
def test_list_dependencies(session_manager,mocker):
    mocker.patch("seedfarmer.cli_groups._list_group.du.generate_deployed_manifest", return_value=(DeploymentManifest(**mock_manifests.deployment_manifest)))
    mocker.patch("seedfarmer.cli_groups._list_group.du.generate_dependency_maps", return_value=None)
    _test_command(
        list,
        options=["dependencies",
                 "-d","test",
                 "-g","test-group",
                 "-m","test-module",
                 "-p","myapp",
                 "--debug",
                 ],
         exit_code=1
    )
# # Test `list deployments` #


@pytest.mark.list
@pytest.mark.list_deployments
def test_list_deployments_help(patch_mgmt_methods):
    _test_command(
        sub_command=list,
        options=["deployments", "--help"],
        exit_code=0,
        expected_output="List the deployments in this account",
    )


@pytest.mark.list
@pytest.mark.list_deployments
def test_list_deployments_extra_args(patch_mgmt_methods):
    
    _test_command(
        sub_command=list,
        options=[
            "deployments",
            "dsfsd",
        ],
        exit_code=2,
        expected_output="Got unexpected extra argument",
    )


@pytest.mark.list
@pytest.mark.list_deployments
def test_list_deployments(session_manager,mocker):
    mocker.patch("seedfarmer.cli_groups._list_group.mi.get_all_deployments", return_value=None)
    _test_command(
        sub_command=list,
        options=["deployments", "-p","myapp", "--debug"],
        exit_code=1,
    )


# # TODO test for no deployments

# # Test `list moduledata` #


@pytest.mark.list
@pytest.mark.list_moduledata
def test_list_moduledata_help():
    _test_command(
        sub_command=list,
        options=["moduledata", "--help"],
        exit_code=0,
        expected_output="Fetch the module metadata",
    )


@pytest.mark.list
@pytest.mark.list_moduledata
def test_list_moduledata_missing_deployment_option():
    _test_command(
        sub_command=list,
        options=[
            "moduledata",
        ],
        exit_code=2,
    )


@pytest.mark.list
@pytest.mark.list_moduledata
def test_list_moduledata_no_dep_manifest(session_manager,mocker):
    mocker.patch("seedfarmer.cli_groups._list_group.du.generate_deployed_manifest", return_value=None)
    _test_command(
        sub_command=list,
        options=[
            "moduledata",
            "-d","test",
            "-g","test-group",
            "-m","test-module",
            "-p","myapp",
            "--debug",
            ],
        exit_code=0,
    )

@pytest.mark.list
@pytest.mark.list_moduledata
def test_list_moduledata(session_manager,mocker):
    mocker.patch("seedfarmer.cli_groups._list_group.du.generate_deployed_manifest", return_value=(DeploymentManifest(**mock_manifests.deployment_manifest)))
    mocker.patch("seedfarmer.cli_groups._list_group.mi.get_module_metadata",return_value=mock_manifests.sample_metadata)

    _test_command(
        sub_command=list,
        options=[
            "moduledata",
            "-d","test",
            "-g","optionals",
            "-m","networking",
            "-p","myapp",
            "--debug",
            ],
        exit_code=0,
    )
 
@pytest.mark.list
@pytest.mark.list_moduledata
def test_list_moduledata_export_envs(session_manager,mocker):
    mocker.patch("seedfarmer.cli_groups._list_group.du.generate_deployed_manifest", return_value=(DeploymentManifest(**mock_manifests.deployment_manifest)))
    mocker.patch("seedfarmer.cli_groups._list_group.mi.get_module_metadata",return_value=mock_manifests.sample_metadata)
    mocker.patch("seedfarmer.cli_groups._list_group.commands.generate_export_env_params",return_value=["export SOMETHING=yo"])

    _test_command(
        sub_command=list,
        options=[
            "moduledata",
            "-d","test",
            "-g","optionals",
            "-m","networking",
            "-p","myapp",
            "--export-local-env",
            "--debug",
            ],
        exit_code=0
    )
 
    
@pytest.mark.list
@pytest.mark.list_moduledata
def test_list_moduledata_mod_not_found(session_manager,mocker):
    mocker.patch("seedfarmer.cli_groups._list_group.du.generate_deployed_manifest", return_value=(DeploymentManifest(**mock_manifests.deployment_manifest)))
    mocker.patch("seedfarmer.cli_groups._list_group.mi.get_module_metadata",return_value=mock_manifests.sample_metadata)

    _test_command(
        sub_command=list,
        options=[
            "moduledata",
            "-d","test",
            "-g","somethingcrazy",
            "-m","networking",
            "-p","myapp",
            "--debug",
            ],
        exit_code=0,
    )

@pytest.mark.list
@pytest.mark.list_moduledata
def test_list_moduledata_missing_deployment_arg():
    _test_command(sub_command=list, options=["moduledata", "-d"], exit_code=2)


@pytest.mark.list
@pytest.mark.list_moduledata
def test_list_moduledata_missing_group_option():
    _test_command(sub_command=list, options=["moduledata", "-d", "test-deployment"], exit_code=2)


@pytest.mark.list
@pytest.mark.list_moduledata
def test_list_moduledata_missing_group_arg():
    _test_command(sub_command=list, options=["moduledata", "-d", "test-deployment", "-g"], exit_code=2)




@pytest.mark.list
@pytest.mark.list_moduledata
def test_list_moduledata_missing_module_arg():
    _test_command(
        sub_command=list, options=["moduledata", "-d", "test-deployment", "-g", "group-name", "-m"], exit_code=2
    )


@pytest.mark.list
@pytest.mark.list_moduledata
def test_list_moduledata_non_existent_module():
    _test_command(
        sub_command=list,
        options=["moduledata", "-d", "test-deployment", "-g", "group-name", "-m", "module-name"],
        exit_code=1,
        return_result=True,
    )



# # Test `list modules` #


@pytest.mark.list
@pytest.mark.list_modules
def test_list_modules_help():
    _test_command(
        sub_command=list,
        options=["modules", "--help"],
        exit_code=0,
        expected_output="List the modules in a deployment",
    )


@pytest.mark.list
@pytest.mark.list_modules
def test_list_modules_incomplete_subcommand():
    _test_command(
        sub_command=list,
        options=[
            "modules",
        ],
        exit_code=2,
    )


@pytest.mark.list
@pytest.mark.list_modules
def test_list_modules_missing_deployment_arg():
    _test_command(sub_command=list, options=["modules", "-d"], exit_code=2)


@pytest.mark.list
@pytest.mark.list_modules
def test_list_modules_non_existent_module():
    _test_command(sub_command=list, options=["modules", "-d", "zzz"], exit_code=1, return_result=True)


@pytest.mark.list
@pytest.mark.list_modules
def test_list_modules(session_manager, mocker):
    mocker.patch("seedfarmer.cli_groups._list_group.du.generate_deployed_manifest", return_value=(DeploymentManifest(**mock_manifests.deployment_manifest)))
    _test_command(
        sub_command=list,
        options=["modules", 
                 "-p", "myapp",
                 "-d", "example-test-dev", 
                 "--debug"],
        exit_code=0
    )



@pytest.mark.list
@pytest.mark.list_build_env_params
def test_list_build_env_params(session_manager, mocker):
    mocker.patch("seedfarmer.cli_groups._list_group.du.generate_deployed_manifest", return_value=(DeploymentManifest(**mock_manifests.deployment_manifest)))
    _test_command(
        sub_command=list,
        options=["buildparams", 
                "-d","test",
                "-g","optionals",
                "-m","networking",
                "--build-id","codebuild:12345",
                "--export-local-env",
                "-p","myapp",
                "--debug",
            ],
        exit_code=0
    )

@pytest.mark.list
@pytest.mark.list_build_env_params
def test_list_build_env_params_no_dep_manifest(session_manager, mocker):
    mocker.patch("seedfarmer.cli_groups._list_group.du.generate_deployed_manifest", return_value=None)
    _test_command(
        sub_command=list,
        options=["buildparams", 
                "-d","test",
                "-g","somethingcrazy",
                "-m","networking",
                "--build-id","codebuild:12345",
                "--export-local-env",
                "-p","myapp",
                "--debug",
            ],
        exit_code=0
    )

@pytest.mark.list
@pytest.mark.list_build_env_params
def test_list_build_env_params_no_with_params(session_manager, mocker):
    mocker.patch("seedfarmer.cli_groups._list_group.du.generate_deployed_manifest", return_value=None)
    mocker.patch("seedfarmer.cli_groups._list_group.bi.get_build_env_params", return_value={"SEEDFARMER_PARAMETER":"AGreatName"})
    _test_command(
        sub_command=list,
        options=["buildparams", 
                "-d","test",
                "-g","optionals",
                "-m","networking",
                "--build-id","codebuild:12345",
                "--export-local-env",
                "-p","myapp",
                "--debug",
            ],
        exit_code=0
    )
    
@pytest.mark.list
@pytest.mark.list_build_env_params
def test_list_build_env_params_session_error(session_manager, mocker):
    mocker.patch("seedfarmer.cli_groups._list_group.du.generate_deployed_manifest", return_value=(DeploymentManifest(**mock_manifests.deployment_manifest)))
    mocker.patch("seedfarmer.cli_groups._list_group.bi.get_build_env_params", return_value={"SEEDFARMER_PARAMETER":"AGreatName"})
    _test_command(
        sub_command=list,
        options=["buildparams", 
                "-d","test",
                "-g","fsafasf",
                "-m","networking",
                "--build-id","codebuild:12345",
                "--export-local-env",
                "-p","myapp",
                "--debug",
            ],
        exit_code=0
    )

@pytest.mark.list
@pytest.mark.list_build_env_params
def test_list_build_env_params_no_export_param(session_manager, mocker):
    mocker.patch("seedfarmer.cli_groups._list_group.du.generate_deployed_manifest", return_value=(DeploymentManifest(**mock_manifests.deployment_manifest)))
    mocker.patch("seedfarmer.cli_groups._list_group.bi.get_build_env_params", return_value={"SEEDFARMER_PARAMETER":"AGreatName"})
    _test_command(
        sub_command=list,
        options=["buildparams", 
                "-d","test",
                "-g","optionals",
                "-m","networking",
                "--build-id","codebuild:12345",
                "-p","myapp",
                "--debug",
            ],
        exit_code=0
    )

@pytest.mark.list
@pytest.mark.list_build_env_params
def test_list_build_env_params_export_param(session_manager, mocker):
    mocker.patch("seedfarmer.cli_groups._list_group.du.generate_deployed_manifest", return_value=(DeploymentManifest(**mock_manifests.deployment_manifest)))
    mocker.patch("seedfarmer.cli_groups._list_group.bi.get_build_env_params", return_value={"SEEDFARMER_PARAMETER":"AGreatName"})
    mocker.patch("seedfarmer.cli_groups._list_group.commands.generate_export_raw_env_params",return_value={"SEEDFARMER_PARAMETER":"AGreatName"})
    _test_command(
        sub_command=list,
        options=["buildparams", 
                "-d","test",
                "-g","optionals",
                "-m","networking",
                "--build-id","codebuild:12345",
                "--export-local-env",
                "-p","myapp",
                "--debug",
            ],
        exit_code=0
    )

# -------------------------------------------
# -----  Test the sub-command `remove`  -----
# -------------------------------------------


@pytest.mark.remove
def test_remove_help():
    # Test the sub-command `remove --help`
    _test_command(
        sub_command=remove,
        options=["--help"],
        exit_code=0,
        expected_output="Top Level command to support removing module metadata",
    )


@pytest.mark.remove
def test_remove_missing_deployment_option():
    _test_command(
        sub_command=remove,
        options=[
            "moduledata",
        ],
        exit_code=2,
    )


@pytest.mark.remove
def test_remove_missing_deployment_argument():
    _test_command(sub_command=remove, options=["moduledata", "-d"], exit_code=2)


@pytest.mark.remove
def test_remove_missing_group_option():
    _test_command(sub_command=remove, options=["moduledata", "-d", "deployment-name"], exit_code=2)


@pytest.mark.remove
def test_remove_missing_group_arg():
    _test_command(sub_command=remove, options=["moduledata", "-d", "deployment-name", "-g"], exit_code=2)


@pytest.mark.remove
def test_remove_missing_module_option():
    _test_command(sub_command=remove, options=["moduledata", "-d", "deployment-name", "-g", "group-name"], exit_code=2)


@pytest.mark.remove
def test_remove_missing_module_arg():
    _test_command(
        sub_command=remove, options=["moduledata", "-d", "deployment-name", "-g", "group-name", "-m"], exit_code=2
    )


# @pytest.mark.remove
# def test_remove_non_existent_module():
#     _test_command(
#         sub_command=remove,
#         options=["moduledata", "-d", "deployment-name", "-g", "group-name", "-m", "zzz", "--debug"],
#         exit_code=0,
#     )


# -------------------------------------------
# -----  Test the sub-command `store`   -----
# -------------------------------------------


@pytest.mark.store
def test_store_help():
    _test_command(
        sub_command=store,
        options=["--help"],
        exit_code=0,
        expected_output="Top Level command to support storing module metadata",
    )


# Testing `store md5` #


@pytest.mark.store
@pytest.mark.store_md5
def test_store_md5_missing_deployment_option(patch_mgmt_methods):
    _test_command(
        sub_command=store,
        options=["md5"],
        exit_code=2,
    )


@pytest.mark.store
@pytest.mark.store_md5
def test_store_md5_missing_deployment_arg(patch_mgmt_methods):
    _test_command(sub_command=store, options=["md5", "-d"], exit_code=2)


@pytest.mark.store
@pytest.mark.store_md5
def test_store_md5_missing_group_option(patch_mgmt_methods):
    _test_command(sub_command=store, options=["md5", "-d", "deployment-name"], exit_code=2)


@pytest.mark.store
@pytest.mark.store_md5
def test_store_md5_missing_group_arg(patch_mgmt_methods):
    _test_command(sub_command=store, options=["md5", "-d", "deployment-name", "-g"], exit_code=2)


@pytest.mark.store
@pytest.mark.store_md5
def test_store_md5_missing_module_option(patch_mgmt_methods):
    _test_command(sub_command=store, options=["md5", "-d", "deployment-name", "-g", "group-name"], exit_code=2)


@pytest.mark.store
@pytest.mark.store_md5
def test_store_md5_missing_module_arg(patch_mgmt_methods):
    _test_command(sub_command=store, 
                  options=["md5", 
                           "-d", "deployment-name", 
                           "-g", "group-name", 
                           "-m"], 
                  exit_code=2
    )



@pytest.mark.store
@pytest.mark.store_md5
def test_store_md5_missing_type_arg(patch_mgmt_methods):
    _test_command(
        sub_command=store,
        options=["md5", "-d", "deployment-name", "-g", "group-name", "-m", "module-name", "-t"],
        exit_code=2,
    )


@pytest.mark.store
@pytest.mark.store_md5
def test_store_md5_deployspec(patch_mgmt_methods):

    # Store hash to SSM of type spec
    _test_command(
        sub_command=store,
        options=[
            "md5",
            "-d",
            "deployment-name",
            "-g",
            "group-name",
            "-m",
            "module-name",
            "-t",
            "spec" "<<< f4k3h4shmd5",
        ],
        exit_code=0,
    )


@pytest.mark.store
@pytest.mark.store_md5
def test_store_md5_bundle(patch_mgmt_methods):
    # Store hash to SSM of type bundle
    _test_command(
        sub_command=store,
        options=[
            "md5",
            "-d",
            "deployment-name",
            "-g",
            "group-name",
            "-m",
            "module-name",
            "--type",
            "bundle" "<<< f4k3h4shbund13",
        ],
        exit_code=0,
    )


# Testing `store moduledata` #


@pytest.mark.store
@pytest.mark.store_moduledata
def test_store_moduledata_missing_deployment_option():
    _test_command(
        sub_command=store,
        options=["moduledata"],
        exit_code=2,
    )


@pytest.mark.store
@pytest.mark.store_moduledata
def test_store_moduledata_deployment_arg():
    _test_command(sub_command=store, options=["moduledata", "-d"], exit_code=2)


@pytest.mark.store
@pytest.mark.store_moduledata
def test_store_moduledata_missing_group_option():
    _test_command(sub_command=store, options=["moduledata", "-d", "deployment-name"], exit_code=2)


@pytest.mark.store
@pytest.mark.store_moduledata
def test_store_moduledata_missing_group_arg():
    _test_command(sub_command=store, options=["moduledata", "-d", "deployment-name", "-g"], exit_code=2)


@pytest.mark.store
@pytest.mark.store_moduledata
def test_store_moduledata_missing_module_option():
    _test_command(sub_command=store, options=["moduledata", "-d", "deployment-name", "-g", "group-name"], exit_code=2)


@pytest.mark.store
@pytest.mark.store_moduledata
def test_store_moduledata_missing_module_arg():
    _test_command(
        sub_command=store, options=["moduledata", "-d", "deployment-name", "-g", "group-name", "-m"], exit_code=2
    )


@pytest.mark.store
@pytest.mark.store_moduledata
def test_store_moduledata(patch_mgmt_methods):
    _test_command(
        sub_command=store,
        options=["moduledata", "-d", "deployment-name", "-g", "group-name", "-m", "module-data", "--project", "myapp"],
        exit_code=0,
    )


@pytest.mark.store
@pytest.mark.store_deployspec
def test_store_deployspec_missing_deployment_option():
    _test_command(
        sub_command=store,
        options=["deployspec"],
        exit_code=2,
    )


@pytest.mark.store
@pytest.mark.store_deployspec
def test_store_deployspec_deployment_arg():
    _test_command(sub_command=store, options=["deployspec", "-d"], exit_code=2)


@pytest.mark.store
@pytest.mark.store_deployspec
def test_store_deployspec_missing_group_option():
    _test_command(sub_command=store, options=["deployspec", "-d", "deployment-name"], exit_code=2)


@pytest.mark.store
@pytest.mark.store_deployspec
def test_store_deployspec_missing_group_arg():
    _test_command(sub_command=store, options=["deployspec", "-d", "deployment-name", "-g"], exit_code=2)


@pytest.mark.store
@pytest.mark.store_deployspec
def test_store_deployspec_missing_module_option():
    _test_command(sub_command=store, options=["deployspec", "-d", "deployment-name", "-g", "group-name"], exit_code=2)


@pytest.mark.store
@pytest.mark.store_deployspec
def test_store_deployspec_missing_module_arg():
    _test_command(
        sub_command=store, options=["deployspec", "-d", "deployment-name", "-g", "group-name", "-m"], exit_code=2
    )


@pytest.mark.store
@pytest.mark.store_deployspec
def test_store_deployspec_missing_path(patch_mgmt_methods):
    _test_command(
        sub_command=store,
        options=["deployspec", "-d", "deployment-name", "-g", "group-name", "-m", "module", "--project", "myapp"],
        exit_code=2,
    )


@pytest.mark.store
@pytest.mark.store_deployspec
def test_store_deployspec_missing_acct(patch_mgmt_methods):
    path = "module/test/test"
    _test_command(
        sub_command=store,
        options=[
            "deployspec",
            "-d",
            "deployment-name",
            "-g",
            "group-name",
            "-m",
            "module",
            "--project",
            "myapp",
            "--path",
            "module/test/test" "target_region",
            "us-east-1",
        ],
        exit_code=2,
    )


@pytest.mark.store
@pytest.mark.store_deployspec
def test_store_deployspec(patch_mgmt_methods):
    path = "module/test/test"
    _test_command(
        sub_command=store,
        options=[
            "deployspec",
            "-d",
            "deployment-name",
            "-g",
            "group-name",
            "-m",
            "module",
            "--project",
            "myapp",
            "--path",
            "module/test/test",
            "--debug",
        ],
        exit_code=0,
    )


@pytest.mark.projectpolicy
def test_get_projectpolicy():

    _test_command(sub_command=projectpolicy, options=["synth"], exit_code=0)


@pytest.mark.projectpolicy
def test_get_projectpolicy_debug():

    _test_command(sub_command=projectpolicy, options=["synth", "--debug"], exit_code=0)
