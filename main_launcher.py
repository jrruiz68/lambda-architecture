import tkinter as tk
from tkinter import scrolledtext, messagebox, font
import subprocess
import threading
import sys
import os
import queue
import webbrowser

class LambdaCommandCenter:
    def __init__(self, root):
        self.root = root
        self.root.title("Medical IoT - Lambda Command Center")
        self.root.geometry("1400x850")
        self.root.configure(bg="#0b0f19") # Fondo oscuro profundo

        self.msg_queue = queue.Queue()
        self.processes = {}
        
        # Contadores Globales
        self.counters = {
            "SENSOR": tk.IntVar(value=0),
            "ANOMALIES": tk.IntVar(value=0)
        }

        self.setup_styles()
        self.create_layout()
        self.update_loop()

    def setup_styles(self):
        """Define la paleta de colores y fuentes estilo Terminal Moderna"""
        self.colors = {
            "bg": "#0b0f19",
            "panel": "#1e293b",
            "text": "#e2e8f0",
            "header": "#0f172a",
            "accent": "#38bdf8",
            "success": "#10b981",
            "warning": "#f59e0b",
            "danger": "#ef4444",
            "batch": "#8b5cf6"
        }
        self.fonts = {
            "title": font.Font(family="Consolas", size=18, weight="bold"),
            "subtitle": font.Font(family="Segoe UI", size=12, weight="bold"),
            "console": font.Font(family="Consolas", size=9),
            "btn": font.Font(family="Segoe UI", size=9, weight="bold")
        }

    def create_layout(self):
        # ==========================================
        # HEADER (TOP BAR)
        # ==========================================
        header_frame = tk.Frame(self.root, bg=self.colors["header"], height=70)
        header_frame.pack(fill="x", side="top")
        header_frame.pack_propagate(False)

        title = tk.Label(header_frame, text="⚡ LAMBDA ARCHITECTURE COMMAND CENTER", 
                         font=self.fonts["title"], bg=self.colors["header"], fg=self.colors["accent"])
        title.pack(side="left", padx=20, pady=15)

        # Estadísticas en vivo
        stats_frame = tk.Frame(header_frame, bg=self.colors["header"])
        stats_frame.pack(side="right", padx=20, pady=15)

        tk.Label(stats_frame, text="LATIDOS ENVIADOS:", font=self.fonts["btn"], bg=self.colors["header"], fg="#94a3b8").pack(side="left")
        tk.Label(stats_frame, textvariable=self.counters["SENSOR"], font=self.fonts["subtitle"], bg=self.colors["header"], fg=self.colors["success"]).pack(side="left", padx=(5, 20))
        
        tk.Label(stats_frame, text="ANOMALÍAS:", font=self.fonts["btn"], bg=self.colors["header"], fg="#94a3b8").pack(side="left")
        tk.Label(stats_frame, textvariable=self.counters["ANOMALIES"], font=self.fonts["subtitle"], bg=self.colors["header"], fg=self.colors["danger"]).pack(side="left", padx=5)

        # ==========================================
        # TOOLBAR (BOTONES GLOBALES)
        # ==========================================
        toolbar = tk.Frame(self.root, bg=self.colors["bg"], pady=10)
        toolbar.pack(fill="x", padx=20)

        tk.Button(toolbar, text="🛑 DETENER TODO", command=self.stop_all, bg=self.colors["danger"], fg="white", font=self.fonts["btn"], relief="flat", padx=15, pady=5).pack(side="left")
        
        tk.Button(toolbar, text="🧠 Abrir MLflow", command=lambda: webbrowser.open("http://localhost:5001"), bg="#1d4ed8", fg="white", font=self.fonts["btn"], relief="flat", padx=15, pady=5).pack(side="right", padx=5)
        tk.Button(toolbar, text="📊 Abrir Grafana", command=lambda: webbrowser.open("http://localhost:3000"), bg="#ea580c", fg="white", font=self.fonts["btn"], relief="flat", padx=15, pady=5).pack(side="right")

        # ==========================================
        # MAIN GRID (LOS 5 MÓDULOS)
        # ==========================================
        main_grid = tk.Frame(self.root, bg=self.colors["bg"])
        main_grid.pack(fill="both", expand=True, padx=15, pady=5)

        # Configuración de los 5 scripts del proyecto
        self.modules = {
            "TRAIN":  {"path": "batch/train_model.py", "name": "1. Pre-Entrenamiento", "color": self.colors["batch"]},
            "SENSOR": {"path": "data_sources/sensor_simulador.py", "name": "2. Sensor ECG (Fuente)", "color": self.colors["success"]},
            "LAKE":   {"path": "streaming/raw_to_datalake.py", "name": "3A. Data Lake Ingest", "color": self.colors["accent"]},
            "DETECT": {"path": "streaming/anomaly_detector.py", "name": "3B. Speed Layer (IA)", "color": self.colors["warning"]},
            "BATCH":  {"path": "batch/scheduler.py", "name": "4. Orquestador Batch", "color": self.colors["danger"]}
        }

        self.consoles = {}
        self.leds = {}

        # Dibujar los módulos en un grid dinámico
        row, col = 0, 0
        for key, info in self.modules.items():
            self.create_module_panel(main_grid, key, info, row, col)
            col += 1
            if col > 2: # 3 columnas máximo
                col = 0
                row += 1

        # Centrar el grid configurando pesos
        for i in range(3): main_grid.columnconfigure(i, weight=1)
        for i in range(2): main_grid.rowconfigure(i, weight=1)

    def create_module_panel(self, parent, key, info, row, col):
        """Crea el panel individual (GUI) para cada script"""
        panel = tk.Frame(parent, bg=self.colors["panel"], bd=0, highlightbackground="#334155", highlightthickness=1)
        panel.grid(row=row, column=col, sticky="nsew", padx=10, pady=10)

        # Título del panel
        header = tk.Frame(panel, bg=self.colors["panel"])
        header.pack(fill="x", padx=10, pady=(10, 5))

        # Indicador LED
        led_canvas = tk.Canvas(header, width=12, height=12, bg=self.colors["panel"], highlightthickness=0)
        led_canvas.pack(side="left", pady=2)
        self.leds[key] = led_canvas.create_oval(2, 2, 10, 10, fill="#475569") # Gris apagado

        tk.Label(header, text=info["name"], font=self.fonts["subtitle"], bg=self.colors["panel"], fg=info["color"]).pack(side="left", padx=5)

        # Botones de control del módulo
        ctrl = tk.Frame(panel, bg=self.colors["panel"])
        ctrl.pack(fill="x", padx=10, pady=5)
        
        btn_start = tk.Button(ctrl, text="▶ START", command=lambda k=key: self.start_proc(k), bg="#334155", fg="white", relief="flat", font=self.fonts["btn"], width=8)
        btn_start.pack(side="left", padx=2)
        
        btn_stop = tk.Button(ctrl, text="⏹ STOP", command=lambda k=key: self.stop_proc(k), bg="#334155", fg="white", relief="flat", font=self.fonts["btn"], width=8)
        btn_stop.pack(side="left", padx=2)

        btn_clear = tk.Button(ctrl, text="🗑 CLEAR", command=lambda k=key: self.clear_console(k), bg="#334155", fg="white", relief="flat", font=self.fonts["btn"])
        btn_clear.pack(side="right", padx=2)

        # Consola de salida
        console = scrolledtext.ScrolledText(panel, bg="#020617", fg="#10b981", font=self.fonts["console"], state="disabled", bd=0, padx=5, pady=5)
        console.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Tags de color para la consola
        console.tag_config("ERROR", foreground=self.colors["danger"])
        console.tag_config("SYSTEM", foreground=self.colors["accent"])
        console.tag_config("ALERT", foreground=self.colors["warning"], background="#451a03")
        
        self.consoles[key] = console

    # ==========================================
    # LOGICA DE PROCESOS Y ACTUALIZACIÓN
    # ==========================================
    def log(self, key, text, tag=None):
        """Encola el mensaje para mostrarlo en la GUI de forma segura"""
        self.msg_queue.put((key, text, tag))

    def update_loop(self):
        """Revisa la cola y actualiza la GUI sin congelarla"""
        while not self.msg_queue.empty():
            key, text, tag = self.msg_queue.get()
            
            # Lógica de detección para contadores globales
            if "Enviando segundo" in text:
                self.counters["SENSOR"].set(self.counters["SENSOR"].get() + 1)
            if "🚨 ANOMALÍA" in text:
                self.counters["ANOMALIES"].set(self.counters["ANOMALIES"].get() + 1)
                tag = "ALERT" # Colorear fondo si es alerta
            if "Error" in text or "Exception" in text or "[ERR]" in text:
                tag = "ERROR"

            if key in self.consoles:
                c = self.consoles[key]
                c.config(state="normal")
                if tag:
                    c.insert(tk.END, f"{text}\n", tag)
                else:
                    c.insert(tk.END, f"{text}\n")
                c.see(tk.END)
                c.config(state="disabled")
        
        self.root.after(50, self.update_loop)

    def set_led(self, key, is_on):
        """Cambia el color del círculo a verde (On) o gris (Off)"""
        color = self.modules[key]["color"] if is_on else "#475569"
        canvas = self.root.nametowidget(self.leds[key])
        # Buscamos el canvas padre iterando (truco de Tkinter)
        for child in self.root.winfo_children():
            self._update_led_recursive(child, key, color)

    def _update_led_recursive(self, widget, key, color):
        if isinstance(widget, tk.Canvas):
            items = widget.find_all()
            if items and items[0] == self.leds[key]:
                widget.itemconfig(items[0], fill=color)
                return
        for child in widget.winfo_children():
            self._update_led_recursive(child, key, color)

    def start_proc(self, key):
        if key in self.processes:
            self.log(key, f"⚠️ El proceso ya está en ejecución.", "SYSTEM")
            return
        
        path = self.modules[key]["path"]
        if not os.path.exists(path):
            self.log(key, f"❌ Archivo no encontrado: {path}", "ERROR")
            return

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8" # Fix para Emojis en Windows
        
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            p = subprocess.Popen([sys.executable, "-u", path], 
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 text=True, encoding='utf-8', env=env, startupinfo=startupinfo)
            self.processes[key] = p
            self.set_led(key, True)
            self.log(key, f"▶ INICIANDO: {self.modules[key]['name']}", "SYSTEM")

            threading.Thread(target=self.stream_watcher, args=(p.stdout, key), daemon=True).start()
            threading.Thread(target=self.stream_watcher, args=(p.stderr, key, "[ERR] "), daemon=True).start()
            
            # Hilo para detectar cuando el proceso termina solo (como los scripts Batch)
            threading.Thread(target=self.wait_proc, args=(p, key), daemon=True).start()

        except Exception as e:
            self.log(key, f"❌ Error fatal: {e}", "ERROR")

    def stream_watcher(self, stream, key, prefix=""):
        for line in iter(stream.readline, ''):
            if line: self.log(key, f"{prefix}{line.strip()}")
        stream.close()

    def wait_proc(self, p, key):
        p.wait()
        if key in self.processes:
            del self.processes[key]
            self.set_led(key, False)
            self.log(key, f"⏹ PROCESO FINALIZADO", "SYSTEM")

    def stop_proc(self, key):
        if key in self.processes:
            self.processes[key].terminate()
            # El hilo wait_proc se encargará de limpiar el diccionario y apagar el LED

    def stop_all(self):
        for key in list(self.processes.keys()):
            self.stop_proc(key)

    def clear_console(self, key):
        self.consoles[key].config(state="normal")
        self.consoles[key].delete('1.0', tk.END)
        self.consoles[key].config(state="disabled")

    def on_close(self):
        self.stop_all()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = LambdaCommandCenter(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()