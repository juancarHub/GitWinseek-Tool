import os
import sys
import json
import shutil
import subprocess
import argparse
import ctypes
import time
from pathlib import Path
from datetime import datetime


# Usage ----->'init', 'refresh', 'remove', 'refresh-all', 'show-registry', 'cleanup') :

# python GitWinSeek.py refresh "C:\Users\LENOVO\Desktop\git_win_tool"

#Compilacion:

# pyinstaller --noconfirm --clean --noconsole  --icon=git_win_tool.ico --name GitWinSeek --onedir --add-data "icons;icons" GitWinSeek.py




APP_NAME = "GitWinSeek"
DESKTOP_DIR = Path.home() / "Desktop"
APPDATA = Path(os.environ.get("APPDATA", Path.home()))
CONFIG_DIR = APPDATA / APP_NAME
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
REGISTRY_FILE = CONFIG_DIR / "tracked_repos.json"
BASE_DIR = Path(__file__).resolve().parent
ICON_SOURCE_DIR = BASE_DIR / "icons"
ICON_FOLDER_NAME = ".jcgiticon"
ICON_FILES = {
    "conflict": "Pendiente_conflictos.ico", # Rojo
    "push": "Pendiente_Push.ico", # Azul
    "local": "con_cambios_locales.ico", # Naranja
    "clean": "repo_limpio.ico" # verde
}



def show_usage_box():
    msg = (
        "Uso incorrecto de GitWinSeek.\n\n"
        "Comandos disponibles:\n\n"
        "init <path>\n"
        "refresh <path>\n"
        "remove <path>\n"
        "refresh-all\n"
        "show-registry\n"
        "cleanup\n"
        "watch [--interval N] [--verbose]\n\n"
        "Ejemplo:\n"
        "GitWinSeek refresh C:\\mi_repo"
    )

    ctypes.windll.user32.MessageBoxW(
        0,
        msg,
        "GitWinSeek - Uso incorrecto",
        0x10  # icono error
    )

def watch_loop(interval=300, verbose=False):
    print(f"GitWinSeek watch activo. Intervalo: {interval} segundos")
    while True:
        try:
            refresh_all(verbose=verbose)
        except Exception as e:
            print(f"Error en watch: {e}")
        time.sleep(interval)

def load_registry():
    if not REGISTRY_FILE.exists():
        return {"repos": []}
    with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_registry(data):
    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def register_repo(path):
    data = load_registry()
    repos = data["repos"]

    for r in repos:
        if r["path"].lower() == str(path).lower():
            return

    repos.append({
        "path": str(path),
        "last_init": datetime.now().isoformat(),
        "last_refresh": datetime.now().isoformat()
    })

    save_registry(data)

def unregister_repo(path):
    data = load_registry()
    repos = data["repos"]

    repos = [r for r in repos if r["path"].lower() != str(path).lower()]

    data["repos"] = repos
    save_registry(data)

def run_git(repo, args):
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=repo,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.stdout.strip(), result.returncode
    except Exception:
        return "", 1

def get_repo_root(path):
    out, code = run_git(path, ["rev-parse", "--show-toplevel"])
    if code != 0:
        return None
    return Path(out)

def has_conflicts(repo):
    out, _ = run_git(repo, ["diff", "--name-only", "--diff-filter=U"])
    return bool(out.strip())

def has_local_changes(repo):
    out, _ = run_git(repo, ["status", "--porcelain"])
    return bool(out.strip())

def ahead_of_remote(repo):
    out, code = run_git(repo, ["rev-list", "--left-right", "--count", "HEAD...@{upstream}"])
    if code != 0:
        return None
    ahead = int(out.split()[0])
    return ahead > 0

def get_state(repo):
    if has_conflicts(repo):
        return "conflict"

    if has_local_changes(repo):
        return "local"

    ahead = ahead_of_remote(repo)

    if ahead is None:
        return "conflict"

    if ahead:
        return "push"

    return "clean"

def ensure_icon_pack(repo_root):

    icon_dir = repo_root / ICON_FOLDER_NAME

    if not icon_dir.exists():
        icon_dir.mkdir()

    for name in ICON_FILES.values():
        target = icon_dir / name
        source = ICON_SOURCE_DIR / name

        if not target.exists():
            shutil.copy2(source, target)

def write_desktop_ini(repo_root, state):
    icon_dir = repo_root / ICON_FOLDER_NAME
    icon_file = ICON_FILES[state]
    icon_path = (icon_dir / icon_file).resolve()

    desktop_ini = repo_root / "desktop.ini"

    # Si ya existe, quitar atributos para poder reescribirlo
    if desktop_ini.exists():
        subprocess.run(f'attrib -h -s "{desktop_ini}"', shell=True)

    content = (
        "[.ShellClassInfo]\n"
        f"IconResource={icon_path},0\n"
         "ConfirmFileOp=0\n"
        f"InfoTip= Registrada con GitWinSeek | Estado:--> {state} \n"
        #"InfoTip=Esta carpeta esta registrada con GitWinSeek.\n"
    )

    with open(desktop_ini, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(content)

    # La carpeta NO oculta; solo read-only para que Windows procese desktop.ini
    subprocess.run(f'attrib +r "{repo_root}"', shell=True)

    # El desktop.ini sí queda oculto y de sistema
    subprocess.run(f'attrib +h +s "{desktop_ini}"', shell=True)
    
def apply_visual_refresh(repo_root):
    time.sleep(0.15)
    clear_icon_cache() 
    refresh_explorer_path(repo_root)
    refresh_explorer_path(repo_root.parent)

    if is_on_desktop(repo_root):
        clear_icon_cache() 
        refresh_explorer_path(DESKTOP_DIR)
        time.sleep(0.10)
        refresh_explorer_path(DESKTOP_DIR)
                    
def is_on_desktop(path: Path) -> bool:
    try:
        return path.parent.resolve() == DESKTOP_DIR.resolve()
    except Exception:
        return False

def clear_icon_cache():
    subprocess.run(
        
        [r"C:\Windows\System32\ie4uinit.exe", "-ClearIconCache"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def refresh_explorer_path(path):
    SHCNE_UPDATEITEM = 0x00002000
    SHCNE_UPDATEDIR = 0x00001000
    SHCNE_ASSOCCHANGED = 0x08000000
    SHCNF_PATHW = 0x0005
    SHCNF_FLUSH = 0x1000

    p = str(path)

    ctypes.windll.shell32.SHChangeNotify(
        SHCNE_UPDATEITEM, SHCNF_PATHW | SHCNF_FLUSH, p, None
    )
    ctypes.windll.shell32.SHChangeNotify(
        SHCNE_UPDATEDIR, SHCNF_PATHW | SHCNF_FLUSH, p, None
    )
    ctypes.windll.shell32.SHChangeNotify(
        SHCNE_ASSOCCHANGED, SHCNF_FLUSH, None, None
    )
    DESKTOP_DIR = Path.home() / "Desktop"

def init_repo(path):

    repo_root = get_repo_root(path)

    if not repo_root:
        print("No es un repositorio Git")
        return

    ensure_icon_pack(repo_root)
    ensure_git_exclude(repo_root)

    state = get_state(repo_root)

    write_desktop_ini(repo_root, state)


    register_repo(repo_root)
    clear_icon_cache()
    refresh_explorer_path(repo_root)
    refresh_explorer_path(repo_root.parent)

    print(f"Repositorio inicializado: {repo_root}")
    print(f"Estado: {state}")

def refresh_repo(path):

    repo_root = get_repo_root(path)

    if not repo_root:
        print("No es un repositorio Git")
        return


    ensure_git_exclude(repo_root)
    
    ensure_icon_pack(repo_root)

    state = get_state(repo_root)

    write_desktop_ini(repo_root, state)

    clear_icon_cache()
    refresh_explorer_path(repo_root)
    #refresh_explorer_path(repo_root.parent)
    
    data = load_registry()

    for r in data["repos"]:
        if r["path"].lower() == str(repo_root).lower():
            r["last_refresh"] = datetime.now().isoformat()

    save_registry(data)

    print(f"Refrescado: {repo_root}")
    print(f"Estado: {state}")
    
def ensure_git_exclude(repo_root):
    git_dir = repo_root / ".git"
    exclude_file = git_dir / "info" / "exclude"

    if not exclude_file.parent.exists():
        exclude_file.parent.mkdir(parents=True, exist_ok=True)

    existing = ""
    if exclude_file.exists():
        existing = exclude_file.read_text(encoding="utf-8", errors="ignore")

    lines_to_add = []
    needed = ["desktop.ini", ".jcgiticon/"]

    for line in needed:
        if line not in existing.splitlines():
            lines_to_add.append(line)

    if lines_to_add:
        with open(exclude_file, "a", encoding="utf-8", newline="\n") as f:
            if existing and not existing.endswith("\n"):
                f.write("\n")
            for line in lines_to_add:
                f.write(line + "\n")

def remove_repo(path):

    repo_root = get_repo_root(path)

    if not repo_root:
        print("No es repo")
        return

    desktop_ini = repo_root / "desktop.ini"

    if desktop_ini.exists():
        desktop_ini.unlink()

    icon_dir = repo_root / ICON_FOLDER_NAME

    if icon_dir.exists():
        shutil.rmtree(icon_dir)

    unregister_repo(repo_root)

    clear_icon_cache() 
    refresh_explorer_path(repo_root)
    refresh_explorer_path(repo_root.parent)

    print("Seguimiento visual eliminado")

def refresh_all(verbose=False):

    data = load_registry()

    for r in list(data["repos"]):

        path = Path(r["path"])

        if not path.exists():
            if verbose:
                print("Ruta eliminada:", path)
            unregister_repo(path)
            continue

        repo_root = get_repo_root(path)

        if not repo_root:
            if verbose:
                print("Ya no es repo:", path)
            unregister_repo(path)
            continue

        state = get_state(repo_root)

        write_desktop_ini(repo_root, state)

        r["last_refresh"] = datetime.now().isoformat()
        #clear_icon_cache()
        #refresh_explorer_path(repo_root)
        #refresh_explorer_path(repo_root.parent)

        if verbose:
            print(repo_root, state)
    clear_icon_cache()        
    refresh_explorer_path(repo_root)

    save_registry(data)
    print(APPDATA)

def show_registry():

    data = load_registry()

    for r in data["repos"]:
        print(r["path"])

def cleanup(verbose=False):

    data = load_registry()

    repos = []

    for r in data["repos"]:

        path = Path(r["path"])

        if not path.exists():
            if verbose:
                print("Eliminando ruta inexistente:", path)
            continue

        repo_root = get_repo_root(path)

        if not repo_root:
            if verbose:
                print("Ya no es repo:", path)
            continue

        repos.append(r)

    data["repos"] = repos

    save_registry(data)

def main():
    
    if len(sys.argv) == 1:
        show_usage_box()
    # sys.exit(1)
        
    parser = argparse.ArgumentParser()

    sub = parser.add_subparsers(dest="cmd")
    
    p_watch = sub.add_parser("watch")
    
    p_watch.add_argument("--interval", type=int, default=300)
    
    p_watch.add_argument("--verbose", action="store_true")

    p1 = sub.add_parser("init")
    p1.add_argument("path")

    p2 = sub.add_parser("refresh")
    p2.add_argument("path")

    p3 = sub.add_parser("remove")
    p3.add_argument("path")

    sub.add_parser("refresh-all")

    sub.add_parser("show-registry")

    sub.add_parser("cleanup")

    args = parser.parse_args()

    if args.cmd == "init":
        init_repo(Path(args.path))

    elif args.cmd == "refresh":
        refresh_repo(Path(args.path))

    elif args.cmd == "remove":
        remove_repo(Path(args.path))

    elif args.cmd == "refresh-all":
        refresh_all()

    elif args.cmd == "cleanup":
        cleanup()

    elif args.cmd == "show-registry":
        show_registry()
        
    elif args.cmd == "watch":
        watch_loop(interval=args.interval, verbose=args.verbose)

    else:
        show_usage_box()
        

if __name__ == "__main__":
    main()