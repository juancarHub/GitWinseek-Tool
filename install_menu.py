import os
import sys
import winreg
import tkinter as tk
from tkinter import messagebox

APP_TITLE = "GitWinTool"
MENU_ROOT_NAME = "GitWinTool"


def show_info(message: str):
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo(APP_TITLE, message)
    root.destroy()


def show_error(message: str):
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(APP_TITLE, message)
    root.destroy()


def get_current_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def get_root_dir() -> str:
    # install_menu\install_menu.exe  --> subir un nivel a la raíz
    return os.path.dirname(get_current_dir())


def build_paths():
    root_dir = get_root_dir()

    git_tool_dir = os.path.join(root_dir, "git_win_tool")
    seek_dir = os.path.join(root_dir, "GitWinSeek")

    git_tool_exe = os.path.join(git_tool_dir, "git_win_tool.exe")
    git_tool_icon = os.path.join(git_tool_dir, "_internal", "git_win_tool.ico")
    seek_exe = os.path.join(seek_dir, "GitWinSeek.exe")

    return {
        "root_dir": root_dir,
        "git_tool_dir": git_tool_dir,
        "seek_dir": seek_dir,
        "git_tool_exe": git_tool_exe,
        "git_tool_icon": git_tool_icon,
        "seek_exe": seek_exe,
    }


def validate_paths(paths: dict):
    missing = []

    for label, path in [
        ("git_win_tool.exe", paths["git_tool_exe"]),
        ("git_win_tool.ico", paths["git_tool_icon"]),
        ("GitWinSeek.exe", paths["seek_exe"]),
    ]:
        if not os.path.exists(path):
            missing.append(f"{label}:\n{path}")

    if missing:
        raise FileNotFoundError(
            "No se han encontrado los siguientes archivos necesarios:\n\n"
            + "\n\n".join(missing)
        )


def set_reg_value(root, subkey: str, name: str, value: str, value_type=winreg.REG_SZ):
    key = winreg.CreateKeyEx(root, subkey, 0, winreg.KEY_WRITE)
    try:
        winreg.SetValueEx(key, name, 0, value_type, value)
    finally:
        winreg.CloseKey(key)


def create_menu_branch(base_key: str, icon_path: str):
    set_reg_value(winreg.HKEY_CURRENT_USER, base_key, "MUIVerb", MENU_ROOT_NAME)
    set_reg_value(winreg.HKEY_CURRENT_USER, base_key, "Icon", icon_path)
    set_reg_value(winreg.HKEY_CURRENT_USER, base_key, "SubCommands", "")


def add_menu_item(base_key: str, item_key_name: str, text: str, icon_path: str, command: str):
    item_key = f"{base_key}\\shell\\{item_key_name}"
    command_key = f"{item_key}\\command"

    set_reg_value(winreg.HKEY_CURRENT_USER, item_key, "MUIVerb", text)
    set_reg_value(winreg.HKEY_CURRENT_USER, item_key, "Icon", icon_path)
    set_reg_value(winreg.HKEY_CURRENT_USER, command_key, "", command)


def install_context_menu():
    paths = build_paths()
    validate_paths(paths)

    icon = paths["git_tool_icon"]
    git_tool_exe = paths["git_tool_exe"]
    seek_exe = paths["seek_exe"]

    # Rama para clic derecho sobre carpeta
    dir_key = r"Software\Classes\Directory\shell\GitTools"
    create_menu_branch(dir_key, icon)

    add_menu_item(
        dir_key,
        "001_OpenTool",
        "Abrir Git Win Tool",
        icon,
        f'"{git_tool_exe}" "%1"',
    )
    add_menu_item(
        dir_key,
        "010_InitSeek",
        "Inicializar icono Git",
        icon,
        f'"{seek_exe}" init "%1"',
    )
    add_menu_item(
        dir_key,
        "020_RefreshSeek",
        "Refrescar icono Git",
        icon,
        f'"{seek_exe}" refresh "%1"',
    )
    add_menu_item(
        dir_key,
        "030_RemoveSeek",
        "Quitar seguimiento visual",
        icon,
        f'"{seek_exe}" remove "%1"',
    )
    add_menu_item(
        dir_key,
        "050_RefreshAll",
        "Refrescar todos los repos GitWinSeek",
        icon,
        f'"{seek_exe}" refresh-all',
    )

    # Rama para clic derecho en el fondo de una carpeta
    bg_key = r"Software\Classes\Directory\Background\shell\GitTools"
    create_menu_branch(bg_key, icon)

    add_menu_item(
        bg_key,
        "001_OpenTool",
        "Abrir Git Win Tool",
        icon,
        f'"{git_tool_exe}" "%V"',
    )
    add_menu_item(
        bg_key,
        "010_InitSeek",
        "Inicializar icono Git",
        icon,
        f'"{seek_exe}" init "%V"',
    )
    add_menu_item(
        bg_key,
        "020_RefreshSeek",
        "Refrescar icono Git",
        icon,
        f'"{seek_exe}" refresh "%V"',
    )
    add_menu_item(
        bg_key,
        "030_RemoveSeek",
        "Quitar seguimiento visual",
        icon,
        f'"{seek_exe}" remove "%V"',
    )
    add_menu_item(
        bg_key,
        "050_RefreshAll",
        "Refrescar todos los repos GitWinSeek",
        icon,
        f'"{seek_exe}" refresh-all',
    )

    show_info(
        "Menú contextual instalado correctamente.\n\n"
        "Para desinstalar:\n"
        "install_menu.exe uninstall"
    )


def delete_tree(root, subkey: str):
    try:
        with winreg.OpenKey(root, subkey, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
            while True:
                try:
                    child = winreg.EnumKey(key, 0)
                    delete_tree(root, subkey + "\\" + child)
                except OSError:
                    break
        winreg.DeleteKey(root, subkey)
    except FileNotFoundError:
        pass


def uninstall_context_menu():
    keys = [
        r"Software\Classes\Directory\shell\GitTools",
        r"Software\Classes\Directory\Background\shell\GitTools",
    ]

    for key in keys:
        delete_tree(winreg.HKEY_CURRENT_USER, key)

    show_info("Menú contextual desinstalado correctamente.")


def main():
    try:
        if len(sys.argv) > 1 and sys.argv[1].strip().lower() == "uninstall":
            uninstall_context_menu()
        else:
            install_context_menu()
    except Exception as e:
        show_error(str(e))


if __name__ == "__main__":
    main()