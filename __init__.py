# Title: ComfyUI Install Customs Nodes and javascript files
# Author: AlekPet
# Version: 2024.08.08
import os
import importlib.util
import subprocess
import sys
import shutil
import __main__

# import pkgutil
import re
import threading
import ast
from concurrent.futures import ThreadPoolExecutor

python = sys.executable

# User extension files in custom_nodes
extension_folder = os.path.dirname(os.path.realpath(__file__))

# ComfyUI folders web
folder_web = os.path.join(os.path.dirname(os.path.realpath(__main__.__file__)), "web")
folder_comfyui_web_extensions = os.path.join(folder_web, "extensions")

folder__web_lib = os.path.join(folder_web, "lib")
extension_dirs = [
    "web_alekpet_nodes",
]

# Debug mode
DEBUG = False

# NODE_CLASS_MAPPINGS = dict()  # dynamic class nodes append in mappings
# NODE_DISPLAY_NAME_MAPPINGS = dict()  # dynamic display names nodes append mappings names

humanReadableTextReg = re.compile("(?<=[a-z0-9])([A-Z])|(?<=[A-Z0-9])([A-Z][a-z]+)")
module_name_cut_version = re.compile("[>=<]")

installed_modules = {}
# installed_modules = {m[1] for m in pkgutil.iter_modules()}

def get_version_extension():
    version = '3'
    # toml_file = os.path.join(extension_folder, 'pyproject.toml')
    # if(os.path.isfile(toml_file)):
    #     try:
    #         with open(toml_file, "r") as v:
    #             version = list(filter(lambda l: l.startswith("version"),v.readlines()))[0]
    #             version = version.split("=")[1].replace("\"","").strip()
    #             return f" \033[1;34mv{version}\033[0m\033[1;35m"
    #     except Exception as e:
    #         print(e)

    return version

def log(*text):
    if DEBUG:
        print("".join(map(str, text)))


def information(datas):
    for info in datas:
        if not DEBUG:
            print(info, end="\r", flush=True)


def printColorInfo(text, color="\033[92m"):
    CLEAR = "\033[0m"
    print(f"{color}{text}{CLEAR}")


def get_classes(code):
    tree = ast.parse(code)
    return [
        n.name
        for n in ast.walk(tree)
        if isinstance(n, ast.ClassDef) and "Node" in n.name
    ]


def addComfyUINodesToMapping(nodeElement):
    log(f"  -> Find class execute node <{nodeElement}>, add NODE_CLASS_MAPPINGS ...")
    node_folder = os.path.join(extension_folder, nodeElement)
    for f in os.listdir(node_folder):
        ext = os.path.splitext(f)
        # Find files extensions .py
        if (
            os.path.isfile(os.path.join(node_folder, f))
            and not f.startswith("__")
            and ext[1] == ".py"
            and ext[0] != "__init__"
        ):
            # remove extensions .py
            module_without_py = f.replace(ext[1], "")
            # Import module
            spec = importlib.util.spec_from_file_location(
                module_without_py, os.path.join(node_folder, f)
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            classes_names = list(
                filter(
                    lambda p: callable(getattr(module, p)) and p.find("Node") != -1,
                    dir(module),
                )
            )
            for class_module_name in classes_names:
                # Check module
                if (
                    class_module_name
                    and class_module_name not in NODE_CLASS_MAPPINGS.keys()
                ):
                    log(
                        f"    [*] Class node found '{class_module_name}' add to NODE_CLASS_MAPPINGS..."
                    )
                    NODE_CLASS_MAPPINGS.update(
                        {class_module_name: getattr(module, class_module_name)}
                    )
                    NODE_DISPLAY_NAME_MAPPINGS.update(
                        {
                            class_module_name: humanReadableTextReg.sub(
                                " \\1\\2", class_module_name
                            )
                        }
                    )


def getNamesNodesInsidePyFile(nodeElement):
    node_folder = os.path.join(extension_folder, nodeElement)
    cls_names = []
    for f in os.listdir(node_folder):
        ext = os.path.splitext(f)
        if (
            os.path.isfile(os.path.join(node_folder, f))
            and not f.startswith("__")
            and ext[1] == ".py"
            and ext[0] != "__init__"
        ):
            with open(os.path.join(node_folder, f), "r") as pyf:
                cls_names.extend(get_classes(pyf.read()))
    return cls_names


def checkFolderIsset():
    log(f"*  Check and make not isset dirs...")
    for d in extension_dirs:
        dir_ = os.path.join(extension_folder, d)
        if not os.path.exists(dir_):
            log(f"* Dir <{d}> is not found, create...")
            os.mkdir(dir_)
            log(f"* Dir <{d}> created!")


def module_install(commands, cwd="."):
    result = subprocess.Popen(
        commands,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    out = threading.Thread(target=information, args=(result.stdout,))
    err = threading.Thread(target=information, args=(result.stderr,))
    out.start()
    err.start()
    out.join()
    err.join()

    return result.wait()


def get_installed_modules():
    result = subprocess.run(
        [sys.executable, "-m", "pip", "list", "--format=freeze"],
        capture_output=True,
        text=True,
        check=True,
    )
    return {line.split("==")[0].lower() for line in result.stdout.splitlines()}


def checkModules(nodeElement):
    file_requir = os.path.join(extension_folder, nodeElement, "requirements.txt")
    if os.path.exists(file_requir):
        log("  -> File 'requirements.txt' found!")
        with open(file_requir) as f:
            required_modules = {
                module_name_cut_version.split(line.strip())[0]
                for line in f
                if not line.startswith("#")
            }

        modules_to_install = required_modules - installed_modules

        if modules_to_install:
            module_install(
                [sys.executable, "-m", "pip", "install", *modules_to_install]
            )


def install_node(nodeElement):
    log(f"* Node <{nodeElement}> is found, installing...")
    web_extensions_dir = os.path.join(extension_folder, extension_dirs[0])

    extensions_dirs_copy = ["js", "css", "assets", "lib", "fonts"]
    for dir_name in extensions_dirs_copy:
        folder_curr = os.path.join(extension_folder, nodeElement, dir_name)
        if os.path.exists(folder_curr):
            folder_curr_dist = os.path.join(
                web_extensions_dir,
                dir_name,
                nodeElement.lower() if dir_name != "js" else web_extensions_dir,
            )
            shutil.copytree(folder_curr, folder_curr_dist, dirs_exist_ok=True)

    clsNodes = getNamesNodesInsidePyFile(nodeElement)
    clsNodesText = "\033[93m" + ", ".join(clsNodes) + "\033[0m" if clsNodes else ""
    printColorInfo(f"Node -> {nodeElement}: {clsNodesText} \033[92m[Loading] ")

    checkModules(nodeElement)
    # addComfyUINodesToMapping(nodeElement) # dynamic class nodes append in mappings


def installNodes():
    global installed_modules
    log(f"\n-------> AlekPet Node Installing [DEBUG] <-------")
    printColorInfo(f"### [START] ComfyUI AlekPet Nodes{get_version_extension()} ###", "\033[1;35m")

    # Remove files in lib directory
    libfiles = ["fabric.js"]
    for file in libfiles:
        filePath = os.path.join(folder__web_lib, file)
        if os.path.isfile(filePath):
            os.remove(filePath)

    # Remove old folder if exist
    oldDirNodes = os.path.join(folder_comfyui_web_extensions, "AlekPet_Nodes")
    if os.path.exists(oldDirNodes):
        shutil.rmtree(oldDirNodes)

    # Clear folder web_alekpet_nodes
    web_extensions_dir = os.path.join(extension_folder, extension_dirs[0])
    if os.path.exists(web_extensions_dir):
        shutil.rmtree(web_extensions_dir)

    checkFolderIsset()

    installed_modules = get_installed_modules()

    nodes = [
        nodeElement
        for nodeElement in os.listdir(extension_folder)
        if not nodeElement.startswith("__")
        and nodeElement.endswith("Node")
        and os.path.isdir(os.path.join(extension_folder, nodeElement))
    ]

    with ThreadPoolExecutor() as executor:
        executor.map(install_node, nodes)

    printColorInfo(f"### [END] ComfyUI AlekPet Nodes ###", "\033[1;35m")


# Mount web directory
WEB_DIRECTORY = f"./{extension_dirs[0]}"


# Install nodes
installNodes()

from .gcp_storage import NODE_CLASS_MAPPINGS as GCP_NODE_CLASS_MAPPINGS
from .gcp_storage import NODE_DISPLAY_NAME_MAPPINGS as GCP_NODE_DISPLAY_NAME_MAPPINGS

from .batch_tester import NODE_CLASS_MAPPINGS as BATCH_TESTER_NODE_CLASS_MAPPINGS
from .batch_tester import NODE_DISPLAY_NAME_MAPPINGS as BATCH_TESTER_NODE_DISPLAY_NAME_MAPPINGS

from .batch_previewer import NODE_CLASS_MAPPINGS as BATCH_PREVIEWER_NODE_CLASS_MAPPINGS
from .batch_previewer import NODE_DISPLAY_NAME_MAPPINGS as BATCH_PREVIEWER_NODE_DISPLAY_NAME_MAPPINGS

from .utils import NODE_CLASS_MAPPINGS as UTILS_NODE_CLASS_MAPPINGS
from .utils import NODE_DISPLAY_NAME_MAPPINGS as UTILS_NODE_DISPLAY_NAME_MAPPINGS

from .mask_drawer import NODE_CLASS_MAPPINGS as MASK_DRAWER_NODE_CLASS_MAPPINGS
from .mask_drawer import NODE_DISPLAY_NAME_MAPPINGS as MASK_DRAWER_NODE_DISPLAY_NAME_MAPPINGS

from .PainterNode.painter_node import PainterNode

NODE_CLASS_MAPPINGS = {**GCP_NODE_CLASS_MAPPINGS,
                       **BATCH_TESTER_NODE_CLASS_MAPPINGS,
                       **BATCH_PREVIEWER_NODE_CLASS_MAPPINGS,
                       **UTILS_NODE_CLASS_MAPPINGS,
                       **MASK_DRAWER_NODE_CLASS_MAPPINGS,
                       "PainterNode": PainterNode}

NODE_DISPLAY_NAME_MAPPINGS = {**GCP_NODE_DISPLAY_NAME_MAPPINGS,
                              **BATCH_TESTER_NODE_DISPLAY_NAME_MAPPINGS,
                              **BATCH_PREVIEWER_NODE_DISPLAY_NAME_MAPPINGS,
                              **UTILS_NODE_DISPLAY_NAME_MAPPINGS,
                              **MASK_DRAWER_NODE_DISPLAY_NAME_MAPPINGS,
                              "PainterNode": "Painter Node"}

# WEB_DIRECTORY = "./js"

# __all__ = ['NODE_CLASS_MAPPINGS',
#            'NODE_DISPLAY_NAME_MAPPINGS',
#            'WEB_DIRECTORY']