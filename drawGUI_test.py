import tkinter as tk
from drawGUI import ManualMarchingAnts

# --- Setup ---
root = tk.Tk()
canvas = tk.Canvas(root, width=500, height=300, bg="white")
canvas.pack()


ManualMarchingAnts(canvas, (50, 100), (150, 100), fill="blue", width=2)
ManualMarchingAnts(canvas, (50, 150), (450, 150), fill="red", width=2)
ManualMarchingAnts(canvas, (450, 150), (450, 50), fill="red", width=2)
ManualMarchingAnts(canvas, (450, 150), (450, 250), fill="red", width=2)


root.mainloop()

