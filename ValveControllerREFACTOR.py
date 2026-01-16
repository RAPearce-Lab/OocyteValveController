# TODO Code: add ways to save protocols; 
# TODO Code: Implement green/red port indicators;  
# TODO Code: polling the valve to confirm actual position?;  
# TODO Code: Add error handling for all of the above;  
# TODO Code: add Bob's pages to protocol builder
# TODO Code (optional):  add additional feedback (console / text output) to indicate when valve changes are complete and verified;  
# TODO Code (optional): add valve changes (in the picture of circles) to show active ports and how they're internally routed;  
# TODO Code (optional): add flow paths (with animation?) to show flow paths (like the highlighter from your diagrams; 

import os
import json
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# --- DLL Handling ---
# We had some issues with python finding the appropriate .dll file.  Here is a 
# hardcoded file location - path to the actual dll folder with FTD2XX64.dll
# TODO move this dll_path to a config file, or suffer the stupid git updates from each user / location that could break any other user's build
# more notes: need the amfTools here: https://pypi.org/project/AMFTools/  and 
# one dependancy is here: https://ftdichip.com/drivers/d2xx-drivers/
# TODO create an "install" file writeup
DLL_PATH = r'C:\Windows\System32\DriverStore\FileRepository\ftdibus.inf_amd64_6d7e924c4fdd3111\amd64' 
try:
    os.add_dll_directory(DLL_PATH)
    import amfTools as AMF
except Exception as e:
    print(f"Hardware library load failed: {e}")


class ValveApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Lab Valve Protocol Builder v2.0")
        
        # --- Data State ---
        self.valve_state = {1: [1, 4], 2: [1, 6], 3: [1, 8], 4: [1, 4], 5: [1, 6], 6: [1, 8]}
        self.presets = {
            "Saline Flush": [ (1, 1.0, 4), (2, 1.0, 1), (6, 1.0, 1) ],
            "Air Purge":    [ (1, 0.5, 2), (2, 0.5, 2), (3, 0.5, 2) ],
            "System Reset": [ (i, 0.1, 1) for i in range(1, 7) ],
            "Sample Load":  [ (4, 1.0, 3), (5, 2.0, 2) ]
        }
        self.valve_map = {}
        self.valve_text_map = {}
        self.is_running = False

        self.setup_ui()

    def setup_ui(self):
        # --- 1. Valve Display (Top) ---
        v_frame = ttk.LabelFrame(self.root, text="Manual Control", padding=10)
        v_frame.pack(fill="x", padx=10, pady=5)
        
        self.canvas = tk.Canvas(v_frame, width=750, height=220, bg="#eeeeee")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.toggle_valve)

        coords = {1: (375, 50), 2: (375, 150), 3: (225, 150), 4: (75, 150), 5: (525, 150), 6: (675, 150)}
        
        for v_id, (x, y) in coords.items():
            s_id = self.canvas.create_oval(x-20, y-20, x+20, y+20, fill="lightblue", width=2)
            t_id = self.canvas.create_text(x + 45, y, text=f"V{v_id} P:{self.valve_state[v_id][0]}", font=("Arial", 9, "bold"))
            self.valve_map[s_id] = v_id
            self.valve_text_map[v_id] = t_id

        # --- 2. Protocol Builder (Middle) ---
        builder_frame = ttk.Frame(self.root, padding=10)
        builder_frame.pack(fill="both", expand=True)
        paned = ttk.PanedWindow(builder_frame, orient="horizontal")
        paned.pack(fill="both", expand=True)

        # Library
        lib_pane = ttk.Frame(paned); paned.add(lib_pane, weight=1)
        self.lib_list = tk.Listbox(lib_pane)
        self.lib_list.pack(fill="both", expand=True)
        for name in sorted(self.presets.keys()): self.lib_list.insert("end", name)
        self.lib_list.bind('<<ListboxSelect>>', self.update_preview)

        # Sequence
        mid_pane = ttk.Frame(paned); paned.add(mid_pane, weight=2)
        self.seq_tree = ttk.Treeview(mid_pane, columns=("preset", "time"), show='headings')
        self.seq_tree.heading("preset", text='Preset Name')
        self.seq_tree.heading("time", text='Wait (s)')
        self.seq_tree.pack(fill="both", expand=True)
        self.seq_tree.bind('<<TreeviewSelect>>', self.update_preview)

        # Preview
        pre_pane = ttk.Frame(paned); paned.add(pre_pane, weight=1)
        self.pre_tree = ttk.Treeview(pre_pane, columns=("v", "p"), show='headings')
        self.pre_tree.heading("v", text='Valve'); self.pre_tree.heading("p", text='Port')
        self.pre_tree.pack(fill="both", expand=True)

        # --- 3. Buttons (Bottom) ---
        btn_frame = ttk.Frame(self.root, padding=10)
        btn_frame.pack(fill="x")
        
        ttk.Button(btn_frame, text="Add Step", command=self.add_step).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Run Protocol", command=self.start_protocol).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Save Protocol", command=self.save_protocol).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Load Protocol", command=self.load_protocol).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Clear", command=lambda: self.seq_tree.delete(*self.seq_tree.get_children())).pack(side="right", padx=2)

    # --- Logic Methods ---
    def toggle_valve(self, event):
        item = self.canvas.find_closest(event.x, event.y)[0]
        if item in self.valve_map:
            v_id = self.valve_map[item]
            cur, m_port = self.valve_state[v_id]
            new_p = (cur % m_port) + 1
            self.valve_state[v_id][0] = new_p
            self.canvas.itemconfig(self.valve_text_map[v_id], text=f"V{v_id} P:{new_p}")

    def add_step(self):
        sel = self.lib_list.curselection()
        if sel:
            name = self.lib_list.get(sel[0])
            self.seq_tree.insert('', 'end', values=(name, "10.0"))

    def update_preview(self, event):
        # Logic to determine which widget triggered the event and update self.pre_tree
        widget = event.widget
        preset = None
        if isinstance(widget, tk.Listbox) and widget.curselection():
            preset = widget.get(widget.curselection()[0])
        elif isinstance(widget, ttk.Treeview) and widget.selection():
            preset = self.seq_tree.item(widget.selection()[0], 'values')[0]
        
        if preset:
            self.pre_tree.delete(*self.pre_tree.get_children())
            for v_id, _, port in self.presets.get(preset, []):
                self.pre_tree.insert('', 'end', values=(f"Valve {v_id}", f"Port {port}"))

    def save_protocol(self):
        """Exports the middle sequence table to a file."""
        # Pull data out of the Treeview
        items = self.seq_tree.get_children()
        if not items:
            messagebox.showwarning("Warning", "Sequence is empty. Nothing to save.")
            return

        protocol_data = []
        for item_id in items:
            # item_values will be something like ('Saline Flush', '10.0')
            item_values = self.seq_tree.item(item_id, 'values')
            protocol_data.append({
                "preset": item_values[0],
                "duration": item_values[1]
            })

        # Open the Windows 'Save As' dialog
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if file_path:
            with open(file_path, 'w') as f:
                json.dump(protocol_data, f, indent=4)
            messagebox.showinfo("Success", f"Protocol saved to {os.path.basename(file_path)}")
        
    def load_protocol(self):
        """Imports a JSON file back into the middle sequence table."""
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            with open(file_path, 'r') as f:
                data = json.load(f)
            # Clear existing sequence before loading new one
            self.seq_tree.delete(*self.seq_tree.get_children())
            for entry in data:
                self.seq_tree.insert('', 'end', values=(entry['preset'], entry['duration']))
            messagebox.showinfo("Loaded", "Protocol loaded successfully.")

    def start_protocol(self):
        if not self.is_running:
            threading.Thread(target=self.run_protocol, daemon=True).start()

    def run_protocol(self):
        self.is_running = True
        try:
            for item in self.seq_tree.get_children():
                name, duration = self.seq_tree.item(item, 'values')
                self.root.after_idle(lambda i=item: self.seq_tree.selection_set(i))
                # Hardware move logic goes here
                time.sleep(float(duration))
        finally:
            self.is_running = False
            
    # def check_valve_status(self):
    #     status = AMF.getValveStatus() 
    #     if status == 0:
    #         self.status_label.config(text="Status: Ready", foreground="green")
    #     else:
    #         self.status_label.config(text="Status: Moving...", foreground="orange")
    #     # Run this function again in 100ms (The Polling Loop)
    #     self.root.after(100, self.check_valve_status)      




if __name__ == "__main__":
    root = tk.Tk()
    app = ValveApp(root)
    root.mainloop()
    
    
    
    
    
    
    
    
    