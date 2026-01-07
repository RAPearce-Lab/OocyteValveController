import math

class ManualMarchingAnts:
    def __init__(self, canvas, start_pt, end_pt, **kwargs):
        self.canvas = canvas
        self.x1, self.y1 = start_pt
        self.x2, self.y2 = end_pt
        self.kwargs = kwargs
        
        # Line properties
        self.dash_length = 10
        self.gap_length = 5
        self.total_cycle = self.dash_length + self.gap_length
        
        # Calculate angle and length of the path
        self.dx = self.x2 - self.x1
        self.dy = self.y2 - self.y1
        self.full_len = math.sqrt(self.dx**2 + self.dy**2)
        
        self.offset = 0
        self.segment_ids = []
        self.animate()

    def animate(self):
        if not self.canvas.winfo_exists():
            return

        # 1. Clear previous segments
        for line_id in self.segment_ids:
            self.canvas.delete(line_id)
        self.segment_ids.clear()

        # 2. Shift the offset
        self.offset = (self.offset + 1) % self.total_cycle

        # 3. Manually calculate and draw each dash
        current_dist = self.offset - self.total_cycle
        while current_dist < self.full_len:
            # Start of dash
            s_dist = max(0, current_dist)
            # End of dash
            e_dist = min(self.full_len, current_dist + self.dash_length)

            if e_dist > s_dist:
                # Convert distance along path to (x, y) coordinates
                # Linear Interpolation (LERP) formula
                sx = self.x1 + (s_dist / self.full_len) * self.dx
                sy = self.y1 + (s_dist / self.full_len) * self.dy
                ex = self.x1 + (e_dist / self.full_len) * self.dx
                ey = self.y1 + (e_dist / self.full_len) * self.dy
                
                lid = self.canvas.create_line(sx, sy, ex, ey, **self.kwargs)
                self.segment_ids.append(lid)

            current_dist += self.total_cycle

        self.canvas.after(30, self.animate)

