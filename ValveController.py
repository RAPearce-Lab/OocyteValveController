import os, json, threading, time, math, pandas as pd
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox

try:
    from amfValveControl import amfValveControl
    HARDWARE_LIB_FOUND = True
except ImportError:
    HARDWARE_LIB_FOUND = False

# --- COMPACT JSON ENCODER ---
class TableEncoder(json.JSONEncoder):
    def encode(self, obj):
        if isinstance(obj, list) and all(isinstance(i, list) and len(i) == 3 for i in obj):
            return "[" + ", ".join(json.dumps(i) for i in obj) + "]"
        return super().encode(obj)

class ValveApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Lab Valve Protocol Designer v7.9")
        self.root.geometry("1320x750")

        self.DEFAULT_STEP_TIME = 3.0
        self.valve_labels = ['A', 'B', 'C', 'D', 'E', 'F']
        self.is_running = False
        self.abort_flag = False
        self.proceed_event = threading.Event()
        
        self.presets = {}
        self.port_data = {}      # (Valve, PortStr) -> Full CSV Row info
        self.valve_ports = {}    # Valve -> List of Port Strings in CSV order
        self.port_ids = {}       # (Valve, PortStr) -> Canvas Object ID
        self.actual_positions = {k: "1" for k in self.valve_labels}
        
        self.valve_shapes, self.valve_text_map, self.valve_map = {}, {}, {}
        self.drag_data, self.ghost_label = None, None

        self.setup_ui()
        self.load_port_map()   
        self.load_library()    
        
        if HARDWARE_LIB_FOUND:
            try:
                self.vc = amfValveControl(status_callback=None)
                self.hardware_enabled = True
                self.log("Hardware Initialized.")
            except:
                self.hardware_enabled = False
                self.log("SIMULATION MODE (Init failed)")
        else:
            self.hardware_enabled = False
            self.log("SIMULATION MODE (amfValveControl.py missing)")

    def load_port_map(self):
        """Loads CSV and maintains the exact row sequence for geometry."""
        if os.path.exists("ValveMap.csv"):
            df = pd.read_csv("ValveMap.csv")
            self.port_data = {}
            self.valve_ports = {v: [] for v in self.valve_labels}
            
            for _, row in df.iterrows():
                v = row['Valve']
                if v not in self.valve_labels: continue
                
                # We use Physical port as the primary visual key
                p_port = str(row['Physical port'])
                if p_port.endswith('.0'): p_port = p_port[:-2]
                
                s_port = str(row['Schematic port'])
                if s_port.endswith('.0'): s_port = s_port[:-2]

                self.port_data[(v, p_port)] = {
                    'py_port': int(row['python port']),
                    'sch_port': s_port,
                    'desc': row['description'] if pd.notna(row['description']) else "---"
                }
                self.valve_ports[v].append(p_port)
        self.draw_physical_layout()

    def draw_physical_layout(self):
        """Draws the manifold using the CSV row order for spacing, but counter-clockwise."""
        centers = {'A': (650, 80), 'B': (650, 270), 'D': (450, 300), 'C': (250, 130), 'F': (850, 300), 'E': (1050, 130)}
        r = 45
        self.canvas.delete("all")
        self.port_ids = {}

        for v, (cx, cy) in centers.items():
            # Valve Body
            v_id = self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, fill="#f9f9f9", width=2)
            self.canvas.create_text(cx, cy, text=v, font=("Arial", 16, "bold"))
            self.valve_shapes[v] = v_id
            self.valve_map[v_id] = v 
            
            ports = self.valve_ports.get(v, [])
            num_positions = len(ports)
            
            for i, p_name in enumerate(ports):
                # Start at Top (-90 degrees)
                # Counter-Clockwise: subtract angle as index increases
                angle = -90 - (i * (360 / num_positions))
                rad = math.radians(angle)
                px, py = cx + (r+22)*math.cos(rad), cy + (r+22)*math.sin(rad)
                
                # Logic for Whole Numbers vs Half-Step Dots
                if ".5" in p_name:
                    p_id = self.canvas.create_oval(px-2, py-2, px+2, py+2, fill="black", outline="black")
                else:
                    p_id = self.canvas.create_text(px, py, text=p_name, font=("Arial", 9))
                
                self.port_ids[(v, p_name)] = p_id
                self.valve_map[p_id] = (v, p_name)

            self.valve_text_map[v] = self.canvas.create_text(cx, cy+r+45, text="Idle", font=("Arial", 8), width=180)

    def moveValve(self, v, p_port):
        """Moves valve, restores red highlight, and logs full description."""
        p_port = str(p_port)
        if p_port.endswith('.0'): p_port = p_port[:-2]
        
        info = self.port_data.get((v, p_port))
        if not info: return

        self.canvas.itemconfig(self.valve_shapes[v], fill="yellow")
        
        if self.hardware_enabled:
            self.vc.setValvePort(v, info['py_port'])
        else:
            time.sleep(0.1)

        # Update Highlighting
        for (vid, pid), tid in self.port_ids.items():
            if vid == v:
                is_dot = ".5" in pid
                color = "black"
                self.canvas.itemconfig(tid, fill=color, width=1 if is_dot else 0)
                if not is_dot: self.canvas.itemconfig(tid, font=("Arial", 9))
        
        # Set Active Port to RED
        if (v, p_port) in self.port_ids:
            tid = self.port_ids[(v, p_port)]
            self.canvas.itemconfig(tid, fill="red")
            if ".5" not in p_port:
                self.canvas.itemconfig(tid, font=("Arial", 10, "bold"))

        self.actual_positions[v] = p_port
        self.canvas.itemconfig(self.valve_shapes[v], fill="#90ee90")
        
        status_txt = f"Port {p_port} (Sch:{info['sch_port']})\n{info['desc']}"
        self.canvas.itemconfig(self.valve_text_map[v], text=status_txt)
        self.log(f"VALVE {v} -> Physical {p_port} | {info['desc']} (Sch:{info['sch_port']})")

    # --- UI & LOGIC BOILERPLATE ---

    def setup_ui(self):
        v_f = ttk.LabelFrame(self.root, text="Counter-Clockwise Physical View"); v_f.pack(fill="x", padx=10, pady=5)
        self.canvas = tk.Canvas(v_f, width=1300, height=380, bg="#ffffff"); self.canvas.pack()
        self.canvas.bind("<Button-1>", self.handle_click)

        self.paned = tk.PanedWindow(self.root, orient="horizontal", sashwidth=4, bg="#cccccc")
        self.paned.pack(fill="both", expand=True, padx=10, pady=10)

        lib_p = ttk.Frame(self.paned); self.paned.add(lib_p, width=250)
        self.lib_list = tk.Listbox(lib_p, font=("Segoe UI", 9)); self.lib_list.pack(fill="both", expand=True)

        seq_p = ttk.Frame(self.paned); self.paned.add(seq_p, width=500)
        self.seq_tree = ttk.Treeview(seq_p, columns=("time",), show='tree headings')
        self.seq_tree.heading("#0", text="Step"); self.seq_tree.heading("time", text="Wait (s)")
        self.seq_tree.pack(fill="both", expand=True); self.seq_tree.tag_configure('group', background='#E6F2FF')

        ctrl = ttk.Frame(seq_p, padding=5); ctrl.pack(fill="x")
        ttk.Button(ctrl, text="+ Group", command=self.add_group).pack(side="left", padx=2)
        ttk.Button(ctrl, text="Save Group", command=self.save_group_as_preset).pack(side="left", padx=2)
        ttk.Button(ctrl, text="Save Seq", command=self.save_protocol).pack(side="left", padx=2)
        ttk.Button(ctrl, text="Load Seq", command=self.load_protocol).pack(side="left", padx=2)

        log_p = ttk.Frame(self.paned); self.paned.add(log_p)
        self.console = tk.Text(log_p, state='disabled', font=("Consolas", 9), height=10); self.console.pack(fill="both", expand=True)

        exec_f = ttk.Frame(log_p, padding=5); exec_f.pack(fill="x")
        ttk.Button(exec_f, text="RUN", command=self.start_protocol).pack(side="left", padx=2)
        self.btn_proceed = ttk.Button(exec_f, text="PROCEED", command=lambda: self.proceed_event.set(), state="disabled"); self.btn_proceed.pack(side="left", padx=2)
        ttk.Button(exec_f, text="STOP", command=self.stop_protocol).pack(side="left", padx=10)

        self.lib_list.bind("<ButtonPress-1>", self.on_drag_start)
        self.lib_list.bind("<B1-Motion>", self.on_drag_motion)
        self.lib_list.bind("<Delete>", self.delete_lib_item)
        self.seq_tree.bind("<ButtonPress-1>", self.on_drag_start)
        self.seq_tree.bind("<B1-Motion>", self.on_drag_motion)
        self.seq_tree.bind("<Delete>", self.delete_seq_item)
        self.seq_tree.bind("<Double-1>", self.on_time_edit)
        self.root.bind("<ButtonRelease-1>", self.on_drop)

    def handle_click(self, event):
        item = self.canvas.find_closest(event.x, event.y)[0]
        m = self.valve_map.get(item)
        if isinstance(m, tuple): threading.Thread(target=self.moveValve, args=m, daemon=True).start()
        elif m:
            p_list = self.valve_ports.get(m, ["1"])
            cur = self.actual_positions[m]
            idx = (p_list.index(cur) + 1) % len(p_list) if cur in p_list else 0
            threading.Thread(target=self.moveValve, args=(m, p_list[idx]), daemon=True).start()

    def save_library_to_disk(self):
        try:
            lines = ["{"]
            keys = sorted(self.presets.keys())
            for i, k in enumerate(keys):
                val_str = json.dumps(self.presets[k], cls=TableEncoder)
                comma = "," if i < len(keys) - 1 else ""
                lines.append(f'    "{k}": {val_str}{comma}')
            lines.append("}")
            with open("valve_library.json", "w") as f: f.write("\n".join(lines))
        except Exception as e: self.log(f"Save Error: {e}")

    def load_library(self):
        self.presets = {"-WAIT STEP-": "WAIT", "-MANUAL PROMPT-": "PROMPT"}
        if os.path.exists("valve_library.json"):
            try:
                with open("valve_library.json", "r") as f:
                    data = json.load(f); self.presets.update(data)
            except: pass
        self.refresh_library_listbox()

    def log(self, msg):
        self.console.config(state='normal'); self.console.insert('end', f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.console.see('end'); self.console.config(state='disabled')

    def start_protocol(self): self.abort_flag = False; threading.Thread(target=self.run_protocol, daemon=True).start()
    def stop_protocol(self): self.abort_flag = True; self.proceed_event.set()

    def run_protocol(self):
        self.is_running = True
        for item in self.seq_tree.get_children(''):
            if self.abort_flag: break
            if self.seq_tree.get_children(item):
                for child in self.seq_tree.get_children(item):
                    if self.abort_flag: break
                    self._step(child)
            else: self._step(item)
        self.log("Protocol Finished."); self.is_running = False

    def _step(self, item_id):
        name = self.seq_tree.item(item_id, 'text')
        dur = float(self.seq_tree.item(item_id, 'values')[0])
        if "PROMPT" in name.upper():
            self.log("PAUSED..."); self.btn_proceed.config(state="normal")
            self.proceed_event.clear(); self.proceed_event.wait(); self.btn_proceed.config(state="disabled")
        elif "WAIT" in name.upper():
            self.log(f"Wait {dur}s"); time.sleep(dur)
        else:
            self.run_preset_data(name); time.sleep(dur)

    def run_preset_data(self, name):
        data = self.presets.get(name)
        if isinstance(data, list) and len(data) > 0:
            if isinstance(data[0], list):
                for v, _, p in data: threading.Thread(target=self.moveValve, args=(v, p), daemon=True).start()
            else:
                for s in data: self.run_preset_data(s['name']); time.sleep(float(s['time']))

    def add_group(self):
        n = simpledialog.askstring("Group", "Name:")
        if n: self.seq_tree.insert('', 'end', text=n, values=("0.0",), tags=('group',), open=True)

    def save_group_as_preset(self):
        sel = self.seq_tree.selection()
        if sel and 'group' in self.seq_tree.item(sel[0], 'tags'):
            n = simpledialog.askstring("Save", "Preset Name:")
            if n:
                steps = [{"name": self.seq_tree.item(c, 'text'), "time": self.seq_tree.item(c, 'values')[0]} for c in self.seq_tree.get_children(sel[0])]
                self.presets[n] = steps; self.save_library_to_disk(); self.refresh_library_listbox()

    def delete_lib_item(self, event):
        sel = self.lib_list.curselection()
        if sel:
            name = self.lib_list.get(sel)
            if messagebox.askyesno("Delete", f"Delete '{name}'?"):
                del self.presets[name]; self.save_library_to_disk(); self.refresh_library_listbox()

    def delete_seq_item(self, event):
        for s in self.seq_tree.selection(): self.seq_tree.delete(s)

    def refresh_library_listbox(self):
        self.lib_list.delete(0, 'end')
        for name in sorted(self.presets.keys()):
            self.lib_list.insert("end", name)
            if isinstance(self.presets[name], list) and len(self.presets[name]) > 0 and isinstance(self.presets[name][0], dict):
                self.lib_list.itemconfig("end", fg="#0056b3")

    def on_time_edit(self, event):
        item = self.seq_tree.identify_row(event.y)
        if item:
            v = self.seq_tree.item(item, 'values')[0]
            t = simpledialog.askfloat("Time", "Seconds:", initialvalue=float(v))
            if t is not None: self.seq_tree.item(item, values=(f"{t:.1f}",))

    def on_drag_start(self, event):
        w = event.widget
        if w == self.lib_list:
            idx = w.nearest(event.y)
            if idx >= 0: self.drag_data = {"type": "lib", "content": w.get(idx), "moved": False}
        else:
            item = w.identify_row(event.y)
            if item: self.drag_data = {"type": "tree", "content": item, "moved": False}

    def on_drag_motion(self, event):
        if not self.drag_data: return
        self.drag_data["moved"] = True
        if not self.ghost_label:
            self.ghost_label = tk.Label(self.root, text=str(self.drag_data["content"]), bg="yellow", bd=1, relief="solid")
        self.ghost_label.place(x=self.root.winfo_pointerx() - self.root.winfo_rootx() + 15,
                               y=self.root.winfo_pointery() - self.root.winfo_rooty() + 15)

    def on_drop(self, event):
        if self.ghost_label: self.ghost_label.destroy(); self.ghost_label = None
        if not self.drag_data or not self.drag_data.get("moved"): return
        ty = self.root.winfo_pointery() - self.seq_tree.winfo_rooty()
        target = self.seq_tree.identify_row(ty)
        parent = target if target and 'group' in self.seq_tree.item(target, 'tags') else self.seq_tree.parent(target)
        if self.drag_data["type"] == "lib":
            name = self.drag_data["content"]; val = self.presets.get(name)
            if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict):
                g = self.seq_tree.insert(parent, 'end', text=name, values=("0.0",), tags=('group',), open=True)
                for s in val: self.seq_tree.insert(g, 'end', text=s['name'], values=(s['time'],))
            else: self.seq_tree.insert(parent, 'end', text=name, values=(f"{self.DEFAULT_STEP_TIME:.1f}",))
        else:
            try: self.seq_tree.move(self.drag_data["content"], parent, 'end')
            except: pass
        self.drag_data = None

    def save_protocol(self):
        p = filedialog.asksaveasfilename(defaultextension=".json")
        if p:
            d = []
            for g in self.seq_tree.get_children(''):
                is_g = 'group' in self.seq_tree.item(g, 'tags')
                d.append({"name": self.seq_tree.item(g, 'text'), "time": self.seq_tree.item(g, 'values')[0], "parent": "", "is_group": is_g})
                for c in self.seq_tree.get_children(g):
                    d.append({"name": self.seq_tree.item(c, 'text'), "time": self.seq_tree.item(c, 'values')[0], "parent": self.seq_tree.item(g, 'text'), "is_group": False})
            with open(p, 'w') as f: json.dump(d, f, indent=4)

    def load_protocol(self):
        p = filedialog.askopenfilename()
        if p:
            with open(p, 'r') as f: d = json.load(f)
            self.seq_tree.delete(*self.seq_tree.get_children()); m = {}
            for r in d:
                if r["is_group"]: m[r["name"]] = self.seq_tree.insert('', 'end', text=r["name"], values=(r["time"],), tags=('group',), open=True)
                else: self.seq_tree.insert(m.get(r["parent"], ""), 'end', text=r["name"], values=(r["time"],))

if __name__ == "__main__":
    root = tk.Tk(); app = ValveApp(root); root.mainloop()