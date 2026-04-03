import os, json, threading, time, math, pandas as pd
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox

# --- IMPORT YOUR ANIMATION LIBRARY ---
try:
    from drawGUI import ManualMarchingAnts
except ImportError:
    class ManualMarchingAnts:
        def __init__(self, *args, **kwargs): pass

try:
    from amfValveControl import amfValveControl
    HARDWARE_LIB_FOUND = True
except ImportError:
    HARDWARE_LIB_FOUND = False

class TableEncoder(json.JSONEncoder):
    def encode(self, obj):
        if isinstance(obj, list) and all(isinstance(i, list) and len(i) == 3 for i in obj):
            return "[" + ", ".join(json.dumps(i) for i in obj) + "]"
        return super().encode(obj)

class ValveApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Lab Valve Protocol Designer v8.5")
        self.root.geometry("1320x820")

        self.valve_labels = ['A', 'B', 'C', 'D', 'E', 'F']
        self.actual_positions = {k: "1" for k in self.valve_labels}
        self.is_running = False
        self.abort_flag = False
        self.proceed_event = threading.Event()
        
        self.presets, self.port_data, self.valve_ports = {}, {}, {}
        self.port_ids, self.valve_shapes, self.valve_text_map, self.valve_map = {}, {}, {}, {}
        
        self.drag_data, self.ghost_label = None, None

        self.setup_ui()
        self.load_port_map()   
        self.load_library()    
        
        if HARDWARE_LIB_FOUND:
            try:
                self.vc = amfValveControl(status_callback=None)
                self.hardware_enabled = True
            except: self.hardware_enabled = False
        else: self.hardware_enabled = False

    def load_port_map(self):
        if os.path.exists("ValveMap.csv"):
            df = pd.read_csv("ValveMap.csv")
            self.valve_ports = {v: [] for v in self.valve_labels}
            for _, row in df.iterrows():
                v = row['Valve']
                p_port = str(row['Physical port']).split('.')[0] if '.' in str(row['Physical port']) and str(row['Physical port']).endswith('.0') else str(row['Physical port'])
                self.port_data[(v, p_port)] = {
                    'py_port': int(row['python port']),
                    'sch_port': str(row['Schematic port']).replace(".0", ""),
                    'desc': row['description'] if pd.notna(row['description']) else "---"
                }
                self.valve_ports[v].append(p_port)
        self.draw_physical_layout()

    def get_port_coords(self, v, p_name, cx, cy, r):
        ports = self.valve_ports.get(v, [])
        if p_name not in ports: return cx, cy
        idx = ports.index(p_name)
        angle = -90 - (idx * (360 / len(ports)))
        rad = math.radians(angle)
        return cx + (r)*math.cos(rad), cy + (r)*math.sin(rad)

    def draw_physical_layout(self):
        # Clean spacing to prevent overlaps
        self.centers = {'A': (650, 100), 'B': (650, 360), 'D': (400, 360), 'C': (200, 130), 'F': (900, 360), 'E': (1100, 130)}
        r = 45
        self.canvas.delete("all")
        self.port_ids = {}
        self.draw_external_tubing()

        for v, (cx, cy) in self.centers.items():
            v_id = self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, fill="#fdfdfd", width=2, outline="#444")
            self.canvas.create_text(cx, cy, text=v, font=("Arial", 14, "bold"), fill="#bbb")
            self.valve_shapes[v] = v_id
            self.valve_map[v_id] = v 
            
            ports = self.valve_ports.get(v, [])
            for p_name in ports:
                px, py = self.get_port_coords(v, p_name, cx, cy, r+18)
                if ".5" in p_name:
                    p_id = self.canvas.create_oval(px-2, py-2, px+2, py+2, fill="#ccc", outline="#ccc")
                else:
                    p_id = self.canvas.create_text(px, py, text=p_name, font=("Arial", 8, "bold"))
                self.port_ids[(v, p_name)] = p_id
                self.valve_map[p_id] = (v, p_name)

            self.valve_text_map[v] = self.canvas.create_text(cx, cy+r+30, text="Idle", 
                                                            font=("Verdana", 8), width=160, 
                                                            anchor="n", justify="center")

    def draw_external_tubing(self):
        c = self.centers
        # C -> D
        self.canvas.create_line(c['C'][0], c['C'][1], c['D'][0], c['C'][1], c['D'][0], c['D'][1]-65, fill="#eeeeee", width=8)
        # E -> F
        self.canvas.create_line(c['E'][0], c['E'][1], c['F'][0], c['E'][1], c['F'][0], c['F'][1]-65, fill="#eeeeee", width=8)
        # B -> A
        self.canvas.create_line(c['B'][0], c['B'][1]-60, c['A'][0], c['A'][1]+65, fill="#eeeeee", width=8)

    def trigger_flow_animation(self, v, p_port):
        """Standardized plumbing based on your map requirements."""
        tag = f"flow_{v}"
        self.canvas.delete(tag) # Immediate stop
        if ".5" in str(p_port): return

        c = self.centers
        # Start at the center of the distributor (Cleaner origin)
        start = (c[v][0], c[v][1])

        # HARD-MAPPED CONNECTIONS (Adjust these port numbers to match your CSV exactly)
        # We target specific ports on the routers A, D, F
        if v == 'C':
            target_port = "1" # Which port on D receives Valve C?
            end = self.get_port_coords('D', target_port, c['D'][0], c['D'][1], 45+18)
            path = [start, (c['D'][0], c['C'][1]), end]
            for i in range(len(path)-1): ManualMarchingAnts(self.canvas, path[i], path[i+1], tag=tag, fill="blue", width=2)
            
        elif v == 'E':
            target_port = "1" # Which port on F receives Valve E?
            end = self.get_port_coords('F', target_port, c['F'][0], c['F'][1], 45+18)
            path = [start, (c['F'][0], c['E'][1]), end]
            for i in range(len(path)-1): ManualMarchingAnts(self.canvas, path[i], path[i+1], tag=tag, fill="blue", width=2)
            
        elif v == 'B':
            target_port = "1" # Which port on A receives Valve B?
            end = self.get_port_coords('A', target_port, c['A'][0], c['A'][1], 45+18)
            path = [start, end]
            for i in range(len(path)-1): ManualMarchingAnts(self.canvas, path[i], path[i+1], tag=tag, fill="cyan", width=2)

    def update_internal_bridges(self, v, p_port):
        if v not in ['A', 'D', 'F']: return
        tag = f"bridge_{v}"; self.canvas.delete(tag)
        if ".5" in str(p_port): return
        try:
            ports = [p for p in self.valve_ports.get(v, []) if ".5" not in p]
            p_port_str = str(p_port).split('.')[0]
            curr_idx = ports.index(p_port_str)
            num, cx, cy, r = len(ports), *self.centers[v], 45
            is_even = (curr_idx % 2 != 0)
            for i in range(1 if is_even else 0, num, 2):
                p1, p2 = ports[i % num], ports[(i + 1) % num]
                c1 = self.get_port_coords(v, p1, cx, cy, r-12); c2 = self.get_port_coords(v, p2, cx, cy, r-12)
                self.canvas.create_line(c1[0], c1[1], c2[0], c2[1], fill="red", width=5, capstyle="round", tags=(tag,))
        except: pass

    def moveValve(self, v, p_port):
        p_port = str(p_port).split('.')[0] if '.' in str(p_port) and str(p_port).endswith('.0') else str(p_port)
        info = self.port_data.get((v, p_port))
        if not info: return

        self.canvas.itemconfig(self.valve_shapes[v], fill="yellow")
        if self.hardware_enabled: threading.Thread(target=lambda: self.vc.setValvePort(v, info['py_port']), daemon=True).start()
        else: time.sleep(0.05)

        for (vid, pid), tid in self.port_ids.items():
            if vid == v: self.canvas.itemconfig(tid, fill="#ccc" if ".5" in pid else "black")
        
        if (v, p_port) in self.port_ids: self.canvas.itemconfig(self.port_ids[(v, p_port)], fill="red")

        self.actual_positions[v] = p_port
        self.update_internal_bridges(v, p_port)
        self.trigger_flow_animation(v, p_port)
        
        self.canvas.itemconfig(self.valve_shapes[v], fill="#e6ffed")
        status_txt = f"Port {p_port} (Sch:{info['sch_port']})\n{info['desc']}"
        self.canvas.itemconfig(self.valve_text_map[v], text=status_txt)

    def setup_ui(self):
        v_f = ttk.LabelFrame(self.root, text="Fluidic Schematic v8.5"); v_f.pack(fill="x", padx=10, pady=5)
        self.canvas = tk.Canvas(v_f, width=1300, height=500, bg="#ffffff"); self.canvas.pack()
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
        self.lib_list.bind("<ButtonPress-1>", self.on_drag_start); self.lib_list.bind("<B1-Motion>", self.on_drag_motion)
        self.lib_list.bind("<Delete>", self.delete_lib_item); self.seq_tree.bind("<ButtonPress-1>", self.on_drag_start)
        self.seq_tree.bind("<B1-Motion>", self.on_drag_motion); self.seq_tree.bind("<Delete>", self.delete_seq_item)
        self.seq_tree.bind("<Double-1>", self.on_time_edit); self.root.bind("<ButtonRelease-1>", self.on_drop)

    def handle_click(self, event):
        item = self.canvas.find_closest(event.x, event.y)[0]
        m = self.valve_map.get(item)
        if isinstance(m, tuple): threading.Thread(target=self.moveValve, args=m, daemon=True).start()
        elif m:
            p_list = self.valve_ports.get(m, ["1"])
            cur = self.actual_positions[m]
            idx = (p_list.index(cur) + 1) % len(p_list) if cur in p_list else 0
            threading.Thread(target=self.moveValve, args=(m, p_list[idx]), daemon=True).start()

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
        name = self.seq_tree.item(item_id, 'text'); dur = float(self.seq_tree.item(item_id, 'values')[0])
        if "PROMPT" in name.upper():
            self.log("PAUSED..."); self.btn_proceed.config(state="normal")
            self.proceed_event.clear(); self.proceed_event.wait(); self.btn_proceed.config(state="disabled")
        elif "WAIT" in name.upper(): self.log(f"Wait {dur}s"); time.sleep(dur)
        else: self.run_preset_data(name); time.sleep(dur)
    def run_preset_data(self, name):
        data = self.presets.get(name)
        if isinstance(data, list) and len(data) > 0:
            if isinstance(data[0], list):
                for v, _, p in data: self.moveValve(v, p)
            else:
                for s in data: self.run_preset_data(s['name']); time.sleep(float(s['time']))
    def load_library(self):
        self.presets = {"-WAIT STEP-": "WAIT", "-MANUAL PROMPT-": "PROMPT"}
        if os.path.exists("valve_library.json"):
            with open("valve_library.json", "r") as f: self.presets.update(json.load(f))
        self.refresh_library_listbox()
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
    def save_library_to_disk(self):
        with open("valve_library.json", "w") as f: json.dump(self.presets, f, cls=TableEncoder, indent=4)
    def refresh_library_listbox(self):
        self.lib_list.delete(0, 'end')
        for name in sorted(self.presets.keys()): self.lib_list.insert("end", name)
    def on_time_edit(self, event):
        item = self.seq_tree.identify_row(event.y)
        if item:
            v = self.seq_tree.item(item, 'values')[0]; t = simpledialog.askfloat("Time", "Seconds:", initialvalue=float(v))
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
        if not self.ghost_label: self.ghost_label = tk.Label(self.root, text=str(self.drag_data["content"]), bg="yellow", bd=1, relief="solid")
        self.ghost_label.place(x=self.root.winfo_pointerx() - self.root.winfo_rootx() + 15, y=self.root.winfo_pointery() - self.root.winfo_rooty() + 15)
    def on_drop(self, event):
        if self.ghost_label: self.ghost_label.destroy(); self.ghost_label = None
        if not self.drag_data or not self.drag_data.get("moved"): return
        ty = self.root.winfo_pointery() - self.seq_tree.winfo_rooty(); target = self.seq_tree.identify_row(ty)
        parent = target if target and 'group' in self.seq_tree.item(target, 'tags') else self.seq_tree.parent(target)
        if self.drag_data["type"] == "lib": self.seq_tree.insert(parent, 'end', text=self.drag_data["content"], values=(f"{3.0:.1f}",))
        else:
            try: self.seq_tree.move(self.drag_data["content"], parent, 'end')
            except: pass
        self.drag_data = None
    def delete_lib_item(self, event):
        sel = self.lib_list.curselection()
        if sel:
            name = self.lib_list.get(sel[0])
            if messagebox.askyesno("Delete", f"Delete '{name}'?"):
                del self.presets[name]; self.save_library_to_disk(); self.refresh_library_listbox()
    def delete_seq_item(self, event):
        for s in self.seq_tree.selection(): self.seq_tree.delete(s)
    def save_protocol(self):
        p = filedialog.asksaveasfilename(defaultextension=".json")
        if p:
            d = []
            for g in self.seq_tree.get_children(''):
                d.append({"name": self.seq_tree.item(g, 'text'), "time": self.seq_tree.item(g, 'values')[0], "parent": "", "is_group": 'group' in self.seq_tree.item(g, 'tags')})
                for c in self.seq_tree.get_children(g): d.append({"name": self.seq_tree.item(c, 'text'), "time": self.seq_tree.item(c, 'values')[0], "parent": self.seq_tree.item(g, 'text'), "is_group": False})
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