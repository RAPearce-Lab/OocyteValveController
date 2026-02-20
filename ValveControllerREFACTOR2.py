
# TODO decide how to fold the refactored code into MAIN;
# TODO pull out some functions into GUI?;  
# TODO As an exercise, I'm trying to modify the code so that it says A:F instead of 1:6 for valve number.  I think keeping the number system and v_id is fine, (better programmatically) so I just want to look for places where it displays text, right?  finding all these: self.canvas.create_text  and the V{v_id} part just change it to;  

# TODO Code: add Bob's pages to protocol builder
# TODO Code: Implement green/red port indicators;  
# TODO Code: polling the valve to confirm actual position?;  
# TODO Code: Add error handling for all of the above;  
# TODO Code (optional):  add additional feedback (console / text output) to indicate when valve changes are complete and verified;  
# TODO Code (optional): add valve changes (in the picture of circles) to show active ports and how they're internally routed;  
# TODO Code (optional): add flow paths (with animation?) to show flow paths (like the highlighter from your diagrams; 

#import os
import json
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog
from amfValveControl import amfValveControl

# --- DLL Handling ---
# We had some issues with python finding the appropriate .dll file.  Here is a 
# hardcoded file location - path to the actual dll folder with FTD2XX64.dll
# TODO move this dll_path to a config file, or suffer the stupid git updates from each user / location that could break any other user's build
# more notes: need the amfTools here: https://pypi.org/project/AMFTools/  and 
# one dependancy is here: https://ftdichip.com/drivers/d2xx-drivers/
# TODO create an "install" file writeup

# try:
#     DLL_PATH = r'C:\Windows\System32\DriverStore\FileRepository\ftdibus.inf_amd64_6d7e924c4fdd3111\amd64' 
#     os.add_dll_directory(DLL_PATH)
#     import amfTools as AMF
#     HARDWARE_CONNECTED = True
# except Exception as e:
#     print(f"Hardware library load failed (Entering Simulation Mode): {e}")
#     HARDWARE_CONNECTED = False

# TODO Implement this in lieu of the simple text outputs
# help(AMF)
# AMF.getValvePosition(self) # int
# AMF.getValveStatus(self) # int
# AMF.setPortNumber(self, portnumber: int = None)  # Set the number of ports of the valve, e.g., portnumber [1; 48]
# AMF.valveMove(self, target: int, mode: int = 0, enforced: bool = False, block: bool = True) #  Move the valve to the target port
# AMF.valveShortestPath(self, target: int, enforced: bool = False, block: bool = True) #  Move to the target port using the shortest path

# TODO valve testing
# TODO (from Bob's pages, above) add fail-stop to cut the flow "GLOBAL_SAFE_PORT = 1"
# TODO need valve move timing (will inform polling interval and how we set them / change them)


# code test with devices:  list_amf = amfTools.util.getProductList() will get the list of connected devices
# amf = amfTools.AMF(list_amf[0])  # this will take the first product it found and assign it to amf.  we probably want to call it valveA:F BUT
# we need to see if a reboot will assign it a different hexID
# amf.getValvePosition() and amf.checkValveStatus() seem to be useful
# ... the address was 0x1f16e5ce750 and after reboot it was 0x1f16e4b3890
# for amf in list_amf:
#    print(amf)
# amf.serialnumber (match this in a list)


class ValveApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Lab Valve Protocol Builder v2.0")
        # --- Data State (Now using Letters) ---
        self.valve_labels = ['A', 'B', 'C', 'D', 'E', 'F']
        self.target_positions = {k: 1 for k in self.valve_labels}
        self.actual_positions = {k: 1 for k in self.valve_labels}
        # modify these - pull from a presets file?
        self.presets = {
            "Saline Flush": [ ('A', 1.0, 4), ('B', 1.0, 1), ('F', 1.0, 1) ],
            "Air Purge":    [ ('A', 0.5, 2), ('B', 0.5, 2), ('C', 0.5, 2) ],
            #"System Reset": [ (i, 0.1, 1) for i in range(1, 7) ],
            "Sample Load":  [ ('D', 1.0, 3), ('E', 2.0, 2) ]
            # TODO send TTL trigger (to start recording)    https://www.adafruit.com/product/954  ???
            # TODO sample apply
            # TODO merge purge / wash / load 
        }
        # some flags and vars
        self.valve_map = {} # Oval ID -> Valve ID
        self.valve_text_map = {} # Valve ID -> Text ID
        self.valve_shapes = {} # Valve ID -> Oval ID
        self.is_running = False
        self.abort_flag = False
        # setup!
        self.setup_ui()
        self.root.update() 
        def gui_log(msg):
            self.log(msg)
        try:
            # create our valveControl interface object
            self.vc = amfValveControl(status_callback=gui_log) 
            # heartbeat loop
            # self.update_hardware_loop()  
        except RuntimeError as e:
            gui_log(f"CRITICAL ERROR: {e}")
            raise
            
       
        


    def setup_ui(self):
        # --- 1. Valve Display (Top) ---
        v_frame = ttk.LabelFrame(self.root, text="Manual Control (Click Circles) - Green=Arrived, Yellow=Moving", padding=10)
        v_frame.pack(fill="x", padx=10, pady=5)
        
        self.canvas = tk.Canvas(v_frame, width=750, height=220, bg="#eeeeee")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.toggle_valve)

        # Format: { Valve_ID: (x, y) }
        coords = {'A': (375, 50), 'B': (375, 150), 'D': (225, 150), 'C': (75, 150), 'F': (525, 150), 'E': (675, 150)}
        
        for label, (x, y) in coords.items():
            s_id = self.canvas.create_oval(x-25, y-25, x+25, y+25, fill="lightgreen", width=2)
            t_id = self.canvas.create_text(x + 55, y, text=f"{label} | P:1", font=("Arial", 9, "bold"))
            self.valve_map[s_id] = label
            self.valve_text_map[label] = t_id
            self.valve_shapes[label] = s_id

        # --- 2. Protocol Builder (Middle) ---
        builder_frame = ttk.Frame(self.root, padding=10)
        builder_frame.pack(fill="both", expand=True)
        paned = ttk.PanedWindow(builder_frame, orient="horizontal")
        paned.pack(fill="both", expand=True)

        # 1. Library
        lib_pane = ttk.Frame(paned); paned.add(lib_pane, weight=1)
        ttk.Label(lib_pane, text="1. Library").pack()
        self.lib_list = tk.Listbox(lib_pane)
        self.lib_list.pack(fill="both", expand=True)
        for name in sorted(self.presets.keys()): self.lib_list.insert("end", name)
        self.lib_list.bind('<<ListboxSelect>>', self.update_preview)

        # 2. Sequence
        mid_pane = ttk.Frame(paned); paned.add(mid_pane, weight=2)
        ttk.Label(mid_pane, text="2. Active Sequence").pack()
        self.seq_tree = ttk.Treeview(mid_pane, columns=("preset", "time"), show='headings')
        self.seq_tree.heading("preset", text='Preset Name')
        self.seq_tree.heading("time", text='Wait (s)')
        self.seq_tree.pack(fill="both", expand=True)
        self.seq_tree.bind('<<TreeviewSelect>>', self.update_preview)

        # 3. Preview
        pre_pane = ttk.Frame(paned); paned.add(pre_pane, weight=1)
        ttk.Label(pre_pane, text="3. Valve Preview").pack()
        self.pre_tree = ttk.Treeview(pre_pane, columns=("v", "p"), show='headings')
        self.pre_tree.heading("v", text='Valve'); self.pre_tree.heading("p", text='Port')
        self.pre_tree.pack(fill="both", expand=True)

        # --- Log Console (System Feedback) ---
        log_frame = ttk.LabelFrame(self.root, text="System Log / Feedback", padding=5)
        log_frame.pack(fill="x", padx=10, pady=5)
        self.console = tk.Text(log_frame, height=5, state='disabled', font=("Consolas", 9))
        self.console.pack(fill="x", side="left", expand=True)
        scrollbar = ttk.Scrollbar(log_frame, command=self.console.yview)
        scrollbar.pack(side="right", fill="y")
        self.console['yscrollcommand'] = scrollbar.set

        # --- 4. Buttons (Bottom) ---
        btn_frame = ttk.Frame(self.root, padding=10)
        btn_frame.pack(fill="x")
        
        ttk.Button(btn_frame, text="Add Step", command=self.add_step).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Run Protocol", command=self.start_protocol).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="STOP", command=self.stop_protocol).pack(side="left", padx=5)
        
        ttk.Button(btn_frame, text="Save Protocol", command=self.save_protocol).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Load Protocol", command=self.load_protocol).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Clear", command=lambda: self.seq_tree.delete(*self.seq_tree.get_children())).pack(side="right", padx=2)

    def moveValve(self, label, port):
        self.target_positions[label] = port
        self.canvas.itemconfig(self.valve_shapes[label], fill="yellow")
        self.log(f"Moving Valve {label} -> Port {port}...")
        self.root.update_idletasks()
        try:
            # 2. Physical Move
            self.vc.setValvePort(label, port)
            # 3. 'Arrived'
            self.actual_positions[label] = port
            self.canvas.itemconfig(self.valve_shapes[label], fill="lightgreen")
            self.canvas.itemconfig(self.valve_text_map[label], text=f"{label} | P:{port}")
        except Exception as e:
            # 4. Error! Turn it Red
            self.canvas.itemconfig(self.valve_shapes[label], fill="red")
            self.log(f"MOVE FAILED: Valve {label} to {port}. Error: {e}")
        self.root.update_idletasks()

    def log(self, message):
        """Adds timestamped feedback to the console."""
        self.console.config(state='normal')
        self.console.insert('end', f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.console.see('end')
        self.console.config(state='disabled')
        
    def update_hardware_loop(self):
        """Checks actual vs target and updates circle fill colors."""
        self.vc.getAllValves(self)
        for label in self.valve_labels:
            target = self.target_positions[label]
            actual = self.actual_positions[label]
            color = "lightgreen" if target == actual else "yellow"
            self.canvas.itemconfig(self.valve_shapes[label], fill=color)
        self.root.after(5000, self.update_hardware_loop)

    def toggle_valve(self, event):
        item = self.canvas.find_closest(event.x, event.y)[0]
        if item in self.valve_map:
            label = self.valve_map[item]
            cur_p = self.actual_positions[label]
            max_p = self.vc.portCounts[label]
            new_p = (cur_p % max_p) + 1
            # Manual moves should run in a thread so they don't lock the GUI
            threading.Thread(target=self.moveValve, args=(label, new_p), daemon=True).start()

    def add_step(self):
        sel = self.lib_list.curselection()
        if sel:
            name = self.lib_list.get(sel[0])
            self.seq_tree.insert('', 'end', values=(name, "10.0"))
            self.log(f"Step Added: {name}")

    def update_preview(self, event):
        widget = event.widget
        preset = None
        if isinstance(widget, tk.Listbox) and widget.curselection():
            preset = widget.get(widget.curselection()[0])
        elif isinstance(widget, ttk.Treeview) and widget.selection():
            preset = self.seq_tree.item(widget.selection()[0], 'values')[0]
        if preset:
            self.pre_tree.delete(*self.pre_tree.get_children())
            for v_id, _, port in self.presets.get(preset, []):
                self.pre_tree.insert('', 'end', values=(f"{v_id}", f"Port {port}"))

    def save_protocol(self):
        items = self.seq_tree.get_children()
        if not items: return
        protocol_data = []
        for item_id in items:
            vals = self.seq_tree.item(item_id, 'values')
            protocol_data.append({"preset": vals[0], "duration": vals[1]})
        file_path = filedialog.asksaveasfilename(defaultextension=".json")
        if file_path:
            with open(file_path, 'w') as f:
                json.dump(protocol_data, f, indent=4)
            self.log("Protocol saved.")
        
    def load_protocol(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if file_path:
            with open(file_path, 'r') as f:
                data = json.load(f)
            self.seq_tree.delete(*self.seq_tree.get_children())
            for entry in data:
                self.seq_tree.insert('', 'end', values=(entry['preset'], entry['duration']))
            self.log("Protocol loaded.")

    def stop_protocol(self):
        self.abort_flag = True
        self.log("ABORT: Stopping all operations.")

    def start_protocol(self):
        if not self.is_running:
            self.abort_flag = False
            threading.Thread(target=self.run_protocol, daemon=True).start()

    def run_protocol(self):
        self.is_running = True
        self.log("Protocol Sequence started.")
        try:
            for item in self.seq_tree.get_children():
                if self.abort_flag: break
                name, duration = self.seq_tree.item(item, 'values')
                # Execute all moves in this preset
                for v_idx, _, port in self.presets.get(name, []):
                    #label = chr(64 + v_idx)
                    self.moveValve(v_idx, port) 
                time.sleep(float(duration))
        finally:
            self.is_running = False



if __name__ == "__main__":
    root = tk.Tk()
    app = ValveApp(root)
    root.mainloop()
