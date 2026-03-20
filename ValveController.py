import os, json, threading, time, math, pandas as pd
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox

# --- Hardware Check & Driver Loading ---
# We wrap the import to ensure the app doesn't crash if the file is missing
try:
    from amfValveControl import amfValveControl
    HARDWARE_LIB_FOUND = True
except ImportError:
    HARDWARE_LIB_FOUND = False

class ValveApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Lab Valve Protocol Builder v5.2 - FULL")

        # --- 1. State Variables ---
        self.valve_labels = ['A', 'B', 'C', 'D', 'E', 'F']
        self.is_running = False
        self.abort_flag = False
        self.hardware_enabled = False
        self.proceed_event = threading.Event()
        
        self.user_to_hw = {}          
        self.port_display_info = {}   
        self.ordered_user_ports = {}  
        self.actual_positions = {k: "1" for k in self.valve_labels}
        
        self.valve_shapes = {}
        self.valve_text_map = {}
        self.port_label_ids = {}
        self.valve_map = {}

        # --- RESTORED FULL PRESETS (NO SKIPS) ---
        self.presets = {
           "1a":            [('A', 1.0, "1"), ('B', 1.0, "4"), ('C', 1.0, "1"), ('D', 1.0, "1"), ('E', 1.0, "1"), ('F', 1.0, "1")],
           "1b":            [('A', 1.0, "1"), ('B', 1.0, "3"), ('C', 1.0, "1"), ('D', 1.0, "1"), ('E', 1.0, "1"), ('F', 1.0, "1")],
           "1c":            [('A', 1.0, "1"), ('B', 1.0, "2"), ('C', 1.0, "1"), ('D', 1.0, "1"), ('E', 1.0, "1"), ('F', 1.0, "1")],
           "2":             [('A', 1.0, "1"), ('B', 1.0, "1"), ('C', 1.0, "1"), ('D', 1.0, "1"), ('E', 1.0, "1"), ('F', 1.0, "1")],
           "3":             [('A', 1.0, "1"), ('B', 1.0, "1"), ('C', 1.0, "7"), ('D', 1.0, "1"), ('E', 1.0, "7"), ('F', 1.0, "1")],
           "4a":            [('A', 1.0, "4"), ('B', 1.0, "4"), ('C', 1.0, "7"), ('D', 1.0, "6"), ('E', 1.0, "7"), ('F', 1.0, "6")],
           "4b air clear":  [('A', 1.0, "4"), ('B', 1.0, "4"), ('C', 1.0, "9"), ('D', 1.0, "6"), ('E', 1.0, "9"), ('F', 1.0, "6")],
           "4c":            [('A', 1.0, "4"), ('B', 1.0, "4"), ('C', 1.0, "1"), ('D', 1.0, "6"), ('E', 1.0, "1"), ('F', 1.0, "6")],
           "4d":            [('A', 1.0, "4"), ('B', 1.0, "4"), ('C', 1.0, "8"), ('D', 1.0, "6"), ('E', 1.0, "8"), ('F', 1.0, "6")],
           "5":             [('A', 1.0, "4"), ('B', 1.0, "3"), ('C', 1.0, "8"), ('D', 1.0, "6"), ('E', 1.0, "8"), ('F', 1.0, "6")],
           "6":             [('A', 1.0, "4"), ('B', 1.0, "2"), ('C', 1.0, "8"), ('D', 1.0, "6"), ('E', 1.0, "8"), ('F', 1.0, "6")],
           "7":             [('A', 1.0, "3"), ('B', 1.0, "2"), ('C', 1.0, "8"), ('D', 1.0, "6"), ('E', 1.0, "8"), ('F', 1.0, "6")],
           "8":             [('A', 1.0, "3"), ('B', 1.0, "3"), ('C', 1.0, "8"), ('D', 1.0, "6"), ('E', 1.0, "8"), ('F', 1.0, "6")],
           "9":             [('A', 1.0, "3"), ('B', 1.0, "1"), ('C', 1.0, "8"), ('D', 1.0, "6"), ('E', 1.0, "8"), ('F', 1.0, "6")],
           "10":            [('A', 1.0, "2"), ('B', 1.0, "4"), ('C', 1.0, "6"), ('D', 1.0, "5"), ('E', 1.0, "6"), ('F', 1.0, "5")],
           "Home lock":     [('A', 1.0, "1.5"), ('B', 1.0, "1.5"), ('C', 1.0, "1.5"), ('D', 1.0, "1.5"), ('E', 1.0, "1.5"), ('F', 1.0, "1.5")],
           "-WAIT STEP-": "WAIT",
           "-MANUAL PROMPT-": "PROMPT"
        }

        self.setup_ui()
        self.load_port_map() 
        
        self.drag_data = None
        self.ghost_label = None

        # --- Hardware Initialization (Safe Start) ---
        if HARDWARE_LIB_FOUND:
            try:
                # This call will trigger your Home cycles if valves are found
                self.vc = amfValveControl(status_callback=self.log)
                self.hardware_enabled = True
                self.log("Hardware Initialized and Homed.")
            except Exception as e:
                self.log(f"!!! SIMULATION MODE !!! (Hardware error: {e})")
                self.vc = None
        else:
            self.log("!!! SIMULATION MODE !!! (amfValveControl.py missing)")
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
        # Top Manifold
        v_frame = ttk.LabelFrame(self.root, text="Physical Layout")
        v_frame.pack(fill="x", padx=10, pady=5)
        self.canvas = tk.Canvas(v_frame, width=1100, height=450, bg="#ffffff")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.handle_click)

        paned = ttk.PanedWindow(self.root, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=10)

        # 1. Presets (Library)
        lib_pane = ttk.Frame(paned); paned.add(lib_pane, weight=1)
        ttk.Label(lib_pane, text="Preset Library").pack()
        self.lib_list = tk.Listbox(lib_pane, height=12)
        self.lib_list.pack(fill="both", expand=True)
        for name in sorted(self.presets.keys()): 
            self.lib_list.insert("end", name)
            if "---" in name: self.lib_list.itemconfig("end", fg="blue")
        
        self.lib_list.bind("<ButtonPress-1>", self.on_start_drag_lib)
        self.lib_list.bind("<B1-Motion>", self.on_drag_motion)

        # 2. Sequence (Treeview)
        seq_pane = ttk.Frame(paned); paned.add(seq_pane, weight=3)
        ttk.Label(seq_pane, text="Sequence Protocol").pack()
        self.seq_tree = ttk.Treeview(seq_pane, columns=("time",), show='tree headings')
        self.seq_tree.heading("#0", text="Step/Group")
        self.seq_tree.heading("time", text="Wait (s)")
        self.seq_tree.pack(fill="both", expand=True)

        # --- NEW: Build Controls tucked under Sequence ---
        build_btn_frame = ttk.Frame(seq_pane, padding=5)
        build_btn_frame.pack(fill="x")
        ttk.Button(build_btn_frame, text="?", width=3, command=self.show_help).pack(side="left", padx=2)
        ttk.Button(build_btn_frame, text="+ New Group", command=self.add_group).pack(side="left", padx=2)
        ttk.Button(build_btn_frame, text="Save Seq", command=self.save_protocol).pack(side="left", padx=2)
        ttk.Button(build_btn_frame, text="Load Seq", command=self.load_protocol).pack(side="left", padx=2)

        # Re-binding events (Keep these as they were)
        self.seq_tree.bind("<ButtonPress-1>", self.on_start_drag_tree)
        self.seq_tree.bind("<B1-Motion>", self.on_drag_motion)
        self.seq_tree.bind("<Delete>", self.delete_selected)
        self.seq_tree.bind("<BackSpace>", self.delete_selected)
        self.seq_tree.bind("<Double-1>", self.on_double_click_tree)

        # 3. Console Log
        log_pane = ttk.Frame(paned); paned.add(log_pane, weight=2)
        self.console = tk.Text(log_pane, height=12, state='disabled', font=("Consolas", 9))
        self.console.pack(fill="both", expand=True)

        # --- NEW: Execution Controls tucked under Log ---
        exec_btn_frame = ttk.Frame(log_pane, padding=5)
        exec_btn_frame.pack(fill="x")
        ttk.Button(exec_btn_frame, text="Run Protocol", command=self.start_protocol).pack(side="left", padx=2)
        self.btn_proceed = ttk.Button(exec_btn_frame, text="PROCEED", command=lambda: self.proceed_event.set(), state="disabled")
        self.btn_proceed.pack(side="left", padx=2)
        ttk.Button(exec_btn_frame, text="STOP", command=self.stop_protocol).pack(side="left", padx=10)

    def draw_physical_layout(self):
        # EXACT COORDINATES FROM YOUR WORKING VERSION
        centers = {'A': (550, 100), 'B': (550, 290), 'D': (350, 320), 'C': (150, 150), 'F': (750, 320), 'E': (950, 150)}
        r = 45 
        self.canvas.delete("all")
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
        if isinstance(mapping, tuple):
            threading.Thread(target=self.moveValve, args=mapping, daemon=True).start()
        else:
            p_list = self.ordered_user_ports[mapping]
            nxt = p_list[(p_list.index(self.actual_positions[mapping]) + 1) % len(p_list)]
            threading.Thread(target=self.moveValve, args=(mapping, nxt), daemon=True).start()

    def moveValve(self, label, port):
        port = str(port)
        self.canvas.itemconfig(self.valve_shapes[label], fill="yellow")
        if self.hardware_enabled and self.vc:
            hw = self.user_to_hw.get((label, port))
            self.vc.setValvePort(label, hw)
        else:
            time.sleep(0.05) # Sim delay

        self.actual_positions[label] = port
        self.canvas.itemconfig(self.valve_shapes[label], fill="#90ee90")
        info = self.port_display_info.get((label, port), f"Port {port}")
        self.canvas.itemconfig(self.valve_text_map[label], text=info)

    def log(self, m):
        self.console.config(state='normal'); self.console.insert('end', f"[{time.strftime('%H:%M:%S')}] {m}\n")
        self.console.see('end'); self.console.config(state='disabled')

    def show_help(self):
        h = "Manual:\n- Drag Presets to Sequence\n- Double-click 'Wait' column to edit time\n- Delete/BackSpace removes steps\n- 'MANUAL PROMPT' stops sequence until you click PROCEED"
        messagebox.showinfo("Protocol Help", h)

    def on_start_drag_lib(self, event):
        idx = self.lib_list.nearest(event.y)
        if idx >= 0:
            self.drag_data = {"type": "lib", "content": self.lib_list.get(idx), "sx": event.x, "sy": event.y, "moved": False}

    def on_start_drag_tree(self, event):
        item = self.seq_tree.identify_row(event.y)
        if item: self.drag_data = {"type": "tree", "content": item, "sx": event.x, "sy": event.y, "moved": False}

    def on_drag_motion(self, event):
        if not self.drag_data: return
        if abs(event.x - self.drag_data["sx"]) > 5 or abs(event.y - self.drag_data["sy"]) > 5:
            self.drag_data["moved"] = True
            if not self.ghost_label:
                self.ghost_label = tk.Label(self.root, text=f"Moving: {self.drag_data['content']}", bg="yellow", relief="ridge")
            self.ghost_label.place(x=self.root.winfo_pointerx() - self.root.winfo_rootx() + 15, y=self.root.winfo_pointery() - self.root.winfo_rooty() + 15)

    def on_drop(self, event):
        if not self.drag_data: return
        if self.ghost_label: self.ghost_label.destroy(); self.ghost_label = None
        if self.drag_data.get("moved"):
            ty = self.root.winfo_pointery() - self.seq_tree.winfo_rooty()
            target = self.seq_tree.identify_row(ty)
            parent = target if target and 'group' in self.seq_tree.item(target, 'tags') else self.seq_tree.parent(target)
            if self.drag_data["type"] == "lib":
                self.seq_tree.insert(parent, 'end', text=self.drag_data["content"], values=("2.5",))
            else:
                src = self.drag_data["content"]
                if src != target: 
                    try: self.seq_tree.move(src, parent, 'end')
                    except: pass
        self.drag_data = None; self.root.update()

    def add_group(self):
        name = simpledialog.askstring("New Group", "Name:")
        if name: self.seq_tree.insert('', 'end', text=name, values=("0.0",), open=True, tags=('group',))

    def on_double_click_tree(self, event):
        item = self.seq_tree.identify_row(event.y)
        if item:
            old = self.seq_tree.item(item, 'values')[0]
            new_t = simpledialog.askfloat("Timer", "Seconds:", initialvalue=float(old))
            if new_t is not None: self.seq_tree.item(item, values=(f"{new_t:.1f}",))

    def delete_selected(self, event=None):
        for item in self.seq_tree.selection(): self.seq_tree.delete(item)

    # --- SAVE / LOAD (FLAT STRUCTURE) ---
    def save_protocol(self):
        path = filedialog.asksaveasfilename(defaultextension=".json")
        if not path: return
        data = []
        for g in self.seq_tree.get_children(''):
            is_g = 'group' in self.seq_tree.item(g, 'tags')
            data.append({"name": self.seq_tree.item(g, 'text'), "time": self.seq_tree.item(g, 'values')[0], "parent": "", "is_group": is_g})
            for c in self.seq_tree.get_children(g):
                data.append({"name": self.seq_tree.item(c, 'text'), "time": self.seq_tree.item(c, 'values')[0], "parent": self.seq_tree.item(g, 'text'), "is_group": False})
        with open(path, 'w') as f: json.dump(data, f)

    def load_protocol(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path: return
        with open(path, 'r') as f: data = json.load(f)
        self.seq_tree.delete(*self.seq_tree.get_children())
        g_map = {}
        for row in data:
            if row["is_group"]:
                gid = self.seq_tree.insert('', 'end', text=row["name"], values=(row["time"],), open=True, tags=('group',))
                g_map[row["name"]] = gid
            else:
                p = g_map.get(row["parent"], "")
                self.seq_tree.insert(p, 'end', text=row["name"], values=(row["time"],))

    def start_protocol(self):
        self.abort_flag = False; threading.Thread(target=self.run_protocol, daemon=True).start()

    def stop_protocol(self):
        self.abort_flag = True; self.proceed_event.set(); self.log("ABORTED")

    def run_protocol(self):
        self.is_running = True
        for top_item in self.seq_tree.get_children(''):
            if self.abort_flag: break
            children = self.seq_tree.get_children(top_item)
            if children: # It's a Group
                self.log(f"Group: {self.seq_tree.item(top_item, 'text')}")
                for child in children:
                    if self.abort_flag: break
                    self._execute_step(child)
            else: # It's a loose step
                self._execute_step(top_item)
        self.is_running = False; self.log("Done.")

    def _execute_step(self, item_id):
        name = self.seq_tree.item(item_id, 'text')
        dur = float(self.seq_tree.item(item_id, 'values')[0])
        if "MANUAL PROMPT" in name:
            self.log("Waiting for PROCEED..."); self.btn_proceed.config(state="normal")
            self.proceed_event.clear(); self.proceed_event.wait(); self.btn_proceed.config(state="disabled")
        elif "WAIT STEP" in name:
            self.log(f"Wait {dur}s"); time.sleep(dur)
        else:
            self.log(f"Run: {name}"); self.runPreset(name); time.sleep(dur)

    def runPreset(self, name):
        if name in self.presets and isinstance(self.presets[name], list):
            for v, _, p in self.presets[name]:
                threading.Thread(target=self.moveValve, args=(v, p), daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk(); app = ValveApp(root); root.mainloop()