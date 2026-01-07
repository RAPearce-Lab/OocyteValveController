import time
import threading 
import tkinter as tk
from tkinter import ttk, messagebox

# --- 1. Configuration & Data ---
# valveCount = 6
# VALVE_POSITIONS = [(0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (2, 1)]
VALVE_STATE = {
    1: [1, 4], 2: [1, 6], 3: [1, 8], 
    4: [1, 4], 5: [1, 6], 6: [1, 8]
}

PRESET_DATA = {
    "Saline Flush": [ (1, 1.0, 4), (2, 1.0, 1), (6, 1.0, 1) ],
    "Air Purge":    [ (1, 0.5, 2), (2, 0.5, 2), (3, 0.5, 2) ],
    "System Reset": [ (i, 0.1, 1) for i in range(1, 7) ],
    "Sample Load":  [ (4, 1.0, 3), (5, 2.0, 2) ]
}

valve_map = {} 
valve_text_map = {}

# --- 2. Core Functions ---

def toggle_valve(event):
    """Handles manual clicking on the valve circles."""
    canvas = event.widget
    clicked_items = canvas.find_closest(event.x, event.y)
    if clicked_items:
        item_id = clicked_items[0]
        if item_id in valve_map:
            v_id = valve_map[item_id]
            current_port, max_ports = VALVE_STATE[v_id]
            new_port = (current_port % max_ports) + 1
            VALVE_STATE[v_id][0] = new_port
            canvas.itemconfig(valve_text_map[v_id], text=f"V{v_id} P:{new_port}")

def update_preview(event):
    """Updates the right-hand preview tree based on Library or Sequence selection."""
    widget = event.widget
    preset_name = None

    # Case A: User clicked the Library (Listbox)
    if isinstance(widget, tk.Listbox):
        selection = widget.curselection()
        if selection:
            preset_name = widget.get(selection[0])
            
    # Case B: User clicked the Sequence (Treeview)
    elif isinstance(widget, ttk.Treeview):
        selection = widget.selection()
        if selection:
            item_data = widget.item(selection[0], 'values')
            if item_data:
                preset_name = item_data[0]

    # If we found a preset name, update the preview table
    if preset_name:
        steps = PRESET_DATA.get(preset_name, [])
        preview_tree.delete(*preview_tree.get_children())
        for v_id, _, port in steps:
            preview_tree.insert('', 'end', values=(f"Valve {v_id}", f"Port {port}"))
            

def add_preset_to_sequence():
    """Adds selected preset from Library to the Active Sequence."""
    selection = library_listbox.curselection()
    if selection:
        preset_name = library_listbox.get(selection[0])
        # Inserting into the TWO named columns
        sequence_tree.insert('', 'end', values=(preset_name, "10.0"))

def save_cell_value(entry, item_id, col_id):
    """Saves edited cell for the 2-column layout."""
    new_value = entry.get()
    current_values = list(sequence_tree.item(item_id, 'values'))
    try:
        if col_id == "preset":
            if new_value not in PRESET_DATA: raise ValueError("Not in Library")
            current_values[0] = new_value
        elif col_id == "time":
            current_values[1] = float(new_value)
        sequence_tree.item(item_id, values=current_values)
    except ValueError as e:
        messagebox.showerror("Error", f"Invalid: {e}")
    finally:
        entry.destroy()

def set_cell_value(event):
    """Enables double-click editing using column names."""
    if not sequence_tree.selection(): return
    item_id = sequence_tree.selection()[0]
    
    # identify column name ("preset" or "time")
    column_id = sequence_tree.identify_column(event.x) 
    # Map physical column position to name
    col_name_map = {"#1": "preset", "#2": "time"}
    if column_id not in col_name_map: return
    
    actual_col = col_name_map[column_id]
    val_index = 0 if actual_col == "preset" else 1
    
    old_val = sequence_tree.item(item_id, 'values')[val_index]
    x, y, w, h = sequence_tree.bbox(item_id, column_id)
    
    entry = ttk.Entry(sequence_tree)
    entry.place(x=x, y=y, width=w, height=h)
    entry.insert(0, old_val)
    entry.focus()
    entry.bind('<Return>', lambda e: save_cell_value(entry, item_id, actual_col))
    entry.bind('<FocusOut>', lambda e: entry.destroy())

def run_protocol_logic(root):
    """Background thread to execute the sequence of presets."""
    if getattr(root, '_is_running', False): return
    root._is_running = True
    try:
        for item_id in sequence_tree.get_children():
            name, duration = sequence_tree.item(item_id, 'values')
            steps = PRESET_DATA.get(name, [])
            
            # Highlight current step
            root.after_idle(lambda i=item_id: sequence_tree.selection_set(i))
            
            for v_id, _, port in steps:
                def update_ui(v=v_id, p=port):
                    VALVE_STATE[v][0] = p
                    valve_canvas.itemconfig(valve_text_map[v], text=f"V{v} P:{p}")
                root.after_idle(update_ui)
            
            time.sleep(float(duration))
        messagebox.showinfo("Done", "Protocol Complete")
    finally:
        root._is_running = False

# --- 3. GUI Layout ---
root = tk.Tk()
root.title("Lab Valve Protocol Builder")


# --- Valve Display (Top) ---
v_frame = ttk.LabelFrame(root, text="Manual Control (Click Circles)", padding=10)
v_frame.pack(fill="x", padx=10, pady=5)
# Increased height slightly to accommodate the vertical stack
valve_canvas = tk.Canvas(v_frame, width=750, height=250, bg="#eeeeee")
valve_canvas.pack()
valve_canvas.bind("<Button-1>", toggle_valve)
# Explicitly define positions for the "Manifold" layout
# Format: { Valve_ID: (x, y) }
VALVE_COORDS = {
    1: (350, 60),   # Top Center
    2: (350, 160),  # Bottom Center
    3: (200, 160),   #  Left 2
    4: (50, 160),  #  Left 1
    5: (500, 160),   #  Right 1
    6: (650, 160)   #  Right 2
}
radius = 20
for v_id, (x, y) in VALVE_COORDS.items():
    # Create the circle
    shape_id = valve_canvas.create_oval(
        x-radius, y-radius, x+radius, y+radius, 
        fill="lightblue", outline="black", width=2
    )
    # Place text to the right of the valve
    t_id = valve_canvas.create_text(
        x + 44, y, 
        text=f"V{v_id} P:{VALVE_STATE[v_id][0]}", 
        font=("Arial", 10, "bold")
    )
    # Map them for the toggle_valve function
    valve_map[shape_id] = v_id
    valve_text_map[v_id] = t_id



# --- Protocol Builder (Middle) ---
s_frame = ttk.LabelFrame(root, text="Protocol Builder", padding=10)
s_frame.pack(fill="both", expand=True, padx=10, pady=5)
paned = ttk.PanedWindow(s_frame, orient="horizontal")
paned.pack(fill="both", expand=True)

# 1. Library
lib_pane = ttk.Frame(paned); paned.add(lib_pane, weight=1)
library_listbox = tk.Listbox(lib_pane)
library_listbox.pack(fill="both", expand=True)
for name in sorted(PRESET_DATA.keys()): 
    library_listbox.insert("end", name)
library_listbox.bind('<<ListboxSelect>>', update_preview)

# 2. Sequence (FIXED COLUMN DEFINITIONS)
mid_pane = ttk.Frame(paned); paned.add(mid_pane, weight=2)
ttk.Label(mid_pane, text="2. Active Sequence").pack(anchor="w")

sequence_tree = ttk.Treeview(mid_pane, columns=("preset", "time"), show='headings', height=8)
sequence_tree.heading("preset", text='Preset Name')
sequence_tree.heading("time", text='Wait (s)')
sequence_tree.column("preset", width=120, anchor='center')
sequence_tree.column("time", width=80, anchor='center')

sequence_tree.bind('<<TreeviewSelect>>', update_preview)
sequence_tree.bind('<Double-1>', set_cell_value)
sequence_tree.pack(fill="both", expand=True)

# 3. Preview
pre_pane = ttk.Frame(paned); paned.add(pre_pane, weight=1)
ttk.Label(pre_pane, text="3. Valve Preview").pack(anchor="w")
preview_tree = ttk.Treeview(pre_pane, columns=("v", "p"), show='headings')
preview_tree.heading("v", text='Valve'); preview_tree.heading("p", text='Port')
preview_tree.column("v", width=80, anchor='center')
preview_tree.column("p", width=80, anchor='center')
preview_tree.pack(fill="both", expand=True)

# --- Buttons (Bottom) ---
b_frame = ttk.Frame(root, padding=10)
b_frame.pack(fill="x")
ttk.Button(b_frame, text="Add Preset", command=add_preset_to_sequence).pack(side="left", padx=5)
ttk.Button(b_frame, text="Run Protocol", command=lambda: threading.Thread(target=run_protocol_logic, args=(root,), daemon=True).start()).pack(side="left", padx=5)
ttk.Button(b_frame, text="Clear", command=lambda: sequence_tree.delete(*sequence_tree.get_children())).pack(side="left", padx=5)

root.mainloop()