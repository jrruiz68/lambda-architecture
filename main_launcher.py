import tkinter as tk
from tkinter import scrolledtext
import subprocess
import threading
import sys
import os
import queue

class MedicalIOTLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("🏥 Medical IoT - Centro de Comando")
        self.root.geometry("1100x700")
        self.root.configure(bg="#2c3e50")

        # Cola para manejar mensajes: (mensaje, tag, destino)
        self.msg_queue = queue.Queue()
        
        # Diccionario de procesos
        self.processes = {}

        self.create_widgets()
        self.update_terminal_output()

    def create_widgets(self):
        # --- HEADER ---
        header = tk.Frame(self.root, bg="#34495e", pady=10)
        header.pack(fill="x")
        title = tk.Label(header, text="Arquitectura Lambda - Monitor de Procesos", 
                         font=("Segoe UI", 16, "bold"), bg="#34495e", fg="white")
        title.pack()

        # --- BOTONES DE CONTROL ---
        btn_frame = tk.Frame(self.root, bg="#2c3e50", pady=15)
        btn_frame.pack(fill="x")

        # Botón 1: Entrenar
        self.btn_train = tk.Button(btn_frame, text="🧠 1. Entrenar Modelo", 
                                   command=self.run_training, bg="#2980b9", fg="white", 
                                   font=("Arial", 10, "bold"), width=20)
        self.btn_train.grid(row=0, column=0, padx=20)

        # Botón 2: Sensor
        self.btn_sensor = tk.Button(btn_frame, text="💓 2. Iniciar Sensor", 
                                    command=self.run_sensor, bg="#27ae60", fg="white", 
                                    font=("Arial", 10, "bold"), width=20)
        self.btn_sensor.grid(row=0, column=1, padx=20)

        # Botón 3: Detector
        self.btn_detector = tk.Button(btn_frame, text="🔎 3. Iniciar Detector", 
                                      command=self.run_detector, bg="#e67e22", fg="white", 
                                      font=("Arial", 10, "bold"), width=20)
        self.btn_detector.grid(row=0, column=2, padx=20)

        # Botón 4: Stop
        self.btn_stop = tk.Button(btn_frame, text="🛑 DETENER TODO", 
                                  command=self.stop_all, bg="#c0392b", fg="white", 
                                  font=("Arial", 10, "bold"), width=20)
        self.btn_stop.grid(row=0, column=3, padx=20)

        # --- ÁREA DE TERMINALES (SPLIT VIEW) ---
        term_container = tk.Frame(self.root, bg="#2c3e50", padx=10, pady=10)
        term_container.pack(fill="both", expand=True)

        # Configurar grid para que se expanda
        term_container.columnconfigure(0, weight=1)
        term_container.columnconfigure(1, weight=1)
        term_container.columnconfigure(2, weight=1)
        term_container.rowconfigure(1, weight=1)

        # -- Columna 1: Entrenamiento --
        lbl_1 = tk.Label(term_container, text="Log: Entrenamiento (Batch)", bg="#2980b9", fg="white", font=("Arial", 9, "bold"))
        lbl_1.grid(row=0, column=0, sticky="ew", padx=2)
        self.term_train = self.create_console(term_container)
        self.term_train.grid(row=1, column=0, sticky="nsew", padx=2)

        # -- Columna 2: Sensor --
        lbl_2 = tk.Label(term_container, text="Log: Sensor (Producer)", bg="#27ae60", fg="white", font=("Arial", 9, "bold"))
        lbl_2.grid(row=0, column=1, sticky="ew", padx=2)
        self.term_sensor = self.create_console(term_container)
        self.term_sensor.grid(row=1, column=1, sticky="nsew", padx=2)

        # -- Columna 3: Detector --
        lbl_3 = tk.Label(term_container, text="Log: Detector (Consumer)", bg="#e67e22", fg="white", font=("Arial", 9, "bold"))
        lbl_3.grid(row=0, column=2, sticky="ew", padx=2)
        self.term_detect = self.create_console(term_container)
        self.term_detect.grid(row=1, column=2, sticky="nsew", padx=2)

        # Mapeo de claves a widgets
        self.consoles = {
            "TRAIN": self.term_train,
            "SENSOR": self.term_sensor,
            "DETECT": self.term_detect
        }

    def create_console(self, parent):
        """Crea un widget de texto estilo terminal"""
        term = scrolledtext.ScrolledText(parent, bg="#1e1e1e", fg="#00ff00", 
                                         font=("Consolas", 9), state="disabled", height=10)
        term.tag_config("INFO", foreground="#00ff00")
        term.tag_config("ERROR", foreground="#ff4444")
        term.tag_config("WARN", foreground="#f1c40f")
        term.tag_config("SYSTEM", foreground="#3498db")
        return term

    def log(self, message, tag="INFO", target="SYSTEM"):
        """Encola el mensaje para la consola correcta"""
        self.msg_queue.put((message, tag, target))

    def update_terminal_output(self):
        """Procesa la cola y actualiza la GUI"""
        while not self.msg_queue.empty():
            msg, tag, target = self.msg_queue.get()
            
            # Determinar a qué consola va
            widget = self.consoles.get(target)
            
            # Si es un mensaje de sistema global, mandar a todas (opcional)
            # O si el target no existe, ignorar
            if widget:
                widget.config(state="normal")
                widget.insert(tk.END, msg + "\n", tag)
                widget.see(tk.END)
                widget.config(state="disabled")
        
        self.root.after(100, self.update_terminal_output)

    def run_script(self, script_path, key, display_name):
        if key in self.processes:
            self.log(f"⚠️ {display_name} ya está corriendo.", "WARN", key)
            return

        full_path = os.path.join(os.getcwd(), script_path)
        if not os.path.exists(full_path):
            self.log(f"❌ No encuentro: {full_path}", "ERROR", key)
            return

        self.log(f"🚀 Iniciando {display_name}...", "SYSTEM", key)
        
        # Entorno UTF-8 (Fix Emojis)
        my_env = os.environ.copy()
        my_env["PYTHONIOENCODING"] = "utf-8"

        cmd = [sys.executable, "-u", full_path]
        
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            p = subprocess.Popen(cmd, 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE, 
                                 bufsize=1, 
                                 universal_newlines=True, 
                                 encoding='utf-8',
                                 startupinfo=startupinfo,
                                 env=my_env)
            
            self.processes[key] = p

            # Hilos de lectura
            t_out = threading.Thread(target=self.read_stream, args=(p.stdout, "", "INFO", key))
            t_out.daemon = True
            t_out.start()

            t_err = threading.Thread(target=self.read_stream, args=(p.stderr, "[ERR] ", "ERROR", key))
            t_err.daemon = True
            t_err.start()

        except Exception as e:
            self.log(f"❌ Error crítico: {e}", "ERROR", key)

    def read_stream(self, stream, prefix, tag, key):
        """Lee la salida y la manda a la consola correspondiente"""
        for line in iter(stream.readline, ''):
            if line:
                self.log(f"{prefix}{line.strip()}", tag, key)
        stream.close()

    # --- ACCIONES ---
    def run_training(self):
        self.btn_train.config(state="disabled")
        threading.Thread(target=self._run_training_thread).start()

    def _run_training_thread(self):
        self.run_script("batch/train_model.py", "TRAIN", "Entrenamiento")
        # Reactivar botón tras 5 seg
        self.root.after(5000, lambda: self.btn_train.config(state="normal"))

    def run_sensor(self):
        self.run_script("streaming/ecg_producer.py", "SENSOR", "Simulador")
        self.btn_sensor.config(state="disabled", bg="#7f8c8d")

    def run_detector(self):
        self.run_script("streaming/anomaly_detector.py", "DETECT", "Detector")
        self.btn_detector.config(state="disabled", bg="#7f8c8d")

    def stop_all(self):
        self.log("🛑 Deteniendo procesos...", "SYSTEM", "TRAIN") # Mensaje a todas o una
        
        killed = 0
        keys_to_del = []
        for key, p in self.processes.items():
            if p.poll() is None:
                p.terminate()
                keys_to_del.append(key)
                killed += 1
                self.log("⏹️ Proceso detenido.", "WARN", key)
        
        for key in keys_to_del:
            del self.processes[key]

        self.btn_sensor.config(state="normal", bg="#27ae60")
        self.btn_detector.config(state="normal", bg="#e67e22")

    def on_closing(self):
        self.stop_all()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MedicalIOTLauncher(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()