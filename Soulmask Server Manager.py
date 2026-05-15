import customtkinter as ctk
from tkinter import filedialog, messagebox
import json
import os
import subprocess
import threading
import urllib.request
import zipfile
from datetime import datetime, timezone
import string
import socket 
import struct 
import time
import sys
import ctypes
import shutil

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class SoulmaskManagerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Soulmask Server Manager")
        self.geometry("1150x850") 
        
        icon_path = resource_path("favicon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(default=icon_path) 
                myappid = 'soulmask.server.manager.pro.1'
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            except: 
                pass
        
        self.config_file = "manager_config.json"
        self.server_process = None
        self.is_initializing = True
        self.current_rules_path = ""
        self.pending_restart = False
        
        self.tracked_players = [] 
        self.active_players = []
        self.timer_id = None
        
        self.map_names_de = ["Regenwald (Level01_Main)", "Wüste (DLC_Level01_Main)"]
        self.map_names_en = ["Cloud Mist Forest (Level01_Main)", "Shifting Sands (DLC_Level01_Main)"]
        self.map_values = ["Level01_Main", "DLC_Level01_Main"]
        
        self.survival_diffs = [
            {"name_de": "Normal", "name_en": "Normal", "desc_de": "Die standardmäßige, vom Entwickler gedachte Überlebens-Herausforderung.", "desc_en": "The standard survival challenge intended by the developers."}
        ]
        
        self.settings = {
            "Language": "English",
            "ServerName": "My Soulmask Server",
            "ServerPassword": "",
            "AdminPassword": "admin",
            "MaxPlayers": "70",
            "BackupIntervalMinutes": "120",
            "ExePath": "",
            "SteamCmdPath": "",
            "InstallDir": "",
            "WorldDbPath": "",
            "PublicIP": "",
            "GamePort": "8777",
            "QueryPort": "27015",
            "EchoPort": "18888",
            "MapName": "Level01_Main",
            "CombatMode": "PvE",
            "Difficulty": "Normal"
        }
        
        self.load_settings()
        self.setup_ui()
        self.apply_language() 
        self.is_initializing = False
        
        self.log("System", "Manager gestartet. Bereit für den Einsatz!", "System", "Manager started. Ready for deployment!")

    def get_map_display_name(self, map_val, de):
        try:
            idx = self.map_values.index(map_val)
        except ValueError:
            idx = 0
        return self.map_names_de[idx] if de else self.map_names_en[idx]

    def get_map_val_from_display(self, display_name):
        if display_name in self.map_names_de:
            return self.map_values[self.map_names_de.index(display_name)]
        if display_name in self.map_names_en:
            return self.map_values[self.map_names_en.index(display_name)]
        return "Level01_Main"

    def on_map_changed(self, *args):
        if self.is_initializing: return
        val = self.get_map_val_from_display(self.var_map_display.get())
        self.settings["MapName"] = val
        self.save_settings()

    def on_diff_changed(self, *args):
        if self.is_initializing: return
        self.update_main_diff_options(update_diff_box=False)
        self.save_settings()

    def setup_ui(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(expand=True, fill='both', padx=20, pady=20)
        
        self.tab_dash = self.tabview.add("🖥️ Dashboard")
        self.tab_players = self.tabview.add("👥 Players | Spieler")
        self.tab_set = self.tabview.add("⚙️ Settings | Einstellungen")
        self.tab_rules = self.tabview.add("📜 Rules | Regeln")
        
        self.setup_dashboard()
        self.setup_players()
        self.setup_settings()
        self.setup_rules()

    def setup_dashboard(self):
        btn_frame = ctk.CTkFrame(self.tab_dash, fg_color="transparent")
        btn_frame.pack(fill='x', pady=10)
        
        self.btn_start = ctk.CTkButton(btn_frame, text="▶ Start", fg_color="#2E7D32", hover_color="#1B5E20", width=100, command=self.start_server)
        self.btn_start.pack(side='left', padx=5)
        
        self.btn_restart = ctk.CTkButton(btn_frame, text="🔄 Neustart", fg_color="#F57C00", hover_color="#E65100", width=100, state='disabled', command=self.restart_server)
        self.btn_restart.pack(side='left', padx=5)
        
        self.btn_stop = ctk.CTkButton(btn_frame, text="⏹ Stopp", fg_color="#C62828", hover_color="#b71c1c", width=100, state='disabled', command=self.stop_server)
        self.btn_stop.pack(side='left', padx=5)

        self.btn_inst_steam = ctk.CTkButton(btn_frame, text="📦 SteamCMD", fg_color="#0277BD", command=self.install_steamcmd)
        self.btn_inst_steam.pack(side='left', padx=20)
        
        self.btn_inst_srv = ctk.CTkButton(btn_frame, text="⏬ Server Install", fg_color="#4527A0", command=self.install_server)
        self.btn_inst_srv.pack(side='left', padx=5)
        
        self.btn_update_srv = ctk.CTkButton(btn_frame, text="🔄 Server Update", fg_color="#00838F", hover_color="#006064", command=self.update_server)
        self.btn_update_srv.pack(side='left', padx=5)
        
        self.lbl_status = ctk.CTkLabel(btn_frame, text="Offline", text_color="#EF5350", font=("Arial", 16, "bold"))
        self.lbl_status.pack(side='right', padx=20)
        
        self.console = ctk.CTkTextbox(self.tab_dash, fg_color="#121212", text_color="#00FF00", font=("Consolas", 13))
        self.console.pack(expand=True, fill='both')
        self.console.configure(state='disabled')

    def setup_players(self):
        top_frame = ctk.CTkFrame(self.tab_players, fg_color="transparent")
        top_frame.pack(fill='x', pady=5)
        
        self.btn_refresh_players = ctk.CTkButton(top_frame, text="🔄 Aktualisieren", command=self.refresh_players_list)
        self.btn_refresh_players.pack(side='left', padx=10)
        
        self.lbl_player_count = ctk.CTkLabel(top_frame, text="Spieler online: 0", font=("Arial", 14, "bold"))
        self.lbl_player_count.pack(side='right', padx=10)
        
        header_frame = ctk.CTkFrame(self.tab_players, fg_color="#1E1E1E")
        header_frame.pack(fill='x', padx=10, pady=(10, 0))
        
        self.lbl_h_name = ctk.CTkLabel(header_frame, text="Steam Name", font=("Arial", 14, "bold"), width=400, anchor='w')
        self.lbl_h_name.pack(side='left', padx=10, pady=5)
        
        self.lbl_h_time = ctk.CTkLabel(header_frame, text="Online seit", font=("Arial", 14, "bold"), width=200, anchor='w')
        self.lbl_h_time.pack(side='left', padx=10, pady=5)
        
        self.scroll_players = ctk.CTkScrollableFrame(self.tab_players, fg_color="#2B2B2B")
        self.scroll_players.pack(expand=True, fill='both', padx=10, pady=(0, 10))

    def setup_settings(self):
        self.scroll_set = ctk.CTkScrollableFrame(self.tab_set, fg_color="transparent")
        self.scroll_set.pack(expand=True, fill='both')

        self.lbl_lang_t = self.create_label(self.scroll_set, "Sprache / Language:", True)
        self.var_lang = ctk.StringVar(value=self.settings["Language"])
        ctk.CTkComboBox(self.scroll_set, variable=self.var_lang, values=["Deutsch", "English"], command=self.change_language).pack(anchor='w', padx=10, pady=5)

        self.lbl_prop_t = self.create_label(self.scroll_set, "Server Details", True)
        self.var_servername = ctk.StringVar(value=self.settings["ServerName"])
        self.lbl_sn = self.create_entry_row(self.scroll_set, "Server Name:", self.var_servername)
        self.var_password = ctk.StringVar(value=self.settings["ServerPassword"])
        self.lbl_pw = self.create_entry_row(self.scroll_set, "Passwort:", self.var_password, True)
        self.var_adminpassword = ctk.StringVar(value=self.settings["AdminPassword"])
        self.lbl_apw = self.create_entry_row(self.scroll_set, "Admin PW:", self.var_adminpassword)
        
        self.var_maxplayers = ctk.StringVar(value=self.settings["MaxPlayers"])
        self.lbl_mp = self.create_entry_row(self.scroll_set, "Max. Spieler:", self.var_maxplayers, width=80)
        
        self.var_backup_interval = ctk.StringVar(value=self.settings.get("BackupIntervalMinutes", "120"))
        self.lbl_backup = self.create_entry_row(self.scroll_set, "Backup Timer (Min):", self.var_backup_interval, width=80)

        self.lbl_game_t = self.create_label(self.scroll_set, "Spiel & Welt / Game & World", True)
        
        f_map = ctk.CTkFrame(self.scroll_set, fg_color="transparent")
        f_map.pack(fill='x', pady=2)
        self.lbl_s_map = ctk.CTkLabel(f_map, text="Map:", width=200, anchor='w')
        self.lbl_s_map.pack(side='left', padx=10)
        
        de = self.var_lang.get() == "Deutsch"
        current_map = self.settings.get("MapName", "Level01_Main")
        self.var_map_display = ctk.StringVar(value=self.get_map_display_name(current_map, de))
        self.cb_map = ctk.CTkComboBox(f_map, variable=self.var_map_display, values=self.map_names_de if de else self.map_names_en, width=250)
        self.cb_map.pack(side='left')

        f_combat = ctk.CTkFrame(self.scroll_set, fg_color="transparent")
        f_combat.pack(fill='x', pady=2)
        self.lbl_s_combat = ctk.CTkLabel(f_combat, text="Combat Mode:", width=200, anchor='w')
        self.lbl_s_combat.pack(side='left', padx=10)
        self.var_combat = ctk.StringVar(value=self.settings.get("CombatMode", "PvE"))
        ctk.CTkComboBox(f_combat, variable=self.var_combat, values=["PvE", "PvP"], width=250).pack(side='left')
        
        self.lbl_s_gmode = ctk.CTkLabel(self.scroll_set, text="Game Mode: Survival Mode (Coming soon)", font=("Arial", 13, "bold"), text_color="#AAAAAA", justify="left")
        self.lbl_s_gmode.pack(anchor='w', padx=10, pady=(5, 0))

        f_diff = ctk.CTkFrame(self.scroll_set, fg_color="transparent")
        f_diff.pack(fill='x', pady=2)
        self.lbl_s_diff = ctk.CTkLabel(f_diff, text="Difficulty (Coming soon):", width=200, anchor='w')
        self.lbl_s_diff.pack(side='left', padx=10)
        self.var_diff = ctk.StringVar(value=self.settings.get("Difficulty", "Normal"))
        self.cb_diff = ctk.CTkComboBox(f_diff, variable=self.var_diff, values=[], width=250, state="disabled")
        self.cb_diff.pack(side='left')
        
        self.lbl_set_diff_desc = ctk.CTkLabel(self.scroll_set, text="", font=("Arial", 12, "italic"), text_color="#00E676", justify="left", wraplength=500)
        self.lbl_set_diff_desc.pack(anchor='w', padx=220, pady=(0, 10))

        self.var_map_display.trace_add("write", self.on_map_changed)
        self.var_diff.trace_add("write", self.on_diff_changed)
        self.var_combat.trace_add("write", lambda *args: self.save_settings())
        
        self.update_main_diff_options()

        self.lbl_path_t = self.create_label(self.scroll_set, "Pfade / Paths", True)
        self.btn_auto_path = ctk.CTkButton(self.scroll_set, text="🪄 Pfade überall suchen", fg_color="#00695C", command=self.auto_detect_paths)
        self.btn_auto_path.pack(anchor='w', padx=10, pady=5)
        
        self.var_steamcmd = ctk.StringVar(value=self.settings["SteamCmdPath"])
        self.lbl_p_steam = self.create_path_row(self.scroll_set, "SteamCMD.exe:", self.var_steamcmd, self.browse_steamcmd)
        self.var_install = ctk.StringVar(value=self.settings["InstallDir"])
        self.lbl_p_inst = self.create_path_row(self.scroll_set, "Install Ordner:", self.var_install, self.browse_install)
        self.var_exe = ctk.StringVar(value=self.settings["ExePath"])
        self.lbl_p_exe = self.create_path_row(self.scroll_set, "WSServer-Win64-Shipping.exe:", self.var_exe, self.browse_exe)
        
        self.var_worlddb = ctk.StringVar(value=self.settings.get("WorldDbPath", ""))
        self.lbl_p_db = self.create_path_row(self.scroll_set, "world.db Datei:", self.var_worlddb, self.browse_db)

        self.lbl_net_t = self.create_label(self.scroll_set, "Netzwerk / Ports", True)
        
        f_ip = ctk.CTkFrame(self.scroll_set, fg_color="transparent")
        f_ip.pack(fill='x', pady=2)
        self.lbl_ip = ctk.CTkLabel(f_ip, text="Öffentliche IP:", width=150, anchor='w')
        self.lbl_ip.pack(side='left', padx=10)
        self.var_publicip = ctk.StringVar(value=self.settings.get("PublicIP", ""))
        ctk.CTkEntry(f_ip, textvariable=self.var_publicip, width=200).pack(side='left')
        self.btn_ip = ctk.CTkButton(f_ip, text="🌍 Auto IP", width=100, fg_color="#1565C0", command=self.fetch_public_ip)
        self.btn_ip.pack(side='left', padx=5)

        self.var_gameport = ctk.StringVar(value=self.settings["GamePort"])
        self.lbl_gp = self.create_entry_row(self.scroll_set, "Game Port:", self.var_gameport, width=100)
        self.var_queryport = ctk.StringVar(value=self.settings["QueryPort"])
        self.lbl_qp = self.create_entry_row(self.scroll_set, "Query Port:", self.var_queryport, width=100)
        self.var_echoport = ctk.StringVar(value=self.settings.get("EchoPort", "18888"))
        self.lbl_ep = self.create_entry_row(self.scroll_set, "Echo Port:", self.var_echoport, width=100)

        self.lbl_port_hint = ctk.CTkLabel(self.scroll_set, text="", text_color="#FFA000", justify="left")
        self.lbl_port_hint.pack(anchor='w', padx=10, pady=(5, 10))

        for v in [self.var_servername, self.var_password, self.var_adminpassword, self.var_maxplayers, self.var_steamcmd, self.var_install, self.var_exe, self.var_worlddb, self.var_gameport, self.var_queryport, self.var_echoport, self.var_publicip, self.var_backup_interval]:
            v.trace_add("write", lambda *args: self.save_settings())

    def update_main_diff_options(self, update_diff_box=True):
        de = self.var_lang.get() == "Deutsch"
        
        diffs = [d["name_de"] if de else d["name_en"] for d in self.survival_diffs]
        
        if update_diff_box:
            self.cb_diff.configure(values=diffs)
            
        current_val = self.var_diff.get()
        if current_val not in diffs:
            idx = 0
            for i, d in enumerate(self.survival_diffs):
                if d["name_de"] == current_val or d["name_en"] == current_val:
                    idx = i
                    break
            new_val = self.survival_diffs[idx]["name_de"] if de else self.survival_diffs[idx]["name_en"]
            self.var_diff.set(new_val)
            current_val = new_val
            
        if hasattr(self, 'lbl_set_diff_desc') and self.lbl_set_diff_desc.winfo_exists():
            for d in self.survival_diffs:
                sub_name = d["name_de"] if de else d["name_en"]
                if sub_name == current_val:
                    desc = d["desc_de"] if de else d["desc_en"]
                    self.lbl_set_diff_desc.configure(text=desc)
                    break
                    
        self.save_settings()

    def setup_rules(self):
        f = ctk.CTkFrame(self.tab_rules, fg_color="transparent"); f.pack(fill='x', pady=5)
        self.btn_r_auto = ctk.CTkButton(f, text="🔍 Auto-Find", width=120, command=self.auto_detect_rules)
        self.btn_r_auto.pack(side='left', padx=5)
        self.btn_r_man = ctk.CTkButton(f, text="📂 Load JSON", width=120, fg_color="#0277BD", command=self.browse_rules_file)
        self.btn_r_man.pack(side='left', padx=5)
        self.btn_r_save = ctk.CTkButton(f, text="💾 Save Rules", width=120, fg_color="#E65100", command=self.save_rules)
        self.btn_r_save.pack(side='left', padx=5)
        self.rules_editor = ctk.CTkTextbox(self.tab_rules, fg_color="#1E1E1E", text_color="#E6E2AA", font=("Consolas", 13))
        self.rules_editor.pack(expand=True, fill='both', pady=10)

    def create_label(self, parent, txt, bold=False):
        lbl = ctk.CTkLabel(parent, text=txt, font=("Arial", 16, "bold") if bold else ("Arial", 14))
        lbl.pack(anchor='w', padx=10, pady=(15, 5)); return lbl

    def create_entry_row(self, parent, txt, var, pw=False, width=300):
        f = ctk.CTkFrame(parent, fg_color="transparent"); f.pack(fill='x', pady=2)
        lbl = ctk.CTkLabel(f, text=txt, width=150, anchor='w'); lbl.pack(side='left', padx=10)
        ctk.CTkEntry(f, textvariable=var, width=width, show="*" if pw else "").pack(side='left'); return lbl

    def create_path_row(self, parent, txt, var, cmd):
        f = ctk.CTkFrame(parent, fg_color="transparent"); f.pack(fill='x', pady=2)
        lbl = ctk.CTkLabel(f, text=txt, width=200, anchor='w'); lbl.pack(side='left', padx=10)
        ctk.CTkEntry(f, textvariable=var, width=350).pack(side='left')
        ctk.CTkButton(f, text="...", width=40, command=cmd).pack(side='left', padx=5); return lbl

    def log(self, prefix_de, msg_de, prefix_en=None, msg_en=None):
        try:
            de = self.var_lang.get() == "Deutsch"
        except:
            de = False
            
        prefix = prefix_de if de else (prefix_en if prefix_en else prefix_de)
        msg = msg_de if de else (msg_en if msg_en else msg_de)
        
        time_str = datetime.now().strftime('%H:%M:%S')
        formatted = f"[{time_str}] [{prefix}] {msg}\n"
        self.console.configure(state='normal')
        self.console.insert("end", formatted)
        self.console.see("end")
        self.console.configure(state='disabled')

    def fetch_public_ip(self):
        def task():
            try:
                self.after(0, lambda: self.var_publicip.set("Lade..." if self.var_lang.get() == "Deutsch" else "Loading..."))
                req = urllib.request.Request('https://api.ipify.org')
                with urllib.request.urlopen(req, timeout=5) as response:
                    ip = response.read().decode('utf-8')
                    self.after(0, lambda: self.var_publicip.set(ip))
                    self.after(0, lambda: self.log("Netzwerk", f"Öffentliche IP gefunden: {ip}", "Network", f"Public IP found: {ip}"))
            except Exception as e:
                self.after(0, lambda: self.var_publicip.set(""))
                self.after(0, lambda: self.log("Fehler", f"IP-Suche fehlgeschlagen: {e}", "Error", f"IP search failed: {e}"))
        threading.Thread(target=task, daemon=True).start()

    def start_server(self):
        de = self.var_lang.get() == "Deutsch"
        exe = self.var_exe.get()
        if not os.path.exists(exe): 
            messagebox.showerror("Fehler" if de else "Error", "WSServer-Win64-Shipping.exe Pfad ungültig!" if de else "WSServer-Win64-Shipping.exe path invalid!")
            return
            
        map_name = self.settings.get("MapName", "Level01_Main")
        combat_mode = self.settings.get("CombatMode", "PvE").lower()
        
        raw_name = self.var_servername.get().strip()
        if not raw_name.endswith("[RM]") and not raw_name.endswith(" RM"):
            final_server_name = f"{raw_name} [RM]"
        else:
            final_server_name = raw_name
        
        cmd_string = (
            f'"{exe}" {map_name} -server '
            f'-Port={self.var_gameport.get()} '
            f'-QueryPort={self.var_queryport.get()} '
            f'-EchoPort={self.settings.get("EchoPort", "18888")} '
            f'-SteamServerName="{final_server_name}" '
            f'-MaxPlayers={self.var_maxplayers.get()} '
            f'-MULTIHOME=0.0.0.0 '
            f'-forcepassthrough '
            f'-{combat_mode} '
            f'-UTF8Output'
        )
        
        pw = self.var_password.get().strip()
        if pw:
            cmd_string += f' -PSW="{pw}" -ServerPassword="{pw}"'
            
        admin_pw = self.var_adminpassword.get().strip()
        if admin_pw:
            cmd_string += f' -adminpsw="{admin_pw}" -ServerAdminPassword="{admin_pw}"'

        try:
            working_dir = os.path.dirname(exe)
            creation_flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
            
            self.server_process = subprocess.Popen(
                cmd_string, 
                cwd=working_dir,
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                stdin=subprocess.PIPE, 
                text=True, 
                bufsize=1,
                creationflags=creation_flags
            )
            
            self.lbl_status.configure(text="Startet..." if de else "Starting...", text_color="#FFA726")
            self.btn_start.configure(state='disabled')
            self.btn_restart.configure(state='normal')
            self.btn_stop.configure(state='normal')
            self.log("System", "Server-Prozess gestartet! Warte darauf, dass die Welt geladen wird...", "System", "Server process started! Waiting for the world to load...")
            
            threading.Thread(target=self._read_console_output, daemon=True).start()
            threading.Thread(target=self._check_server_ready, daemon=True).start()
            
            threading.Thread(target=self._backup_task, daemon=True).start()
                
        except Exception as e: 
            self.log("Fehler", str(e), "Error", str(e))

    def _backup_task(self):
        while self.server_process and self.server_process.poll() is None:
            try:
                interval_minutes = int(self.var_backup_interval.get())
            except ValueError:
                interval_minutes = 120
                
            if interval_minutes <= 0:
                for _ in range(60):
                    if not self.server_process or self.server_process.poll() is not None:
                        return
                    time.sleep(1)
                continue
                
            interval_seconds = interval_minutes * 60
            
            for _ in range(interval_seconds):
                if not self.server_process or self.server_process.poll() is not None:
                    return
                time.sleep(1)
            
            if self.server_process and self.server_process.poll() is None:
                self._trigger_save_and_backup()

    def _trigger_save_and_backup(self):
        de = self.var_lang.get() == "Deutsch"
        self.after(0, lambda: self.log("Backup", "Starte automatisches Backup...", "Backup", "Starting automatic backup..."))
        
        try:
            try: echo_port = int(self.settings.get('EchoPort', '18888'))
            except: echo_port = 18888

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3.0)
            sock.connect(("127.0.0.1", echo_port))
            sock.sendall(b"saveworld 1\r\n")
            sock.close()
        except Exception:
            if self.server_process and self.server_process.poll() is None:
                try:
                    self.server_process.stdin.write("saveworld 1\r\n")
                    self.server_process.stdin.flush()
                except:
                    pass
        
        time.sleep(10)
        
        db_path = self.var_worlddb.get()
        if db_path and os.path.exists(db_path):
            backup_path = db_path + ".backup"
            try:
                shutil.copy2(db_path, backup_path)
                self.after(0, lambda: self.log("Backup", "Backup erfolgreich erstellt (Altes überschrieben).", "Backup", "Backup successfully created (Old one overwritten)."))
            except Exception as e:
                self.after(0, lambda: self.log("Fehler", f"Backup fehlgeschlagen: {e}", "Error", f"Backup failed: {e}"))
        else:
            self.after(0, lambda: self.log("Backup", "world.db nicht gefunden! Bitte Pfad in den Einstellungen prüfen.", "Backup", "world.db not found! Please check path in settings."))

    def restart_server(self):
        de = self.var_lang.get() == "Deutsch"
        if not self.server_process: 
            return
            
        self.btn_restart.configure(state='disabled')
        self.btn_stop.configure(state='disabled')
        
        self.log("System", "Neustart eingeleitet...", "System", "Restart initiated...")
        self.pending_restart = True
        self.stop_server()

    def _check_server_ready(self):
        ip = "127.0.0.1"
        try:
            port = int(self.var_queryport.get())
        except:
            self.after(0, lambda: self.lbl_status.configure(text="Online", text_color="#69F0AE"))
            return

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2.0)
        
        while self.server_process and self.server_process.poll() is None:
            try:
                sock.sendto(b'\xFF\xFF\xFF\xFFTSource Engine Query\x00', (ip, port))
                data, _ = sock.recvfrom(4096)
                
                if data:
                    self.after(0, lambda: self.lbl_status.configure(text="Online", text_color="#69F0AE"))
                    self.after(0, lambda: self.log("System", "Server ist erfolgreich hochgefahren und bereit für Spieler!", "System", "Server is fully loaded and ready for players!"))
                    break
            except socket.timeout:
                pass
            except Exception:
                pass
            
            time.sleep(2)
            
        sock.close()

    def stop_server(self):
        if not self.server_process: 
            return

        self.btn_stop.configure(state='disabled')
        self.btn_restart.configure(state='disabled')
        
        de = self.var_lang.get() == "Deutsch"
        self.lbl_status.configure(text="Speichert..." if de else "Saving...", text_color="#FFA726")
        
        self.log("System", "Fahre Server sicher herunter und speichere Welt...", "System", "Safely shutting down server and saving world...")

        def shutdown_task():
            try:
                try: echo_port = int(self.settings.get('EchoPort', '18888'))
                except: echo_port = 18888

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3.0)
                try:
                    sock.connect(("127.0.0.1", echo_port))
                    
                    sock.sendall(b"saveworld 1\r\n")
                    self.after(0, lambda: self.log("System", "Speichern der world.db eingeleitet (Telnet)... Warte 5 Sekunden.", "System", "Saving world.db initiated (Telnet)... Waiting 5 seconds."))
                    time.sleep(5)
                    
                    sock.sendall(b"quit 5\r\n")
                    self.after(0, lambda: self.log("System", "Beenden-Signal gesendet. Server fährt in 5 Sekunden herunter...", "System", "Quit signal sent. Server shutting down in 5 seconds..."))
                    sock.close()
                except Exception as e:
                    self.after(0, lambda: self.log("Warnung", f"Konnte nicht per Telnet verbinden ({e}). Versuche Fallback...", "Warning", f"Could not connect via Telnet ({e}). Trying fallback..."))
                    if self.server_process.poll() is None:
                        self.server_process.stdin.write("saveworld 1\r\n")
                        self.server_process.stdin.flush()
                        time.sleep(5)
                    if self.server_process.poll() is None:
                        self.server_process.stdin.write("quit 5\r\n")
                        self.server_process.stdin.flush()

                for _ in range(20):
                    if self.server_process.poll() is not None:
                        break 
                    time.sleep(1)

                if self.server_process.poll() is None:
                    self.after(0, lambda: self.log("Warnung", "Server reagiert nicht auf Shutdown, erzwinge Abbruch...", "Warning", "Server not responding to shutdown, forcing termination..."))
                    self.server_process.terminate()

            except Exception as e:
                self.after(0, lambda: self.log("Fehler", f"Fehler beim Beenden: {e}", "Error", f"Error during shutdown: {e}"))
                try: self.server_process.terminate()
                except: pass

            self.server_process = None
            self.after(0, self._finalize_stop_ui)

        threading.Thread(target=shutdown_task, daemon=True).start()

    def _finalize_stop_ui(self):
        self.lbl_status.configure(text="Offline", text_color="#EF5350")
        self.btn_start.configure(state='normal')
        
        de = self.var_lang.get() == "Deutsch"
        self.btn_stop.configure(text="⏹ Stopp" if de else "⏹ Stop")
        self.btn_restart.configure(text="🔄 Neustart" if de else "🔄 Restart")
        
        self.tracked_players = [] 
        
        if self.timer_id:
            self.after_cancel(self.timer_id)
            self.timer_id = None
            
        self.log("System", "Server erfolgreich gestoppt & Welt gespeichert!", "System", "Server successfully stopped & world saved!")

        if getattr(self, 'pending_restart', False):
            self.pending_restart = False
            self.log("System", "Starte Server in 3 Sekunden neu...", "System", "Restarting server in 3 seconds...")
            self.after(3000, self.start_server)

    def _read_console_output(self):
        if not self.server_process or not self.server_process.stdout:
            return
        try:
            for line in iter(self.server_process.stdout.readline, ''):
                if line:
                    self.after(0, lambda l=line: self._insert_console_raw(l))
        except Exception as e:
            pass
        self.after(0, lambda: self.log("System", "Server-Prozess wurde beendet.", "System", "Server process has been terminated."))

    def _insert_console_raw(self, msg):
        self.console.configure(state='normal')
        self.console.insert("end", msg)
        self.console.see("end")
        self.console.configure(state='disabled')

    def format_time(self, seconds):
        if seconds < 0: seconds = 0
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h > 0: return f"{h}h {m}m"
        elif m > 0: return f"{m}m {s}s"
        else: return f"{s}s"

    def _get_recent_players_from_log(self):
        install_dir = self.var_install.get()
        if not install_dir: return []
        
        log_path = os.path.join(install_dir, "WS", "Saved", "Logs", "WS.log")
        recent_players = []
        
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    for line in reversed(lines):
                        if "LogNet: Join succeeded:" in line:
                            try:
                                name_part = line.split("LogNet: Join succeeded:")[1].strip()
                                time_part = line.split("]")[0].strip("[") 
                                time_str = time_part.split(":")[0] 
                                
                                if not any(p['name'] == name_part for p in recent_players):
                                    dt = datetime.strptime(time_str, "%Y.%m.%d-%H.%M.%S")
                                    dt = dt.replace(tzinfo=timezone.utc) 
                                    join_epoch = dt.timestamp()
                                    recent_players.append({"name": name_part, "join_time": join_epoch})
                            except:
                                pass
            except:
                pass
                
        return recent_players

    def refresh_players_list(self):
        de = self.var_lang.get() == "Deutsch"
        if self.lbl_status.cget("text") not in ["Online", "Startet...", "Starting..."]:
            messagebox.showinfo("Info", "Der Server muss Online sein, um Spieler anzuzeigen." if de else "The server must be online to show players.")
            return
            
        self.btn_refresh_players.configure(state="disabled", text="Lade..." if de else "Loading...")
        
        if self.timer_id:
            self.after_cancel(self.timer_id)
            self.timer_id = None
            
        threading.Thread(target=self._query_players_thread, daemon=True).start()

    def _query_players_thread(self):
        ip = "127.0.0.1" 
        de = self.var_lang.get() == "Deutsch"
        try:
            port = int(self.var_queryport.get())
        except:
            self.after(0, self._query_failed, "Ungültiger Query Port" if de else "Invalid Query Port")
            return

        players = []
        total_players_info = 0
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2.0) 
            
            try:
                sock.sendto(b'\xFF\xFF\xFF\xFFTSource Engine Query\x00', (ip, port))
                info_data, _ = sock.recvfrom(4096)
                if len(info_data) > 5 and info_data[4] == 0x49:
                    offset = 6 
                    for _ in range(4): 
                        offset = info_data.find(b'\x00', offset) + 1
                    offset += 2 
                    total_players_info = info_data[offset]
            except:
                pass 
                
            sock.sendto(b'\xFF\xFF\xFF\xFF\x55\xFF\xFF\xFF\xFF', (ip, port))
            data, _ = sock.recvfrom(4096)
            
            if len(data) >= 5 and data[4] == 0x41: 
                challenge = data[5:9]
                sock.sendto(b'\xFF\xFF\xFF\xFF\x55' + challenge, (ip, port))
                data, _ = sock.recvfrom(4096)
                
                if len(data) >= 5 and data[4] == 0x44: 
                    player_count = data[5]
                    offset = 6
                    
                    for _ in range(player_count):
                        if offset >= len(data): break
                        offset += 1 
                        
                        name_end = data.find(b'\x00', offset)
                        if name_end != -1:
                            name = data[offset:name_end].decode('utf-8', errors='ignore').strip()
                            offset = name_end + 1
                        else:
                            name = ""
                            
                        if offset + 4 <= len(data): 
                            offset += 4 
                            
                        duration = 0.0
                        if offset + 4 <= len(data):
                            duration = struct.unpack('<f', data[offset:offset+4])[0]
                            offset += 4
                        
                        players.append({"name": name, "duration": duration})
            
            log_players = self._get_recent_players_from_log()
            a2s_found_names = [p["name"] for p in players if p["name"]]
            
            available_log_players = [p for p in log_players if p["name"] not in a2s_found_names]
            
            if total_players_info > len(players):
                missing = total_players_info - len(players)
                for _ in range(missing):
                    players.append({"name": "", "duration": 0.0})
                    
            current_time = time.time()
            
            for p in players:
                if not p["name"]:
                    if available_log_players:
                        log_p = available_log_players.pop(0)
                        p["name"] = log_p["name"]
                        p["duration"] = current_time - log_p["join_time"]
                        if p["duration"] < 0: p["duration"] = 0
            
            self.after(0, self._update_players_ui, players)
            
        except socket.timeout:
            self.after(0, self._query_failed, "Timeout: Server antwortet nicht auf Query Port." if de else "Timeout: Server not responding on Query Port.")
        except Exception as e:
            self.after(0, self._query_failed, f"Fehler: {e}" if de else f"Error: {e}")
        finally:
            sock.close()

    def _query_failed(self, error_msg):
        lbl = ctk.CTkLabel(self.scroll_players, text=error_msg, text_color="#EF5350")
        lbl.pack(pady=10)
        self._reset_refresh_btn()

    def _update_players_ui(self, players):
        de = self.var_lang.get() == "Deutsch"
        self.lbl_player_count.configure(text=f"Spieler online: {len(players)}" if de else f"Players online: {len(players)}")
        
        current_time = time.time()
        new_tracked = []
        
        for widget in self.scroll_players.winfo_children():
            widget.destroy()
            
        for p in players:
            existing = next((t for t in self.tracked_players if t["name"] == p["name"] and p["name"]), None)
            join_time = current_time - p["duration"]
            
            if existing and p["duration"] == 0:
                join_time = existing["join_time"]
            elif not p["name"] and p["duration"] == 0:
                existing_anon = [t for t in self.tracked_players if not t["name"]]
                if existing_anon:
                    join_time = existing_anon[0]["join_time"]
                    self.tracked_players.remove(existing_anon[0])
            
            new_tracked.append({"name": p["name"], "join_time": join_time})
            
        self.tracked_players = new_tracked
        self.tracked_players.sort(key=lambda x: x["join_time"])
        
        self.active_players = []
        
        if not self.tracked_players:
            txt = "Niemand ist online." if de else "Nobody is online."
            ctk.CTkLabel(self.scroll_players, text=txt, text_color="#888888").pack(pady=20)
        else:
            for idx, p in enumerate(self.tracked_players):
                row = ctk.CTkFrame(self.scroll_players, fg_color="#333333" if idx % 2 == 0 else "transparent")
                row.pack(fill='x', pady=1)
                
                display_name = p["name"]
                if not display_name:
                    display_name = "Verdeckter Spieler" if de else "Hidden Player"
                
                name_lbl = ctk.CTkLabel(row, text=display_name, width=400, anchor='w')
                name_lbl.pack(side='left', padx=10, pady=5)
                
                duration = current_time - p["join_time"]
                time_lbl = ctk.CTkLabel(row, text=self.format_time(duration), width=200, anchor='w')
                time_lbl.pack(side='left', padx=10, pady=5)
                
                self.active_players.append({"label": time_lbl, "join_time": p["join_time"]})
                
            self._tick_timers()
                
        self._reset_refresh_btn()

    def _tick_timers(self):
        current_time = time.time()
        for p in self.active_players:
            if p["label"].winfo_exists():
                new_duration = current_time - p["join_time"]
                p["label"].configure(text=self.format_time(new_duration))
                
        self.timer_id = self.after(1000, self._tick_timers)

    def _reset_refresh_btn(self):
        de = self.var_lang.get() == "Deutsch"
        self.btn_refresh_players.configure(state="normal", text="🔄 Aktualisieren" if de else "🔄 Refresh")

    def install_steamcmd(self):
        folder = filedialog.askdirectory(title="Ordner für SteamCMD wählen")
        if not folder: return
        def task():
            try:
                self.after(0, lambda: self.log("SteamCMD", "Lade herunter...", "SteamCMD", "Downloading..."))
                urllib.request.urlretrieve("https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip", os.path.join(folder, "steamcmd.zip"))
                with zipfile.ZipFile(os.path.join(folder, "steamcmd.zip"), 'r') as z: z.extractall(folder)
                self.after(0, lambda: self.var_steamcmd.set(os.path.join(folder, "steamcmd.exe")))
                self.after(0, lambda: self.log("SteamCMD", "Erfolgreich installiert!", "SteamCMD", "Successfully installed!"))
            except Exception as e: 
                self.after(0, lambda: self.log("Fehler", str(e), "Error", str(e)))
        threading.Thread(target=task, daemon=True).start()

    def install_server(self):
        de = self.var_lang.get() == "Deutsch"
        cmd = self.var_steamcmd.get()
        if not os.path.exists(cmd): 
            self.log("Fehler", "SteamCMD Pfad fehlt! Bitte in den Einstellungen festlegen.", "Error", "SteamCMD path missing! Please set it in the settings.")
            messagebox.showerror("Fehler" if de else "Error", "Bitte lade zuerst SteamCMD herunter oder wähle den SteamCMD.exe Pfad!" if de else "Please download SteamCMD first or select the SteamCMD.exe path!")
            return
            
        msg = "Wähle nun den Ordner aus, in dem der Soulmask Server installiert werden soll." if de else "Please select the folder where the Soulmask server should be installed."
        messagebox.showinfo("Server Installation" if de else "Server Installation", msg)
        
        target_dir = filedialog.askdirectory(title="Installations-Ordner für Soulmask auswählen" if de else "Select installation folder for Soulmask")
        if not target_dir:
            self.log("System", "Server Installation vom Benutzer abgebrochen.", "System", "Server installation aborted by user.")
            return
            
        self.var_install.set(target_dir)
        self.save_settings()
        
        self._open_install_wizard(cmd, target_dir)

    def _open_install_wizard(self, cmd, target_dir):
        de = self.var_lang.get() == "Deutsch"
        
        wizard = ctk.CTkToplevel(self)
        wizard.title("Server Setup" if de else "Server Setup")
        wizard.geometry("750x650")
        wizard.transient(self)
        wizard.grab_set()
        
        ctk.CTkLabel(wizard, text="Soulmask Server Setup", font=("Arial", 18, "bold")).pack(pady=(20, 10))
        
        f_map = ctk.CTkFrame(wizard, fg_color="transparent")
        f_map.pack(fill='x', padx=40, pady=5)
        ctk.CTkLabel(f_map, text="Map / Welt:" if de else "Map:", width=150, anchor='w').pack(side='left')
        
        current_map = self.settings.get("MapName", "Level01_Main")
        display_map = self.get_map_display_name(current_map, de)
        map_list = self.map_names_de if de else self.map_names_en
        
        var_map_wizard = ctk.StringVar(value=display_map)
        ctk.CTkComboBox(f_map, variable=var_map_wizard, values=map_list).pack(side='left', fill='x', expand=True)

        f_combat = ctk.CTkFrame(wizard, fg_color="transparent")
        f_combat.pack(fill='x', padx=40, pady=5)
        ctk.CTkLabel(f_combat, text="Kampfmodus:" if de else "Combat Mode:", width=150, anchor='w').pack(side='left')
        var_combat_wizard = ctk.StringVar(value=self.settings.get("CombatMode", "PvE"))
        ctk.CTkComboBox(f_combat, variable=var_combat_wizard, values=["PvE", "PvP"]).pack(side='left', fill='x', expand=True)
        
        lbl_mode_desc = ctk.CTkLabel(wizard, text="Das klassische Soulmask-Überlebenserlebnis. Ressourcenmanagement und Planung sind essenziell." if de else "The classic Soulmask survival experience. Resource management and planning are essential.", font=("Arial", 12, "italic"), text_color="#AAAAAA", wraplength=600, justify="center")
        lbl_mode_desc.pack(padx=40, pady=(10, 10))
        
        f_diff_container = ctk.CTkFrame(wizard)
        f_diff_container.pack(fill='x', padx=40, pady=10)
        ctk.CTkLabel(f_diff_container, text="Schwierigkeit (Coming soon):" if de else "Difficulty (Coming soon):", font=("Arial", 14, "bold")).pack(pady=5)
        
        f_diff_radios_1 = ctk.CTkFrame(f_diff_container, fg_color="transparent")
        f_diff_radios_1.pack(pady=2)
        f_diff_radios_2 = ctk.CTkFrame(f_diff_container, fg_color="transparent")
        f_diff_radios_2.pack(pady=2)
        
        lbl_diff_desc = ctk.CTkLabel(f_diff_container, text="", font=("Arial", 13), text_color="#00E676", wraplength=600, justify="center", height=60)
        lbl_diff_desc.pack(pady=10)
        
        var_diff_wizard = ctk.StringVar(value=self.var_diff.get())
        
        def update_difficulties():
            current_diff_names = [d["name_de"] if de else d["name_en"] for d in self.survival_diffs]
            if var_diff_wizard.get() not in current_diff_names:
                var_diff_wizard.set(current_diff_names[0])
            
            for i, d in enumerate(self.survival_diffs):
                name = d["name_de"] if de else d["name_en"]
                desc_de = d["desc_de"]
                desc_en = d["desc_en"]
                
                parent = f_diff_radios_1 if i < 3 else f_diff_radios_2
                rb = ctk.CTkRadioButton(parent, text=name, variable=var_diff_wizard, value=name, state="disabled")
                rb.pack(side='left', padx=10, pady=5)
                
                def make_on_enter(text_de, text_en):
                    return lambda e, t_de=text_de, t_en=text_en: lbl_diff_desc.configure(text=t_de if self.var_lang.get() == "Deutsch" else t_en)
                    
                def on_leave(e):
                    current_val = var_diff_wizard.get()
                    for d_sub in self.survival_diffs:
                        sub_name = d_sub["name_de"] if self.var_lang.get() == "Deutsch" else d_sub["name_en"]
                        if sub_name == current_val:
                            lbl_diff_desc.configure(text=d_sub["desc_de"] if self.var_lang.get() == "Deutsch" else d_sub["desc_en"])
                            break
                            
                rb.bind("<Enter>", make_on_enter(desc_de, desc_en))
                rb.bind("<Leave>", on_leave)
                
            on_leave(None)

        update_difficulties() 
        
        def finish_setup():
            self.settings["MapName"] = self.get_map_val_from_display(var_map_wizard.get())
            self.var_map_display.set(var_map_wizard.get())
            
            self.settings["CombatMode"] = var_combat_wizard.get()
            self.var_combat.set(var_combat_wizard.get())
            
            self.settings["Difficulty"] = var_diff_wizard.get()
            self.var_diff.set(var_diff_wizard.get())
            
            self.save_settings()
            self.update_main_diff_options()
            
            wizard.destroy()
            
            self.log("System", f"Starte Server Install in {target_dir} via SteamCMD...", "System", f"Starting Server Install in {target_dir} via SteamCMD...")
            subprocess.Popen([cmd, "+force_install_dir", target_dir, "+login", "anonymous", "+app_update", "3017310", "validate", "+quit"], creationflags=subprocess.CREATE_NEW_CONSOLE)
            
        btn_frame = ctk.CTkFrame(wizard, fg_color="transparent")
        btn_frame.pack(side="bottom", pady=30) 
        
        btn_cancel = ctk.CTkButton(btn_frame, text="Abbrechen" if de else "Cancel", 
                                   fg_color="#C62828", hover_color="#b71c1c", 
                                   command=wizard.destroy)
        btn_cancel.pack(side='left', padx=10)
        
        btn_install = ctk.CTkButton(btn_frame, text="Installieren" if de else "Install", 
                                    fg_color="#2E7D32", hover_color="#1B5E20", 
                                    command=finish_setup)
        btn_install.pack(side='left', padx=10)

    def update_server(self):
        de = self.var_lang.get() == "Deutsch"
        cmd = self.var_steamcmd.get()
        target_dir = self.var_install.get()

        if not os.path.exists(cmd): 
            self.log("Fehler", "SteamCMD Pfad fehlt! Bitte in den Einstellungen festlegen.", "Error", "SteamCMD path missing! Please set it in the settings.")
            messagebox.showerror("Fehler" if de else "Error", "Bitte lade zuerst SteamCMD herunter oder wähle den SteamCMD.exe Pfad!" if de else "Please download SteamCMD first or select the SteamCMD.exe path!")
            return
            
        if not target_dir or not os.path.exists(target_dir):
            self.log("Fehler", "Installations-Ordner fehlt oder ist ungültig!", "Error", "Installation folder missing or invalid!")
            messagebox.showerror("Fehler" if de else "Error", "Bitte setze den Installations-Ordner in den Einstellungen oder nutze zuerst 'Server Install'!" if de else "Please set the installation folder in settings or use 'Server Install' first!")
            return

        self.log("System", f"Starte Server Update in {target_dir} via SteamCMD...", "System", f"Starting Server Update in {target_dir} via SteamCMD...")
        subprocess.Popen([cmd, "+force_install_dir", target_dir, "+login", "anonymous", "+app_update", "3017310", "validate", "+quit"], creationflags=subprocess.CREATE_NEW_CONSOLE)

    def auto_detect_paths(self):
        self.log("System", "Starte Festplatten-Suche... (Dies läuft im Hintergrund)", "System", "Starting deep drive search... (This runs in the background)")
        self.btn_auto_path.configure(state='disabled')
        
        def search_task():
            for p in [r"C:\SteamCMD\steamcmd.exe", r"D:\SteamCMD\steamcmd.exe"]:
                if os.path.exists(p): self.after(0, lambda p=p: self.var_steamcmd.set(p)); break
                
            install_dir = self.var_install.get()
            if not install_dir:
                for p in [r"C:\SoulmaskServer", r"D:\SoulmaskServer"]:
                    if os.path.exists(p):
                        install_dir = p
                        self.after(0, lambda p=p: self.var_install.set(p))
                        break
            
            if install_dir:
                exe = os.path.join(install_dir, "WS", "Binaries", "Win64", "WSServer-Win64-Shipping.exe")
                if os.path.exists(exe): self.after(0, lambda exe=exe: self.var_exe.set(exe))
            
            found_db = False
            if install_dir:
                target_dir = os.path.join(install_dir, "WS", "Saved", "Worlds", "Dedicated", "Level01_Main")
                search_dirs = [target_dir, os.path.join(install_dir, "WS", "Saved")]
                
                for s_dir in search_dirs:
                    if os.path.exists(s_dir):
                        for root, dirs, files in os.walk(s_dir):
                            for file in files:
                                if file.lower() == "world.db":
                                    self.after(0, lambda path=os.path.join(root, file): self.var_worlddb.set(path))
                                    found_db = True
                                    break
                            if found_db: break
                    if found_db: break

            if not found_db:
                self.after(0, lambda: self.log("System", "world.db nicht im Standard-Ordner. Durchsuche ALLE Festplatten (Das dauert etwas...)", "System", "world.db not in default folder. Searching ALL drives (This takes a while...)"))
                drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
                for drive in drives:
                    for root, dirs, files in os.walk(drive):
                        if "Windows" in root or "$Recycle.Bin" in root or "ProgramData" in root:
                            continue
                        if "world.db" in [f.lower() for f in files]:
                            if "WS" in root and "Level01_Main" in root:
                                db_path = os.path.join(root, "world.db")
                                self.after(0, lambda path=db_path: self.var_worlddb.set(path))
                                self.after(0, lambda path=db_path: self.log("System", f"world.db auf Laufwerk gefunden: {path}", "System", f"world.db found on drive: {path}"))
                                found_db = True
                                break
                    if found_db: break
            
            if not found_db:
                self.after(0, lambda: self.log("System", "Keine world.db gefunden. Hast du den Server schon einmal komplett gestartet?", "System", "No world.db found. Have you completely started the server at least once?"))

            self.after(0, lambda: self.log("System", "Auto-Suche abgeschlossen.", "System", "Auto-search complete."))
            self.after(0, lambda: self.btn_auto_path.configure(state='normal'))

        threading.Thread(target=search_task, daemon=True).start()

    def auto_detect_rules(self):
        install_dir = self.var_install.get()
        if not install_dir:
            self.log("Rules", "Bitte setze zuerst den Install-Ordner!", "Rules", "Please set the installation folder first!")
            return
            
        rules_dir = os.path.join(install_dir, "WS", "Saved", "GameplaySettings")
        
        if os.path.exists(rules_dir):
            json_files = [os.path.join(rules_dir, f) for f in os.listdir(rules_dir) if f.endswith('.json')]
            if json_files:
                latest_rule_file = max(json_files, key=os.path.getmtime)
                try:
                    with open(latest_rule_file, 'r', encoding='utf-8') as f: 
                        self.rules_editor.delete("0.0", "end")
                        self.rules_editor.insert("0.0", f.read())
                    self.current_rules_path = latest_rule_file
                    filename = os.path.basename(latest_rule_file)
                    self.log("Rules", f"Regeln automatisch geladen: {filename}", "Rules", f"Rules automatically loaded: {filename}")
                except Exception as e:
                    self.log("Fehler", f"Konnte Regel-Datei nicht lesen: {e}", "Error", f"Could not read rule file: {e}")
            else:
                self.log("Rules", "GameplaySettings Ordner gefunden, aber keine .json Datei darin.", "Rules", "GameplaySettings folder found, but no .json file inside.")
        else: 
            self.log("Rules", f"Ordner nicht gefunden: {rules_dir}", "Rules", f"Folder not found: {rules_dir}")

    def browse_rules_file(self):
        p = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if p:
            with open(p, 'r', encoding='utf-8') as f: 
                self.rules_editor.delete("0.0", "end")
                self.rules_editor.insert("0.0", f.read())
            self.current_rules_path = p

    def save_rules(self):
        de = self.var_lang.get() == "Deutsch"
        if not self.current_rules_path: 
            messagebox.showerror("Fehler" if de else "Error", "Keine Datei ausgewählt!" if de else "No file selected!")
            return
        with open(self.current_rules_path, 'w', encoding='utf-8') as f: 
            f.write(self.rules_editor.get("0.0", "end").strip())
        self.log("Rules", "Gespeichert!", "Rules", "Saved!")
        messagebox.showinfo("Erfolg" if de else "Success", "Regeln gespeichert!" if de else "Rules saved!")

    def change_language(self, c): 
        self.var_lang.set(c)
        self.save_settings()
        self.apply_language()

    def apply_language(self):
        de = self.var_lang.get() == "Deutsch"
        
        self.btn_start.configure(text="▶ Start")
        
        current_status = self.lbl_status.cget("text")
        if current_status in ["Startet...", "Starting..."]:
            self.lbl_status.configure(text="Startet..." if de else "Starting...")
        elif current_status in ["Speichert...", "Saving..."]:
            self.lbl_status.configure(text="Speichert..." if de else "Saving...")
        
        if self.server_process: 
            self.btn_stop.configure(text="⏹ Stoppt..." if de else "⏹ Stopping...")
            self.btn_restart.configure(text="🔄 Neustartet..." if de else "🔄 Restarting...")
        else: 
            self.btn_stop.configure(text="⏹ Stopp" if de else "⏹ Stop")
            self.btn_restart.configure(text="🔄 Neustart" if de else "🔄 Restart")
            
        self.btn_inst_srv.configure(text="⏬ Server Install" if de else "⏬ Install Server")
        self.btn_update_srv.configure(text="🔄 Server Update" if de else "🔄 Update Server")
        
        self.btn_refresh_players.configure(text="🔄 Aktualisieren" if de else "🔄 Refresh")
        self.lbl_h_time.configure(text="Online seit" if de else "Online since")
        
        try: count = len(self.scroll_players.winfo_children()) 
        except: count = 0
        self.lbl_player_count.configure(text=f"Spieler online: {count}" if de else f"Players online: {count}")
        
        self.lbl_lang_t.configure(text="Sprache:" if de else "Language:")
        self.lbl_prop_t.configure(text="Server Eigenschaften" if de else "Server Properties")
        self.lbl_sn.configure(text="Server Name:")
        self.lbl_pw.configure(text="Passwort:" if de else "Password:")
        self.lbl_apw.configure(text="Admin PW:")
        self.lbl_mp.configure(text="Max. Spieler:" if de else "Max. Players:")
        if hasattr(self, 'lbl_backup'):
            self.lbl_backup.configure(text="Backup Timer (Min):" if de else "Backup Timer (Min):")
        
        self.lbl_game_t.configure(text="Spiel & Welt / Game & World")
        self.lbl_s_map.configure(text="Map / Welt:" if de else "Map:")
        self.lbl_s_combat.configure(text="Kampfmodus:" if de else "Combat Mode:")
        self.lbl_s_diff.configure(text="Schwierigkeit (Coming soon):" if de else "Difficulty (Coming soon):")
        self.lbl_s_gmode.configure(text="Spielmodus: Survival Mode (Coming soon)" if de else "Game Mode: Survival Mode (Coming soon)")

        self.lbl_path_t.configure(text="Pfade" if de else "Paths")
        self.btn_auto_path.configure(text="🪄 Pfade überall suchen" if de else "🪄 Deep Auto-Detect")
        self.lbl_net_t.configure(text="Netzwerk & Ports" if de else "Network & Ports")
        self.lbl_ip.configure(text="Öffentliche IP:" if de else "Public IP:")
        self.btn_ip.configure(text="🌍 Auto IP" if de else "🌍 Get IP")
        
        hint_de = "⚠️ WICHTIG: Damit Freunde beitreten können, musst du diese Ports in deinem\nRouter (Port Forwarding) nur für UDP freigeben!"
        hint_en = "⚠️ IMPORTANT: For friends to join, you must forward these ports in your\nrouter settings (Port Forwarding) for UDP only!"
        self.lbl_port_hint.configure(text=hint_de if de else hint_en)
        
        self.btn_r_auto.configure(text="🔍 Automatisch" if de else "🔍 Auto-Find")
        self.btn_r_man.configure(text="📂 Laden" if de else "📂 Load JSON")
        self.btn_r_save.configure(text="💾 Speichern" if de else "💾 Save Rules")
        
        current_map_val = self.settings.get("MapName", "Level01_Main")
        map_list = self.map_names_de if de else self.map_names_en
        if hasattr(self, 'cb_map'):
            self.cb_map.configure(values=map_list)
            self.var_map_display.set(self.get_map_display_name(current_map_val, de))
            
        self.update_main_diff_options(update_diff_box=True)

    def load_settings(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f: self.settings.update(json.load(f))
            except: pass

    def save_settings(self):
        if self.is_initializing: return
        self.settings.update({
            "Language": self.var_lang.get(), "ServerName": self.var_servername.get(), 
            "ServerPassword": self.var_password.get(), "AdminPassword": self.var_adminpassword.get(), 
            "MaxPlayers": self.var_maxplayers.get(), "ExePath": self.var_exe.get(), 
            "InstallDir": self.var_install.get(), "WorldDbPath": self.var_worlddb.get(),
            "GamePort": self.var_gameport.get(), "QueryPort": self.var_queryport.get(), 
            "EchoPort": self.var_echoport.get(),
            "PublicIP": self.var_publicip.get(), "SteamCmdPath": self.var_steamcmd.get(),
            "MapName": self.get_map_val_from_display(self.var_map_display.get()),
            "CombatMode": self.var_combat.get(),
            "Difficulty": self.var_diff.get(),
            "BackupIntervalMinutes": self.var_backup_interval.get()
        })
        try:
            with open(self.config_file, 'w') as f: json.dump(self.settings, f, indent=4)
        except: pass

    def browse_exe(self):
        f = filedialog.askopenfilename(filetypes=[("Exe", "*.exe")])
        if f: self.var_exe.set(f)
        
    def browse_install(self):
        d = filedialog.askdirectory()
        if d: self.var_install.set(d)

    def browse_steamcmd(self):
        f = filedialog.askopenfilename(filetypes=[("Exe", "*.exe")])
        if f: self.var_steamcmd.set(f)
        
    def browse_db(self):
        f = filedialog.askopenfilename(filetypes=[("Database", "*.db")])
        if f: self.var_worlddb.set(f)

if __name__ == "__main__":
    app = SoulmaskManagerApp()
    app.mainloop()