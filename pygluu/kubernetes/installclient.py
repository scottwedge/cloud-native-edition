"""
 License terms and conditions for Gluu Cloud Native Edition:
 https://www.apache.org/licenses/LICENSE-2.0
"""
# TODO: Delete this script as soon as the kubernetes python client fixes CRD issue

from .yamlparser import get_logger
from pathlib import Path
import subprocess
import os
import tarfile

logger = get_logger("python-k8-installer")


# TODO: remove this section once fixed by kubernetes
def subprocess_cmd(command):
    """Execute command"""
    process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    proc_stdout = process.communicate()[0].strip()
    return proc_stdout


def install_kubernetes_client_11_0_0():
    logger.warning("https://github.com/kubernetes-client/python/issues/1022"
                   " We have provided an in-house workaround for the issue regarding  building CRDs with"
                   " kubernetes client. This workaround will be removed once resolved by kubernetes")
    kubernetes_package = os.path.join(os.path.dirname(__file__), "templates/kubernetesv11.0.0.tar.gz")
    kubernetes_package_setup = os.path.join(os.path.dirname(__file__),
                                            "kubernetes-client/kubernetesv11.0.0/setup.py")
    extract_kubernetes_client_tar(kubernetes_package)
    working_directory_kubernetes_client = os.path.join(os.path.dirname(__file__),
                                                       "kubernetes-client/kubernetesv11.0.0/kubernetes/__init__.py")
    MODULE_PATH = working_directory_kubernetes_client
    MODULE_NAME = "kubernetes"
    import importlib
    import sys
    spec = importlib.util.spec_from_file_location(MODULE_NAME, MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)


def extract_kubernetes_client_tar(tar_file):
    kubernetes_extract_folder = os.path.join(os.path.dirname(__file__), "kubernetes-client")
    extract_folder = Path(kubernetes_extract_folder)
    # logger.info("Extracting {} in {} ".format(tar_file, extract_folder))
    tr = tarfile.open(tar_file)
    tr.extractall(path=extract_folder)
    tr.close()
# TODO: End  of section to be removed
