import os, json, threading, time, math, pandas as pd
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox

try:
    from amfValveControl import amfValveControl
    HARDWARE_LIB_FOUND = True
except ImportError:
    HARDWARE_LIB_FOUND = False

class ValveApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Lab Valve Protocol Designer v7.1")
        self.root.geometry("1320x750")

        self.valve_labels = ['A', 'B', 'C', 'D', 'E', 'F']
        self.is_running = False
        self.abort_flag = False
        self.hardware_enabled = False
        self.proceed_event = threading.Event()
        self.user_to_hw = {}          
        self.port_display_info = {}   
        self.ordered_user_ports = {}  
        self.actual_positions = {k: "1" for k in self.valve_labels}
        self.valve_shapes, self.valve_text_map, self.valve_map = {}, {}, {}
        self.presets = {}

        self.setup_ui()
        self.load_library() 
        self.load_port_map() 
        
        # Drag and Drop State
        self.drag_data = None
        self.ghost_label = None

        if HARDWARE_LIB_FOUND:
            try:
                self.vc = amfValveControl(status_callback=self.log)
                self.hardware_enabled = True
                self.log("Hardware Initialized.")
            except Exception as e:
                self.log(f"SIMULATION (Hardware error: {e})")
                self.vc = None
        else:
            self.log("SIMULATION MODE (amfValveControl.py missing)")

    def setup_ui(self):
        # 1. Manifold Top
        v_frame = ttk.LabelFrame(self.root, text="Physical Manifold Layout")
        v_frame.pack(fill="x", padx=10, pady=5)
        self.canvas = tk.Canvas(v_frame, width=1300, height=380, bg="#ffffff")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.handle_click)

        # 2. Workspace Panes
        self.paned = tk.PanedWindow(self.root, orient="horizontal", sashwidth=4, bg="#cccccc")
        self.paned.pack(fill="both", expand=True, padx=10, pady=10)

        # LEFT: Library
        lib_pane = ttk.Frame(self.paned)
        self.paned.add(lib_pane, width=250)
        ttk.Label(lib_pane, text="Preset Library").pack()
        self.lib_list = tk.Listbox(lib_pane, font=("Segoe UI", 9))
        self.lib_list.pack(fill="both", expand=True)

        # MIDDLE: Sequence
        seq_pane = ttk.Frame(self.paned)
        self.paned.add(seq_pane, width=500)
        ttk.Label(seq_pane, text="Sequence Protocol").pack()
        self.seq_tree = ttk.Treeview(seq_pane, columns=("time",), show='tree headings')
        self.seq_tree.heading("#0", text="Step / Group")
        self.seq_tree.heading("time", text="Wait (s)")
        self.seq_tree.pack(fill="both", expand=True)
        self.seq_tree.tag_configure('group', background='#E6F2FF')

        build_btns = ttk.Frame(seq_pane, padding=5)
        build_btns.pack(fill="x")
        ttk.Button(build_btns, text="+ New Group", command=self.add_group).pack(side="left", padx=2)
        ttk.Button(build_btns, text="Save Preset", command=self.save_group_as_preset).pack(side="left", padx=2)
        ttk.Button(build_btns, text="Save Seq", command=self.save_protocol).pack(side="left", padx=2)
        ttk.Button(build_btns, text="Load Seq", command=self.load_protocol).pack(side="left", padx=2)

        # RIGHT: Log
        log_pane = ttk.Frame(self.paned)
        self.paned.add(log_pane)
        self.paned.paneconfig(log_pane, minsize=400) 
        
        ttk.Label(log_pane, text="Execution Log").pack()
        self.console = tk.Text(log_pane, state='disabled', font=("Consolas", 9), height=10)
        self.console.pack(fill="both", expand=True)

        exec_btns = ttk.Frame(log_pane, padding=5)
        exec_btns.pack(fill="x")
        ttk.Button(exec_btns, text="Run Protocol", command=self.start_protocol).pack(side="left", padx=2)
        self.btn_proceed = ttk.Button(exec_btns, text="PROCEED", command=lambda: self.proceed_event.set(), state="disabled")
        self.btn_proceed.pack(side="left", padx=2)
        ttk.Button(exec_btns, text="STOP", command=self.stop_protocol).pack(side="left", padx=10)

        # Bindings for Drag and Drop
        self.lib_list.bind("<ButtonPress-1>", self.on_start_drag_lib)
        self.lib_list.bind("<B1-Motion>", self.on_drag_motion)
        self.seq_tree.bind("<ButtonPress-1>", self.on_start_drag_tree)
        self.seq_tree.bind("<B1-Motion>", self.on_drag_motion)
        self.seq_tree.bind("<Delete>", self.delete_selected)
        self.seq_tree.bind("<Double-1>", self.on_double_click_tree)
        self.root.bind("<ButtonRelease-1>", self.on_drop)

    def load_library(self):
        self.presets = {
           "1a": [["A", 1.0, "1"], ["B", 1.0, "4"], ["C", 1.0, "1"], ["D", 1.0, "1"], ["E", 1.0, "1"], ["F", 1.0, "1"]],
           "Home lock": [["A", 1.0, "1.5"], ["B", 1.0, "1.5"], ["C", 1.0, "1.5"], ["D", 1.0, "1.5"], ["E", 1.0, "1.5"], ["F", 1.0, "1.5"]],
           "-WAIT STEP-": "WAIT", "-MANUAL PROMPT-": "PROMPT"
        }
        if os.path.exists("valve_library.json"):
            try:
                with open("valve_library.json", "r") as f:
                    data = json.load(f); self.presets.update(data if data else {})
            except: pass
        self.lib_list.delete(0, 'end')
        for name in sorted(self.presets.keys()):
            self.lib_list.insert("end", name)
            if isinstance(self.presets[name], list) and len(self.presets[name]) > 0 and isinstance(self.presets[name][0], dict):
                self.lib_list.itemconfig("end", fg="#0056b3")
            if "-" in name: self.lib_list.itemconfig("end", fg="darkgreen")

    # --- RESTORED INTERACTION METHODS ---
    def on_start_drag_lib(self, event):
        idx = self.lib_list.nearest(event.y)
        if idx >= 0:
            val = self.lib_list.get(idx)
            self.drag_data = {"type": "lib", "content": val, "moved": False}

    def on_start_drag_tree(self, event):
        item = self.seq_tree.identify_row(event.y)
        if item:
            self.drag_data = {"type": "tree", "content": item, "moved": False}

    def on_drag_motion(self, event):
        if not self.drag_data: return
        self.drag_data["moved"] = True
        if not self.ghost_label:
            self.ghost_label = tk.Label(self.root, text=str(self.drag_data["content"]), 
                                        bg="yellow", relief="solid", borderwidth=1)
        self.ghost_label.place(x=self.root.winfo_pointerx() - self.root.winfo_rootx() + 15,
                               y=self.root.winfo_pointery() - self.root.winfo_rooty() + 15)

    def on_drop(self, event):
        if self.ghost_label:
            self.ghost_label.destroy()
            self.ghost_label = None
        
        if not self.drag_data or not self.drag_data.get("moved"):
            self.drag_data = None
            return

        # Check if drop target is in the Treeview
        tx = self.root.winfo_pointerx() - self.seq_tree.winfo_rootx()
        ty = self.root.winfo_pointery() - self.seq_tree.winfo_rooty()
        target_id = self.seq_tree.identify_row(ty)
        
        # Determine parent (if dropping on/into a group)
        parent = ""
        if target_id:
            tags = self.seq_tree.item(target_id, 'tags')
            parent = target_id if 'group' in tags else self.seq_tree.parent(target_id)

        if self.drag_data["type"] == "lib":
            name = self.drag_data["content"]
            data = self.presets.get(name)
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                # Restored Group Insertion logic
                new_g = self.seq_tree.insert(parent, 'end', text=name, values=("0.0",), tags=('group',), open=True)
                for s in data:
                    self.seq_tree.insert(new_g, 'end', text=s['name'], values=(s['time'],))
            else:
                self.seq_tree.insert(parent, 'end', text=name, values=("1.0",))
        else:
            # Reorder existing tree item
            try: self.seq_tree.move(self.drag_data["content"], parent, 'end')
            except: pass

        self.drag_data = None

    # --- RE-RESTORED MANIFOLD LOGIC ---
    def draw_physical_layout(self):
        centers = {'A': (650, 80), 'B': (650, 270), 'D': (450, 300), 'C': (250, 130), 'F': (850, 300), 'E': (1050, 130)}
        r = 45
        self.canvas.delete("all")
        for label, (cx, cy) in centers.items():
            v_id = self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, fill="#f9f9f9", width=2)
            self.canvas.create_text(cx, cy, text=label, font=("Arial", 16, "bold"))
            self.valve_shapes[label] = v_id
            self.valve_map[v_id] = label 
            ports = self.ordered_user_ports.get(label, [])
            for i, p_name in enumerate(ports):
                angle = (i * (360 / len(ports))) - 90
                rad = math.radians(angle)
                px, py = cx + (r+22)*math.cos(rad), cy + (r+22)*math.sin(rad)
                p_id = self.canvas.create_text(px, py, text=p_name if ".5" not in p_name else "·", font=("Arial", 8))
                self.valve_map[p_id] = (label, p_name)
            self.valve_text_map[label] = self.canvas.create_text(cx, cy+r+45, text="Idle", font=("Arial", 8), width=180)

    def load_port_map(self):
        if os.path.exists("ValveMap.csv"):
            df = pd.read_csv("ValveMap.csv")
            for v in self.valve_labels:
                v_data = df[df['Valve'] == v]
                if v_data.empty: continue
                self.ordered_user_ports[v] = []
                last = "1"
                for _, row in v_data.iterrows():
                    u_port = str(int(float(row['Schematic port']))) if pd.notna(row['Schematic port']) else f"{last}.5"
                    last = u_port.split('.')[0]
                    self.user_to_hw[(v, u_port)] = int(row['python port'])
                    self.ordered_user_ports[v].append(u_port)
                    self.port_display_info[(v, u_port)] = f"P:{row['Physical port']} | {row['description']} ({u_port})"
        self.draw_physical_layout()

    def moveValve(self, label, port):
        self.canvas.itemconfig(self.valve_shapes[label], fill="yellow")
        if self.hardware_enabled and self.vc: 
            self.vc.setValvePort(label, self.user_to_hw.get((label, str(port))))
        else: time.sleep(0.05)
        self.actual_positions[label] = str(port)
        self.canvas.itemconfig(self.valve_shapes[label], fill="#90ee90") 
        display_txt = self.port_display_info.get((label, str(port)), port)
        self.canvas.itemconfig(self.valve_text_map[label], text=display_txt)

    def handle_click(self, event):
        item = self.canvas.find_closest(event.x, event.y)[0]
        m = self.valve_map.get(item)
        if not m: return
        if isinstance(m, tuple): threading.Thread(target=self.moveValve, args=m, daemon=True).start()
        else:
            p_list = self.ordered_user_ports.get(m, ["1"])
            cur = self.actual_positions[m]
            nxt = p_list[(p_list.index(cur) + 1) % len(p_list)]
            threading.Thread(target=self.moveValve, args=(m, nxt), daemon=True).start()

    def log(self, m):
        self.console.config(state='normal'); self.console.insert('end', f"[{time.strftime('%H:%M:%S')}] {m}\n")
        self.console.see('end'); self.console.config(state='disabled')

    def start_protocol(self):
        self.abort_flag = False; threading.Thread(target=self.run_protocol, daemon=True).start()

    def stop_protocol(self):
        self.abort_flag = True; self.proceed_event.set(); self.log("ABORTED")

    def run_protocol(self):
        self.is_running = True
        for item in self.seq_tree.get_children(''):
            if self.abort_flag: break
            if self.seq_tree.get_children(item):
                self.log(f"Group: {self.seq_tree.item(item, 'text')}")
                for child in self.seq_tree.get_children(item):
                    if self.abort_flag: break
                    self._execute_step(child)
            else: self._execute_step(item)
        self.log("Protocol Finished."); self.is_running = False

    def _execute_step(self, item_id):
        name = self.seq_tree.item(item_id, 'text')
        dur = float(self.seq_tree.item(item_id, 'values')[0])
        if "PROMPT" in name.upper():
            self.log("PAUSED - Click PROCEED"); self.btn_proceed.config(state="normal")
            self.proceed_event.clear(); self.proceed_event.wait(); self.btn_proceed.config(state="disabled")
        elif "WAIT" in name.upper():
            self.log(f"Waiting {dur}s"); time.sleep(dur)
        else:
            self.log(f"Run: {name}"); self.runPreset(name); time.sleep(dur)

    def runPreset(self, name):
        data = self.presets.get(name)
        if not data: return
        if isinstance(data, list) and len(data) > 0:
            if isinstance(data[0], list):
                for v, _, p in data: threading.Thread(target=self.moveValve, args=(v, p), daemon=True).start()
            elif isinstance(data[0], dict):
                for s in data:
                    self.runPreset(s['name'])
                    time.sleep(float(s['time']))

    def add_group(self):
        n = simpledialog.askstring("Group", "Name:")
        if n: self.seq_tree.insert('', 'end', text=n, values=("0.0",), tags=('group',), open=True)

    def save_group_as_preset(self):
        sel = self.seq_tree.selection()
        if not sel: return
        item = sel[0]
        if 'group' not in self.seq_tree.item(item, 'tags'): return
        name = simpledialog.askstring("Save Preset", "Name for Group Preset:")
        if name:
            group_steps = []
            for child in self.seq_tree.get_children(item):
                group_steps.append({"name": self.seq_tree.item(child, 'text'), "time": self.seq_tree.item(child, 'values')[0]})
            self.presets[name] = group_steps
            with open("valve_library.json", "w") as f: json.dump(self.presets, f, indent=2)
            self.load_library()

    def on_double_click_tree(self, event):
        item = self.seq_tree.identify_row(event.y)
        if item:
            v = self.seq_tree.item(item, 'values')[0]
            t = simpledialog.askfloat("Time", "Sec:", initialvalue=float(v))
            if t is not None: self.seq_tree.item(item, values=(f"{t:.1f}",))

    def delete_selected(self, event=None):
        for s in self.seq_tree.selection(): self.seq_tree.delete(s)

    def save_protocol(self):
        p = filedialog.asksaveasfilename(defaultextension=".json")
        if p:
            d = []
            for g in self.seq_tree.get_children(''):
                is_g = 'group' in self.seq_tree.item(g, 'tags')
                d.append({"name": self.seq_tree.item(g, 'text'), "time": self.seq_tree.item(g, 'values')[0], "parent": "", "is_group": is_g})
                for c in self.seq_tree.get_children(g):
                    d.append({"name": self.seq_tree.item(c, 'text'), "time": self.seq_tree.item(c, 'values')[0], "parent": self.seq_tree.item(g, 'text'), "is_group": False})
            with open(p, 'w') as f: json.dump(d, f)

    def load_protocol(self):
        p = filedialog.askopenfilename()
        if p:
            with open(p, 'r') as f: d = json.load(f)
            self.seq_tree.delete(*self.seq_tree.get_children())
            m = {}
            for r in d:
                if r["is_group"]: m[r["name"]] = self.seq_tree.insert('', 'end', text=r["name"], values=(r["time"],), tags=('group',), open=True)
                else: self.seq_tree.insert(m.get(r["parent"], ""), 'end', text=r["name"], values=(r["time"],))

if __name__ == "__main__":
    root = tk.Tk(); app = ValveApp(root); root.mainloop()