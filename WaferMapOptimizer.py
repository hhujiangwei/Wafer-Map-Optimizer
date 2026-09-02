import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Rectangle, Circle, Polygon
import os,sys

def resource_path(relative_path):
    """获取资源的路径，支持打包后的应用"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

icon_path = resource_path("temp_icon.ico")
# from PIL import Image
# img = Image.open(icon_path)
# ico_path = "temp_icon.ico"
# # 保存为ICO格式，指定大小
# img.save(ico_path, format='ICO', sizes=[(64, 64)])

class FinalWaferAnalyzer:
    def __init__(self, root):
        self.root = root
        self.root.title("Wafer Map Optimizer")
        self.root.geometry("1600x1000")
        self.root.wm_iconbitmap(icon_path)

        # Main layout
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Control panel
        self.control_frame = ttk.LabelFrame(self.main_frame, text="Control Panel", width=380)
        self.control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        # Visualization area
        self.visual_frame = ttk.Frame(self.main_frame)
        self.visual_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.create_parameter_inputs()
        self.create_operation_controls()
        self.create_results_display()
        self.create_visualization()
        self.current_layout = None

    def create_parameter_inputs(self):
        """Create parameter input controls"""
        param_frame = ttk.LabelFrame(self.control_frame, text="Wafer Parameters")
        param_frame.pack(fill=tk.X, padx=5, pady=5)

        parameters = [
            ("Wafer Diameter (mm):", "wafer_dia"),
            ("Edge Exclusion (mm):", "edge_excl"),
            ("Chip X (mm):", "chip_x"),
            ("Chip Y (mm):", "chip_y"),
            ("Orientation:", "notch_angle"),
            ("Optimize Step (1/):", "optimize_step")
        ]

        self.entries = {}
        for i, (text, name) in enumerate(parameters):
            label = ttk.Label(param_frame, text=text)
            label.grid(row=i, column=0, padx=5, pady=2, sticky=tk.W)

            if name == "notch_angle":
                self.notch_combobox = ttk.Combobox(param_frame,
                                                   values=["0", "90", "180", "270"],
                                                   width=8)
                self.notch_combobox.set("180")
                self.notch_combobox.grid(row=i, column=1, padx=5, pady=2)
                self.entries[name] = self.notch_combobox

            elif name == "optimize_step":
                self.step_combobox = ttk.Combobox(param_frame,
                                                   values=["1", "2", "4", "5", "10"],
                                                   width=8)
                self.step_combobox.set("4")
                self.step_combobox.grid(row=i, column=1, padx=5, pady=2)
                self.entries[name] = self.step_combobox

            else:
                entry = ttk.Entry(param_frame, width=10)
                entry.grid(row=i, column=1, padx=5, pady=2)
                self.entries[name] = entry

        # Set default values
        defaults = {
            'wafer_dia': '300',
            'edge_excl': '3',
            'chip_x': '32',
            'chip_y': '45'
        }
        for k, v in defaults.items():
            self.entries[k].insert(0, v)

    def create_operation_controls(self):
        """Create operation buttons"""
        btn_frame = ttk.Frame(self.control_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(btn_frame, text="Generate Map",
                   command=self.run_optimization).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Export SINF",
                   command=self.export_sinf).pack(side=tk.LEFT, padx=2)

    def create_results_display(self):
        """Create results display area"""
        result_frame = ttk.LabelFrame(self.control_frame, text="Analysis Results")
        result_frame.pack(fill=tk.X, padx=5, pady=5)

        self.stats_vars = {
            'colqty':tk.StringVar(),
            'rowqty':tk.StringVar(),
            'count': tk.StringVar(),
            'best_offset': tk.StringVar(),
            'min_dist1': tk.StringVar(),
            'min_dist2': tk.StringVar(),
            'min_dist3': tk.StringVar(),
            'min_dist4': tk.StringVar()
        }

        stats = [
            ("Column Count:",'colqty'),
            ("Row Count:",'rowqty'),
            ("Total Dies:", 'count'),
            ("Optimal Offset:", 'best_offset'),
            ("Min Dist 1:", 'min_dist1'),
            ("Min Dist 2:", 'min_dist2'),
            ("Min Dist 3:", 'min_dist3'),
            ("Min Dist 4:", 'min_dist4')
        ]

        for i, (label, name) in enumerate(stats):
            row = ttk.Frame(result_frame)
            row.pack(fill=tk.X, padx=2, pady=2)
            ttk.Label(row, text=label, width=14, anchor=tk.W).pack(side=tk.LEFT)
            ttk.Label(row, textvariable=self.stats_vars[name],
                      width=12, anchor=tk.E).pack(side=tk.RIGHT)

    def create_visualization(self):
        """Create visualization components"""
        self.fig = plt.Figure(figsize=(12, 12), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.visual_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def run_optimization(self):
        """Execute optimization process"""
        try:
            params = self.get_parameters()
            best = self.find_optimal_offset(params)
            self.current_layout = best
            self.update_display(best)
            self.draw_wafermap(params, best)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def get_parameters(self):
        """Validate and return parameters"""
        params = {
            'wafer_dia': float(self.entries['wafer_dia'].get()),
            'edge_excl': float(self.entries['edge_excl'].get()),
            'chip_x': float(self.entries['chip_x'].get()),
            'chip_y': float(self.entries['chip_y'].get()),
            'notch_angle': int(self.entries['notch_angle'].get()),
            'optimize_step': int(self.entries['optimize_step'].get())
        }

        if any(v <= 0 for k, v in params.items() if k != 'notch_angle'):
            raise ValueError("All parameters must be positive")

        wafer_radius = params['wafer_dia'] / 2
        if params['edge_excl'] >= wafer_radius:
            raise ValueError("Edge exclusion exceeds wafer radius")

        return params

    def find_optimal_offset(self, params):
        """Core optimization algorithm"""
        chip_x, chip_y = params['chip_x'], params['chip_y']
        base_offsets = [(0, 0), (chip_x / 2, 0), (0, chip_y / 2), (chip_x / 2, chip_y / 2)]
        best = {'count': 0}

        for offset in base_offsets + self.generate_adaptive_offsets(chip_x, chip_y,params['optimize_step']):
            layout = self.generate_tile_layout(params, *offset)
            if layout['count'] > best['count'] or \
                    (layout['count'] == best['count'] and offset in base_offsets):
                best = layout
        return best

    def generate_adaptive_offsets(self, chip_x, chip_y,step):
        """Generate adaptive offset candidates"""
        step_x = chip_x / int(step)
        step_y = chip_y / int(step)
        return [(x, y) for x in np.arange(0, chip_x, step_x)
                for y in np.arange(0, chip_y, step_y)
                if (x, y) not in [(0, 0), (chip_x / 2, 0), (0, chip_y / 2), (chip_x / 2, chip_y / 2)]]

    def generate_tile_layout(self, params, offset_x, offset_y):
        """Generate tile layout with coordinate mapping"""
        wafer_radius = params['wafer_dia'] / 2
        eff_radius = wafer_radius - params['edge_excl']
        chip_x, chip_y = params['chip_x'], params['chip_y']

        positions = []
        coord_map = {}
        current_ring = 0
        min_dists = []

        while True:
            ring_added = False
            for dx in range(-current_ring, current_ring + 1):
                for dy in range(-current_ring, current_ring + 1):
                    x = dx * chip_x + offset_x
                    y = dy * chip_y + offset_y

                    if (x, y) not in positions and self.is_valid_position(x, y, chip_x, chip_y, eff_radius):
                        positions.append((x, y))
                        # coord_map especially for map 2D list generate
                        coord_map[(x, y)] = (dx, dy)
                        ring_added = True
                        # 每颗 die 取四角余量最小值，作为该 die 距有效边缘的最近距离
                        min_dists.append(min(self.get_corner_distances(x, y, chip_x, chip_y, eff_radius)))

            if not ring_added:
                break
            current_ring += 1

        return {
            'positions': positions,
            'coord_map': coord_map,
            'count': len(positions),
            'offset': (offset_x, offset_y),
            'min_dists': sorted(min_dists)[:4]
        }

    def get_corner_distances(self, x, y, dx, dy, eff_radius):
        """Calculate edge clearance distances"""
        corners = [
            (x + dx / 2, y + dy / 2),
            (x + dx / 2, y - dy / 2),
            (x - dx / 2, y + dy / 2),
            (x - dx / 2, y - dy / 2)
        ]
        return [eff_radius - np.hypot(cx, cy) for cx, cy in corners]

    def is_valid_position(self, x, y, dx, dy, radius):
        """Validate die position"""
        half_dx = dx / 2
        half_dy = dy / 2
        corners = [
            (x + half_dx, y + half_dy),
            (x + half_dx, y - half_dy),
            (x - half_dx, y + half_dy),
            (x - half_dx, y - half_dy)
        ]
        return all(cx ** 2 + cy ** 2 <= radius ** 2 for cx, cy in corners)

    def update_display(self, best):
        cols = [col for (col, _) in best['coord_map'].values()]
        rows = [row for (_, row) in best['coord_map'].values()]
        col_ct = max(cols) - min(cols) + 1
        row_ct = max(rows) - min(rows) + 1
        """Update results display"""
        self.stats_vars['colqty'].set(col_ct)
        self.stats_vars['rowqty'].set(row_ct)
        self.stats_vars['count'].set(best['count'])
        self.stats_vars['best_offset'].set(f"({best['offset'][0]:.2f}, {best['offset'][1]:.2f})")

        distances = best.get('min_dists', [0, 0, 0, 0])
        self.stats_vars['min_dist1'].set(f"{distances[0]:.3f} mm" if distances else "N/A")
        self.stats_vars['min_dist2'].set(f"{distances[1]:.3f} mm" if len(distances) > 1 else "N/A")
        self.stats_vars['min_dist3'].set(f"{distances[2]:.3f} mm" if len(distances) > 2 else "N/A")
        self.stats_vars['min_dist4'].set(f"{distances[3]:.3f} mm" if len(distances) > 3 else "N/A")

    def draw_wafermap(self, params, layout):
        """Draw optimized wafer map with annotations"""
        self.ax.clear()
        wafer_radius = params['wafer_dia'] / 2

        # Draw wafer outline
        self.ax.add_patch(Circle((0, 0), wafer_radius, ec='black', fc='none', lw=1))
        self.ax.add_patch(Circle((0, 0), wafer_radius - params['edge_excl'],
                                 ec='red', fc='none', ls='--', lw=0.8))

        # Draw notch
        self.draw_notch(params['notch_angle'], wafer_radius)

        # Draw center cross
        cross_size = 2.5
        self.ax.plot([-cross_size, cross_size], [cross_size, -cross_size],
                     color='red', ls=':', lw=0.8, alpha=0.7)
        self.ax.plot([-cross_size, cross_size], [-cross_size, cross_size],
                     color='red', ls=':', lw=0.8, alpha=0.7)

        # Draw dies
        chip_x, chip_y = params['chip_x'], params['chip_y']
        for (x, y), (col, row) in layout['coord_map'].items():
            rect = Rectangle((x - chip_x / 2, y - chip_y / 2), chip_x, chip_y,
                             facecolor='white', edgecolor='#1F4E79', lw=0.4)
            self.ax.add_patch(rect)

        # Add coordinate labels
        self.add_coordinate_labels(layout['coord_map'], chip_x, chip_y, wafer_radius)

        # Set plot limits
        lim = wafer_radius * 1.1
        self.ax.set_xlim(-lim, lim)
        self.ax.set_ylim(-lim, lim)
        self.ax.set_aspect('equal')
        self.ax.axis('off')

        self.canvas.draw()

    def draw_notch(self, angle, wafer_radius):
        """Draw notch at specified angle"""
        angle_dict = {"0":90,"90":0,"180":270,"270":180}
        mapped_angle = angle_dict[str(angle)]
        notch_height = min(3, wafer_radius/50)
        notch_width = min(3, wafer_radius/50)
        p1_radius = wafer_radius - notch_height

        # Calculate notch position based on angle
        theta_p1 = np.radians(mapped_angle)
        theta_p2 = np.radians(mapped_angle)-np.arcsin(0.5*notch_width/wafer_radius)
        theta_p3 = np.radians(mapped_angle)+np.arcsin(0.5*notch_width/wafer_radius)
        base_p1_x = p1_radius * np.cos(theta_p1)
        base_p2_x = wafer_radius * np.cos(theta_p2)
        base_p3_x = wafer_radius * np.cos(theta_p3)
        base_p1_y = p1_radius * np.sin(theta_p1)
        base_p2_y = wafer_radius * np.sin(theta_p2)
        base_p3_y = wafer_radius * np.sin(theta_p3)

        # Create notch triangle
        points = [(base_p1_x, base_p1_y), (base_p2_x, base_p2_y), (base_p3_x, base_p3_y)]
        self.ax.add_patch(Polygon(points, closed=True, color='black'))

    def add_coordinate_labels(self, coord_map, chip_x, chip_y, wafer_radius):
        """Add X/Y coordinate labels"""
        # Get min/max coordinates
        xs = sorted(dict.fromkeys([x for (x, _) in coord_map.keys()]))
        ys = sorted(dict.fromkeys([y for (_ ,y) in coord_map.keys()]))
        axis_shift = min(10,wafer_radius/30)

        # X-axis labels (bottom)
        for i,x in enumerate(xs):
            self.ax.text(x, -axis_shift - wafer_radius, str(i),
                         ha='center', va='top', fontsize=8, color='black')

        # Y-axis labels (left)
        for j,y in enumerate(ys):
            self.ax.text(-axis_shift - wafer_radius, y, str(j),
                         ha='right', va='center', fontsize=8, color='black')

    def export_sinf(self):
        """Export wafer map in SINF format"""
        if not self.current_layout:
            messagebox.showwarning("Warning", "Please generate a map first")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("SINF files", "*.txt"), ("All files", "*.*")]
        )
        if not file_path:
            return

        try:
            with open(file_path, 'w') as f:
                f.write(self.generate_sinf_content())
            messagebox.showinfo("Success", "SINF file exported successfully")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def generate_sinf_content(self):
        """Generate SINF file content"""
        if not self.current_layout:
            return ""

        # Get layout parameters
        params = self.get_parameters()
        coord_map = self.current_layout['coord_map']

        # Calculate row and column counts
        cols = [col for (col, _) in coord_map.values()]
        rows = [row for (_, row) in coord_map.values()]
        col_ct = max(cols) - min(cols) + 1
        row_ct = max(rows) - min(rows) + 1

        # Create empty map grid
        map_grid = [["___" for _ in range(col_ct)] for _ in range(row_ct)]

        # Fill in valid dies
        for (col, row) in coord_map.values():
            col = col - min(cols)
            row = row - min(rows)
            map_grid[row][col] = "000"

        # Generate header
        content = [
            "DEVICE:",
            "LOT:",
            "WAFER:",
            f"FNLOC:{self.entries['notch_angle'].get()}",
            f"ROWCT:{row_ct}",
            f"COLCT:{col_ct}",
            "BCEQU:000",
            "REFPX:0",
            "REFPY:0",
            "DUTMS:mm",
            f"XDIES:{params['chip_x']}",
            f"YDIES:{params['chip_y']}"
        ]

        # Add map data
        for row in reversed(map_grid):  # Reverse to match standard orientation
            content.append("RowData:" + " ".join(row))

        return "\n".join(content)


if __name__ == "__main__":
    root = tk.Tk()
    app = FinalWaferAnalyzer(root)
    root.mainloop()
