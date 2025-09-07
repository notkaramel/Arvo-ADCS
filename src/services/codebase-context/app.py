
from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
from typing import Dict, List, Optional
import tempfile, zipfile, os, re, json, yaml

app = FastAPI(title="Codebase Context Extraction", version="0.1.0")

LANG_BY_EXT = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".go": "Go",
    ".java": "Java",
    ".rb": "Ruby",
    ".rs": "Rust",
    ".php": "PHP",
    ".kt": "Kotlin",
    ".swift": "Swift",
    ".cs": "C#",
    ".cpp": "C++",
    ".c": "C",
    ".m": "Objective-C",
    ".scala": "Scala",
}

PKG_MANAGERS = {
    "npm": ["package.json"],
    "pnpm": ["pnpm-lock.yaml", "pnpm-workspace.yaml"],
    "yarn": ["yarn.lock"],
    "pip": ["requirements.txt"],
    "poetry": ["pyproject.toml", "poetry.lock"],
    "pipenv": ["Pipfile", "Pipfile.lock"],
    "poetry2nix": ["poetry.lock"],
    "go": ["go.mod", "go.sum"],
    "maven": ["pom.xml"],
    "gradle": ["build.gradle", "build.gradle.kts", "settings.gradle", "gradlew"],
    "cargo": ["Cargo.toml", "Cargo.lock"],
    "composer": ["composer.json", "composer.lock"],
    "swiftpm": ["Package.swift"],
    "dotnet": ["*.csproj", "*.sln"],
}

def scan_files(root_dir: str) -> List[str]:
    paths = []
    for base, _, files in os.walk(root_dir):
        for f in files:
            paths.append(os.path.join(base, f))
    return paths

def detect_languages(files: List[str]) -> Dict[str, int]:
    counts = {}
    for p in files:
        _, ext = os.path.splitext(p)
        if ext in LANG_BY_EXT:
            lang = LANG_BY_EXT[ext]
            counts[lang] = counts.get(lang, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: -x[1]))

def detect_pkg_managers(files: List[str]) -> List[str]:
    res = set()
    for pm, patterns in PKG_MANAGERS.items():
        for pat in patterns:
            if "*" in pat:
                # simple glob-like
                regex = re.compile("^" + pat.replace(".", r"\.").replace("*", ".*") + "$")
                if any(regex.search(os.path.basename(f)) for f in files):
                    res.add(pm)
            else:
                if any(os.path.basename(f) == pat for f in files):
                    res.add(pm)
    return sorted(res)

def detect_app_type(files: List[str]) -> List[str]:
    indicators = []
    names = [os.path.basename(f).lower() for f in files]
    paths_l = [f.lower() for f in files]

    # Basic heuristics
    if any(n in names for n in ["next.config.js", "next.config.mjs", "nuxt.config.js", "astro.config.mjs", "vite.config.ts", "vite.config.js"]):
        indicators.append("frontend")
    if any(n in names for n in ["package.json"]) and any("express" in open(f, errors="ignore").read().lower() for f in files if f.endswith("package.json")):
        indicators.append("api-backend")
    if any(n in names for n in ["fastapi", "flask", "django"]):
        pass  # handled below by content scan
    # Python frameworks
    for f in files:
        if f.endswith(".py"):
            try:
                txt = open(f, errors="ignore").read().lower()
                if "fastapi" in txt or "flask" in txt or "django" in txt:
                    indicators.append("api-backend")
                    break
            except Exception:
                pass
    # Go http server
    for f in files:
        if f.endswith(".go"):
            try:
                txt = open(f, errors="ignore").read().lower()
                if re.search(r'http\.listenandserve|gin-gonic|echo\.new\(|fiber', txt):
                    indicators.append("api-backend")
                    break
            except Exception:
                pass
    # React/Vue/Angular presence
    if any(n in names for n in ["angular.json", "vue.config.js"]) or any("/src/components" in p for p in paths_l):
        indicators.append("frontend")

    return sorted(set(indicators)) or ["unspecified"]

def detect_architecture(root_dir: str, files: List[str]) -> str:
    # Simple heuristic: multi services if docker-compose has multiple services or multiple Dockerfiles in subdirs
    compose_files = [f for f in files if os.path.basename(f).lower() in ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]]
    dockerfiles = [f for f in files if os.path.basename(f).lower() == "dockerfile"]
    if compose_files:
        try:
            data = yaml.safe_load(open(compose_files[0]))
            if isinstance(data, dict) and "services" in data and len(data["services"]) > 1:
                return "multi-microservices"
        except Exception:
            pass
    # multiple dockerfiles in nested dirs often indicates multi services
    dockerfile_dirs = set(os.path.dirname(f) for f in dockerfiles)
    if len(dockerfile_dirs) > 1:
        return "multi-microservices"
    if dockerfiles:
        return "single-microservice"
    return "monolith"

def detect_containerization(files: List[str]) -> Dict[str, bool]:
    names = [os.path.basename(f).lower() for f in files]
    k8s = any(n in names for n in ["deployment.yaml", "deployment.yml", "kustomization.yaml", "kustomization.yml", "chart.yaml", "chart.yml"])
    compose = any(n in names for n in ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"])
    dockerfile = any(os.path.basename(f).lower() == "dockerfile" for f in files)
    return {"dockerfile": dockerfile, "compose": compose, "kubernetes": k8s}

def collect_env_vars(files: List[str]) -> Dict[str, List[str]]:
    envs = set()
    for f in files:
        bn = os.path.basename(f).lower()
        if bn == ".env" or bn.startswith(".env"):
            try:
                for line in open(f, errors="ignore"):
                    m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
                    if m:
                        envs.add(m.group(1))
            except Exception:
                pass
        # scan for process.env / os.environ
        try:
            if f.endswith((".js",".ts",".tsx",".jsx")):
                txt = open(f, errors="ignore").read()
                for m in re.finditer(r"process\.env\.([A-Za-z_][A-Za-z0-9_]*)", txt):
                    envs.add(m.group(1))
            if f.endswith(".py"):
                txt = open(f, errors="ignore").read()
                for m in re.finditer(r"os\.environ\.get\(['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\)", txt):
                    envs.add(m.group(1))
        except Exception:
            pass
    return {"variables": sorted(envs)}

def parse_network(files: List[str]) -> Dict[str, List[dict]]:
    compose_files = [f for f in files if os.path.basename(f).lower() in ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]]
    networks = []
    ports = []
    if compose_files:
        for cf in compose_files:
            try:
                data = yaml.safe_load(open(cf))
                if "services" in data:
                    for sname, spec in data["services"].items():
                        if isinstance(spec, dict):
                            ps = spec.get("ports", [])
                            for p in ps or []:
                                ports.append({"service": sname, "mapping": p})
            except Exception:
                pass
    return {"compose_ports": ports}

@app.post("/")
async def extract(repo_url: Optional[str] = Form(default=None),
                  repo_zip: Optional[UploadFile] = File(default=None)):
    analyzed = False
    tmpdir = None
    files_list = []
    root_dir = None

    if repo_zip is not None:
        with tempfile.TemporaryDirectory() as td:
            tmpdir = td
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
            net = parse_network(files_list)
    else:
        languages = {}
        pkg_managers = []
        app_type = ["unspecified"]
        architecture = "unspecified"
        containerization = {"dockerfile": False, "compose": False, "kubernetes": False}
        env_vars = {"variables": []}
        net = {"compose_ports": []}

    return {
        "analyzed": analyzed,
        "repo_url": repo_url,
        "languages": languages,
        "package_managers": pkg_managers,
        "application_type": app_type,
        "architecture": architecture,
        "containerization": containerization,
        "env": env_vars,
        "network": net,
        "file_count": len(files_list)
    }
