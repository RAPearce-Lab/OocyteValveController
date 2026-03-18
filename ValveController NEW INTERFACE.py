import os
import json
import threading
import time
import math
import pandas as pd
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog
from amfValveControl import amfValveControl

class ValveApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Lab Valve Protocol Builder v3.2")

        # --- 1. State Variables ---
        self.valve_labels = ['A', 'B', 'C', 'D', 'E', 'F']
        self.is_running = False
        self.abort_flag = False
        
        self.user_to_hw = {}          
        self.port_display_info = {}   
        self.ordered_user_ports = {}  
        self.actual_positions = {k: "1" for k in self.valve_labels}
        
        self.valve_shapes = {} 
        self.valve_text_map = {} 
        self.port_label_ids = {} 
        self.valve_map = {} 

        # Default Presets
        self.presets = {
            "1a":           [('A', 1.0, "1"), ('B', 1.0, "4"), ('C', 1.0, "1"), ('D', 1.0, "1"), ('E', 1.0, "1"), ('F', 1.0, "1")],
            "1b":           [('A', 1.0, "1"), ('B', 1.0, "3"), ('C', 1.0, "1"), ('D', 1.0, "1"), ('E', 1.0, "1"), ('F', 1.0, "1")],
            "1c":           [('A', 1.0, "1"), ('B', 1.0, "2"), ('C', 1.0, "1"), ('D', 1.0, "1"), ('E', 1.0, "1"), ('F', 1.0, "1")],
            "2":            [('A', 1.0, "1"), ('B', 1.0, "1"), ('C', 1.0, "1"), ('D', 1.0, "1"), ('E', 1.0, "1"), ('F', 1.0, "1")],
            "3":            [('A', 1.0, "1"), ('B', 1.0, "1"), ('C', 1.0, "7"), ('D', 1.0, "1"), ('E', 1.0, "7"), ('F', 1.0, "1")],
            "4a":           [('A', 1.0, "4"), ('B', 1.0, "4"), ('C', 1.0, "7"), ('D', 1.0, "6"), ('E', 1.0, "7"), ('F', 1.0, "6")],
            "4b air clear": [('A', 1.0, "4"), ('B', 1.0, "4"), ('C', 1.0, "9"), ('D', 1.0, "6"), ('E', 1.0, "9"), ('F', 1.0, "6")],
            "4c":           [('A', 1.0, "4"), ('B', 1.0, "4"), ('C', 1.0, "1"), ('D', 1.0, "6"), ('E', 1.0, "1"), ('F', 1.0, "6")],
            "4d":           [('A', 1.0, "4"), ('B', 1.0, "4"), ('C', 1.0, "8"), ('D', 1.0, "6"), ('E', 1.0, "8"), ('F', 1.0, "6")],
            "5":            [('A', 1.0, "4"), ('B', 1.0, "3"), ('C', 1.0, "8"), ('D', 1.0, "6"), ('E', 1.0, "8"), ('F', 1.0, "6")],
            "6":            [('A', 1.0, "4"), ('B', 1.0, "2"), ('C', 1.0, "8"), ('D', 1.0, "6"), ('E', 1.0, "8"), ('F', 1.0, "6")],
            "7":            [('A', 1.0, "3"), ('B', 1.0, "2"), ('C', 1.0, "8"), ('D', 1.0, "6"), ('E', 1.0, "8"), ('F', 1.0, "6")],
            "8":            [('A', 1.0, "3"), ('B', 1.0, "3"), ('C', 1.0, "8"), ('D', 1.0, "6"), ('E', 1.0, "8"), ('F', 1.0, "6")],
            "9":            [('A', 1.0, "3"), ('B', 1.0, "1"), ('C', 1.0, "8"), ('D', 1.0, "6"), ('E', 1.0, "8"), ('F', 1.0, "6")],
            "10":           [('A', 1.0, "2"), ('B', 1.0, "4"), ('C', 1.0, "6"), ('D', 1.0, "5"), ('E', 1.0, "6"), ('F', 1.0, "5")],
            "Home lock":    [('A', 1.0, "1.5"), ('B', 1.0, "1.5"), ('C', 1.0, "1.5"), ('D', 1.0, "1.5"), ('E', 1.0, "1.5"), ('F', 1.0, "1.5")]
        }

        self.setup_ui()
        self.load_port_map() 

        try:
            self.vc = amfValveControl(status_callback=self.log)
            self.runPreset("Home lock")
        except Exception as e:
            self.log(f"Hardware Offline: {e}")
            self.vc = None

    def load_port_map(self, csv_file="ValveMap.csv"):
        if not os.path.exists(csv_file):
            self.log(f"WARNING: {csv_file} not found!")
            return
        
        df = pd.read_csv(csv_file)
        for v in self.valve_labels:
            v_data = df[df['Valve'] == v]
            if v_data.empty: continue
            
            self.ordered_user_ports[v] = []
            last_schem = "1"
            for _, row in v_data.iterrows():
                hw_port = int(row['python port'])
                phys = row['Physical port']
                desc = row['description'] if pd.notna(row['description']) else "---"
                u_port = str(int(float(row['Schematic port']))) if pd.notna(row['Schematic port']) else f"{last_schem}.5"
                last_schem = u_port.split('.')[0]

                self.user_to_hw[(v, u_port)] = hw_port
                self.ordered_user_ports[v].append(u_port)
                self.port_display_info[(v, u_port)] = f"P:{phys} | {desc} ({u_port})"

        self.draw_physical_layout()

    def setup_ui(self):
        # Top: Interactive Manifold
        v_frame = ttk.LabelFrame(self.root, text="Physical Layout (Click Numbers to Jump)")
        v_frame.pack(fill="x", padx=10, pady=5)
        
        self.canvas = tk.Canvas(v_frame, width=1100, height=450, bg="#ffffff")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.handle_click)

        # Middle: Logic Panes
        ctrl_main = ttk.Frame(self.root, padding=10)
        ctrl_main.pack(fill="both", expand=True)
        
        paned = ttk.PanedWindow(ctrl_main, orient="horizontal")
        paned.pack(fill="both", expand=True)

        # 1. Preset Library
        lib_pane = ttk.Frame(paned); paned.add(lib_pane, weight=1)
        ttk.Label(lib_pane, text="Presets").pack()
        self.lib_list = tk.Listbox(lib_pane, height=8)
        self.lib_list.pack(fill="both", expand=True)
        for name in sorted(self.presets.keys()): self.lib_list.insert("end", name)

        # 2. Sequence Tree
        seq_pane = ttk.Frame(paned); paned.add(seq_pane, weight=2)
        ttk.Label(seq_pane, text="Sequence").pack()
        self.seq_tree = ttk.Treeview(seq_pane, columns=("preset", "time"), show='headings')
        self.seq_tree.heading("preset", text='Preset'); self.seq_tree.heading("time", text='Wait (s)')
        self.seq_tree.pack(fill="both", expand=True)
        self.seq_tree.bind("<Double-1>", self.on_double_click_time)

        # 3. Log
        log_pane = ttk.Frame(paned); paned.add(log_pane, weight=2)
        ttk.Label(log_pane, text="Log").pack()
        self.console = tk.Text(log_pane, height=8, state='disabled', font=("Consolas", 9))
        self.console.pack(fill="both", expand=True)

        # Bottom: Control Buttons
        btn_row = ttk.Frame(self.root, padding=5)
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="Add Step", command=self.add_step).pack(side="left", padx=2)
        ttk.Button(btn_row, text="Run Protocol", command=self.start_protocol).pack(side="left", padx=2)
        ttk.Button(btn_row, text="STOP", command=self.stop_protocol, style="Alarm.TButton").pack(side="left", padx=10)
        
        ttk.Button(btn_row, text="Clear List", command=lambda: self.seq_tree.delete(*self.seq_tree.get_children())).pack(side="right", padx=2)
        ttk.Button(btn_row, text="Load JSON", command=self.load_protocol).pack(side="right", padx=2)
        ttk.Button(btn_row, text="Save JSON", command=self.save_protocol).pack(side="right", padx=2)

    def draw_physical_layout(self):
        # A is Top-Middle
        # B is below A
        # C-D are left of B, F-E are right of B (Same vertical level)
        centers = {
            'A': (550, 100),
            'B': (550, 290),
            'D': (350, 320),
            'C': (150, 150),
            'F': (750, 320),
            'E': (950, 150)
        }
        r = 45 

        # Optional Header Source
        self.canvas.create_rectangle(500, 10, 600, 40, fill="#f0f0f0")
        self.canvas.create_text(550, 25, text="ND96 Source", font=("Arial", 9, "italic"))

        for label, (cx, cy) in centers.items():
            v_id = self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, fill="#f9f9f9", width=2)
            self.canvas.create_text(cx, cy, text=label, font=("Arial", 16, "bold"))
            self.valve_shapes[label] = v_id
            self.valve_map[v_id] = label 

            ports = self.ordered_user_ports.get(label, [])
            n = len(ports)
            for i, p_name in enumerate(ports):
                angle = (i * (360 / n)) - 90
                rad = math.radians(angle)
                px, py = cx + (r+22)*math.cos(rad), cy + (r+22)*math.sin(rad)
                
                disp = p_name if ".5" not in p_name else "·"
                p_id = self.canvas.create_text(px, py, text=disp, font=("Arial", 8))
                self.port_label_ids[(label, p_name)] = p_id
                self.valve_map[p_id] = (label, p_name)

            t_id = self.canvas.create_text(cx, cy+r+45, text="Idle", font=("Arial", 8), width=180, justify="center")
            self.valve_text_map[label] = t_id

    def handle_click(self, event):
        item = self.canvas.find_closest(event.x, event.y)[0]
        mapping = self.valve_map.get(item)
        if not mapping: return
        if isinstance(mapping, tuple): # Jump to port
            threading.Thread(target=self.moveValve, args=mapping, daemon=True).start()
        else: # Step forward
            p_list = self.ordered_user_ports[mapping]
            nxt = p_list[(p_list.index(self.actual_positions[mapping]) + 1) % len(p_list)]
            threading.Thread(target=self.moveValve, args=(mapping, nxt), daemon=True).start()

    def moveValve(self, label, user_port):
        user_port = str(user_port)
        hw_port = self.user_to_hw.get((label, user_port))
        info = self.port_display_info.get((label, user_port), f"Port {user_port}")

        self.canvas.itemconfig(self.valve_shapes[label], fill="yellow")
        for p in self.ordered_user_ports.get(label, []):
            self.canvas.itemconfig(self.port_label_ids[(label, p)], fill="black", font=("Arial", 8))

        if self.vc: self.vc.setValvePort(label, hw_port)
        
        self.actual_positions[label] = user_port
        self.canvas.itemconfig(self.valve_shapes[label], fill="#90ee90") 
        self.canvas.itemconfig(self.valve_text_map[label], text=info)
        self.canvas.itemconfig(self.port_label_ids[(label, user_port)], fill="red", font=("Arial", 10, "bold"))

    def log(self, message):
        self.console.config(state='normal')
        self.console.insert('end', f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.console.see('end')
        self.console.config(state='disabled')

    def add_step(self):
        sel = self.lib_list.curselection()
        if sel: self.seq_tree.insert('', 'end', values=(self.lib_list.get(sel[0]), "1.0"))

    def on_double_click_time(self, event):
        item_id = self.seq_tree.identify_row(event.y)
        if item_id:
            old_val = self.seq_tree.item(item_id, 'values')
            new_t = simpledialog.askfloat("Duration", "Seconds:", initialvalue=float(old_val[1]))
            if new_t is not None:
                self.seq_tree.item(item_id, values=(old_val[0], f"{new_t:.1f}"))

    def start_protocol(self):
        if not self.is_running:
            self.abort_flag = False
            threading.Thread(target=self.run_protocol, daemon=True).start()

    def stop_protocol(self):
        self.abort_flag = True
        self.log("PROTOCOL ABORTED BY USER")

    def run_protocol(self):
        self.is_running = True
        for item in self.seq_tree.get_children():
            if self.abort_flag: break
            name, duration = self.seq_tree.item(item, 'values')
            self.log(f"Running Preset: {name}")
            for v_label, _, port in self.presets.get(name, []):
                self.moveValve(v_label, port)
            time.sleep(float(duration))
        self.is_running = False
        self.log("Sequence Finished.")

    def save_protocol(self):
        path = filedialog.asksaveasfilename(defaultextension=".json")
        if path:
            steps = [self.seq_tree.item(i, 'values') for i in self.seq_tree.get_children()]
            with open(path, 'w') as f: json.dump(steps, f)

    def load_protocol(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if path:
            with open(path, 'r') as f: steps = json.load(f)
            self.seq_tree.delete(*self.seq_tree.get_children())
            for s in steps: self.seq_tree.insert('', 'end', values=s)

    def runPreset(self, presetName):
        for label, _, port in self.presets.get(presetName, []):
            threading.Thread(target=self.moveValve, args=(label, port), daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = ValveApp(root)
    root.mainloop()