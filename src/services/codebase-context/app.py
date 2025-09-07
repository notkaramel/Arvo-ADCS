from fastapi import FastAPI, UploadFile, File
from typing import Optional, Dict, List
import tempfile, zipfile, os, re

app = FastAPI(title="Codebase Context Extraction", version="0.3.0")

# --- Helper Constants ---
LANG_BY_EXT = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".java": "Java",
    ".go": "Go",
    ".rb": "Ruby",
    ".php": "PHP",
    ".rs": "Rust",
    ".cpp": "C++",
    ".c": "C",
    ".cs": "C#",
    ".html": "HTML",
    ".css": "CSS",
    ".sh": "Shell",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".json": "JSON",
}

PKG_MANAGERS = {
    "package.json": "npm/yarn",
    "requirements.txt": "pip",
    "Pipfile": "pipenv",
    "pyproject.toml": "poetry",
    "Gemfile": "bundler",
    "go.mod": "go modules",
    "Cargo.toml": "cargo",
    "pom.xml": "maven",
    "build.gradle": "gradle",
}

CONTAINER_FILES = {
    "Dockerfile": "dockerfile",
    "docker-compose.yml": "compose",
    "docker-compose.yaml": "compose",
    "k8s.yaml": "kubernetes",
    "k8s.yml": "kubernetes",
}

# --- Helper Functions ---

def scan_files(root_dir: str) -> List[str]:
    """Recursively list all files in a directory."""
    file_list = []
    for dirpath, _, filenames in os.walk(root_dir):
        for f in filenames:
            file_list.append(os.path.join(dirpath, f))
    return file_list

def detect_languages(files_list: List[str]) -> Dict[str, int]:
    """Count files by programming language based on extension."""
    lang_count = {}
    for f in files_list:
        _, ext = os.path.splitext(f)
        lang = LANG_BY_EXT.get(ext.lower())
        if lang:
            lang_count[lang] = lang_count.get(lang, 0) + 1
    return lang_count

def detect_pkg_managers(files_list: List[str]) -> List[str]:
    """Detect package managers present in the repo."""
    managers = []
    for f in files_list:
        name = os.path.basename(f)
        if name in PKG_MANAGERS and PKG_MANAGERS[name] not in managers:
            managers.append(PKG_MANAGERS[name])
    return managers

def detect_app_type(files_list: List[str]) -> List[str]:
    """Rudimentary detection of app type."""
    types = []
    names = [os.path.basename(f).lower() for f in files_list]
    if "manage.py" in names:
        types.append("Django")
    if "package.json" in names:
        types.append("Node.js")
    if "requirements.txt" in names or "pyproject.toml" in names:
        types.append("Python")
    if not types:
        types.append("unspecified")
    return types

def detect_architecture(root_dir: str, files_list: List[str]) -> str:
    """Rudimentary detection based on presence of certain folders."""
    dirs = [d.lower() for d in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, d))]
    if "src" in dirs and "tests" in dirs:
        return "standard multi-folder structure"
    elif "app" in dirs:
        return "single-app"
    return "unspecified"

def detect_containerization(files_list: List[str]) -> Dict[str, bool]:
    """Detect presence of container-related files."""
    result = {"dockerfile": False, "compose": False, "kubernetes": False}
    names = [os.path.basename(f) for f in files_list]
    for f in names:
        if f in CONTAINER_FILES:
            result[CONTAINER_FILES[f]] = True
    return result

def collect_env_vars(files_list: List[str]) -> Dict[str, List[str]]:
    """Scan for .env files and collect variable names."""
    env_vars = []
    for f in files_list:
        if os.path.basename(f) == ".env":
            with open(f, "r", encoding="utf-8", errors="ignore") as file:
                for line in file:
                    if "=" in line and not line.strip().startswith("#"):
                        key = line.split("=", 1)[0].strip()
                        env_vars.append(key)
    return {"variables": env_vars}

def parse_network(files_list: List[str]) -> Dict[str, List[str]]:
    """Detect ports in docker-compose files."""
    ports = []
    for f in files_list:
        if os.path.basename(f) in ["docker-compose.yml", "docker-compose.yaml"]:
            with open(f, "r", encoding="utf-8", errors="ignore") as file:
                for line in file:
                    match = re.search(r"(\d{2,5}):\d{2,5}", line)
                    if match:
                        ports.append(match.group(1))
    return {"compose_ports": ports}


# --- FastAPI Endpoints ---

@app.get('/')
async def index():
    return {"message": "Codebase Context Extraction Service is running."}

@app.post("/extract")
async def extract(repo_zip: Optional[UploadFile] = File(default=None)):
    analyzed = False
    files_list: List[str] = []
    root_dir: Optional[str] = None

    if repo_zip:
        with tempfile.TemporaryDirectory() as td:
            zip_path = os.path.join(td, "repo.zip")
            with open(zip_path, "wb") as f:
                f.write(await repo_zip.read())
            with zipfile.ZipFile(zip_path) as z:
                z.extractall(os.path.join(td, "repo"))
            root_dir = os.path.join(td, "repo")
            files_list = scan_files(root_dir)
            analyzed = True

            languages = detect_languages(files_list)
            pkg_managers = detect_pkg_managers(files_list)
            app_type = detect_app_type(files_list)
            architecture = detect_architecture(root_dir, files_list)
            containerization = detect_containerization(files_list)
            env_vars = collect_env_vars(files_list)
            network = parse_network(files_list)
    else:
        languages = {}
        pkg_managers = []
        app_type = ["unspecified"]
        architecture = "unspecified"
        containerization = {"dockerfile": False, "compose": False, "kubernetes": False}
        env_vars = {"variables": []}
        network = {"compose_ports": []}

    return {
        "analyzed": analyzed,
        "languages": languages,
        "package_managers": pkg_managers,
        "application_type": app_type,
        "architecture": architecture,
        "containerization": containerization,
        "env": env_vars,
        "network": network,
        "file_count": len(files_list)
    }
