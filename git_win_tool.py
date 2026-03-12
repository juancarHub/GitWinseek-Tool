import os
import sys
import json
import subprocess
import tkinter as tk
from tkinter import messagebox, simpledialog
from datetime import datetime
from pathlib import Path
from gitwinseek_core import refresh_repo, init_repo, get_repo_root


#pyinstaller --onefile --noconsole --windowed --icon=git_win_tool.ico --add-data "git_win_tool.ico;." git_win_tool.py



APP_TITLE = "Git Branch Peek Tool"
WIN_W = 920#860
WIN_H = 560#620


MIN_UI_SCALE = 0.75
MAX_UI_SCALE = 1.45

INFO_SCALE = 1.00
ACTIONS_SCALE = 1.29



def get_app_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

SETTINGS_FILE = get_app_base_dir() / "git_win_tool_settings.json"

def sync_gitwinseek(repo_path):
    try:
        from gitwinseek_core import refresh_repo
        refresh_repo(repo_path)
    except Exception as e:
        print(f"[GitWinSeek sync error] {e}")

def clamp_ui_scale(value):
    try:
        value = float(value)
    except Exception:
        return 1.0
    return max(MIN_UI_SCALE, min(MAX_UI_SCALE, value))

def load_settings():
    default = {
        "ui_scale": 1.0,
        "main_geometry": f"{WIN_W}x{WIN_H}",
        "branch_geometry": "800x520",
        "commit_geometry": "920x560",
        "output_geometry": "780x460",
    }

    if not SETTINGS_FILE.exists():
        return default

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            default.update(data)
    except Exception as e:
        print(f"[SETTINGS LOAD ERROR] {e}")

    default["ui_scale"] = clamp_ui_scale(default.get("ui_scale", 1.0))
    return default

def save_settings(data):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[SETTINGS SAVE ERROR] {e}")

APP_SETTINGS = load_settings()
UI_SCALE = APP_SETTINGS.get("ui_scale", 1.0)

def scale(value):
    return max(1, int(round(value * UI_SCALE)))
def scale_info(value):
    return max(1, int(round(value * UI_SCALE * INFO_SCALE)))
def scale_actions(value):
    return max(1, int(round(value * UI_SCALE * ACTIONS_SCALE)))
def resource_path(filename):
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / filename
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / filename
    return Path(__file__).resolve().parent / filename


# =========================
# Utilidades Git
# =========================

def _hidden_subprocess_kwargs():
    if os.name != "nt":
        return {}

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    return {
        "startupinfo": startupinfo,
        "creationflags": subprocess.CREATE_NO_WINDOW,
    }

def run_git_command(args, cwd):
    try:
        kwargs = {
            "cwd": cwd,
            "capture_output": True,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "shell": False,
        }
        kwargs.update(_hidden_subprocess_kwargs())

        result = subprocess.run(["git"] + args, **kwargs)
        rc = result.returncode
        out = result.stdout.strip()
        err = result.stderr.strip()
        if rc == 0:
            maybe_refresh_gitwinseek(args, cwd)
        
        
        return rc, out, err
    
    except Exception as e:
        return 1, "", str(e)

def maybe_refresh_gitwinseek(args, repo_path):
    commands_that_change_repo = {
        "commit",
        "push",
        "pull",
        "merge",
        "rebase",
        "checkout",
        "reset",
        "stash",
    }

    if args and args[0] in commands_that_change_repo:
        try:
            from gitwinseek_core import refresh_repo
            refresh_repo(repo_path)
        except Exception:
            pass

def find_git_root(start_path):
    path = os.path.abspath(start_path)

    if os.path.isfile(path):
        path = os.path.dirname(path)

    while True:
        git_entry = os.path.join(path, ".git")
        if os.path.isdir(git_entry) or os.path.isfile(git_entry):
            return path

        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent

def is_git_available():
    try:
        kwargs = {
            "capture_output": True,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "shell": False,
        }
        kwargs.update(_hidden_subprocess_kwargs())

        result = subprocess.run(["git", "--version"], **kwargs)
        return result.returncode == 0
    except Exception:
        return False

def get_branch_info(repo_path):
    repo_name = os.path.basename(repo_path)

    rc, stdout, _ = run_git_command(["branch", "--show-current"], repo_path)
    if rc == 0 and stdout:
        return repo_name, stdout, False

    rc, stdout, _ = run_git_command(["rev-parse", "--abbrev-ref", "HEAD"], repo_path)
    if rc == 0:
        if stdout == "HEAD":
            rc2, commit_out, _ = run_git_command(["rev-parse", "--short", "HEAD"], repo_path)
            short_commit = commit_out if rc2 == 0 and commit_out else "desconocido"
            return repo_name, f"DETACHED @ {short_commit}", True
        return repo_name, stdout, False

    return repo_name, "desconocido", False

def get_working_tree_status(repo_path):
    rc, stdout, _ = run_git_command(["status", "--porcelain"], repo_path)
    if rc != 0:
        return False, 0

    lines = [line for line in stdout.splitlines() if line.strip()]
    return len(lines) > 0, len(lines)

def get_working_tree_details(repo_path):
    rc, stdout, stderr = run_git_command(["status", "--short"], repo_path)
    if rc != 0:
        return False, (stderr or stdout or "No se pudo obtener el estado detallado.")

    lines = [line for line in stdout.splitlines() if line.strip()]
    if not lines:
        return True, "Working tree limpio.\n\nNo hay archivos modificados, nuevos o eliminados."

    content = []
    content.append("Estado detallado del working tree")
    content.append("")
    content.append(f"Total de entradas: {len(lines)}")
    content.append("")
    content.append(stdout)

    return True, "\n".join(content)

def get_ahead_behind(repo_path):
    rc, stdout, _ = run_git_command(["status", "-sb"], repo_path)
    if rc != 0 or not stdout:
        return {
            "ahead": 0,
            "behind": 0,
            "text": "No se pudo comprobar",
            "has_remote": False,
        }

    first_line = stdout.splitlines()[0]

    if "..." not in first_line:
        return {
            "ahead": 0,
            "behind": 0,
            "text": "Sin remoto configurado",
            "has_remote": False,
        }

    ahead = 0
    behind = 0

    if "[" in first_line and "]" in first_line:
        status_block = first_line.split("[", 1)[1].split("]", 1)[0]
        parts = [p.strip() for p in status_block.split(",")]
        for part in parts:
            if part.startswith("ahead "):
                try:
                    ahead = int(part.replace("ahead ", "").strip())
                except ValueError:
                    pass
            elif part.startswith("behind "):
                try:
                    behind = int(part.replace("behind ", "").strip())
                except ValueError:
                    pass

    if ahead == 0 and behind == 0:
        text = "Al día con remoto"
    else:
        text = f"Ahead {ahead} / Behind {behind}"

    return {
        "ahead": ahead,
        "behind": behind,
        "text": text,
        "has_remote": True,
    }

def get_last_commit(repo_path):
    rc, stdout, _ = run_git_command(["log", "-1", "--pretty=format:%h | %s"], repo_path)
    if rc == 0 and stdout:
        return stdout
    return "No disponible"

def get_repo_data(path_selected):
    repo_root = find_git_root(path_selected)
    if not repo_root:
        return {
            "ok": False,
            "selected_path": os.path.abspath(path_selected),
            "message": "Esta carpeta no pertenece a ningún repositorio Git."
        }

    repo_name, branch_name, detached = get_branch_info(repo_root)
    dirty, changed_count = get_working_tree_status(repo_root)
    remote_info = get_ahead_behind(repo_root)
    last_commit = get_last_commit(repo_root)

    ahead = remote_info["ahead"]
    behind = remote_info["behind"]
    remote_state = remote_info["text"]
    has_remote = remote_info["has_remote"]

    if detached:
        status_label = "DETACHED"
        status_color = "#f39c12"
        status_text = "HEAD desacoplado"
    elif dirty:
        status_label = "DIRTY"
        status_color = "#e67e22"
        status_text = "Con cambios locales"
    elif has_remote and ahead > 0 and behind == 0:
        status_label = "PUSH"
        status_color = "#3498db"
        status_text = "Push pendiente"
    elif has_remote and behind > 0 and ahead == 0:
        status_label = "PULL"
        status_color = "#9b59b6"
        status_text = "Pull pendiente"
    elif has_remote and ahead > 0 and behind > 0:
        status_label = "DIVERGED"
        status_color = "#8e44ad"
        status_text = "Rama divergente"
    else:
        status_label = "CLEAN"
        status_color = "#27ae60"
        status_text = "Limpio"



    compact_line = f"{repo_name} [{branch_name}] - {status_label}"

    return {
        "ok": True,
        "selected_path": os.path.abspath(path_selected),
        "repo_root": repo_root,
        "repo_name": repo_name,
        "branch_name": branch_name,
        "detached": detached,
        "dirty": dirty,
        "changed_count": changed_count,
        "remote_state": remote_state,
        "last_commit": last_commit,
        "status_label": status_label,
        "status_color": status_color,
        "status_text": status_text,
        "compact_line": compact_line
    }

def get_local_branches(repo_path):
    rc, stdout, _ = run_git_command(
        ["for-each-ref", "--format=%(refname:short)|%(HEAD)|%(upstream:short)", "refs/heads"],
        repo_path
    )
    if rc != 0:
        return []

    branches = []
    for line in stdout.splitlines():
        parts = line.split("|")
        while len(parts) < 3:
            parts.append("")
        name, head_mark, upstream = parts[0].strip(), parts[1].strip(), parts[2].strip()
        branches.append({
            "name": name,
            "is_current": (head_mark == "*"),
            "upstream": upstream
        })
    return branches

def get_remote_branches(repo_path):
    rc, stdout, _ = run_git_command(
        ["for-each-ref", "--format=%(refname:short)", "refs/remotes"],
        repo_path
    )
    if rc != 0:
        return []

    branches = []
    for line in stdout.splitlines():
        name = line.strip()
        if not name or name.endswith("/HEAD"):
            continue
        branches.append(name)
    return branches

def checkout_branch(repo_path, branch_name):
    return run_git_command(["checkout", branch_name], repo_path)

def get_commits(repo_path, max_count=30):
    fmt = "%h|%ad|%an|%s"
    rc, stdout, _ = run_git_command(
        ["log", f"--max-count={max_count}", "--date=short", f"--pretty=format:{fmt}"],
        repo_path
    )
    if rc != 0:
        return []

    commits = []
    for line in stdout.splitlines():
        parts = line.split("|", 3)
        if len(parts) < 4:
            continue
        commits.append({
            "hash": parts[0].strip(),
            "date": parts[1].strip(),
            "author": parts[2].strip(),
            "subject": parts[3].strip()
        })
    return commits

def git_fetch(repo_path):
    return run_git_command(["fetch"], repo_path)

def git_pull(repo_path):
    return run_git_command(["pull"], repo_path)

def git_push_flow(repo_path, commit_message):
    lines = []

    if not is_git_available():
        return False, "[ERROR] Git no está instalado o no está en el PATH."

    rc, stdout, stderr = run_git_command(["rev-parse", "--is-inside-work-tree"], repo_path)
    if rc != 0 or stdout.lower() != "true":
        return False, "[ERROR] La ruta no pertenece a un repositorio Git válido."

    rc, top_level, _ = run_git_command(["rev-parse", "--show-toplevel"], repo_path)
    if rc == 0 and top_level:
        lines.append("Repo top-level:")
        lines.append(top_level)
        lines.append("")

    lines.append("=== STATUS (ANTES) ===")
    rc, status_before, err = run_git_command(["status", "-sb"], repo_path)
    lines.append(status_before if status_before else (err or "No disponible"))
    lines.append("")

    lines.append("=== GIT ADD -A ===")
    rc, out, err = run_git_command(["add", "-A"], repo_path)
    if rc != 0:
        lines.append(err or out or "Error en git add -A")
        return False, "\n".join(lines)
    lines.append("OK")
    lines.append("")

    lines.append("=== GIT COMMIT ===")
    rc, out, err = run_git_command(["commit", "-m", commit_message], repo_path)
    if rc == 0:
        lines.append(out or "Commit realizado.")
    else:
        commit_msg = "\n".join([x for x in [out, err] if x]).strip()
        if not commit_msg:
            commit_msg = "No había nada que commitear o Git devolvió aviso."
        lines.append(commit_msg)
    lines.append("")

    lines.append("=== GIT PUSH ===")
    rc, out, err = run_git_command(["push"], repo_path)
    if rc != 0:
        lines.append(err or out or "Error en git push")
        return False, "\n".join(lines)

    lines.append(out or "Push realizado.")
    lines.append("")
    lines.append("=== OK: Subido a GitHub ===")

    return True, "\n".join(lines)

def sanitize_filename(value):
    invalid = '<>:"/\\|?*'
    result = "".join("_" if ch in invalid else ch for ch in value)
    return result.strip().replace(" ", "_")

def build_markdown_report(data):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        "# Estado del repositorio\n\n"
        f"- **Repositorio:** {data['repo_name']}\n"
        f"- **Branch actual:** {data['branch_name']}\n"
        f"- **Estado local:** {data['status_text']}\n"
        f"- **Ficheros cambiados:** {data['changed_count']}\n"
        f"- **Estado remoto:** {data['remote_state']}\n"
        f"- **Último commit:** {data['last_commit']}\n"
        f"- **Repo raíz:** `{data['repo_root']}`\n"
        f"- **Ruta seleccionada:** `{data['selected_path']}`\n"
        f"- **Fecha:** {timestamp}\n"
    )

def save_markdown_report(data):
    repo_name = sanitize_filename(data["repo_name"])
    branch_name = sanitize_filename(data["branch_name"])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"git_branch_status_{repo_name}_{branch_name}_{timestamp}.md"
    full_path = os.path.join(data["repo_root"], filename)

    content = build_markdown_report(data)

    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

    return full_path

def place_near_parent(win, parent, offset_x=40, offset_y=40):
    try:
        parent.update_idletasks()
        win.update_idletasks()

        px = parent.winfo_x()
        py = parent.winfo_y()
        pw = parent.winfo_width()
        ph = parent.winfo_height()

        ww = win.winfo_width()
        wh = win.winfo_height()

        x = px + offset_x
        y = py + offset_y

        screen_w = win.winfo_screenwidth()
        screen_h = win.winfo_screenheight()

        if x + ww > screen_w:
            x = max(0, px + pw - ww - 20)

        if y + wh > screen_h:
            y = max(0, py + ph - wh - 40)

        win.geometry(f"+{x}+{y}")
    except Exception:
        pass



class OutputWindow(tk.Toplevel):
    def __init__(self, parent, title_text, content, ok=True):
        super().__init__(parent)
        self.title(title_text)
        self.geometry(APP_SETTINGS.get("output_geometry", "780x460"))
        self.minsize(scale(680), scale(380))
        self.configure(bg="#1e1f22")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        outer = tk.Frame(self, bg="#1e1f22")
        outer.pack(fill="both", expand=True, padx=scale(10), pady=scale(10))

        header_color = "#27ae60" if ok else "#e74c3c"

        header = tk.Frame(outer, bg="#2b2d31", highlightthickness=1, highlightbackground="#3a3d44")
        header.pack(fill="x", pady=(0, scale(12)))

        tk.Label(
            header,
            text=title_text,
            font=("Segoe UI", scale(16), "bold"),
            fg="#f8fafc",
            bg="#2b2d31"
        ).pack(side="left", padx=scale(16), pady=scale(14))

        tk.Label(
            header,
            text=" OPERACIÓN OK" if ok else " OPERACIÓN ERROR ",
            font=("Segoe UI", scale(9), "bold"),
            fg="white",
            bg=header_color,
            padx=scale(8),
            pady=scale(4)
        ).pack(side="right", padx=scale(16))

        text = tk.Text(
            outer,
            wrap="word",
            font=("Consolas", scale(9)),
            bg="#111827",
            fg="#e5e7eb",
            bd=0,
            highlightthickness=0,
            padx=scale(8),
            pady=scale(6)
        )
        text.pack(fill="both", expand=True)
        text.insert("1.0", content)
        text.config(state="disabled")

        btns = tk.Frame(outer, bg="#1e1f22")
        btns.pack(fill="x", pady=(scale(12), 0))

        tk.Button(
            btns, text="Cerrar", command=self.on_close,
            font=("Segoe UI", scale(8), "bold"),
            bg="#6b7280", fg="white", activebackground="#6b7280", activeforeground="white",
            relief="flat", bd=0, padx=scale(8), pady=scale(6), cursor="hand2"
        ).pack(side="right")
        
        place_near_parent(self, parent)

    def on_close(self):
        APP_SETTINGS["output_geometry"] = self.geometry()
        save_settings(APP_SETTINGS)
        self.destroy()

class BranchManagerWindow(tk.Toplevel):
    def __init__(self, parent, repo_root, current_branch, status_dirty):
        super().__init__(parent)
        self.parent = parent
        self.repo_root = repo_root
        self.current_branch = current_branch
        self.status_dirty = status_dirty

        self.title("Branches del repositorio")
        self.geometry(APP_SETTINGS.get("branch_geometry", "800x520"))
        self.minsize(scale(720), scale(440))
        self.configure(bg="#1e1f22")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.local_branches = []
        self.remote_branches = []
        self.selected_local_branch = None
        self.selected_remote_branch = None

        self._build_ui()
        self.refresh_lists()
        place_near_parent(self, parent)

    def on_close(self):
        APP_SETTINGS["branch_geometry"] = self.geometry()
        save_settings(APP_SETTINGS)
        self.destroy()

    def _build_ui(self):
        outer = tk.Frame(self, bg="#1e1f22")
        outer.pack(fill="both", expand=True, padx=scale(10), pady=scale(10))

        header = tk.Frame(outer, bg="#2b2d31", highlightthickness=1, highlightbackground="#3a3d44")
        header.pack(fill="x", pady=(0, scale(14)))

        tk.Label(
            header,
            text="Gestión de branches",
            font=("Segoe UI", scale(16), "bold"),
            fg="#f8fafc",
            bg="#2b2d31"
        ).pack(anchor="w", padx=scale(18), pady=(scale(18), scale(6)))

        tk.Label(
            header,
            text=f"Branch actual: {self.current_branch}",
            font=("Consolas", scale(11), "bold"),
            fg="#93c5fd",
            bg="#2b2d31"
        ).pack(anchor="w", padx=scale(18), pady=(0, scale(4)))

        tk.Label(
            header,
            text=f"Ruta del repo: {self.repo_root}",
            font=("Consolas", scale(8)),
            fg="#d1d5db",
            bg="#2b2d31"
        ).pack(anchor="w", padx=scale(18), pady=(0, scale(18)))

        if self.status_dirty:
            warning = tk.Frame(outer, bg="#4a2424", highlightthickness=1, highlightbackground="#7f1d1d")
            warning.pack(fill="x", pady=(0, scale(12)))
            tk.Label(
                warning,
                text="Atención: hay cambios sin commit en el repositorio. Cambiar de branch puede fallar o requerir limpieza previa.",
                font=("Segoe UI", scale(9), "bold"),
                fg="#fecaca",
                bg="#4a2424",
                wraplength=scale(740),
                justify="left"
            ).pack(anchor="w", padx=scale(16), pady=scale(12))

        body = tk.Frame(outer, bg="#1e1f22")
        body.pack(fill="both", expand=True)

        left = tk.Frame(body, bg="#1e1f22")
        left.pack(side="left", fill="both", expand=True)

        right = tk.Frame(body, bg="#1e1f22")
        right.pack(side="right", fill="both", expand=True, padx=(scale(14), 0))

        local_card = tk.Frame(left, bg="#2b2d31", highlightthickness=1, highlightbackground="#3a3d44")
        local_card.pack(fill="both", expand=True)

        tk.Label(
            local_card,
            text="Branches locales",
            font=("Segoe UI", scale(12), "bold"),
            fg="#f8fafc",
            bg="#2b2d31"
        ).pack(anchor="w", padx=scale(16), pady=(scale(16), scale(10)))

        self.local_list = tk.Listbox(
            local_card,
            font=("Consolas", scale(10)),
            bg="#1f2937",
            fg="#f8fafc",
            selectbackground="#2563eb",
            selectforeground="white",
            activestyle="none",
            height=18,
            bd=0,
            highlightthickness=0
        )
        self.local_list.pack(fill="both", expand=True, padx=scale(16), pady=(0, scale(12)))
        self.local_list.bind("<<ListboxSelect>>", self.on_local_select)
        self.local_list.bind("<Double-Button-1>", self.checkout_selected_branch)

        local_btns = tk.Frame(local_card, bg="#2b2d31")
        local_btns.pack(fill="x", padx=scale(16), pady=(0, scale(16)))

        self._make_button(local_btns, "Cambiar a branch local", self.checkout_selected_branch, "#16a34a").pack(side="left", padx=(0, scale(10)))
        self._make_button(local_btns, "Copiar nombre", self.copy_selected_local_branch, "#2563eb").pack(side="left")

        remote_card = tk.Frame(right, bg="#2b2d31", highlightthickness=1, highlightbackground="#3a3d44")
        remote_card.pack(fill="both", expand=True)

        tk.Label(
            remote_card,
            text="Branches remotas",
            font=("Segoe UI", scale(14), "bold"),
            fg="#f8fafc",
            bg="#2b2d31"
        ).pack(anchor="w", padx=scale(16), pady=(scale(16), scale(10)))

        self.remote_list = tk.Listbox(
            remote_card,
            font=("Consolas", scale(10)),
            bg="#111827",
            fg="#d1d5db",
            selectbackground="#7c3aed",
            selectforeground="white",
            activestyle="none",
            height=18,
            bd=0,
            highlightthickness=0
        )
        self.remote_list.pack(fill="both", expand=True, padx=scale(16), pady=(0, scale(12)))
        self.remote_list.bind("<<ListboxSelect>>", self.on_remote_select)

        remote_btns = tk.Frame(remote_card, bg="#2b2d31")
        remote_btns.pack(fill="x", padx=scale(16), pady=(0, scale(16)))

        self._make_button(remote_btns, "Copiar remota", self.copy_selected_remote_branch, "#8b5cf6").pack(side="left", padx=(0, scale(10)))
        self._make_button(remote_btns, "Refrescar", self.refresh_lists, "#f59e0b").pack(side="left")

        bottom = tk.Frame(outer, bg="#1e1f22")
        bottom.pack(fill="x", pady=(scale(14), 0))

        self.status_label = tk.Label(
            bottom,
            text="Listo.",
            font=("Segoe UI", scale(9)),
            fg="#d1d5db",
            bg="#1e1f22"
        )
        self.status_label.pack(side="left")

        self._make_button(bottom, "Cerrar", self.on_close, "#6b7280").pack(side="right")

    def _make_button(self, parent, text, command, color): #una
        return tk.Button(
            parent,
            text=text,
            command=command,
            font=("Segoe UI", scale(10), "bold"),
            bg=color,
            fg="white",
            activebackground=color,
            activeforeground="white",
            relief="flat",
            bd=0,
            padx=scale(8),
            pady=scale(6),
            cursor="hand2"
        )

    def refresh_lists(self):
        self.local_branches = get_local_branches(self.repo_root)
        self.remote_branches = get_remote_branches(self.repo_root)

        self.local_list.delete(0, tk.END)
        for item in self.local_branches:
            prefix = "★" if item["is_current"] else " "
            upstream = f"  ->  {item['upstream']}" if item["upstream"] else ""
            text = f"{prefix} {item['name']}{upstream}"
            self.local_list.insert(tk.END, text)
            idx = self.local_list.size() - 1
            self.local_list.itemconfig(idx, fg="#86efac" if item["is_current"] else "#f8fafc")

        self.remote_list.delete(0, tk.END)
        for item in self.remote_branches:
            self.remote_list.insert(tk.END, item)

        self.selected_local_branch = None
        self.selected_remote_branch = None
        self.status_label.config(text="Listas actualizadas.")

    def on_local_select(self, event=None):
        selection = self.local_list.curselection()
        if not selection:
            self.selected_local_branch = None
            return
        idx = selection[0]
        self.selected_local_branch = self.local_branches[idx]["name"]
        self.status_label.config(text=f"Seleccionada branch local: {self.selected_local_branch}")

    def on_remote_select(self, event=None):
        selection = self.remote_list.curselection()
        if not selection:
            self.selected_remote_branch = None
            return
        idx = selection[0]
        self.selected_remote_branch = self.remote_branches[idx]
        self.status_label.config(text=f"Seleccionada branch remota: {self.selected_remote_branch}")

    def copy_selected_local_branch(self):
        if not self.selected_local_branch:
            messagebox.showwarning("Sin selección", "Selecciona una branch local.")
            return
        self.clipboard_clear()
        self.clipboard_append(self.selected_local_branch)
        self.update()
        self.status_label.config(text=f"Copiada branch local: {self.selected_local_branch}")

    def copy_selected_remote_branch(self):
        if not self.selected_remote_branch:
            messagebox.showwarning("Sin selección", "Selecciona una branch remota.")
            return
        self.clipboard_clear()
        self.clipboard_append(self.selected_remote_branch)
        self.update()
        self.status_label.config(text=f"Copiada branch remota: {self.selected_remote_branch}")

    def checkout_selected_branch(self, event=None):
        if not self.selected_local_branch:
            messagebox.showwarning("Sin selección", "Selecciona una branch local.")
            return

        if self.selected_local_branch == self.current_branch:
            messagebox.showinfo("Sin cambios", "Esa ya es la branch actual.")
            return

        confirm = messagebox.askyesno(
            "Cambiar de branch",
            f"Se va a cambiar de:\n\n{self.current_branch}\n\na:\n\n{self.selected_local_branch}\n\n¿Continuar?"
        )
        if not confirm:
            return

        rc, stdout, stderr = checkout_branch(self.repo_root, self.selected_local_branch)

        if rc == 0:
            messagebox.showinfo("Cambio realizado", f"Ahora estás en la branch:\n{self.selected_local_branch}")
            self.current_branch = self.selected_local_branch
            self.refresh_lists()
            self.parent.refresh_data()
        else:
            messagebox.showerror("No se pudo cambiar de branch", stderr or stdout or "Git devolvió un error.")
            self.status_label.config(text="Falló el cambio de branch.")

class CommitHistoryWindow(tk.Toplevel):
    def __init__(self, parent, repo_root, branch_name):
        super().__init__(parent)
        self.parent = parent
        self.repo_root = repo_root
        self.branch_name = branch_name
        self.max_count = 30
        self.commits = []

        self.title("Historial de commits")
        self.geometry(APP_SETTINGS.get("commit_geometry", "920x560"))
        self.minsize(scale(820), scale(480))
        self.configure(bg="#1e1f22")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self._build_ui()
        self.load_commits()
        place_near_parent(self, parent)

    def on_close(self):
        APP_SETTINGS["commit_geometry"] = self.geometry()
        save_settings(APP_SETTINGS)
        self.destroy()

    def _build_ui(self):
        outer = tk.Frame(self, bg="#1e1f22")
        outer.pack(fill="both", expand=True, padx=scale(10), pady=scale(10))

        header = tk.Frame(outer, bg="#2b2d31", highlightthickness=1, highlightbackground="#3a3d44")
        header.pack(fill="x", pady=(0, scale(14)))

        tk.Label(
            header,
            text="Historial de commits",
            font=("Segoe UI", scale(18), "bold"),
            fg="#f8fafc",
            bg="#2b2d31"
        ).pack(anchor="w", padx=scale(18), pady=(scale(18), scale(6)))

        tk.Label(
            header,
            text=f"Branch actual: {self.branch_name}",
            font=("Consolas", scale(11), "bold"),
            fg="#93c5fd",
            bg="#2b2d31"
        ).pack(anchor="w", padx=scale(18), pady=(0, scale(4)))

        tk.Label(
            header,
            text=f"Repo: {self.repo_root}",
            font=("Consolas", scale(8)),
            fg="#d1d5db",
            bg="#2b2d31"
        ).pack(anchor="w", padx=scale(18), pady=(0, scale(18)))

        top_actions = tk.Frame(outer, bg="#1e1f22")
        top_actions.pack(fill="x", pady=(0, scale(12)))

        self._make_button(top_actions, "Cargar 30", lambda: self.set_count_and_reload(30), "#2563eb").pack(side="left", padx=(0, scale(8)))
        self._make_button(top_actions, "Cargar 50", lambda: self.set_count_and_reload(50), "#0ea5e9").pack(side="left", padx=(0, scale(8)))
        self._make_button(top_actions, "Cargar 100", lambda: self.set_count_and_reload(100), "#8b5cf6").pack(side="left", padx=(0, scale(8)))
        self._make_button(top_actions, "Refrescar", self.load_commits, "#f59e0b").pack(side="left", padx=(0, scale(8)))

        self.status_label = tk.Label(
            top_actions,
            text="",
            font=("Segoe UI", scale(9)),
            fg="#d1d5db",
            bg="#1e1f22"
        )
        self.status_label.pack(side="right")

        body = tk.Frame(outer, bg="#1e1f22")
        body.pack(fill="both", expand=True)

        left = tk.Frame(body, bg="#1e1f22")
        left.pack(side="left", fill="both", expand=True)

        right = tk.Frame(body, bg="#1e1f22", width=scale(280))
        right.pack(side="right", fill="y", padx=(scale(14), 0))
        right.pack_propagate(False)

        list_card = tk.Frame(left, bg="#2b2d31", highlightthickness=1, highlightbackground="#3a3d44")
        list_card.pack(fill="both", expand=True)

        tk.Label(
            list_card,
            text="Commits",
            font=("Segoe UI", scale(14), "bold"),
            fg="#f8fafc",
            bg="#2b2d31"
        ).pack(anchor="w", padx=scale(16), pady=(scale(16), scale(10)))

        self.commit_list = tk.Listbox(
            list_card,
            font=("Consolas", scale(9)),
            bg="#111827",
            fg="#f8fafc",
            selectbackground="#2563eb",
            selectforeground="white",
            activestyle="none",
            bd=0,
            highlightthickness=0
        )
        self.commit_list.pack(fill="both", expand=True, padx=scale(16), pady=(0, scale(16)))
        self.commit_list.bind("<<ListboxSelect>>", self.on_commit_select)

        detail_card = tk.Frame(right, bg="#2b2d31", highlightthickness=1, highlightbackground="#3a3d44")
        detail_card.pack(fill="both", expand=True)

        tk.Label(
            detail_card,
            text="Detalle del commit",
            font=("Segoe UI", scale(14), "bold"),
            fg="#f8fafc",
            bg="#2b2d31"
        ).pack(anchor="w", padx=scale(16), pady=(scale(16), scale(10)))

        self.detail_text = tk.Text(
            detail_card,
            wrap="word",
            font=("Consolas", scale(9)),
            bg="#1f2937",
            fg="#e5e7eb",
            bd=0,
            highlightthickness=0,
            padx=scale(8),
            pady=scale(6)
        )
        self.detail_text.pack(fill="both", expand=True, padx=scale(16), pady=(0, scale(12)))
        self.detail_text.config(state="disabled")

        btns = tk.Frame(detail_card, bg="#2b2d31")
        btns.pack(fill="x", padx=scale(16), pady=(0, scale(16)))

        self._make_button(btns, "Copiar hash", self.copy_selected_hash, "#16a34a").pack(side="left", padx=(0, scale(8)))
        self._make_button(btns, "Copiar línea", self.copy_selected_line, "#2563eb").pack(side="left", padx=(0, scale(8)))
        self._make_button(btns, "Cerrar", self.on_close, "#6b7280").pack(side="right")

    def _make_button(self, parent, text, command, color): #otraBotones de la principal
        return tk.Button(
            parent,
            text=text,
            command=command,
            # font=("Segoe UI", scale(8), "bold"),
            font=("Consolas", scale(16), "bold") if text in ("+", "-") else ("Segoe UI", scale(8), "bold"),
            bg=color,
            fg="white",
            activebackground=color,
            activeforeground="white",
            relief="flat",
            bd=0,
            padx=scale(8),
            pady=scale(6),
            cursor="hand2"
        )

    def set_count_and_reload(self, count):
        self.max_count = count
        self.load_commits()

    def load_commits(self):
        self.commits = get_commits(self.repo_root, self.max_count)
        self.commit_list.delete(0, tk.END)

        for c in self.commits:
            line = f"{c['hash']:8}  {c['date']}  {c['author'][:16]:16}  {c['subject']}"
            self.commit_list.insert(tk.END, line)

        self.status_label.config(text=f"{len(self.commits)} commits cargados")
        self.clear_detail()

    def clear_detail(self):
        self.detail_text.config(state="normal")
        self.detail_text.delete("1.0", tk.END)
        self.detail_text.insert("1.0", "Selecciona un commit para ver el detalle.")
        self.detail_text.config(state="disabled")

    def on_commit_select(self, event=None):
        selection = self.commit_list.curselection()
        if not selection:
            return

        idx = selection[0]
        c = self.commits[idx]

        detail = (
            f"Hash:    {c['hash']}\n"
            f"Fecha:   {c['date']}\n"
            f"Autor:   {c['author']}\n\n"
            f"Mensaje:\n{c['subject']}"
        )

        self.detail_text.config(state="normal")
        self.detail_text.delete("1.0", tk.END)
        self.detail_text.insert("1.0", detail)
        self.detail_text.config(state="disabled")

    def get_selected_commit(self):
        selection = self.commit_list.curselection()
        if not selection:
            return None
        return self.commits[selection[0]]

    def copy_selected_hash(self):
        c = self.get_selected_commit()
        if not c:
            messagebox.showwarning("Sin selección", "Selecciona un commit.")
            return
        self.clipboard_clear()
        self.clipboard_append(c["hash"])
        self.update()
        self.status_label.config(text=f"Hash copiado: {c['hash']}")

    def copy_selected_line(self):
        c = self.get_selected_commit()
        if not c:
            messagebox.showwarning("Sin selección", "Selecciona un commit.")
            return
        line = f"{c['hash']} | {c['date']} | {c['author']} | {c['subject']}"
        self.clipboard_clear()
        self.clipboard_append(line)
        self.update()
        self.status_label.config(text="Línea de commit copiada")

class GitBranchPeekApp(tk.Tk):
    def __init__(self, selected_path):
        super().__init__()
        self.selected_path = selected_path
        self.data = get_repo_data(selected_path)
        icon_path = resource_path("git_win_tool.ico")
        if icon_path.exists():
            self.iconbitmap(str(icon_path))
            self.title(APP_TITLE)
             
        #TAMAÑO MINIMO---------------------------------
      

        self.geometry(APP_SETTINGS.get("main_geometry", f"{WIN_W}x{WIN_H}"))
        self._apply_main_window_size_rules()    


        self.update_idletasks()
        current_w = self.winfo_width()
        current_h = self.winfo_height()

        
        self.configure(bg="#1e1f22")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self._build_ui()
        

    def on_close(self):
        APP_SETTINGS["main_geometry"] = self.geometry()
        APP_SETTINGS["ui_scale"] = UI_SCALE
        save_settings(APP_SETTINGS)
        self.destroy()

    def _apply_main_window_size_rules(self):
        if UI_SCALE <= MIN_UI_SCALE:
            min_w, min_h = 602, 570
            self.minsize(min_w, min_h)
            self.geometry(f"{min_w}x{min_h}")
        else:
            min_w, min_h = scale(760), scale(520)
            self.minsize(min_w, min_h)

            self.update_idletasks()
            current_w = self.winfo_width()
            current_h = self.winfo_height()

            if current_w < min_w or current_h < min_h:
                self.geometry(f"{max(current_w, min_w)}x{max(current_h, min_h)}")

    def save_and_destroy(self):
        self.on_close()

    def change_ui_scale(self, delta):
        global UI_SCALE

        if delta < 0 and UI_SCALE <= MIN_UI_SCALE:
            return

        if delta > 0 and UI_SCALE >= MAX_UI_SCALE:
            return

        UI_SCALE = clamp_ui_scale(UI_SCALE + delta)
        APP_SETTINGS["ui_scale"] = UI_SCALE

       
        self._apply_main_window_size_rules()
        self._build_ui()

        APP_SETTINGS["main_geometry"] = self.geometry()
        save_settings(APP_SETTINGS)
             

    def _build_ui(self):
        for child in self.winfo_children():
            child.destroy()

        if not self.data["ok"]:
            self._build_error_ui()
        else:
            self._build_main_ui()

    def _build_error_ui(self):
        outer = tk.Frame(self, bg="#1e1f22")
        outer.pack(fill="both", expand=True, padx=scale(12), pady=scale(12))

        card = tk.Frame(outer, bg="#2b2d31", bd=0, highlightthickness=1, highlightbackground="#3a3d44")
        card.pack(fill="both", expand=True)

        tk.Label(
            card,
            text="No se ha detectado un repositorio Git",
            font=("Segoe UI", scale(18), "bold"),
            fg="#ff6b6b",
            bg="#2b2d31"
        ).pack(anchor="w", padx=scale(12), pady=(scale(12), scale(6)))

        tk.Label(
            card,
            text=self.data["message"],
            font=("Segoe UI", scale(10)),
            fg="#e5e7eb",
            bg="#2b2d31"
        ).pack(anchor="w", padx=scale(12), pady=(0, scale(8)))

        self._add_info_block(card, "Ruta analizada", self.data["selected_path"])

        btns = tk.Frame(card, bg="#2b2d31")
        btns.pack(fill="x", padx=scale(12), pady=scale(12))

        self._make_button(btns, "Copiar ruta", self.copy_selected_path, "#3b82f6").pack(side="left", padx=(0, scale(8)))
        self._make_button(btns, "Cerrar", self.save_and_destroy, "#6b7280").pack(side="right")

    def _build_main_ui(self):
        outer = tk.Frame(self, bg="#1e1f22")
        outer.pack(fill="both", expand=True, padx=scale(10), pady=scale(10))

        header = tk.Frame(outer, bg="#2b2d31", highlightthickness=1, highlightbackground="#3a3d44")
        header.pack(fill="x", pady=(0, scale(16)))

        top_row = tk.Frame(header, bg="#2b2d31")
        top_row.pack(fill="x", padx=scale(12), pady=(scale(10), scale(4)))

        tk.Label(
            top_row,
            text=APP_TITLE,
            font=("Segoe UI", scale(14), "bold"),
            fg="#f8fafc",
            bg="#2b2d31"
        ).pack(side="left")

        tk.Label(
            top_row,
            text=f"  {self.data['status_label']}  ",
            font=("Segoe UI", scale(24), "bold"),
            fg="white",
            bg=self.data["status_color"],
            padx=scale(11),
            pady=scale(5),
            relief="flat",
            bd=0
        ).pack(side="right")

        tk.Label(
            header,
            text=self.data["compact_line"],
            font=("Consolas", scale(18), "bold"),
            fg="#93c5fd",
            bg="#2b2d31"
        ).pack(anchor="w", padx=scale(12), pady=(0, scale(10)))

        body = tk.Frame(outer, bg="#1e1f22")
        body.pack(fill="both", expand=True)

        left_container = tk.Frame(body, bg="#1e1f22")
        left_container.pack(side="left", fill="both", expand=True)

       
        left_canvas = tk.Canvas(
            left_container,
            bg="#1e1f22",
            highlightthickness=0,
            bd=0
        )
        left_scrollbar = tk.Scrollbar(left_container, orient="vertical", command=left_canvas.yview)
        left_canvas.configure(yscrollcommand=left_scrollbar.set)

        left_canvas.pack(side="left", fill="both", expand=True)

        left_col = tk.Frame(left_canvas, bg="#1e1f22")
        left_canvas_window = left_canvas.create_window((0, 0), window=left_col, anchor="nw")

        scrollbar_visible = {"shown": False}

        def _update_left_scrollbar():
            left_canvas.update_idletasks()

            bbox = left_canvas.bbox("all")
            if not bbox:
                return

            content_height = bbox[3] - bbox[1]
            visible_height = left_canvas.winfo_height()

            needs_scroll = content_height > visible_height + 2

            if needs_scroll and not scrollbar_visible["shown"]:
                left_scrollbar.pack(side="right", fill="y")
                scrollbar_visible["shown"] = True
            elif not needs_scroll and scrollbar_visible["shown"]:
                left_scrollbar.pack_forget()
                scrollbar_visible["shown"] = False

        def _sync_left_scroll(event=None):
            left_canvas.configure(scrollregion=left_canvas.bbox("all"))
            _update_left_scrollbar()

        def _resize_left_inner(event):
            left_canvas.itemconfigure(left_canvas_window, width=event.width)
            _update_left_scrollbar()

        left_col.bind("<Configure>", _sync_left_scroll)
        left_canvas.bind("<Configure>", _resize_left_inner)


        def _on_mousewheel(event):
            left_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        #left_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        left_canvas.bind("<MouseWheel>", _on_mousewheel)

        right_col = tk.Frame(body, bg="#1e1f22", width=scale_actions(220))
        right_col.pack(side="right", fill="y", padx=(scale(10), 0))
        right_col.pack_propagate(False)

        self._add_info_block(left_col, "Repositorio", self.data["repo_name"])
        self._add_info_block(left_col, "Branch actual", self.data["branch_name"], accent="#9adf1b")
        self._add_info_block(left_col, "Estado local", self.data["status_text"], accent=self.data["status_color"])
        
        changed_text = "0 (limpio)" if self.data["changed_count"] == 0 else str(self.data["changed_count"])
        self._add_info_block(left_col, "Ficheros cambiados", changed_text)
        
        self._add_info_block(left_col, "Estado remoto", self.data["remote_state"])
        self._add_info_block(left_col, "Último commit", self.data["last_commit"])
        self._add_info_block(left_col, "Ruta seleccionada", self.data["selected_path"], mono=True)
        self._add_info_block(left_col, "Repo raíz", self.data["repo_root"], mono=True)
        self.after(50, _update_left_scrollbar)

        actions_card = tk.Frame(right_col, bg="#2b2d31", highlightthickness=1, highlightbackground="#3a3d44")
        actions_card.pack(fill="x")

        tk.Label(
            actions_card,
            text="Acciones",
            font=("Segoe UI", scale_actions(14), "bold"),
            fg="#f8fafc",
            bg="#2b2d31"
        ).pack(anchor="w", padx=scale(12), pady=(scale(10), scale(8)))

        zoom_row = tk.Frame(actions_card, bg="#2b2d31")
        zoom_row.pack(fill="x", padx=scale_actions(10), pady=(0, scale_actions(6)))

        self._make_button(zoom_row, "🔍-", lambda: self.change_ui_scale(-0.05), "#2b2d31").pack(side="left", fill="x", expand=True, padx=(0, scale(24))) #"#4b5563"
        self._make_button(zoom_row, "🔍+", lambda: self.change_ui_scale(0.05), "#2b2d31").pack(side="left", fill="x", expand=True, padx=(scale(4), 0))
      


        self._make_button(actions_card, "Push", self.do_push_flow, "#f21919").pack(fill="x", padx=scale(10), pady=scale(3))
        self._make_button(actions_card, "Fetch", self.do_fetch, "#f05521").pack(fill="x", padx=scale(10), pady=scale(3))
        self._make_button(actions_card, "Pull", self.do_pull, "#b5af08").pack(fill="x", padx=scale(10), pady=scale(3))
        self._make_button(actions_card, "Ver Branches", self.open_branches_window, "#7c33f9").pack(fill="x", padx=scale(10), pady=scale(3))
        self._make_button(actions_card, "Ver Commits", self.open_commits_window, "#7c33f9").pack(fill="x", padx=scale(10), pady=scale(3))
        self._make_button(actions_card, "Ver cambios", self.open_changes_window, "#7c33f9").pack(fill="x", padx=scale(10), pady=scale(3))
        self._make_button(actions_card, "Exportar Detalle a .md", self.export_detail_to_md, "#0ea5e9").pack(fill="x", padx=scale(10), pady=scale(3))
        self._make_button(actions_card, "Refrescar", self.refresh_data, "#088677").pack(fill="x", padx=scale(10), pady=scale(3))
        self._make_button(actions_card, "Abrir CMD en repo", self.open_cmd_repo, "#682c07").pack(fill="x", padx=scale(10), pady=scale(3))
        self._make_button(actions_card, "Cerrar", self.save_and_destroy, "#6b7280").pack(fill="x", padx=scale(10), pady=(scale(3), scale(10)))

    
    
    #------------------------------------------------------------------------
    
    
    
    def _add_info_block(self, parent, title, value, accent="#3b82f6", mono=False):
        card = tk.Frame(parent, bg="#2b2d31", highlightthickness=1, highlightbackground="#3a3d44")
        card.pack(fill="x", pady=scale_info(4))

        top = tk.Frame(card, bg="#2b2d31")
        top.pack(fill="x", padx=scale_info(10), pady=(scale_info(8), scale_info(3)))

        accent_bar = tk.Frame(top, bg=accent, width=scale_info(5), height=scale_info(18))
        accent_bar.pack(side="left", padx=(0, scale_info(8)))

        tk.Label(
            top,
            text=title,
            font=("Segoe UI", scale_info(10), "bold"),
            fg="#f8fafc",
            bg="#2b2d31"
        ).pack(side="left")

        value_font = ("Consolas", scale_info(8)) if mono else ("Segoe UI", scale_info(9))

        tk.Label(
            card,
            text=value,
            font=value_font,
            fg="#e5e7eb",
            bg="#2b2d31",
            justify="left",
            anchor="w",
            wraplength=scale_info(430)
        ).pack(fill="x", padx=scale_info(10), pady=(0, scale_info(8)))

    def _make_button(self, parent, text, command, color):

        is_zoom = "+" in text or "-" in text

        # font = ("Segoe UI Emoji", scale_actions(18)) if text in ("+", "-") else ("Consolas", scale_actions(8), "bold")
        font = ("Segoe UI Emoji", scale_actions(10) if is_zoom else scale_actions(8), "bold")

        padx = scale_actions(3) if is_zoom else scale_actions(6) #6
        pady = scale_actions(4) if is_zoom else scale_actions(5) #5

        return tk.Button(
            parent,
            text=text,
            command=command,
            font=font,
            bg=color,
            fg="white",
            activebackground=color,
            activeforeground="white",
            relief="flat",
            bd=0,
            padx=padx,
            pady=pady,
            cursor="hand2"

        )
    



    def copy_to_clipboard(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()

    def copy_selected_path(self):
        self.copy_to_clipboard(self.data["selected_path"])
        messagebox.showinfo("Copiado", "Ruta copiada al portapapeles.")

    def open_cmd_repo(self):
        if self.data.get("repo_root"):
            os.system(f'start cmd /K cd /d "{self.data["repo_root"]}"')

    def open_branches_window(self):
        if not self.data["ok"]:
            return
        win = BranchManagerWindow(
            self,
            self.data["repo_root"],
            self.data["branch_name"],
            self.data["dirty"]
        )
        win.grab_set()

    def open_commits_window(self):
        if not self.data["ok"]:
            return
        win = CommitHistoryWindow(
            self,
            self.data["repo_root"],
            self.data["branch_name"]
        )
        win.grab_set()
        
    def open_changes_window(self):
        if not self.data["ok"]:
            return

        ok, content = get_working_tree_details(self.data["repo_root"])
        win = OutputWindow(self, "Cambios del working tree", content, ok=ok)
        win.grab_set()    
        
        
        

    def export_detail_to_md(self):
        try:
            path = save_markdown_report(self.data)
            messagebox.showinfo("Markdown generado", f"Se ha creado:\n\n{path}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo crear el fichero .md\n\n{e}")

    def do_fetch(self):
        confirm = messagebox.askyesno("Fetch", "Se va a ejecutar git fetch sobre este repositorio.\n\n¿Continuar?")
        if not confirm:
            return

        rc, stdout, stderr = git_fetch(self.data["repo_root"])
        ok = (rc == 0)
        content = stdout or stderr or ("Fetch completado." if ok else "Error en fetch.")
        win = OutputWindow(self, "Resultado de git fetch", content, ok=ok)
        win.grab_set()
        if ok:
            self.refresh_data()

    def do_pull(self):
        confirm = messagebox.askyesno("Pull", "Se va a ejecutar git pull sobre este repositorio.\n\n¿Continuar?")
        if not confirm:
            return

        rc, stdout, stderr = git_pull(self.data["repo_root"])
        ok = (rc == 0)
        content = stdout or stderr or ("Pull completado." if ok else "Error en pull.")
        win = OutputWindow(self, "Resultado de git pull", content, ok=ok)
        win.grab_set()
        if ok:
            self.refresh_data()

    def do_push_flow(self):
        msg = simpledialog.askstring(
            "Mensaje de commit",
            "Mensaje de commit (vacío = Update):",
            parent=self
        )
        if msg is None:
            return

        msg = msg.strip() or "Update"

        confirm = messagebox.askyesno(
            "Push",
            f"Se ejecutará este flujo:\n\n"
            f"1. git add -A\n"
            f"2. git commit -m \"{msg}\"\n"
            f"3. git push\n\n"
            f"¿Continuar?"
        )
        if not confirm:
            return

        ok, content = git_push_flow(self.data["repo_root"], msg)
        win = OutputWindow(self, "Resultado de push", content, ok=ok)
        win.grab_set()
        self.refresh_data()

    def refresh_data(self):
        APP_SETTINGS["main_geometry"] = self.geometry()
        APP_SETTINGS["ui_scale"] = UI_SCALE
        save_settings(APP_SETTINGS)
        self.data = get_repo_data(self.selected_path)
        try:
            repo_root = self.data.get("repo_root")
            if repo_root:
                sync_gitwinseek(repo_root)
        except Exception as e:
            print(f"[GitWinSeek refresh button sync error] {e}")
            
        self._build_ui()


def main():
    if len(sys.argv) > 1:
        selected_path = sys.argv[1]
    else:
        selected_path = os.getcwd()

    app = GitBranchPeekApp(selected_path)
    app.mainloop()


if __name__ == "__main__":
    main()
