import tkinter as tk
from tkinter import ttk
import math
import numpy as np

# Attempt to import Shapely
try:
    from shapely.geometry import Polygon, Point
    from shapely.ops import unary_union
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False
    # print("Shapely library not found. For accurate union area, please install it: pip install shapely")

# Attempt to import scikit-learn for Gaussian Process
try:
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("Scikit-learn library not found. GP reconstruction functionality will be disabled. "
          "Please install it: pip install scikit-learn")


# --- Constants ---
CELL_SIZE = 10
AXIS_MARGIN = 30
CANVAS_WIDTH = AXIS_MARGIN + 600 + CELL_SIZE
CANVAS_HEIGHT = AXIS_MARGIN + 480 + CELL_SIZE
SIM_CONTROLS_HEIGHT = 100 
TOTAL_CANVAS_HEIGHT = CANVAS_HEIGHT + SIM_CONTROLS_HEIGHT

COLOR_SCALE_WIDTH = 70 # Increased width for better label spacing
COLOR_SCALE_PADDING = 10

GRID_COLOR = "lightgray"
AXIS_LINE_COLOR = "black"
LABEL_COLOR = "dim gray"
LABEL_FONT = ("Arial", 8)
LABEL_INTERVAL = CELL_SIZE * 3

DEFAULT_RECT_COLOR = "lightgoldenrodyellow"
DEFAULT_CIRCLE_COLOR = "" 
SHAPE_STIPPLE = "gray12" 

SELECTED_OUTLINE_COLOR = "blue" 
SELECTED_OUTLINE_WIDTH = 2
DEFAULT_OUTLINE_COLOR = "black"
DEFAULT_OUTLINE_WIDTH = 1

# Dirichlet Field Constants (Ground Truth)
DIRICHLET_BASE_ALPHA = 0.5
DIRICHLET_SCALE_FACTOR = 100.0 

# Sensor Constants
SENSOR_DRAW_RADIUS_PIXELS = CELL_SIZE * 0.35 # Increased from 0.20 for larger clickable area
SENSOR_DEFAULT_INFLUENCE_RADIUS_PIXELS = CELL_SIZE * 3 # For Dirichlet influence
SENSOR_DEFAULT_SENSING_RADIUS_PIXELS = CELL_SIZE * 0.75 # For GP reading from ground truth
SENSOR_DEFAULT_INFLUENCE_STRENGTH = 2.0 
SENSOR_MIN_INFLUENCE_RADIUS = CELL_SIZE * 0.5
SENSOR_MAX_INFLUENCE_RADIUS = CELL_SIZE * 10
SENSOR_MIN_INFLUENCE_STRENGTH = 0.1
SENSOR_MAX_INFLUENCE_STRENGTH = 10.0
SENSOR_OUTLINE_COLOR = "red"
SENSOR_SELECTED_OUTLINE_COLOR = "magenta"
SENSOR_SELECTED_OUTLINE_WIDTH = 3
SENSOR_READING_NOISE_STD = 2.0 # Std dev of noise added to sensor readings for GP

# GP Constants
GP_UPDATE_EVERY_N_FRAMES = 5 # Update GP every N simulation frames where Dirichlet field also changes


# --- Sensor Class ---
class Sensor:
    def __init__(self, x_canvas, y_canvas, 
                 influence_radius=SENSOR_DEFAULT_INFLUENCE_RADIUS_PIXELS, 
                 influence_strength=SENSOR_DEFAULT_INFLUENCE_STRENGTH,
                 sensing_radius=SENSOR_DEFAULT_SENSING_RADIUS_PIXELS): # Added sensing_radius
        self.x = x_canvas 
        self.y = y_canvas 
        self.influence_radius = influence_radius # For Dirichlet alpha
        self.influence_strength = influence_strength # For Dirichlet alpha
        self.sensing_radius = sensing_radius # For reading from ground truth for GP
        self.draw_radius = SENSOR_DRAW_RADIUS_PIXELS # Fixed visual radius
        self.canvas_item_id = None
        self.selected = False
        self.influence_vis_id = None
        self.sensing_vis_id = None # For visualizing sensing radius

    def draw(self, canvas):
        # Main sensor marker
        self.canvas_item_id = canvas.create_oval(
            self.x - self.draw_radius, self.y - self.draw_radius,
            self.x + self.draw_radius, self.y + self.draw_radius,
            fill=SENSOR_OUTLINE_COLOR, outline=SENSOR_OUTLINE_COLOR, width=1, tags="sensor_marker"
        )
        # Influence radius visualization (dashed gray)
        self.influence_vis_id = canvas.create_oval(
            self.x - self.influence_radius, self.y - self.influence_radius,
            self.x + self.influence_radius, self.y + self.influence_radius,
            outline="darkgray", dash=(2,2), width=1, tags=("sensor_marker_influence", f"sensor_influence_{self.canvas_item_id}")
        )
        # Sensing radius visualization (dotted blue) - might be too busy, optional
        # self.sensing_vis_id = canvas.create_oval(
        #     self.x - self.sensing_radius, self.y - self.sensing_radius,
        #     self.x + self.sensing_radius, self.y + self.sensing_radius,
        #     outline="blue", dash=(1,3), width=1, tags=("sensor_marker_sensing", f"sensor_sensing_{self.canvas_item_id}")
        # )
        canvas.tag_raise(self.canvas_item_id)
        canvas.tag_lower(self.influence_vis_id, self.canvas_item_id)
        # if self.sensing_vis_id: canvas.tag_lower(self.sensing_vis_id, self.influence_vis_id)


    def contains_point(self, px, py): 
        return (px - self.x)**2 + (py - self.y)**2 <= self.draw_radius**2

    def select(self, canvas):
        self.selected = True
        if self.canvas_item_id:
            canvas.itemconfig(self.canvas_item_id, outline=SENSOR_SELECTED_OUTLINE_COLOR, fill=SENSOR_SELECTED_OUTLINE_COLOR, width=SENSOR_SELECTED_OUTLINE_WIDTH)
            canvas.tag_raise(self.canvas_item_id)
            if self.influence_vis_id: 
                canvas.itemconfig(self.influence_vis_id, outline="magenta", width=1.5, dash=(4,2))
                canvas.tag_raise(self.influence_vis_id)
            # if self.sensing_vis_id: canvas.itemconfig(self.sensing_vis_id, outline="cyan", width=1.5, dash=(1,2))


    def deselect(self, canvas):
        self.selected = False
        if self.canvas_item_id:
            canvas.itemconfig(self.canvas_item_id, outline=SENSOR_OUTLINE_COLOR, fill=SENSOR_OUTLINE_COLOR, width=1)
            if self.influence_vis_id: canvas.itemconfig(self.influence_vis_id, outline="darkgray", width=1, dash=(2,2))
            # if self.sensing_vis_id: canvas.itemconfig(self.sensing_vis_id, outline="blue", width=1, dash=(1,3))


    def move_to(self, canvas, new_x, new_y):
        self.x = new_x
        self.y = new_y
        if self.canvas_item_id:
            canvas.coords(self.canvas_item_id,
                          self.x - self.draw_radius, self.y - self.draw_radius,
                          self.x + self.draw_radius, self.y + self.draw_radius)
        if self.influence_vis_id:
            canvas.coords(self.influence_vis_id,
                          self.x - self.influence_radius, self.y - self.influence_radius,
                          self.x + self.influence_radius, self.y + self.influence_radius)
        # if self.sensing_vis_id:
        #     canvas.coords(self.sensing_vis_id,
        #                   self.x - self.sensing_radius, self.y - self.sensing_radius,
        #                   self.x + self.sensing_radius, self.y + self.sensing_radius)
            
    def update_influence_radius(self, canvas, new_radius):
        self.influence_radius = max(SENSOR_MIN_INFLUENCE_RADIUS, min(new_radius, SENSOR_MAX_INFLUENCE_RADIUS))
        if self.influence_vis_id:
            canvas.coords(self.influence_vis_id,
                          self.x - self.influence_radius, self.y - self.influence_radius,
                          self.x + self.influence_radius, self.y + self.influence_radius)

    def update_influence_strength(self, new_strength):
        self.influence_strength = max(SENSOR_MIN_INFLUENCE_STRENGTH, min(new_strength, SENSOR_MAX_INFLUENCE_STRENGTH))
    
    # Placeholder for sensing radius update if UI is added
    # def update_sensing_radius(self, canvas, new_radius):
    #     self.sensing_radius = new_radius
    #     if self.sensing_vis_id:
    #         canvas.coords(self.sensing_vis_id, ...)


# --- Shape Classes (Region Shapes) ---
class Shape: 
    def __init__(self, x, y, color):
        self.x = x; self.y = y; self.color = color
        self.canvas_item_id = None; self.selected = False
    def draw(self, canvas): raise NotImplementedError
    def contains_point(self, px, py): raise NotImplementedError
    def select(self, canvas):
        self.selected = True
        if self.canvas_item_id:
            canvas.itemconfig(self.canvas_item_id, outline=SELECTED_OUTLINE_COLOR, width=SELECTED_OUTLINE_WIDTH)
            canvas.tag_raise(self.canvas_item_id) 
    def deselect(self, canvas):
        self.selected = False
        if self.canvas_item_id:
            canvas.itemconfig(self.canvas_item_id, outline=DEFAULT_OUTLINE_COLOR, width=DEFAULT_OUTLINE_WIDTH)
    def move_to(self, canvas, new_ref_x, new_ref_y): raise NotImplementedError
    def resize(self, canvas, param1, param2): raise NotImplementedError
    def update_coords_from_canvas(self, canvas): pass
    def calculate_area(self): raise NotImplementedError

class Rectangle(Shape):
    def __init__(self, x, y, width, height, color):
        super().__init__(x, y, color); self.width = width; self.height = height
    def draw(self, canvas):
        self.canvas_item_id = canvas.create_rectangle(
            self.x, self.y, self.x + self.width, self.y + self.height,
            fill=self.color, outline=DEFAULT_OUTLINE_COLOR, 
            width=DEFAULT_OUTLINE_WIDTH, tags="user_shape",
            stipple=SHAPE_STIPPLE 
        )
    def contains_point(self, px, py): return self.x <= px <= self.x + self.width and self.y <= py <= self.y + self.height
    def move_to(self, canvas, new_x, new_y):
        self.x = new_x; self.y = new_y
        if self.canvas_item_id: canvas.coords(self.canvas_item_id, self.x, self.y, self.x + self.width, self.y + self.height)
    def resize(self, canvas, new_corner_x, new_corner_y):
        self.width = max(CELL_SIZE // 2, new_corner_x - self.x)
        self.height = max(CELL_SIZE // 2, new_corner_y - self.y)
        if self.canvas_item_id: canvas.coords(self.canvas_item_id, self.x, self.y, self.x + self.width, self.y + self.height)
    def update_coords_from_canvas(self, canvas):
        if self.canvas_item_id:
            coords = canvas.coords(self.canvas_item_id)
            if coords: self.x, self.y, self.width, self.height = coords[0], coords[1], abs(coords[2] - coords[0]), abs(coords[3] - coords[1])
    def calculate_area(self): return self.width * self.height

class Circle(Shape):
    def __init__(self, center_x, center_y, radius, color):
        super().__init__(center_x, center_y, color); self.radius = radius
    def draw(self, canvas):
        self.canvas_item_id = canvas.create_oval(
            self.x - self.radius, self.y - self.radius, 
            self.x + self.radius, self.y + self.radius,
            fill=self.color, outline=DEFAULT_OUTLINE_COLOR, 
            width=DEFAULT_OUTLINE_WIDTH, tags="user_shape",
            stipple=SHAPE_STIPPLE 
        )
    def contains_point(self, px, py): return (px - self.x)**2 + (py - self.y)**2 <= self.radius**2
    def move_to(self, canvas, new_center_x, new_center_y):
        self.x = new_center_x; self.y = new_center_y
        if self.canvas_item_id: canvas.coords(self.canvas_item_id, self.x - self.radius, self.y - self.radius, self.x + self.radius, self.y + self.radius)
    def resize(self, canvas, edge_x, edge_y):
        new_radius = math.sqrt((edge_x - self.x)**2 + (edge_y - self.y)**2)
        self.radius = max(CELL_SIZE // 4, new_radius)
        if self.canvas_item_id: canvas.coords(self.canvas_item_id, self.x - self.radius, self.y - self.radius, self.x + self.radius, self.y + self.radius)
    def update_coords_from_canvas(self, canvas):
        if self.canvas_item_id:
            coords = canvas.coords(self.canvas_item_id)
            if coords: self.x, self.y, self.radius = (coords[0] + coords[2]) / 2, (coords[1] + coords[3]) / 2, abs(coords[2] - coords[0]) / 2
    def calculate_area(self): return math.pi * (self.radius ** 2)

# --- Main Application ---
class DrawingApp:
    def __init__(self, master_root):
        self.root = master_root
        self.root.title("Tkinter GP Reconstruction of Dirichlet Field")

        self.current_mode = "select"
        self.shapes_list = [] 
        self.selected_shape_obj = None
        self.sensors_list = []
        self.selected_sensor_obj = None

        self.is_dragging = False
        self.was_resizing_session = False
        self.drag_action_occurred = False
        self.drag_offset_x = 0 
        self.drag_offset_y = 0

        self.sim_grid_rows = (CANVAS_HEIGHT - AXIS_MARGIN) // CELL_SIZE
        self.sim_grid_cols = (CANVAS_WIDTH - AXIS_MARGIN) // CELL_SIZE
        self.data_field = np.zeros((self.sim_grid_rows, self.sim_grid_cols), dtype=float) # Ground truth (Dirichlet)
        self.map_mask = np.zeros((self.sim_grid_rows, self.sim_grid_cols), dtype=int)
        
        self.sim_running = False 
        self.sim_job_id = None 
        self.field_vis_cells = {} # For heatmap cells

        # GP related attributes
        self.gp_model = None
        self.gp_mean_field = np.zeros((self.sim_grid_rows, self.sim_grid_cols), dtype=float) # Inferred field
        self.XY_gp_prediction_grid = self._create_gp_prediction_grid() # Coords for GP prediction
        self.gp_update_counter = 0
        self.current_gp_display_min = 0.0 # For GP heatmap scale
        self.current_gp_display_max = DIRICHLET_SCALE_FACTOR 

        if SKLEARN_AVAILABLE:
            # Kernel for GP: RBF for spatial correlation, WhiteKernel for noise in sensor readings
            kernel = ConstantKernel(1.0, (1e-3, 1e3)) * RBF(length_scale=CELL_SIZE*2, length_scale_bounds=(CELL_SIZE*0.5, CELL_SIZE*10)) \
                     + WhiteKernel(noise_level=SENSOR_READING_NOISE_STD**2, noise_level_bounds=(1e-2, 1e2))
            self.gp_model = GaussianProcessRegressor(kernel=kernel, alpha=1e-7, # Small alpha for numerical stability
                                                     optimizer='fmin_l_bfgs_b', 
                                                     n_restarts_optimizer=3, normalize_y=True)
        else:
            print("WARNING: Scikit-learn not found. GP reconstruction will be disabled.")


        self._setup_ui() 

    def _setup_ui(self):
        main_app_frame = ttk.Frame(self.root, padding="5")
        main_app_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        controls_params_top_frame = ttk.Frame(main_app_frame)
        controls_params_top_frame.pack(side=tk.TOP, fill=tk.X, pady=(0,10))
        self.drawing_controls_frame = ttk.LabelFrame(controls_params_top_frame, text="Region & Sensor Controls", padding="5") 
        self.drawing_controls_frame.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.sensor_params_frame = ttk.LabelFrame(controls_params_top_frame, text="Selected Sensor Parameters", padding="5")
        canvas_area_frame = ttk.Frame(main_app_frame)
        canvas_area_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.drawing_canvas = tk.Canvas(canvas_area_frame, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg="white", relief=tk.SUNKEN, borderwidth=1)
        self.drawing_canvas.pack(side=tk.LEFT, padx=(0,COLOR_SCALE_PADDING), pady=0, expand=True, fill=tk.BOTH)
        self.color_scale_canvas = tk.Canvas(canvas_area_frame, width=COLOR_SCALE_WIDTH, height=CANVAS_HEIGHT, bg="whitesmoke", relief=tk.SUNKEN, borderwidth=1)
        self.color_scale_canvas.pack(side=tk.RIGHT, pady=0, fill=tk.Y)
        sim_toggle_status_frame = ttk.LabelFrame(main_app_frame, text="GP Inferred Field Display", padding="5") # Updated title
        sim_toggle_status_frame.pack(side=tk.BOTTOM, padx=5, pady=(10,0), fill=tk.X)

        ttk.Label(self.drawing_controls_frame, text="Mode:").grid(row=0, column=0, padx=2, pady=2, sticky=tk.W)
        self.mode_var = tk.StringVar(value=self.current_mode)
        self.mode_radios = [] 
        modes = [("Select", "select"), ("Draw Rectangle", "rectangle"), 
                 ("Draw Circle", "circle"), ("Add Sensor", "add_sensor")]
        for i, (text, mode_val) in enumerate(modes):
            rb = ttk.Radiobutton(self.drawing_controls_frame, text=text, variable=self.mode_var, value=mode_val, command=self.set_current_mode)
            rb.grid(row=0, column=i+1, padx=2, pady=2, sticky=tk.W)
            self.mode_radios.append(rb)
        self.delete_button = ttk.Button(self.drawing_controls_frame, text="Delete Selected", command=self.delete_selected_item)
        self.delete_button.grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.clear_sensors_button = ttk.Button(self.drawing_controls_frame, text="Clear All Sensors", command=self.clear_all_sensors)
        self.clear_sensors_button.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        self.union_area_label_var = tk.StringVar(value="Region Area: N/A")
        ttk.Label(self.drawing_controls_frame, textvariable=self.union_area_label_var).grid(row=1, column=2, columnspan=2, padx=5, pady=5, sticky=tk.W)

        self.selected_sensor_radius_var = tk.DoubleVar(value=SENSOR_DEFAULT_INFLUENCE_RADIUS_PIXELS)
        self.selected_sensor_strength_var = tk.DoubleVar(value=SENSOR_DEFAULT_INFLUENCE_STRENGTH)
        ttk.Label(self.sensor_params_frame, text="Influence Radius (Dirichlet):").grid(row=0, column=0, sticky=tk.W, padx=2)
        self.radius_scale = ttk.Scale(self.sensor_params_frame, from_=SENSOR_MIN_INFLUENCE_RADIUS, to=SENSOR_MAX_INFLUENCE_RADIUS,
                                      variable=self.selected_sensor_radius_var, orient=tk.HORIZONTAL, length=150,
                                      command=self._update_selected_sensor_radius_from_scale)
        self.radius_scale.grid(row=0, column=1, sticky=tk.EW, padx=2)
        self.radius_label = ttk.Label(self.sensor_params_frame, text=f"{self.selected_sensor_radius_var.get():.0f} px")
        self.radius_label.grid(row=0, column=2, sticky=tk.W, padx=2)
        ttk.Label(self.sensor_params_frame, text="Influence Strength (Dirichlet):").grid(row=1, column=0, sticky=tk.W, padx=2)
        self.strength_scale = ttk.Scale(self.sensor_params_frame, from_=SENSOR_MIN_INFLUENCE_STRENGTH, to=SENSOR_MAX_INFLUENCE_STRENGTH,
                                       variable=self.selected_sensor_strength_var, orient=tk.HORIZONTAL, length=150,
                                       command=self._update_selected_sensor_strength_from_scale)
        self.strength_scale.grid(row=1, column=1, sticky=tk.EW, padx=2)
        self.strength_label = ttk.Label(self.sensor_params_frame, text=f"{self.selected_sensor_strength_var.get():.1f}")
        self.strength_label.grid(row=1, column=2, sticky=tk.W, padx=2)
        
        self.sim_status_label_var = tk.StringVar(value="Simulation: Stopped. Editing enabled.")
        ttk.Label(sim_toggle_status_frame, textvariable=self.sim_status_label_var).pack(side=tk.LEFT, padx=5)
        self.field_scale_label_var = tk.StringVar(value=f"GP Field Scale: {self.current_gp_display_min:.1f}-{self.current_gp_display_max:.1f}") # Updated label
        ttk.Label(sim_toggle_status_frame, textvariable=self.field_scale_label_var).pack(side=tk.LEFT, padx=5)
        self.sim_toggle_button = ttk.Button(sim_toggle_status_frame, text="Initialize & Run GP", command=self.toggle_simulation) # Updated button text
        self.sim_toggle_button.pack(side=tk.LEFT, padx=5)
        
        self.draw_visual_grid_and_axes()
        self.draw_color_scale()
        self.drawing_canvas.bind("<Button-1>", self.handle_mouse_down)
        self.drawing_canvas.bind("<B1-Motion>", self.handle_mouse_drag)
        self.drawing_canvas.bind("<ButtonRelease-1>", self.handle_mouse_up)
        self.root.bind("<Delete>", lambda e: self.delete_selected_item()) 
        self.root.bind("<BackSpace>", lambda e: self.delete_selected_item())
        self.root.bind("<Escape>", self.handle_escape_key)
        self.update_union_area_display()

    def _create_gp_prediction_grid(self):
        """Creates a grid of canvas coordinates for GP prediction (centers of all sim cells)."""
        grid_points = []
        for r_idx in range(self.sim_grid_rows):
            for c_idx in range(self.sim_grid_cols):
                canvas_x = AXIS_MARGIN + c_idx * CELL_SIZE + CELL_SIZE / 2
                canvas_y = AXIS_MARGIN + r_idx * CELL_SIZE + CELL_SIZE / 2
                grid_points.append([canvas_x, canvas_y])
        return np.array(grid_points)


    def _update_selected_sensor_radius_from_scale(self, value_str):
        if self.selected_sensor_obj:
            new_radius = float(value_str)
            self.selected_sensor_obj.update_influence_radius(self.drawing_canvas, new_radius)
            self.radius_label.config(text=f"{self.selected_sensor_obj.influence_radius:.0f} px")
            self.sim_status_label_var.set("Sensor influence radius changed. Re-initialize field.")


    def _update_selected_sensor_strength_from_scale(self, value_str):
        if self.selected_sensor_obj:
            new_strength = float(value_str)
            self.selected_sensor_obj.update_influence_strength(new_strength)
            self.strength_label.config(text=f"{self.selected_sensor_obj.influence_strength:.1f}")
            self.sim_status_label_var.set("Sensor influence strength changed. Re-initialize field.")


    def _show_sensor_params_frame(self, show=True):
        if show and self.selected_sensor_obj:
            self.selected_sensor_radius_var.set(self.selected_sensor_obj.influence_radius)
            self.radius_label.config(text=f"{self.selected_sensor_obj.influence_radius:.0f} px")
            self.selected_sensor_strength_var.set(self.selected_sensor_obj.influence_strength)
            self.strength_label.config(text=f"{self.selected_sensor_obj.influence_strength:.1f}")
            if not self.sensor_params_frame.winfo_ismapped():
                 self.sensor_params_frame.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.Y, in_=self.drawing_controls_frame.master)
        else:
            self.sensor_params_frame.pack_forget()

    def _sim_to_canvas_coords_center(self, sim_row, sim_col):
        return AXIS_MARGIN + sim_col*CELL_SIZE + CELL_SIZE/2, AXIS_MARGIN + sim_row*CELL_SIZE + CELL_SIZE/2

    def handle_escape_key(self, event=None):
        if self.sim_running: 
            self.sim_status_label_var.set("Field Evolving. Editing locked. Press 'Clear Field' to unlock.")
            return

        if self.current_mode == "add_sensor": 
            self.mode_var.set("select"); self.set_current_mode()
        elif self.selected_shape_obj:
            self.selected_shape_obj.deselect(self.drawing_canvas); self.selected_shape_obj = None
        elif self.selected_sensor_obj:
            self.selected_sensor_obj.deselect(self.drawing_canvas); self.selected_sensor_obj = None
            self._show_sensor_params_frame(False)


    def update_union_area_display(self): 
        if not SHAPELY_AVAILABLE: self.union_area_label_var.set(f"Region Area: (Shapely N/A)"); return
        if not self.shapes_list: self.union_area_label_var.set("Region Area: 0.00 units²"); return
        geoms = []
        for s in self.shapes_list:
            try:
                if isinstance(s, Rectangle) and s.width>0 and s.height>0: geoms.append(Polygon([(s.x,s.y),(s.x+s.width,s.y),(s.x+s.width,s.y+s.height),(s.x,s.y+s.height)]))
                elif isinstance(s, Circle) and s.radius>0: geoms.append(Point(s.x,s.y).buffer(s.radius))
            except: pass 
        if not geoms: self.union_area_label_var.set("Region Area: 0.00 units²"); return
        try: self.union_area_label_var.set(f"Region Area: {unary_union(geoms).area:.2f} units²")
        except: self.union_area_label_var.set("Region Area: Error")

    def set_current_mode(self):
        old_mode = self.current_mode
        self.current_mode = self.mode_var.get()

        if self.sim_running and self.current_mode != "select":
            self.mode_var.set("select") 
            self.current_mode = "select"
            self.sim_status_label_var.set("Field Evolving. Editing locked. Mode forced to Select.")
            
        if old_mode == "select":
            if self.selected_shape_obj and self.current_mode != "select":
                self.selected_shape_obj.deselect(self.drawing_canvas); self.selected_shape_obj = None
            if self.selected_sensor_obj and self.current_mode != "select":
                self.selected_sensor_obj.deselect(self.drawing_canvas); self.selected_sensor_obj = None
                self._show_sensor_params_frame(False)
        self.is_dragging = False; self.was_resizing_session = False; self.drag_action_occurred = False

    def draw_visual_grid_and_axes(self): 
        self.drawing_canvas.delete("grid", "axis_label", "grid_axis_line")
        self.drawing_canvas.create_line(AXIS_MARGIN, AXIS_MARGIN, CANVAS_WIDTH - CELL_SIZE, AXIS_MARGIN, fill=AXIS_LINE_COLOR, width=1, tags="grid_axis_line")
        self.drawing_canvas.create_line(AXIS_MARGIN, AXIS_MARGIN, AXIS_MARGIN, CANVAS_HEIGHT - CELL_SIZE, fill=AXIS_LINE_COLOR, width=1, tags="grid_axis_line")
        for y in range(AXIS_MARGIN+CELL_SIZE,CANVAS_HEIGHT-CELL_SIZE+1,CELL_SIZE): self.drawing_canvas.create_line(AXIS_MARGIN,y,CANVAS_WIDTH-CELL_SIZE,y,fill=GRID_COLOR,tags="grid")
        for x in range(AXIS_MARGIN+CELL_SIZE,CANVAS_WIDTH-CELL_SIZE+1,CELL_SIZE): self.drawing_canvas.create_line(x,AXIS_MARGIN,x,CANVAS_HEIGHT-CELL_SIZE,fill=GRID_COLOR,tags="grid")
        for x in range(AXIS_MARGIN,CANVAS_WIDTH-CELL_SIZE+1,CELL_SIZE):
            if (x-AXIS_MARGIN)%LABEL_INTERVAL==0: self.drawing_canvas.create_text(x,AXIS_MARGIN-10,text=str(x-AXIS_MARGIN),anchor=tk.S,font=LABEL_FONT,fill=LABEL_COLOR,tags="axis_label")
        for y in range(AXIS_MARGIN,CANVAS_HEIGHT-CELL_SIZE+1,CELL_SIZE):
            if (y-AXIS_MARGIN)%LABEL_INTERVAL==0: self.drawing_canvas.create_text(AXIS_MARGIN-10,y,text=str(y-AXIS_MARGIN),anchor=tk.E,font=LABEL_FONT,fill=LABEL_COLOR,tags="axis_label")
        self.drawing_canvas.tag_lower("grid"); self.drawing_canvas.tag_lower("grid_axis_line","grid"); self.drawing_canvas.tag_lower("axis_label")
        self.drawing_canvas.tag_raise("user_shape")


    def _canvas_to_sim_coords(self, canvas_x, canvas_y):
        if canvas_x < AXIS_MARGIN or canvas_y < AXIS_MARGIN: return None, None
        col = int((canvas_x - AXIS_MARGIN) // CELL_SIZE)
        row = int((canvas_y - AXIS_MARGIN) // CELL_SIZE)
        if 0 <= row < self.sim_grid_rows and 0 <= col < self.sim_grid_cols: return row, col
        return None, None

    def _sim_to_canvas_coords(self, sim_row, sim_col):
        return AXIS_MARGIN + sim_col * CELL_SIZE, AXIS_MARGIN + sim_row * CELL_SIZE

    def handle_mouse_down(self, event):
        eff_x = self.drawing_canvas.canvasx(event.x)
        eff_y = self.drawing_canvas.canvasy(event.y)

        if self.sim_running:
            self.sim_status_label_var.set("Field Evolving. Editing locked. Press 'Clear Field' to unlock.")
            return 

        if self.current_mode == "add_sensor": self.handle_add_sensor_click(eff_x, eff_y); return

        self.is_dragging = True; self.was_resizing_session = False; self.drag_action_occurred = False
        
        if self.current_mode == "select":
            clicked_item = None 
            if self.selected_sensor_obj and self.selected_sensor_obj.contains_point(eff_x, eff_y): clicked_item = self.selected_sensor_obj
            else: 
                for sensor_obj in reversed(self.sensors_list): 
                    if sensor_obj.contains_point(eff_x, eff_y): clicked_item = sensor_obj; break
            if not clicked_item: 
                if self.selected_shape_obj and self.selected_shape_obj.contains_point(eff_x, eff_y): clicked_item = self.selected_shape_obj
                else:
                    for shape_obj in reversed(self.shapes_list): 
                        if shape_obj.contains_point(eff_x, eff_y): clicked_item = shape_obj; break
            
            if clicked_item:
                if isinstance(clicked_item, Sensor):
                    if self.selected_sensor_obj != clicked_item: 
                        if self.selected_sensor_obj: self.selected_sensor_obj.deselect(self.drawing_canvas)
                        self.selected_sensor_obj = clicked_item
                        self.selected_sensor_obj.select(self.drawing_canvas)
                        self._show_sensor_params_frame(True)
                    if self.selected_shape_obj: 
                        self.selected_shape_obj.deselect(self.drawing_canvas); self.selected_shape_obj = None
                    self.drag_offset_x = eff_x - self.selected_sensor_obj.x
                    self.drag_offset_y = eff_y - self.selected_sensor_obj.y
                elif isinstance(clicked_item, Shape):
                    if self.selected_shape_obj != clicked_item: 
                        if self.selected_shape_obj: self.selected_shape_obj.deselect(self.drawing_canvas)
                        self.selected_shape_obj = clicked_item
                        self.selected_shape_obj.select(self.drawing_canvas)
                    if self.selected_sensor_obj: 
                        self.selected_sensor_obj.deselect(self.drawing_canvas); self.selected_sensor_obj = None
                        self._show_sensor_params_frame(False)
                    self.drag_offset_x = eff_x - self.selected_shape_obj.x
                    self.drag_offset_y = eff_y - self.selected_shape_obj.y
            else: 
                if self.selected_shape_obj: self.selected_shape_obj.deselect(self.drawing_canvas); self.selected_shape_obj = None
                if self.selected_sensor_obj: self.selected_sensor_obj.deselect(self.drawing_canvas); self.selected_sensor_obj = None; self._show_sensor_params_frame(False)
                self.drag_offset_x = 0; self.drag_offset_y = 0
        elif self.current_mode == "rectangle": self.add_new_shape(Rectangle(eff_x, eff_y, CELL_SIZE * 3, CELL_SIZE * 2, DEFAULT_RECT_COLOR))
        elif self.current_mode == "circle": self.add_new_shape(Circle(eff_x, eff_y, CELL_SIZE * 1.5, DEFAULT_CIRCLE_COLOR))

    def add_new_shape(self, shape_obj): 
        if self.sim_running:
            self.sim_status_label_var.set("Cannot add shapes while field is evolving. Clear field first.")
            return

        shape_obj.draw(self.drawing_canvas)
        self.shapes_list.append(shape_obj)
        if self.selected_shape_obj: self.selected_shape_obj.deselect(self.drawing_canvas)
        if self.selected_sensor_obj: self.selected_sensor_obj.deselect(self.drawing_canvas); self.selected_sensor_obj = None; self._show_sensor_params_frame(False)
        self.selected_shape_obj = shape_obj; self.selected_shape_obj.select(self.drawing_canvas)
        self.mode_var.set("select"); self.set_current_mode()
        self.update_union_area_display()

    def handle_add_sensor_click(self, canvas_x, canvas_y):
        if self.sim_running:
            self.sim_status_label_var.set("Cannot add sensors while field is evolving. Clear field first.")
            return

        new_sensor = Sensor(canvas_x, canvas_y) 
        new_sensor.draw(self.drawing_canvas)
        self.sensors_list.append(new_sensor)
        self.sim_status_label_var.set(f"Sensor added. Total: {len(self.sensors_list)}. Re-initialize field to see effect.")
        if self.selected_sensor_obj: self.selected_sensor_obj.deselect(self.drawing_canvas)
        if self.selected_shape_obj: self.selected_shape_obj.deselect(self.drawing_canvas); self.selected_shape_obj = None
        self.selected_sensor_obj = new_sensor
        self.selected_sensor_obj.select(self.drawing_canvas)
        self._show_sensor_params_frame(True)
        self.mode_var.set("select"); self.set_current_mode()


    def handle_mouse_drag(self, event):
        if self.sim_running: return 

        if not self.is_dragging or self.current_mode != "select": return
        selected_item = self.selected_shape_obj if self.selected_shape_obj else self.selected_sensor_obj
        if not selected_item: return
        self.drag_action_occurred = True
        eff_x = self.drawing_canvas.canvasx(event.x); eff_y = self.drawing_canvas.canvasy(event.y)
        if isinstance(selected_item, Shape):
            is_shift = (event.state & 0x0001) != 0 
            if is_shift: self.was_resizing_session = True; selected_item.resize(self.drawing_canvas, eff_x, eff_y)
            else: selected_item.move_to(self.drawing_canvas, eff_x - self.drag_offset_x, eff_y - self.drag_offset_y)
        elif isinstance(selected_item, Sensor): 
            selected_item.move_to(self.drawing_canvas, eff_x - self.drag_offset_x, eff_y - self.drag_offset_y)

    def handle_mouse_up(self, event):
        if self.sim_running: return 

        if self.is_dragging and self.drag_action_occurred:
            if self.selected_shape_obj:
                self.selected_shape_obj.update_coords_from_canvas(self.drawing_canvas) 
                self.update_union_area_display()
            elif self.selected_sensor_obj:
                self.sim_status_label_var.set("Sensor moved. Re-initialize field to see effect.")
        self.is_dragging = False; self.was_resizing_session = False; self.drag_action_occurred = False

    def delete_selected_item(self):
        if self.sim_running:
            self.sim_status_label_var.set("Cannot delete while field is evolving. Clear field first.")
            return

        item_deleted_msg = ""
        if self.selected_shape_obj:
            self.drawing_canvas.delete(self.selected_shape_obj.canvas_item_id)
            if self.selected_shape_obj in self.shapes_list: self.shapes_list.remove(self.selected_shape_obj)
            self.selected_shape_obj = None
            self.update_union_area_display()
            item_deleted_msg = "Shape deleted."
        elif self.selected_sensor_obj:
            self.drawing_canvas.delete(self.selected_sensor_obj.canvas_item_id)
            if self.selected_sensor_obj.influence_vis_id: self.drawing_canvas.delete(self.selected_sensor_obj.influence_vis_id)
            # if self.selected_sensor_obj.sensing_vis_id: self.drawing_canvas.delete(self.selected_sensor_obj.sensing_vis_id)
            if self.selected_sensor_obj in self.sensors_list: self.sensors_list.remove(self.selected_sensor_obj)
            self.selected_sensor_obj = None
            self._show_sensor_params_frame(False)
            item_deleted_msg = "Sensor deleted. Re-initialize field if needed."
        if item_deleted_msg: self.sim_status_label_var.set(item_deleted_msg)

    def clear_all_sensors(self):
        if self.sim_running:
            self.sim_status_label_var.set("Cannot clear sensors while field is evolving. Clear field first.")
            return
        for sensor_obj in self.sensors_list:
            self.drawing_canvas.delete(sensor_obj.canvas_item_id)
            if sensor_obj.influence_vis_id: self.drawing_canvas.delete(sensor_obj.influence_vis_id)
            # if sensor_obj.sensing_vis_id: self.drawing_canvas.delete(sensor_obj.sensing_vis_id)
        self.sensors_list.clear()
        if self.selected_sensor_obj: self.selected_sensor_obj = None; self._show_sensor_params_frame(False)
        self.sim_status_label_var.set(f"All sensors cleared. Re-initialize field if needed.")


    def initialize_dirichlet_field(self, scale_factor=100.0):
        """Generates the ground truth Dirichlet field, influenced by sensor parameters."""
        num_cells_total = self.sim_grid_rows * self.sim_grid_cols
        if num_cells_total == 0: return

        alpha_array = np.full(num_cells_total, DIRICHLET_BASE_ALPHA, dtype=float)
        for sensor_obj in self.sensors_list:
            for r_idx in range(self.sim_grid_rows):
                for c_idx in range(self.sim_grid_cols):
                    cell_center_x, cell_center_y = self._sim_to_canvas_coords_center(r_idx, c_idx)
                    dist_sq = (cell_center_x - sensor_obj.x)**2 + (cell_center_y - sensor_obj.y)**2
                    if dist_sq <= sensor_obj.influence_radius**2: # Use influence_radius for Dirichlet
                        flat_idx = r_idx * self.sim_grid_cols + c_idx
                        alpha_array[flat_idx] += sensor_obj.influence_strength
        alpha_array[alpha_array <= 0] = 1e-6 
        dirichlet_samples = np.random.dirichlet(alpha_array, size=1).flatten()
        self.data_field = dirichlet_samples.reshape((self.sim_grid_rows, self.sim_grid_cols)) * scale_factor

    def collect_sensor_data_for_gp(self):
        """Collects readings from the 'data_field' (ground truth) at sensor locations for GP."""
        sensor_coords_X = [] # List of [canvas_x, canvas_y] for GP input
        sensor_readings_y = [] # List of measured values for GP input

        for sensor_obj in self.sensors_list:
            # Check if sensor's center grid cell is within a defined region shape
            sensor_grid_r, sensor_grid_c = self._canvas_to_sim_coords(sensor_obj.x, sensor_obj.y)
            if sensor_grid_r is None or (np.any(self.map_mask) and self.map_mask[sensor_grid_r, sensor_grid_c] != 1):
                continue # Skip sensor if its center is not in an active region cell

            sensor_coords_X.append([sensor_obj.x, sensor_obj.y]) # Use canvas coords for GP
            
            # Average ground truth values under the sensor's SENSING_RADIUS
            cells_under_sensor_values = []
            for r_idx in range(self.sim_grid_rows):
                for c_idx in range(self.sim_grid_cols):
                    if self.map_mask[r_idx, c_idx] == 1: # Only consider cells within active regions
                        cell_center_x_c, cell_center_y_c = self._sim_to_canvas_coords_center(r_idx, c_idx)
                        dist_sq = (cell_center_x_c - sensor_obj.x)**2 + (cell_center_y_c - sensor_obj.y)**2
                        if dist_sq <= sensor_obj.sensing_radius**2: # Use SENSING_RADIUS here
                            cells_under_sensor_values.append(self.data_field[r_idx, c_idx])
            
            if cells_under_sensor_values:
                avg_value = np.mean(cells_under_sensor_values)
                noisy_value = avg_value + np.random.normal(0, SENSOR_READING_NOISE_STD) 
                sensor_readings_y.append(max(0, noisy_value)) # Ensure non-negative
            elif sensor_grid_r is not None : # Sensor is in a region cell, but sensing radius covers no other cells
                 # Take direct reading from the cell the sensor is in
                 direct_value = self.data_field[sensor_grid_r, sensor_grid_c]
                 noisy_value = direct_value + np.random.normal(0, SENSOR_READING_NOISE_STD)
                 sensor_readings_y.append(max(0, noisy_value))
        return np.array(sensor_coords_X), np.array(sensor_readings_y)

    def update_gp_model_and_predict(self):
        """Updates the GP model with new sensor data and predicts the mean field."""
        fallback_to_truth = False
        status_suffix = " (GP Active)"

        if not SKLEARN_AVAILABLE or self.gp_model is None:
            fallback_to_truth = True
            status_suffix = " (No Sklearn - Showing Truth)"
        elif not self.sensors_list:
            fallback_to_truth = True
            status_suffix = " (No Sensors - Showing Truth)"
        
        if fallback_to_truth:
            if np.any(self.map_mask): self.gp_mean_field = self.data_field.copy() # Show ground truth
            else: self.gp_mean_field.fill(0)
        else: 
            sensor_X, sensor_y = self.collect_sensor_data_for_gp()
            if sensor_X.shape[0] > 0 and sensor_y.shape[0] > 0 and sensor_X.shape[0] == sensor_y.shape[0]:
                try:
                    self.gp_model.fit(sensor_X, sensor_y)
                    predicted_flat = self.gp_model.predict(self.XY_gp_prediction_grid)
                    self.gp_mean_field = predicted_flat.reshape((self.sim_grid_rows, self.sim_grid_cols))
                    np.clip(self.gp_mean_field, 0, DIRICHLET_SCALE_FACTOR * 1.5, out=self.gp_mean_field) # Clip GP predictions
                except Exception as e:
                    print(f"Error during GP fitting/prediction: {e}")
                    if np.any(self.map_mask): self.gp_mean_field = self.data_field.copy() 
                    else: self.gp_mean_field.fill(0)
                    status_suffix = " (GP Error - Showing Truth)"
            else: # No valid sensor data for GP
                if np.any(self.map_mask): self.gp_mean_field = self.data_field.copy() 
                else: self.gp_mean_field.fill(0)
                status_suffix = " (No Sensor Data for GP - Showing Truth)"
        
        if self.sim_running: self.sim_status_label_var.set("Field Evolving." + status_suffix)

        # Update display scale for GP inferred field
        active_gp_cells = self.gp_mean_field[self.map_mask == 1]
        if active_gp_cells.size > 0:
            self.current_gp_display_min = np.min(active_gp_cells)
            self.current_gp_display_max = np.max(active_gp_cells)
        else:
            self.current_gp_display_min = 0.0
            self.current_gp_display_max = DIRICHLET_SCALE_FACTOR
        
        if self.current_gp_display_max <= self.current_gp_display_min: 
            val = self.current_gp_display_min 
            self.current_gp_display_min = max(0, val - 0.5 * abs(val) - 0.1) 
            self.current_gp_display_max = val + 0.5 * abs(val) + 0.1
            if abs(self.current_gp_display_max - self.current_gp_display_min) < 1e-6 : 
                 self.current_gp_display_max = self.current_gp_display_min + 0.1 
        self.field_scale_label_var.set(f"GP Field Scale: {self.current_gp_display_min:.2f}-{self.current_gp_display_max:.2f}")


    def prepare_visualization_map(self): 
        self.map_mask.fill(0) 
        for r in range(self.sim_grid_rows):
            for c in range(self.sim_grid_cols):
                cx_c, cy_c = self._sim_to_canvas_coords_center(r,c) 
                for s_obj in self.shapes_list:
                    if s_obj.contains_point(cx_c,cy_c): self.map_mask[r,c]=1; break 
        for item_id in self.field_vis_cells.values(): self.drawing_canvas.delete(item_id)
        self.field_vis_cells.clear()
        for r in range(self.sim_grid_rows):
            for c in range(self.sim_grid_cols):
                if self.map_mask[r,c]==1: 
                    x0,y0=self._sim_to_canvas_coords(r,c)
                    # Heatmap cells are now for gp_mean_field
                    vis_id=self.drawing_canvas.create_rectangle(x0,y0,x0+CELL_SIZE,y0+CELL_SIZE,fill="",outline="",tags="gp_field_cell")
                    self.field_vis_cells[(r,c)]=vis_id
        self.drawing_canvas.tag_lower("gp_field_cell") 

    def toggle_simulation(self): 
        if self.sim_running: # "Clear Field"
            self.sim_running = False
            # self.gp_mean_field.fill(0) # Clear GP field
            self.draw_field_visualization() # Redraw (will be blank if cells are cleared)
            self.draw_color_scale() 
            self.sim_toggle_button.config(text="Initialize & Run GP")
            self.sim_status_label_var.set("Field Cleared. Editing enabled.")
            if self.sim_job_id: self.root.after_cancel(self.sim_job_id); self.sim_job_id = None
            for rb in self.mode_radios: rb.config(state=tk.NORMAL)
            self.delete_button.config(state=tk.NORMAL)
            self.clear_sensors_button.config(state=tk.NORMAL)
            if self.selected_sensor_obj: self.radius_scale.config(state=tk.NORMAL); self.strength_scale.config(state=tk.NORMAL)
            elif self.sensor_params_frame.winfo_ismapped(): 
                self.radius_scale.config(state=tk.NORMAL); self.strength_scale.config(state=tk.NORMAL)
        else: # "Initialize & Run GP"
            if not self.shapes_list: self.sim_status_label_var.set("Draw region shapes first!"); return
            if not SKLEARN_AVAILABLE: self.sim_status_label_var.set("Scikit-learn missing! GP Reconstruction disabled."); return

            self.sim_running = True
            self.prepare_visualization_map() 
            self.gp_update_counter = 0 # Reset GP counter
            
            # Initial generation of ground truth and first GP prediction
            self.initialize_dirichlet_field(scale_factor=DIRICHLET_SCALE_FACTOR) 
            self.update_gp_model_and_predict() # This sets gp_mean_field and its display scale
            
            self.draw_field_visualization() 
            self.draw_color_scale()
            
            self.sim_toggle_button.config(text="Clear Field")
            # Status is set within update_gp_model_and_predict
            
            self.mode_var.set("select") 
            for rb in self.mode_radios:
                if rb.cget("value") != "select": rb.config(state=tk.DISABLED)
                else: rb.config(state=tk.NORMAL) 
            self.delete_button.config(state=tk.DISABLED)
            self.clear_sensors_button.config(state=tk.DISABLED)
            if self.selected_sensor_obj: self.radius_scale.config(state=tk.DISABLED); self.strength_scale.config(state=tk.DISABLED)
            elif self.sensor_params_frame.winfo_ismapped(): 
                self.radius_scale.config(state=tk.DISABLED); self.strength_scale.config(state=tk.DISABLED)

            if not self.sim_job_id: self.run_simulation_step()


    def draw_field_visualization(self): # Now draws gp_mean_field
        min_val = self.current_gp_display_min; max_val = self.current_gp_display_max
        range_val = max_val - min_val
        if abs(range_val) < 1e-6: range_val = 1e-6 

        for r_idx in range(self.sim_grid_rows):
            for c_idx in range(self.sim_grid_cols):
                cell_id = self.field_vis_cells.get((r_idx,c_idx))
                if cell_id:
                    if self.sim_running and self.map_mask[r_idx, c_idx] == 1:
                        concentration = self.gp_mean_field[r_idx, c_idx] # Use GP field
                        normalized_conc = (concentration - min_val) / range_val
                        intensity = int(min(255, max(0, normalized_conc * 255)))
                        # Color for GP inferred field (e.g., a blue-ish tint)
                        color = f'#{intensity//2:02x}{intensity//2:02x}{intensity:02x}' # Blueish
                        # color = f'#00{intensity:02x}00' # Original Green
                        self.drawing_canvas.itemconfig(cell_id, fill=color, outline=color) 
                    else: self.drawing_canvas.itemconfig(cell_id, fill="", outline="")
        self.drawing_canvas.tag_raise("user_shape") 
        for sensor_obj in self.sensors_list: 
            if sensor_obj.canvas_item_id: self.drawing_canvas.tag_raise(sensor_obj.canvas_item_id)
            if sensor_obj.influence_vis_id: self.drawing_canvas.tag_raise(sensor_obj.influence_vis_id) 

    def draw_color_scale(self): # Now uses gp_display_min/max
        self.color_scale_canvas.delete("all")
        if not self.sim_running: 
            self.color_scale_canvas.create_text(COLOR_SCALE_WIDTH/2, CANVAS_HEIGHT/2, text="N/A", anchor=tk.CENTER, font=LABEL_FONT)
            return

        min_val = self.current_gp_display_min
        max_val = self.current_gp_display_max
        range_val = max_val - min_val
        if abs(range_val) < 1e-6: range_val = 1e-6 

        num_segments = 100 
        segment_height = (CANVAS_HEIGHT - 2 * AXIS_MARGIN) / num_segments 
        gradient_bar_width = COLOR_SCALE_WIDTH * 0.4 
        x_offset = COLOR_SCALE_WIDTH * 0.2 # Centered bar a bit more

        for i in range(num_segments):
            val = max_val - (i / num_segments) * range_val
            normalized_conc = (val - min_val) / range_val
            intensity = int(min(255, max(0, normalized_conc * 255)))
            color = f'#{intensity//2:02x}{intensity//2:02x}{intensity:02x}' # Blueish, matching heatmap
            
            y0 = AXIS_MARGIN + i * segment_height
            y1 = AXIS_MARGIN + (i + 1) * segment_height
            self.color_scale_canvas.create_rectangle(x_offset, y0, x_offset + gradient_bar_width, y1, fill=color, outline=color)

        label_x = x_offset + gradient_bar_width + 7 
        self.color_scale_canvas.create_text(label_x, AXIS_MARGIN, text=f"{max_val:.1f}", anchor=tk.NW, font=LABEL_FONT, fill=LABEL_COLOR)
        self.color_scale_canvas.create_text(label_x, CANVAS_HEIGHT - AXIS_MARGIN, text=f"{min_val:.1f}", anchor=tk.SW, font=LABEL_FONT, fill=LABEL_COLOR)
        mid_val = min_val + range_val / 2
        mid_y = AXIS_MARGIN + (CANVAS_HEIGHT - 2 * AXIS_MARGIN) / 2
        self.color_scale_canvas.create_text(label_x, mid_y, text=f"{mid_val:.1f}", anchor=tk.W, font=LABEL_FONT, fill=LABEL_COLOR)
        self.color_scale_canvas.create_text(COLOR_SCALE_WIDTH/2, AXIS_MARGIN/2, text="GP Value", anchor=tk.CENTER, font=LABEL_FONT, fill=LABEL_COLOR)


    def run_simulation_step(self): 
        if not self.sim_running: 
            if self.sim_job_id: self.root.after_cancel(self.sim_job_id); self.sim_job_id = None
            return
        
        # 1. Generate new ground truth Dirichlet field
        self.initialize_dirichlet_field(scale_factor=DIRICHLET_SCALE_FACTOR)
        
        # 2. Periodically update GP model based on new ground truth
        self.gp_update_counter += 1
        if self.gp_update_counter >= GP_UPDATE_EVERY_N_FRAMES:
            self.update_gp_model_and_predict() # This sets gp_mean_field and its display scale
            self.gp_update_counter = 0
        elif not SKLEARN_AVAILABLE or not self.sensors_list: # If GP isn't active, ensure gp_mean_field mirrors data_field
             self.update_gp_model_and_predict() # This will handle the fallback

        # 3. Draw the GP inferred field and color scale
        self.draw_field_visualization() 
        self.draw_color_scale() 
        
        self.sim_job_id = self.root.after(100, self.run_simulation_step) 

if __name__ == "__main__":
    app_root = tk.Tk()
    if not SKLEARN_AVAILABLE:
        print("--- WARNING: Scikit-learn (sklearn) is NOT installed. ---")
        print("--- The Gaussian Process reconstruction will be disabled. ---")
        print("--- To enable it, please install scikit-learn: pip install scikit-learn ---")
    drawing_app = DrawingApp(app_root)
    app_root.mainloop()
