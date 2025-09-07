from fastapi import FastAPI, UploadFile, File, Form
from typing import Optional, Dict, List
import tempfile, zipfile, os, re, yaml

app = FastAPI(title="Codebase Context Extraction", version="0.2.0")

# --- Keep LANG_BY_EXT, PKG_MANAGERS, and helper functions as you already have ---
# scan_files, detect_languages, detect_pkg_managers, detect_app_type,
# detect_architecture, detect_containerization, collect_env_vars, parse_network
# ... (unchanged) ...

@app.post("/extract")
async def extract(
    repo_url: Optional[str] = Form(default=None),
    repo_zip: Optional[UploadFile] = File(default=None)
):
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
        "repo_url": repo_url,
        "languages": languages,
        "package_managers": pkg_managers,
        "application_type": app_type,
        "architecture": architecture,
        "containerization": containerization,
        "env": env_vars,
        "network": network,
        "file_count": len(files_list)
    }
