import tkinter as tk
from tkinter import ttk, colorchooser
import math
import numpy as np
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from enum import Enum, auto
import random

from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel
import matplotlib.cm as cm
import matplotlib.colors as mcolors

SHAPELY_AVAILABLE = True
SKLEARN_AVAILABLE = True

# --- Constants from better-sample.py ---
NORMAL_O2_PERCENTAGE = 21.0
NORMAL_CO2_PPM = 400.0
MARS_O2_PERCENTAGE = 0.13
MARS_CO2_PERCENTAGE = 95.0  # This is a percentage
MARS_CO2_PPM = MARS_CO2_PERCENTAGE * 10000 # Convert to PPM (950,000 PPM)

HUMAN_O2_CONSUMPTION_PER_HOUR_PERSON = 0.035 # percentage points per hour per person (approx 0.84 kg/day, typical habitat volume assumed)
HUMAN_CO2_PRODUCTION_PER_HOUR_PERSON = 0.042 # percentage points per hour per person (approx 1 kg/day)
# Convert CO2 production to PPM: 1% = 10000 PPM. So, 0.042% = 420 PPM.
HUMAN_CO2_PRODUCTION_PPM_PER_HOUR_PERSON = HUMAN_CO2_PRODUCTION_PER_HOUR_PERSON * 10000


SIM_STEP_REAL_TIME_SECONDS = 0.1 # How often run_simulation_step is called
SIM_TIME_SCALE_FACTOR = 1.0 / 36.0 # Scales real time to simulation hours (e.g., 1 real sec = 1/36 sim hour => 1 sim hour = 36 real secs)
                                 # So, 0.1 real sec step = 0.1/36 sim hours.
SIM_DT_HOURS = SIM_STEP_REAL_TIME_SECONDS * SIM_TIME_SCALE_FACTOR


class RoomType(Enum):
    LIVING_QUARTERS = auto()
    LABORATORY = auto()
    GREENHOUSE = auto()
    COMMAND_CENTER = auto()
    AIRLOCK = auto()
    CORRIDOR = auto()
    STORAGE = auto()
    MEDICAL_BAY = auto()
    NONE = auto() # For unassigned shapes

    @classmethod
    def get_color(cls, room_type):
        colors = {
            cls.LIVING_QUARTERS: "#ADD8E6",  # Light blue
            cls.LABORATORY: "#FFFFE0",       # Light yellow
            cls.GREENHOUSE: "#90EE90",       # Light green
            cls.COMMAND_CENTER: "#FFB6C1",   # Light red (pinkish)
            cls.AIRLOCK: "#D3D3D3",          # Light gray
            cls.CORRIDOR: "#E0E0E0",         # Lighter gray
            cls.STORAGE: "#DEB887",          # Burlywood (brownish)
            cls.MEDICAL_BAY: "#FFC0CB",      # Pink
            cls.NONE: "#FFFFFF"              # White for unassigned
        }
        return colors.get(room_type, "#FFFFFF")

    @classmethod
    def get_default_population_capacity(cls, room_type):
        # Rough estimate, can be tied to area later
        capacities = {
            cls.LIVING_QUARTERS: 2,
            cls.LABORATORY: 3,
            cls.GREENHOUSE: 1,
            cls.COMMAND_CENTER: 4,
            cls.AIRLOCK: 1,
            cls.CORRIDOR: 0,
            cls.STORAGE: 0,
            cls.MEDICAL_BAY: 2,
            cls.NONE: 0
        }
        return capacities.get(room_type, 0)

# --- Constants ---
CELL_SIZE = 10 # Grid cell size in pixels
AXIS_MARGIN = 30
CANVAS_WIDTH = AXIS_MARGIN + 600 + CELL_SIZE
CANVAS_HEIGHT = AXIS_MARGIN + 480 + CELL_SIZE
SIM_CONTROLS_HEIGHT = 100
TOTAL_CANVAS_HEIGHT = CANVAS_HEIGHT + SIM_CONTROLS_HEIGHT

COLOR_SCALE_WIDTH = 80
COLOR_SCALE_PADDING = 10

# Diffusion constants (Original, may need re-evaluation for gas dynamics)
DIFFUSION_COEFFICIENT = 0.1  # Controls diffusion rate within rooms if enabled
DIFFUSION_UPDATE_EVERY_N_FRAMES = 5

GRID_COLOR = "lightgray"
AXIS_LINE_COLOR = "black"
LABEL_COLOR = "dim gray"
LABEL_FONT = ("Arial", 8)
LABEL_INTERVAL = CELL_SIZE * 5

DEFAULT_OUTLINE_COLOR = "black"
DEFAULT_OUTLINE_WIDTH = 1
SELECTED_OUTLINE_COLOR = "blue"
SELECTED_OUTLINE_WIDTH = 2
SHAPE_STIPPLE = "" # Not used for rooms

# Sensor Constants
SENSOR_DRAW_RADIUS_PIXELS = CELL_SIZE * 0.40
SENSOR_SENSING_RADIUS_PIXELS = CELL_SIZE * 0.75 # For GP reading from ground truth (area average)
SENSOR_DEFAULT_O2_VARIANCE = 0.5 # variance for O2 reading
SENSOR_DEFAULT_CO2_VARIANCE = 20.0 # variance for CO2 reading
SENSOR_OUTLINE_COLOR = "red"
SENSOR_SELECTED_OUTLINE_COLOR = "magenta"
SENSOR_SELECTED_OUTLINE_WIDTH = 2

# GP Constants
GP_UPDATE_EVERY_N_FRAMES = 3 # Update GP every N simulation frames
SENSOR_READING_NOISE_STD_O2 = math.sqrt(SENSOR_DEFAULT_O2_VARIANCE) # Std dev for O2
SENSOR_READING_NOISE_STD_CO2 = math.sqrt(SENSOR_DEFAULT_CO2_VARIANCE) # Std dev for CO2

# Breach Constants
DEFAULT_BREACH_FLOW_RATE_PER_HOUR = 0.1 # Percentage of volume exchanged per hour per unit breach size

# Door Constants
DOOR_WIDTH_PIXELS = CELL_SIZE * 0.8
DOOR_COLOR_OPEN = "green"
DOOR_COLOR_CLOSED = "red"
DOOR_FLOW_RATE_OPEN_PER_HOUR = 0.2 # Gas exchange rate when open (fraction of volume difference)
DOOR_FLOW_RATE_CLOSED_PER_HOUR = 0.005 # Slight leak for closed doors

# --- Sensor Class ---
class Sensor:
    def __init__(self, x_canvas, y_canvas,
                 o2_variance=SENSOR_DEFAULT_O2_VARIANCE,
                 co2_variance=SENSOR_DEFAULT_CO2_VARIANCE,
                 sensing_radius=SENSOR_SENSING_RADIUS_PIXELS):
        self.x = x_canvas
        self.y = y_canvas
        self.o2_variance = o2_variance
        self.co2_variance = co2_variance
        self.sensing_radius = sensing_radius
        self.draw_radius = SENSOR_DRAW_RADIUS_PIXELS
        self.canvas_item_id = None
        self.selected = False
        self.last_o2_reading = None
        self.last_co2_reading = None

    def draw(self, canvas):
        self.canvas_item_id = canvas.create_oval(
            self.x - self.draw_radius, self.y - self.draw_radius,
            self.x + self.draw_radius, self.y + self.draw_radius,
            fill=SENSOR_OUTLINE_COLOR, outline=SENSOR_OUTLINE_COLOR, width=1, tags="sensor_marker"
        )

    def contains_point(self, px, py):
        return (px - self.x)**2 + (py - self.y)**2 <= self.draw_radius**2

    def select(self, canvas):
        self.selected = True
        if self.canvas_item_id:
            canvas.itemconfig(self.canvas_item_id, outline=SENSOR_SELECTED_OUTLINE_COLOR, fill=SENSOR_SELECTED_OUTLINE_COLOR, width=SENSOR_SELECTED_OUTLINE_WIDTH)
            canvas.tag_raise(self.canvas_item_id)

    def deselect(self, canvas):
        self.selected = False
        if self.canvas_item_id:
            canvas.itemconfig(self.canvas_item_id, outline=SENSOR_OUTLINE_COLOR, fill=SENSOR_OUTLINE_COLOR, width=1)

    def move_to(self, canvas, new_x, new_y):
        self.x = new_x
        self.y = new_y
        if self.canvas_item_id:
            canvas.coords(self.canvas_item_id,
                          self.x - self.draw_radius, self.y - self.draw_radius,
                          self.x + self.draw_radius, self.y + self.draw_radius)

    def read_gas_levels(self, true_o2_value, true_co2_value):
        self.last_o2_reading = max(0, np.random.normal(true_o2_value, math.sqrt(self.o2_variance)))
        self.last_co2_reading = max(0, np.random.normal(true_co2_value, math.sqrt(self.co2_variance)))
        return self.last_o2_reading, self.last_co2_reading

    def update_params(self, o2_var, co2_var):
        self.o2_variance = o2_var
        self.co2_variance = co2_var


# --- RoomShape Classes (Formerly Shape) ---
class RoomShape:
    _id_counter = 0
    def __init__(self, x, y, room_type=RoomType.NONE):
        self.id = RoomShape._id_counter
        RoomShape._id_counter += 1
        self.x = x  # For Rectangle: top-left x, For Circle: center_x
        self.y = y  # For Rectangle: top-left y, For Circle: center_y
        self.room_type = room_type
        self.color = RoomType.get_color(self.room_type)

        self.canvas_item_id = None
        self.selected = False

        self.o2_level = NORMAL_O2_PERCENTAGE
        self.co2_level = NORMAL_CO2_PPM
        self.population = 0 #RoomType.get_default_population_capacity(self.room_type)
        self.breach_level = 0.0  # 0.0 to 1.0, representing severity/size of breach
        self.connected_doors = [] # List of Door objects

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
    def calculate_area_pixels(self): raise NotImplementedError # Area in pixel units
    
    def get_volume_liters(self):
        # Assume standard room height of 2.5 meters
        # CELL_SIZE is pixels per meter (e.g., if 10 pixels = 1 meter)
        # Area in m^2 = area_pixels / (pixels_per_meter^2)
        # For now, let's use a simpler proxy or make area more significant
        # A typical room might be 50 m^3 = 50000 Liters.
        # Let area be a proxy for volume for now.
        # Area in "units^2" from calculate_area_pixels is pixel^2.
        # If CELL_SIZE = 10px represents 1 meter, then 1m^2 = 100px^2.
        # Volume = Area_m2 * Height_m. Let Height_m = 2.5m
        area_px2 = self.calculate_area_pixels()
        if area_px2 is None or area_px2 == 0: return 1000 # Min volume
        area_m2 = area_px2 / (CELL_SIZE**2) # if CELL_SIZE is px/m
        volume_m3 = area_m2 * 2.5 # Assume 2.5m height
        return volume_m3 * 1000 # m^3 to Liters

    def update_room_type(self, new_room_type, canvas):
        self.room_type = new_room_type
        self.color = RoomType.get_color(new_room_type)
        if not self.population_fixed_by_user: # Only if not manually set
            self.population = RoomType.get_default_population_capacity(new_room_type)
        if self.canvas_item_id:
            canvas.itemconfig(self.canvas_item_id, fill=self.color)

    def get_center_canvas_coords(self):
        raise NotImplementedError

class RoomRectangle(RoomShape):
    def __init__(self, x, y, width, height, room_type=RoomType.NONE):
        super().__init__(x, y, room_type)
        self.width = width
        self.height = height
        self.population_fixed_by_user = False


    def draw(self, canvas):
        self.canvas_item_id = canvas.create_rectangle(
            self.x, self.y, self.x + self.width, self.y + self.height,
            fill=self.color, outline=DEFAULT_OUTLINE_COLOR,
            width=DEFAULT_OUTLINE_WIDTH, tags=("user_shape", f"room_{self.id}")
        )

    def contains_point(self, px, py):
        return self.x <= px <= self.x + self.width and self.y <= py <= self.y + self.height

    def move_to(self, canvas, new_x, new_y):
        self.x = new_x; self.y = new_y
        if self.canvas_item_id:
            canvas.coords(self.canvas_item_id, self.x, self.y, self.x + self.width, self.y + self.height)

    def resize(self, canvas, new_corner_x, new_corner_y):
        self.width = max(CELL_SIZE, new_corner_x - self.x) # Min width/height of 1 cell
        self.height = max(CELL_SIZE, new_corner_y - self.y)
        if self.canvas_item_id:
            canvas.coords(self.canvas_item_id, self.x, self.y, self.x + self.width, self.y + self.height)

    def update_coords_from_canvas(self, canvas):
        if self.canvas_item_id:
            coords = canvas.coords(self.canvas_item_id)
            if coords:
                self.x, self.y = coords[0], coords[1]
                self.width = abs(coords[2] - coords[0])
                self.height = abs(coords[3] - coords[1])
    
    def calculate_area_pixels(self): return self.width * self.height

    def get_center_canvas_coords(self):
        return self.x + self.width / 2, self.y + self.height / 2
    
    def get_shapely_polygon(self):
        return Polygon([(self.x, self.y), (self.x + self.width, self.y),
                        (self.x + self.width, self.y + self.height), (self.x, self.y + self.height)])


class RoomCircle(RoomShape):
    def __init__(self, center_x, center_y, radius, room_type=RoomType.NONE):
        super().__init__(center_x, center_y, room_type) # x,y are center for Circle
        self.radius = radius
        self.population_fixed_by_user = False

    def draw(self, canvas):
        self.canvas_item_id = canvas.create_oval(
            self.x - self.radius, self.y - self.radius,
            self.x + self.radius, self.y + self.radius,
            fill=self.color, outline=DEFAULT_OUTLINE_COLOR,
            width=DEFAULT_OUTLINE_WIDTH, tags=("user_shape", f"room_{self.id}")
        )

    def contains_point(self, px, py):
        return (px - self.x)**2 + (py - self.y)**2 <= self.radius**2

    def move_to(self, canvas, new_center_x, new_center_y):
        self.x = new_center_x; self.y = new_center_y
        if self.canvas_item_id:
            canvas.coords(self.canvas_item_id, self.x - self.radius, self.y - self.radius, self.x + self.radius, self.y + self.radius)

    def resize(self, canvas, edge_x, edge_y):
        new_radius = math.sqrt((edge_x - self.x)**2 + (edge_y - self.y)**2)
        self.radius = max(CELL_SIZE / 2, new_radius) # Min radius
        if self.canvas_item_id:
            canvas.coords(self.canvas_item_id, self.x - self.radius, self.y - self.radius, self.x + self.radius, self.y + self.radius)

    def update_coords_from_canvas(self, canvas):
        if self.canvas_item_id:
            coords = canvas.coords(self.canvas_item_id)
            if coords:
                self.x = (coords[0] + coords[2]) / 2
                self.y = (coords[1] + coords[3]) / 2
                self.radius = abs(coords[2] - coords[0]) / 2
    
    def calculate_area_pixels(self): return math.pi * (self.radius ** 2)

    def get_center_canvas_coords(self):
        return self.x, self.y

    def get_shapely_polygon(self):
        return Point(self.x, self.y).buffer(self.radius)

class Door:
    _id_counter = 0
    def __init__(self, room1_id: int, room2_id: int, position: tuple, app_ref):
        self.id = Door._id_counter
        Door._id_counter += 1
        self.room1_id = room1_id
        self.room2_id = room2_id # Can be None for external door
        self.position = position # (x,y) center of the door on canvas
        self.is_open = True
        self.canvas_item_id = None
        self.app = app_ref # Reference to DrawingApp for finding rooms

    def draw(self, canvas):
        x, y = self.position
        half_width = DOOR_WIDTH_PIXELS / 2
        color = DOOR_COLOR_OPEN if self.is_open else DOOR_COLOR_CLOSED
        self.canvas_item_id = canvas.create_rectangle(
            x - half_width, y - half_width, x + half_width, y + half_width, # Make it a square for now
            fill=color, outline="black", tags=("door", f"door_{self.id}")
        )

    def toggle_state(self, canvas):
        self.is_open = not self.is_open
        color = DOOR_COLOR_OPEN if self.is_open else DOOR_COLOR_CLOSED
        if self.canvas_item_id:
            canvas.itemconfig(self.canvas_item_id, fill=color)

    def contains_point(self, px, py):
        x, y = self.position
        half_width = DOOR_WIDTH_PIXELS / 2
        return (x - half_width <= px <= x + half_width) and \
               (y - half_width <= py <= y + half_width)

    def get_connected_rooms(self):
        room1 = self.app.get_room_by_id(self.room1_id)
        room2 = self.app.get_room_by_id(self.room2_id) if self.room2_id is not None else None
        return room1, room2

# --- Main Application ---
class DrawingApp:
    def __init__(self, master_root):
        self.root = master_root
        self.root.title("Mars Habitat Life Support Simulator (GP Reconstruction)")

        self.current_mode = "select"
        self.rooms_list = [] # List of RoomShape objects
        self.selected_room_obj = None
        self.sensors_list = []
        self.selected_sensor_obj = None
        self.doors_list = []
        self.selected_door_obj = None

        self.is_dragging = False
        self.was_resizing_session = False
        self.drag_action_occurred = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        
        self.temp_door_room1_id = None # For multi-click door placement

        self.sim_grid_rows = (CANVAS_HEIGHT - AXIS_MARGIN) // CELL_SIZE
        self.sim_grid_cols = (CANVAS_WIDTH - AXIS_MARGIN) // CELL_SIZE

        # Ground truth gas fields (pixel grid resolution)
        self.o2_field_ground_truth = np.full((self.sim_grid_rows, self.sim_grid_cols), MARS_O2_PERCENTAGE, dtype=float)
        self.co2_field_ground_truth = np.full((self.sim_grid_rows, self.sim_grid_cols), MARS_CO2_PPM, dtype=float)
        
        self.map_mask = np.zeros((self.sim_grid_rows, self.sim_grid_cols), dtype=int) # 1 if cell is in any room

        self.sim_running = False
        self.sim_job_id = None
        self.field_vis_cells = {} # For heatmap cells { (r,c): canvas_id }

        # GP related attributes
        self.gp_model_o2 = None
        self.gp_model_co2 = None
        self.gp_reconstructed_field = np.zeros((self.sim_grid_rows, self.sim_grid_cols), dtype=float) # Current gas view
        self.XY_gp_prediction_grid = self._create_gp_prediction_grid()
        self.gp_update_counter = 0
        self.diffusion_update_counter = 0 # For original diffusion, might remove

        self.current_gas_view = tk.StringVar(value="O2") # "O2" or "CO2"
        self.current_gp_display_min = 0.0
        self.current_gp_display_max = NORMAL_O2_PERCENTAGE

        if SKLEARN_AVAILABLE:
            kernel_o2 = ConstantKernel(1.0, (1e-3, 1e3)) * RBF(length_scale=CELL_SIZE*3, length_scale_bounds=(CELL_SIZE*0.5, CELL_SIZE*15)) \
                       + WhiteKernel(noise_level=SENSOR_READING_NOISE_STD_O2**2, noise_level_bounds=(1e-2, 1e2))
            self.gp_model_o2 = GaussianProcessRegressor(kernel=kernel_o2, alpha=1e-7, optimizer='fmin_l_bfgs_b', n_restarts_optimizer=3, normalize_y=True)

            kernel_co2 = ConstantKernel(1.0, (1e-3, 1e3)) * RBF(length_scale=CELL_SIZE*3, length_scale_bounds=(CELL_SIZE*0.5, CELL_SIZE*15)) \
                       + WhiteKernel(noise_level=SENSOR_READING_NOISE_STD_CO2**2, noise_level_bounds=(1e-2, 1e2)) # Higher noise for CO2
            self.gp_model_co2 = GaussianProcessRegressor(kernel=kernel_co2, alpha=1e-7, optimizer='fmin_l_bfgs_b', n_restarts_optimizer=3, normalize_y=True)
        else:
            print("WARNING: Scikit-learn not found. GP reconstruction will be disabled.")

        self._setup_ui()
        self.initialize_gas_fields() # Initialize with Mars values

    def get_room_by_id(self, room_id):
        for room in self.rooms_list:
            if room.id == room_id:
                return room
        return None

    def _setup_ui(self):
        main_app_frame = ttk.Frame(self.root, padding="10")
        main_app_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Top: Controls and Parameters
        controls_params_top_frame = ttk.Frame(main_app_frame)
        controls_params_top_frame.pack(side=tk.TOP, fill=tk.X, pady=(0,10))

        # Left part of Top: Drawing/Mode Controls
        self.drawing_controls_frame = ttk.LabelFrame(controls_params_top_frame, text="Habitat Element Controls", padding="10")
        self.drawing_controls_frame.pack(side=tk.LEFT, padx=5, fill=tk.Y, expand=False)

        # Right part of Top: Selected Element Parameters
        self.element_params_frame = ttk.Frame(controls_params_top_frame)
        self.element_params_frame.pack(side=tk.LEFT, padx=15, fill=tk.BOTH, expand=True)
        
        self.room_params_frame = ttk.LabelFrame(self.element_params_frame, text="Selected Room Parameters", padding="10")
        # Packed later when a room is selected
        self.sensor_params_frame = ttk.LabelFrame(self.element_params_frame, text="Selected Sensor Parameters", padding="10")
        # Packed later when a sensor is selected

        # Middle: Canvas Area
        canvas_area_frame = ttk.Frame(main_app_frame)
        canvas_area_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(0,10))
        self.drawing_canvas = tk.Canvas(canvas_area_frame, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg="white", relief=tk.SUNKEN, borderwidth=1)
        self.drawing_canvas.pack(side=tk.LEFT, padx=(0,COLOR_SCALE_PADDING), pady=0, expand=True, fill=tk.BOTH)
        self.color_scale_canvas = tk.Canvas(canvas_area_frame, width=COLOR_SCALE_WIDTH, height=CANVAS_HEIGHT, bg="whitesmoke", relief=tk.SUNKEN, borderwidth=1)
        self.color_scale_canvas.pack(side=tk.RIGHT, pady=0, fill=tk.Y)

        # Bottom: Simulation Controls and Status
        sim_status_bottom_frame = ttk.Frame(main_app_frame)
        sim_status_bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5,0))
        
        self.gp_display_controls_frame = ttk.LabelFrame(sim_status_bottom_frame, text="GP Inferred Field Display", padding="5")
        self.gp_display_controls_frame.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        self.sim_toggle_frame = ttk.LabelFrame(sim_status_bottom_frame, text="Simulation Control", padding="5")
        self.sim_toggle_frame.pack(side=tk.LEFT, padx=5, fill=tk.X)


        # --- Populate Drawing Controls Frame ---
        ttk.Label(self.drawing_controls_frame, text="Mode:").grid(row=0, column=0, columnspan=2, padx=2, pady=2, sticky=tk.W)
        self.mode_var = tk.StringVar(value=self.current_mode)
        modes = [("Select", "select"), ("Draw Room (Rect)", "rectangle"),
                 ("Draw Room (Circle)", "circle"), ("Add Sensor", "add_sensor"),
                 ("Add Door", "add_door")]
        for i, (text, mode_val) in enumerate(modes):
            rb = ttk.Radiobutton(self.drawing_controls_frame, text=text, variable=self.mode_var, value=mode_val, command=self.set_current_mode)
            rb.grid(row=i+1, column=0, columnspan=2, padx=2, pady=2, sticky=tk.W)
        
        self.delete_button = ttk.Button(self.drawing_controls_frame, text="Delete Selected", command=self.delete_selected_item)
        self.delete_button.grid(row=len(modes)+1, column=0, padx=5, pady=5, sticky=tk.W)
        self.clear_sensors_button = ttk.Button(self.drawing_controls_frame, text="Clear All Sensors", command=self.clear_all_sensors)
        self.clear_sensors_button.grid(row=len(modes)+1, column=1, padx=5, pady=5, sticky=tk.W)
        self.clear_doors_button = ttk.Button(self.drawing_controls_frame, text="Clear All Doors", command=self.clear_all_doors)
        self.clear_doors_button.grid(row=len(modes)+2, column=0, padx=5, pady=5, sticky=tk.W)


        self.union_area_label_var = tk.StringVar(value="Total Room Area: N/A")
        ttk.Label(self.drawing_controls_frame, textvariable=self.union_area_label_var).grid(row=len(modes)+3, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W)

        # --- Populate Room Parameters Frame ---
        self.selected_room_id_label = ttk.Label(self.room_params_frame, text="Room ID: -")
        self.selected_room_id_label.grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=2, pady=2)

        ttk.Label(self.room_params_frame, text="Room Type:").grid(row=1, column=0, sticky=tk.W, padx=2)
        self.room_type_var = tk.StringVar()
        self.room_type_options = [rt.name for rt in RoomType]
        self.room_type_menu = ttk.OptionMenu(self.room_params_frame, self.room_type_var, "", *self.room_type_options, command=self._update_selected_room_type)
        self.room_type_menu.grid(row=1, column=1, sticky=tk.EW, padx=2)

        ttk.Label(self.room_params_frame, text="Population:").grid(row=2, column=0, sticky=tk.W, padx=2)
        self.population_var = tk.IntVar(value=0)
        self.population_spinbox = ttk.Spinbox(self.room_params_frame, from_=0, to=20, textvariable=self.population_var, width=5, command=self._update_selected_room_population)
        self.population_spinbox.grid(row=2, column=1, sticky=tk.W, padx=2)
        
        ttk.Label(self.room_params_frame, text="Breach Level (0-1):").grid(row=3, column=0, sticky=tk.W, padx=2)
        self.breach_var = tk.DoubleVar(value=0.0)
        self.breach_scale = ttk.Scale(self.room_params_frame, from_=0.0, to=1.0, variable=self.breach_var, orient=tk.HORIZONTAL, length=100, command=self._update_selected_room_breach)
        self.breach_scale.grid(row=3, column=1, sticky=tk.EW, padx=2)
        self.breach_label = ttk.Label(self.room_params_frame, text="0.0")
        self.breach_label.grid(row=3, column=2, sticky=tk.W, padx=2)

        self.room_o2_label = ttk.Label(self.room_params_frame, text="O2: - %")
        self.room_o2_label.grid(row=4, column=0, columnspan=3, sticky=tk.W, padx=2, pady=2)
        self.room_co2_label = ttk.Label(self.room_params_frame, text="CO2: - ppm")
        self.room_co2_label.grid(row=5, column=0, columnspan=3, sticky=tk.W, padx=2, pady=2)


        # --- Populate Sensor Parameters Frame ---
        self.selected_sensor_id_label = ttk.Label(self.sensor_params_frame, text="Sensor ID: -")
        self.selected_sensor_id_label.grid(row=0, column=0, columnspan=3, sticky=tk.W, padx=2, pady=2)
        
        ttk.Label(self.sensor_params_frame, text="O2 Variance:").grid(row=1, column=0, sticky=tk.W, padx=2)
        self.sensor_o2_var_var = tk.DoubleVar(value=SENSOR_DEFAULT_O2_VARIANCE)
        self.sensor_o2_var_scale = ttk.Scale(self.sensor_params_frame, from_=0.01, to=5.0, variable=self.sensor_o2_var_var, orient=tk.HORIZONTAL, length=100, command=self._update_selected_sensor_params)
        self.sensor_o2_var_scale.grid(row=1, column=1, sticky=tk.EW, padx=2)
        self.sensor_o2_var_label = ttk.Label(self.sensor_params_frame, text=f"{SENSOR_DEFAULT_O2_VARIANCE:.2f}")
        self.sensor_o2_var_label.grid(row=1, column=2, sticky=tk.W, padx=2)

        ttk.Label(self.sensor_params_frame, text="CO2 Variance:").grid(row=2, column=0, sticky=tk.W, padx=2)
        self.sensor_co2_var_var = tk.DoubleVar(value=SENSOR_DEFAULT_CO2_VARIANCE)
        self.sensor_co2_var_scale = ttk.Scale(self.sensor_params_frame, from_=1.0, to=200.0, variable=self.sensor_co2_var_var, orient=tk.HORIZONTAL, length=100, command=self._update_selected_sensor_params)
        self.sensor_co2_var_scale.grid(row=2, column=1, sticky=tk.EW, padx=2)
        self.sensor_co2_var_label = ttk.Label(self.sensor_params_frame, text=f"{SENSOR_DEFAULT_CO2_VARIANCE:.1f}")
        self.sensor_co2_var_label.grid(row=2, column=2, sticky=tk.W, padx=2)

        self.sensor_o2_reading_label = ttk.Label(self.sensor_params_frame, text="O2 Reading: - %")
        self.sensor_o2_reading_label.grid(row=3, column=0, columnspan=3, sticky=tk.W, padx=2, pady=2)
        self.sensor_co2_reading_label = ttk.Label(self.sensor_params_frame, text="CO2 Reading: - ppm")
        self.sensor_co2_reading_label.grid(row=4, column=0, columnspan=3, sticky=tk.W, padx=2, pady=2)


        # --- Populate GP Display Controls Frame ---
        ttk.Label(self.gp_display_controls_frame, text="View Gas:").pack(side=tk.LEFT, padx=(5,0))
        ttk.Radiobutton(self.gp_display_controls_frame, text="O2", variable=self.current_gas_view, value="O2", command=self._on_gas_view_change).pack(side=tk.LEFT)
        ttk.Radiobutton(self.gp_display_controls_frame, text="CO2", variable=self.current_gas_view, value="CO2", command=self._on_gas_view_change).pack(side=tk.LEFT, padx=(0,10))
        
        self.field_scale_label_var = tk.StringVar(value=f"GP Scale: {self.current_gp_display_min:.1f}-{self.current_gp_display_max:.1f}")
        ttk.Label(self.gp_display_controls_frame, textvariable=self.field_scale_label_var).pack(side=tk.LEFT, padx=5)
        
        # --- Populate Simulation Toggle Frame ---
        self.sim_status_label_var = tk.StringVar(value="Simulation: Stopped. Editing enabled.")
        ttk.Label(self.sim_toggle_frame, textvariable=self.sim_status_label_var).pack(side=tk.LEFT, padx=5)
        self.sim_toggle_button = ttk.Button(self.sim_toggle_frame, text="Initialize & Run Sim", command=self.toggle_simulation)
        self.sim_toggle_button.pack(side=tk.LEFT, padx=5)

        # --- Final UI Setup ---
        self.draw_visual_grid_and_axes()
        self.draw_color_scale() # Initial draw
        self.drawing_canvas.bind("<Button-1>", self.handle_mouse_down)
        self.drawing_canvas.bind("<B1-Motion>", self.handle_mouse_drag)
        self.drawing_canvas.bind("<ButtonRelease-1>", self.handle_mouse_up)
        self.root.bind("<Delete>", lambda e: self.delete_selected_item())
        self.root.bind("<BackSpace>", lambda e: self.delete_selected_item())
        self.root.bind("<Escape>", self.handle_escape_key)
        self.update_union_area_display()
        self._show_element_params_frame() # Initially hide params

    def _create_gp_prediction_grid(self):
        grid_points = []
        for r_idx in range(self.sim_grid_rows):
            for c_idx in range(self.sim_grid_cols):
                canvas_x = AXIS_MARGIN + c_idx * CELL_SIZE + CELL_SIZE / 2
                canvas_y = AXIS_MARGIN + r_idx * CELL_SIZE + CELL_SIZE / 2
                grid_points.append([canvas_x, canvas_y])
        return np.array(grid_points)

    def _update_selected_room_type(self, selected_type_str):
        if self.selected_room_obj:
            new_type = RoomType[selected_type_str]
            self.selected_room_obj.update_room_type(new_type, self.drawing_canvas)
            self.population_var.set(self.selected_room_obj.population) # Update spinbox
            self.selected_room_obj.population_fixed_by_user = False # Reset flag
            self.sim_status_label_var.set(f"Room type changed. Re-init sim if running.")
            self.prepare_visualization_map_and_fields() # Update map mask for colors

    def _update_selected_room_population(self):
        if self.selected_room_obj:
            self.selected_room_obj.population = self.population_var.get()
            self.selected_room_obj.population_fixed_by_user = True # User manually set it
            self.sim_status_label_var.set(f"Room population changed.")
            # No need to re-init sim, effect is immediate in next step

    def _update_selected_room_breach(self, value_str):
        if self.selected_room_obj:
            new_breach_level = float(value_str)
            self.selected_room_obj.breach_level = new_breach_level
            self.breach_label.config(text=f"{new_breach_level:.2f}")
            self.sim_status_label_var.set(f"Room breach level changed.")

    def _update_selected_sensor_params(self, value_str=None): # value_str not always used if called directly
        if self.selected_sensor_obj:
            o2_var = self.sensor_o2_var_var.get()
            co2_var = self.sensor_co2_var_var.get()
            self.selected_sensor_obj.update_params(o2_var, co2_var)
            self.sensor_o2_var_label.config(text=f"{o2_var:.2f}")
            self.sensor_co2_var_label.config(text=f"{co2_var:.1f}")
            self.sim_status_label_var.set("Sensor params changed. Re-init sim if running.")

    def _show_element_params_frame(self):
        # Hide all first
        self.room_params_frame.pack_forget()
        self.sensor_params_frame.pack_forget()

        if self.selected_room_obj:
            self.room_params_frame.pack(side=tk.TOP, padx=5, pady=5, fill=tk.X)
            self.selected_room_id_label.config(text=f"Room ID: {self.selected_room_obj.id}")
            self.room_type_var.set(self.selected_room_obj.room_type.name)
            self.population_var.set(self.selected_room_obj.population)
            self.breach_var.set(self.selected_room_obj.breach_level)
            self.breach_label.config(text=f"{self.selected_room_obj.breach_level:.2f}")
            self.room_o2_label.config(text=f"O2: {self.selected_room_obj.o2_level:.2f}%")
            self.room_co2_label.config(text=f"CO2: {self.selected_room_obj.co2_level:.0f} ppm")
        elif self.selected_sensor_obj:
            self.sensor_params_frame.pack(side=tk.TOP, padx=5, pady=5, fill=tk.X)
            self.selected_sensor_id_label.config(text=f"Sensor ID: S{self.sensors_list.index(self.selected_sensor_obj)}")
            self.sensor_o2_var_var.set(self.selected_sensor_obj.o2_variance)
            self.sensor_co2_var_var.set(self.selected_sensor_obj.co2_variance)
            self.sensor_o2_var_label.config(text=f"{self.selected_sensor_obj.o2_variance:.2f}")
            self.sensor_co2_var_label.config(text=f"{self.selected_sensor_obj.co2_variance:.1f}")
            o2_read = self.selected_sensor_obj.last_o2_reading
            co2_read = self.selected_sensor_obj.last_co2_reading
            self.sensor_o2_reading_label.config(text=f"O2 Reading: {o2_read:.2f}%" if o2_read is not None else "O2 Reading: N/A")
            self.sensor_co2_reading_label.config(text=f"CO2 Reading: {co2_read:.0f} ppm" if co2_read is not None else "CO2 Reading: N/A")

    def _sim_to_canvas_coords_center(self, sim_row, sim_col):
        return AXIS_MARGIN + sim_col*CELL_SIZE + CELL_SIZE/2, AXIS_MARGIN + sim_row*CELL_SIZE + CELL_SIZE/2

    def handle_escape_key(self, event=None):
        if self.sim_running:
            self.sim_status_label_var.set("Sim Running. Editing locked. Press 'Clear Sim' to unlock.")
            return

        if self.current_mode == "add_door" and self.temp_door_room1_id is not None:
            self.temp_door_room1_id = None # Cancel door placement
            self.sim_status_label_var.set("Door placement cancelled. Select first room for door.")
            self.mode_var.set("select"); self.set_current_mode() # Revert to select
            return

        if self.current_mode not in ["select", "rectangle", "circle", "add_sensor", "add_door"]: # If in a drawing mode
            self.mode_var.set("select"); self.set_current_mode()
        elif self.selected_room_obj:
            self.selected_room_obj.deselect(self.drawing_canvas); self.selected_room_obj = None
        elif self.selected_sensor_obj:
            self.selected_sensor_obj.deselect(self.drawing_canvas); self.selected_sensor_obj = None
        elif self.selected_door_obj:
            # Doors don't have a separate select/deselect visual state other than toggle
            self.selected_door_obj = None 
        self._show_element_params_frame()


    def update_union_area_display(self):
        if not SHAPELY_AVAILABLE: self.union_area_label_var.set(f"Total Room Area: (Shapely N/A)"); return
        if not self.rooms_list: self.union_area_label_var.set("Total Room Area: 0.00 units²"); return
        
        total_pixel_area = 0
        for room in self.rooms_list:
            total_pixel_area += room.calculate_area_pixels()
        
        # Convert pixel area to m^2, assuming CELL_SIZE is pixels per meter
        # This is a rough estimate.
        area_m2 = total_pixel_area / (CELL_SIZE**2) if CELL_SIZE > 0 else 0
        self.union_area_label_var.set(f"Total Room Area: {area_m2:.2f} m² (approx)")


    def set_current_mode(self):
        old_mode = self.current_mode
        self.current_mode = self.mode_var.get()

        if self.sim_running and self.current_mode != "select":
            self.mode_var.set("select")
            self.current_mode = "select"
            self.sim_status_label_var.set("Sim Running. Editing locked. Mode forced to Select.")

        if old_mode == "select": # Deselect if switching away from select mode
            if self.selected_room_obj and self.current_mode != "select":
                self.selected_room_obj.deselect(self.drawing_canvas); self.selected_room_obj = None
            if self.selected_sensor_obj and self.current_mode != "select":
                self.selected_sensor_obj.deselect(self.drawing_canvas); self.selected_sensor_obj = None
            self._show_element_params_frame()
        
        if self.current_mode == "add_door":
            self.temp_door_room1_id = None
            self.sim_status_label_var.set("Door Mode: Click first room for door.")
        elif old_mode == "add_door" and self.temp_door_room1_id is not None: # Cancel pending door
            self.temp_door_room1_id = None
            self.sim_status_label_var.set("Door placement cancelled.")


        self.is_dragging = False; self.was_resizing_session = False; self.drag_action_occurred = False

    def draw_visual_grid_and_axes(self):
        self.drawing_canvas.delete("grid", "axis_label", "grid_axis_line")
        self.drawing_canvas.create_line(AXIS_MARGIN, AXIS_MARGIN, CANVAS_WIDTH - CELL_SIZE, AXIS_MARGIN, fill=AXIS_LINE_COLOR, width=1, tags="grid_axis_line")
        self.drawing_canvas.create_line(AXIS_MARGIN, AXIS_MARGIN, AXIS_MARGIN, CANVAS_HEIGHT - CELL_SIZE, fill=AXIS_LINE_COLOR, width=1, tags="grid_axis_line")
        for x_coord in range(AXIS_MARGIN,CANVAS_WIDTH-CELL_SIZE+1,CELL_SIZE):
            # Grid lines (optional, can be very dense)
            # self.drawing_canvas.create_line(x, AXIS_MARGIN, x, CANVAS_HEIGHT - CELL_SIZE, fill=GRID_COLOR, tags="grid")
            if (x_coord-AXIS_MARGIN)%LABEL_INTERVAL==0: self.drawing_canvas.create_text(x_coord,AXIS_MARGIN-10,text=str(x_coord-AXIS_MARGIN),anchor=tk.S,font=LABEL_FONT,fill=LABEL_COLOR,tags="axis_label")
        for y_coord in range(AXIS_MARGIN,CANVAS_HEIGHT-CELL_SIZE+1,CELL_SIZE):
            # self.drawing_canvas.create_line(AXIS_MARGIN, y, CANVAS_WIDTH - CELL_SIZE, y, fill=GRID_COLOR, tags="grid")
            if (y_coord-AXIS_MARGIN)%LABEL_INTERVAL==0: self.drawing_canvas.create_text(AXIS_MARGIN-10,y_coord,text=str(y_coord-AXIS_MARGIN),anchor=tk.E,font=LABEL_FONT,fill=LABEL_COLOR,tags="axis_label")
        # self.drawing_canvas.tag_lower("grid")
        self.drawing_canvas.tag_lower("grid_axis_line")
        self.drawing_canvas.tag_lower("axis_label")
        self.drawing_canvas.tag_raise("user_shape")
        self.drawing_canvas.tag_raise("door")
        self.drawing_canvas.tag_raise("sensor_marker")


    def _canvas_to_sim_coords(self, canvas_x, canvas_y):
        if canvas_x < AXIS_MARGIN or canvas_y < AXIS_MARGIN: return None, None
        col = int((canvas_x - AXIS_MARGIN) // CELL_SIZE)
        row = int((canvas_y - AXIS_MARGIN) // CELL_SIZE)
        if 0 <= row < self.sim_grid_rows and 0 <= col < self.sim_grid_cols: return row, col
        return None, None

    def _sim_to_canvas_coords(self, sim_row, sim_col): # Top-left of cell
        return AXIS_MARGIN + sim_col * CELL_SIZE, AXIS_MARGIN + sim_row * CELL_SIZE

    def handle_mouse_down(self, event):
        eff_x = self.drawing_canvas.canvasx(event.x)
        eff_y = self.drawing_canvas.canvasy(event.y)

        if self.sim_running:
            self.sim_status_label_var.set("Sim Running. Editing locked. Press 'Clear Sim' to unlock.")
            # Allow door toggling even if sim is running
            if self.current_mode == "select":
                for door in reversed(self.doors_list):
                    if door.contains_point(eff_x, eff_y):
                        door.toggle_state(self.drawing_canvas)
                        self.sim_status_label_var.set(f"Door {door.id} toggled. Sim running.")
                        return
            return

        if self.current_mode == "add_sensor": self.handle_add_sensor_click(eff_x, eff_y); return
        if self.current_mode == "add_door": self.handle_add_door_click(eff_x, eff_y); return


        self.is_dragging = True; self.was_resizing_session = False; self.drag_action_occurred = False
        
        if self.current_mode == "select":
            clicked_item = None
            # Priority: Sensor > Door > Room
            if self.selected_sensor_obj and self.selected_sensor_obj.contains_point(eff_x, eff_y): clicked_item = self.selected_sensor_obj
            else:
                for sensor_obj in reversed(self.sensors_list):
                    if sensor_obj.contains_point(eff_x, eff_y): clicked_item = sensor_obj; break
            
            if not clicked_item:
                for door_obj in reversed(self.doors_list):
                    if door_obj.contains_point(eff_x, eff_y): clicked_item = door_obj; break

            if not clicked_item:
                if self.selected_room_obj and self.selected_room_obj.contains_point(eff_x, eff_y): clicked_item = self.selected_room_obj
                else:
                    for room_obj in reversed(self.rooms_list):
                        if room_obj.contains_point(eff_x, eff_y): clicked_item = room_obj; break
            
            # Deselect previous items
            if self.selected_room_obj and self.selected_room_obj != clicked_item:
                self.selected_room_obj.deselect(self.drawing_canvas); self.selected_room_obj = None
            if self.selected_sensor_obj and self.selected_sensor_obj != clicked_item:
                self.selected_sensor_obj.deselect(self.drawing_canvas); self.selected_sensor_obj = None
            # Doors don't have a visual "selected" state beyond their open/close color
            if self.selected_door_obj and self.selected_door_obj != clicked_item:
                 self.selected_door_obj = None


            if isinstance(clicked_item, Sensor):
                self.selected_sensor_obj = clicked_item
                self.selected_sensor_obj.select(self.drawing_canvas)
                self.drag_offset_x = eff_x - self.selected_sensor_obj.x
                self.drag_offset_y = eff_y - self.selected_sensor_obj.y
            elif isinstance(clicked_item, RoomShape):
                self.selected_room_obj = clicked_item
                self.selected_room_obj.select(self.drawing_canvas)
                self.drag_offset_x = eff_x - self.selected_room_obj.x
                self.drag_offset_y = eff_y - self.selected_room_obj.y
            elif isinstance(clicked_item, Door):
                self.selected_door_obj = clicked_item
                clicked_item.toggle_state(self.drawing_canvas) # Toggle on click
                self.sim_status_label_var.set(f"Door {clicked_item.id} toggled.")
                self.is_dragging = False # Don't drag doors
            else: # Clicked on empty space
                self.drag_offset_x = 0; self.drag_offset_y = 0
            
            self._show_element_params_frame()

        elif self.current_mode == "rectangle": self.add_new_room(RoomRectangle(eff_x, eff_y, CELL_SIZE * 4, CELL_SIZE * 3, RoomType.LIVING_QUARTERS))
        elif self.current_mode == "circle": self.add_new_room(RoomCircle(eff_x, eff_y, CELL_SIZE * 2, RoomType.LABORATORY))

    def add_new_room(self, room_obj):
        if self.sim_running:
            self.sim_status_label_var.set("Cannot add rooms while sim is running.")
            return

        room_obj.draw(self.drawing_canvas)
        self.rooms_list.append(room_obj)
        if self.selected_room_obj: self.selected_room_obj.deselect(self.drawing_canvas)
        if self.selected_sensor_obj: self.selected_sensor_obj.deselect(self.drawing_canvas); self.selected_sensor_obj = None
        
        self.selected_room_obj = room_obj
        self.selected_room_obj.select(self.drawing_canvas)
        self._show_element_params_frame()
        self.mode_var.set("select"); self.set_current_mode()
        self.update_union_area_display()
        self.prepare_visualization_map_and_fields() # Update map mask and fields

    def handle_add_sensor_click(self, canvas_x, canvas_y):
        if self.sim_running:
            self.sim_status_label_var.set("Cannot add sensors while sim is running.")
            return

        new_sensor = Sensor(canvas_x, canvas_y)
        new_sensor.draw(self.drawing_canvas)
        self.sensors_list.append(new_sensor)
        self.sim_status_label_var.set(f"Sensor S{self.sensors_list.index(new_sensor)} added. Total: {len(self.sensors_list)}. Re-init sim if running.")
        
        if self.selected_sensor_obj: self.selected_sensor_obj.deselect(self.drawing_canvas)
        if self.selected_room_obj: self.selected_room_obj.deselect(self.drawing_canvas); self.selected_room_obj = None
        
        self.selected_sensor_obj = new_sensor
        self.selected_sensor_obj.select(self.drawing_canvas)
        self._show_element_params_frame()
        self.mode_var.set("select"); self.set_current_mode()

    def handle_add_door_click(self, canvas_x, canvas_y):
        if self.sim_running:
            self.sim_status_label_var.set("Cannot add doors while sim is running.")
            return

        clicked_room = None
        for room in self.rooms_list:
            if room.contains_point(canvas_x, canvas_y):
                clicked_room = room
                break
        
        if not clicked_room:
            self.sim_status_label_var.set("Door Mode: Click inside a room.")
            return

        if self.temp_door_room1_id is None:
            self.temp_door_room1_id = clicked_room.id
            self.sim_status_label_var.set(f"Door Mode: First room R{clicked_room.id} selected. Click second room (or same room for external).")
        else:
            room1_id = self.temp_door_room1_id
            room2_id = clicked_room.id # Could be same as room1_id for an "external" door concept

            if room1_id == room2_id:
                # For simplicity, let's assume external doors are not explicitly linked to "Mars" object
                # but are just doors on a single room. The logic for exchange would treat room2 as Mars.
                # Or, require two distinct rooms for now.
                # For now, let's make it simpler: a door needs two distinct points or edges.
                # This click-based placement is very basic.
                # A better way would be to click on edges.
                # For now, place door at click location, associated with room1 and room2.
                pass # Allow door on same room, implies external if logic handles it.

            # Create door at the click position (eff_x, eff_y)
            # This position might not be on the border, which is a simplification.
            new_door = Door(room1_id, room2_id, (canvas_x, canvas_y), self)
            new_door.draw(self.drawing_canvas)
            self.doors_list.append(new_door)
            
            # Link door to rooms
            room1_obj = self.get_room_by_id(room1_id)
            room2_obj = self.get_room_by_id(room2_id)
            if room1_obj: room1_obj.connected_doors.append(new_door)
            if room2_obj and room1_obj != room2_obj : room2_obj.connected_doors.append(new_door)


            self.sim_status_label_var.set(f"Door D{new_door.id} added between R{room1_id} and R{room2_id}.")
            self.temp_door_room1_id = None
            self.mode_var.set("select"); self.set_current_mode()


    def handle_mouse_drag(self, event):
        if self.sim_running: return
        if not self.is_dragging or self.current_mode != "select": return
        
        selected_item = self.selected_room_obj if self.selected_room_obj else self.selected_sensor_obj
        if not selected_item: return
        
        self.drag_action_occurred = True
        eff_x = self.drawing_canvas.canvasx(event.x); eff_y = self.drawing_canvas.canvasy(event.y)

        if isinstance(selected_item, RoomShape):
            is_shift = (event.state & 0x0001) != 0 # Shift key for resize
            if is_shift:
                self.was_resizing_session = True
                selected_item.resize(self.drawing_canvas, eff_x, eff_y)
            else:
                selected_item.move_to(self.drawing_canvas, eff_x - self.drag_offset_x, eff_y - self.drag_offset_y)
        elif isinstance(selected_item, Sensor):
            selected_item.move_to(self.drawing_canvas, eff_x - self.drag_offset_x, eff_y - self.drag_offset_y)

    def handle_mouse_up(self, event):
        if self.sim_running: return

        if self.is_dragging and self.drag_action_occurred:
            if self.selected_room_obj:
                self.selected_room_obj.update_coords_from_canvas(self.drawing_canvas)
                self.update_union_area_display()
                self.prepare_visualization_map_and_fields() # Remask and update fields
                self.sim_status_label_var.set("Room moved/resized. Re-init sim if running.")
            elif self.selected_sensor_obj:
                self.sim_status_label_var.set("Sensor moved. Re-init sim if running.")
        
        self.is_dragging = False; self.was_resizing_session = False; self.drag_action_occurred = False

    def delete_selected_item(self):
        if self.sim_running:
            self.sim_status_label_var.set("Cannot delete while sim is running.")
            return

        item_deleted_msg = ""
        if self.selected_room_obj:
            self.drawing_canvas.delete(self.selected_room_obj.canvas_item_id)
            # Remove associated doors
            doors_to_remove = [d for d in self.doors_list if d.room1_id == self.selected_room_obj.id or d.room2_id == self.selected_room_obj.id]
            for door in doors_to_remove:
                if door.canvas_item_id: self.drawing_canvas.delete(door.canvas_item_id)
                if door in self.doors_list: self.doors_list.remove(door)
                # Also remove from other room's connected_doors list
                r1, r2 = door.get_connected_rooms()
                if r1 and r1 != self.selected_room_obj and door in r1.connected_doors: r1.connected_doors.remove(door)
                if r2 and r2 != self.selected_room_obj and door in r2.connected_doors: r2.connected_doors.remove(door)

            if self.selected_room_obj in self.rooms_list: self.rooms_list.remove(self.selected_room_obj)
            self.selected_room_obj = None
            self.update_union_area_display()
            self.prepare_visualization_map_and_fields()
            item_deleted_msg = "Room and associated doors deleted."
        elif self.selected_sensor_obj:
            self.drawing_canvas.delete(self.selected_sensor_obj.canvas_item_id)
            if self.selected_sensor_obj in self.sensors_list: self.sensors_list.remove(self.selected_sensor_obj)
            self.selected_sensor_obj = None
            item_deleted_msg = "Sensor deleted. Re-init sim if running."
        elif self.selected_door_obj: # Though doors are not "selected" in the same way
            # This path might not be hit if selection clears selected_door_obj
            # Let's assume delete works on last clicked/toggled door if no room/sensor selected
            door_to_delete = self.selected_door_obj # Or find by some other means
            if door_to_delete:
                 if door_to_delete.canvas_item_id: self.drawing_canvas.delete(door_to_delete.canvas_item_id)
                 if door_to_delete in self.doors_list: self.doors_list.remove(door_to_delete)
                 r1, r2 = door_to_delete.get_connected_rooms()
                 if r1 and door_to_delete in r1.connected_doors: r1.connected_doors.remove(door_to_delete)
                 if r2 and door_to_delete in r2.connected_doors: r2.connected_doors.remove(door_to_delete)
                 self.selected_door_obj = None
                 item_deleted_msg = f"Door D{door_to_delete.id} deleted."


        if item_deleted_msg: self.sim_status_label_var.set(item_deleted_msg)
        self._show_element_params_frame()

    def clear_all_sensors(self):
        if self.sim_running:
            self.sim_status_label_var.set("Cannot clear sensors while sim is running.")
            return
        for sensor_obj in self.sensors_list:
            self.drawing_canvas.delete(sensor_obj.canvas_item_id)
        self.sensors_list.clear()
        if self.selected_sensor_obj: self.selected_sensor_obj = None
        self._show_element_params_frame()
        self.sim_status_label_var.set(f"All sensors cleared. Re-init sim if needed.")

    def clear_all_doors(self):
        if self.sim_running:
            self.sim_status_label_var.set("Cannot clear doors while sim is running.")
            return
        for door_obj in self.doors_list:
            if door_obj.canvas_item_id: self.drawing_canvas.delete(door_obj.canvas_item_id)
            r1,r2 = door_obj.get_connected_rooms()
            if r1 and door_obj in r1.connected_doors: r1.connected_doors.remove(door_obj)
            if r2 and door_obj in r2.connected_doors: r2.connected_doors.remove(door_obj)
        self.doors_list.clear()
        if self.selected_door_obj: self.selected_door_obj = None # Should not be selected this way
        self.sim_status_label_var.set(f"All doors cleared.")


    def initialize_gas_fields(self):
        """Initializes gas fields based on rooms and Mars environment."""
        self.o2_field_ground_truth.fill(MARS_O2_PERCENTAGE)
        self.co2_field_ground_truth.fill(MARS_CO2_PPM)

        for room in self.rooms_list:
            room.o2_level = NORMAL_O2_PERCENTAGE # Reset room internal state
            room.co2_level = NORMAL_CO2_PPM
            # Apply these initial room values to the ground truth grid
            for r_idx in range(self.sim_grid_rows):
                for c_idx in range(self.sim_grid_cols):
                    # Check center of the grid cell
                    cx_c, cy_c = self._sim_to_canvas_coords_center(r_idx, c_idx)
                    if room.contains_point(cx_c, cy_c):
                        self.o2_field_ground_truth[r_idx, c_idx] = room.o2_level
                        self.co2_field_ground_truth[r_idx, c_idx] = room.co2_level
        
        # Also update the map mask
        self.update_map_mask()


    def update_map_mask(self):
        self.map_mask.fill(0)
        for r_idx in range(self.sim_grid_rows):
            for c_idx in range(self.sim_grid_cols):
                cx_c, cy_c = self._sim_to_canvas_coords_center(r_idx, c_idx)
                for room_obj in self.rooms_list:
                    if room_obj.contains_point(cx_c, cy_c):
                        self.map_mask[r_idx, c_idx] = 1 # Mark as inside a room
                        break # Move to next cell

    def prepare_visualization_map_and_fields(self):
        """Prepares map mask, clears/creates vis cells, and re-initializes gas fields if no sim running."""
        self.update_map_mask() # Update self.map_mask based on current room_list

        if not self.sim_running: # If sim not running, reset field values based on rooms
            self.initialize_gas_fields()

        # Clear existing visualization cells for the heatmap
        for item_id in self.field_vis_cells.values():
            self.drawing_canvas.delete(item_id)
        self.field_vis_cells.clear()

        # Create new visualization cells for ALL grid cells (color will be based on mask)
        for r in range(self.sim_grid_rows):
            for c in range(self.sim_grid_cols):
                x0, y0 = self._sim_to_canvas_coords(r, c)
                # Heatmap cells are for gp_reconstructed_field or ground truth
                vis_id = self.drawing_canvas.create_rectangle(
                    x0, y0, x0 + CELL_SIZE, y0 + CELL_SIZE,
                    fill="", outline="", tags="gp_field_cell" # outline="" for no grid lines from cells
                )
                self.field_vis_cells[(r, c)] = vis_id
        self.drawing_canvas.tag_lower("gp_field_cell") # Ensure they are behind shapes/sensors
        self.draw_visual_grid_and_axes() # Redraw axes on top of cells but below shapes
        
        # Redraw all rooms and sensors to ensure they are on top of heatmap cells
        for room in self.rooms_list: room.draw(self.drawing_canvas)
        for sensor in self.sensors_list: sensor.draw(self.drawing_canvas)
        for door in self.doors_list: door.draw(self.drawing_canvas)


    def _on_gas_view_change(self):
        # This will trigger a redraw of field and color scale in the next sim step or toggle
        if self.sim_running:
            self.update_gp_model_and_predict() # Force update if sim running
            self.draw_field_visualization()
            self.draw_color_scale()
        else: # If sim not running, just update display based on current ground truth
            self.update_gp_model_and_predict() # Update to show correct ground truth / GP if sensors exist
            self.draw_field_visualization()
            self.draw_color_scale()
        self.sim_status_label_var.set(f"View changed to {self.current_gas_view.get()}.")


    def collect_sensor_data_for_gp(self):
        sensor_coords_X = []
        sensor_readings_y = [] # This will be O2 or CO2 based on current_gas_view

        active_gas_field = self.o2_field_ground_truth if self.current_gas_view.get() == "O2" else self.co2_field_ground_truth

        for sensor_obj in self.sensors_list:
            sensor_grid_r, sensor_grid_c = self._canvas_to_sim_coords(sensor_obj.x, sensor_obj.y)

            true_value_at_sensor = MARS_O2_PERCENTAGE if self.current_gas_view.get() == "O2" else MARS_CO2_PPM # Default to Mars
            
            # Determine if sensor is in a room
            sensor_in_room = False
            for room in self.rooms_list:
                if room.contains_point(sensor_obj.x, sensor_obj.y):
                    true_value_at_sensor = room.o2_level if self.current_gas_view.get() == "O2" else room.co2_level
                    sensor_in_room = True
                    break
            
            # If not in any room, it's reading Mars environment from the grid cell it's in (if any)
            if not sensor_in_room and sensor_grid_r is not None and sensor_grid_c is not None:
                 true_value_at_sensor = active_gas_field[sensor_grid_r, sensor_grid_c]


            # Simulate sensor reading with noise
            reading_variance = sensor_obj.o2_variance if self.current_gas_view.get() == "O2" else sensor_obj.co2_variance
            noisy_reading = max(0, np.random.normal(true_value_at_sensor, math.sqrt(reading_variance)))

            sensor_coords_X.append([sensor_obj.x, sensor_obj.y])
            sensor_readings_y.append(noisy_reading)
            
            # Update sensor's last reading display values (always do both O2 and CO2 for display)
            # This part is slightly off as it uses the current gas view's true value for both.
            # For accurate display, sensor should "know" both true values.
            # Let's fix this:
            true_o2_val_for_sensor = MARS_O2_PERCENTAGE
            true_co2_val_for_sensor = MARS_CO2_PPM
            s_in_room_obj = None
            for r_obj in self.rooms_list:
                if r_obj.contains_point(sensor_obj.x, sensor_obj.y):
                    s_in_room_obj = r_obj
                    break
            if s_in_room_obj:
                true_o2_val_for_sensor = s_in_room_obj.o2_level
                true_co2_val_for_sensor = s_in_room_obj.co2_level
            elif sensor_grid_r is not None and sensor_grid_c is not None: # Mars from grid
                true_o2_val_for_sensor = self.o2_field_ground_truth[sensor_grid_r, sensor_grid_c]
                true_co2_val_for_sensor = self.co2_field_ground_truth[sensor_grid_r, sensor_grid_c]

            sensor_obj.read_gas_levels(true_o2_val_for_sensor, true_co2_val_for_sensor)


        return np.array(sensor_coords_X), np.array(sensor_readings_y)


    def update_gp_model_and_predict(self):
        fallback_to_truth = False
        status_suffix = f" (GP for {self.current_gas_view.get()})"
        current_gp_model = self.gp_model_o2 if self.current_gas_view.get() == "O2" else self.gp_model_co2
        active_ground_truth_field = self.o2_field_ground_truth if self.current_gas_view.get() == "O2" else self.co2_field_ground_truth
        default_max_val = NORMAL_O2_PERCENTAGE if self.current_gas_view.get() == "O2" else (NORMAL_CO2_PPM * 5) # Higher range for CO2 display

        if not SKLEARN_AVAILABLE or current_gp_model is None:
            fallback_to_truth = True
            status_suffix = f" (No Sklearn - Showing Truth for {self.current_gas_view.get()})"
        elif not self.sensors_list:
            fallback_to_truth = True
            status_suffix = f" (No Sensors - Showing Truth for {self.current_gas_view.get()})"

        if fallback_to_truth:
            self.gp_reconstructed_field = active_ground_truth_field.copy()
        else:
            sensor_X, sensor_y = self.collect_sensor_data_for_gp() # sensor_y is for current_gas_view
            if sensor_X.shape[0] > 0 and sensor_y.shape[0] > 0 and sensor_X.shape[0] == sensor_y.shape[0]:
                try:
                    current_gp_model.fit(sensor_X, sensor_y)
                    predicted_flat = current_gp_model.predict(self.XY_gp_prediction_grid)
                    self.gp_reconstructed_field = predicted_flat.reshape((self.sim_grid_rows, self.sim_grid_cols))
                    # Clipping based on gas type
                    min_clip = 0
                    max_clip = (NORMAL_O2_PERCENTAGE * 1.5) if self.current_gas_view.get() == "O2" else (MARS_CO2_PPM * 1.1) # Allow higher than Mars CO2
                    np.clip(self.gp_reconstructed_field, min_clip, max_clip, out=self.gp_reconstructed_field)
                except Exception as e:
                    print(f"Error during GP fitting/prediction for {self.current_gas_view.get()}: {e}")
                    self.gp_reconstructed_field = active_ground_truth_field.copy()
                    status_suffix = f" (GP Error - Showing Truth for {self.current_gas_view.get()})"
            else: # No valid sensor data for GP
                self.gp_reconstructed_field = active_ground_truth_field.copy()
                status_suffix = f" (No Sensor Data for GP - Showing Truth for {self.current_gas_view.get()})"
        
        if self.sim_running: self.sim_status_label_var.set("Sim Running." + status_suffix)
        else: self.sim_status_label_var.set("Sim Stopped." + status_suffix)


        # Update display scale for GP inferred field (or ground truth if fallback)
        # Consider only cells within rooms for min/max, or all cells?
        # For now, use all cells of the reconstructed field.
        active_gp_cells = self.gp_reconstructed_field # Use the whole field for scaling
        if active_gp_cells.size > 0:
            self.current_gp_display_min = np.min(active_gp_cells)
            self.current_gp_display_max = np.max(active_gp_cells)
        else:
            self.current_gp_display_min = 0.0
            self.current_gp_display_max = default_max_val
        
        if self.current_gp_display_max <= self.current_gp_display_min:
            val = self.current_gp_display_min
            self.current_gp_display_min = max(0, val - 0.5 * abs(val) - 0.1)
            self.current_gp_display_max = val + 0.5 * abs(val) + 0.1
            if abs(self.current_gp_display_max - self.current_gp_display_min) < 1e-2 : # Adjusted for larger CO2 ppm values
                 self.current_gp_display_max = self.current_gp_display_min + (1.0 if self.current_gas_view.get() == "O2" else 100.0)
        
        self.field_scale_label_var.set(f"GP Scale ({self.current_gas_view.get()}): {self.current_gp_display_min:.1f}-{self.current_gp_display_max:.1f}")


    def get_color_from_value(self, value, min_val, max_val):
        norm = mcolors.Normalize(vmin=min_val, vmax=max_val)
        # Use different colormaps for O2 and CO2 for better visual distinction if desired
        cmap_name = 'coolwarm' # Default
        if self.current_gas_view.get() == "O2":
            cmap_name = 'RdYlGn' # Red-Yellow-Green for O2 (Low-Mid-High)
        elif self.current_gas_view.get() == "CO2":
            cmap_name = 'YlOrRd' # Yellow-Orange-Red for CO2 (Low-Mid-High danger)
        
        try:
            cmap = cm.get_cmap(cmap_name)
            rgba = cmap(norm(value))
            return mcolors.to_hex(rgba) # Use to_hex for simplicity
        except Exception as e:
            print(f"Error getting color: {e}, value: {value}, min: {min_val}, max: {max_val}")
            return "#FFFFFF" # Default to white on error


    def draw_color_scale(self):
        self.color_scale_canvas.delete("all")
        min_val = self.current_gp_display_min
        max_val = self.current_gp_display_max
        
        if abs(max_val - min_val) < 1e-6: # Handle case where min and max are virtually the same
            if abs(max_val) < 1e-6: # Both are near zero
                 max_val = min_val + (1.0 if self.current_gas_view.get() == "O2" else 100.0)
            else: # Shift slightly to create a range
                max_val = min_val * 1.1 if min_val > 0 else min_val * 0.9
                min_val = min_val * 0.9 if min_val > 0 else min_val * 1.1
                if abs(max_val-min_val) < 1e-6: max_val = min_val + (1.0 if self.current_gas_view.get() == "O2" else 100.0)


        range_val = max_val - min_val
        if abs(range_val) < 1e-6: range_val = (1.0 if self.current_gas_view.get() == "O2" else 100.0)


        num_segments = 50
        segment_height = (CANVAS_HEIGHT - 2 * AXIS_MARGIN) / num_segments
        gradient_bar_width = 20
        x_offset = 15 # Adjusted for wider scale canvas
        
        for i in range(num_segments):
            # For RdYlGn (O2), high values are at the top of the scale visually
            # For YlOrRd (CO2), high values are also at the top (more red)
            # The loop goes from bottom (i=0) to top.
            # So, val should go from min_val to max_val as i increases.
            val_at_segment_bottom = min_val + (i / num_segments) * range_val
            color = self.get_color_from_value(val_at_segment_bottom, min_val, max_val)
            
            y0 = AXIS_MARGIN + (num_segments - 1 - i) * segment_height # Draw from top down
            y1 = AXIS_MARGIN + (num_segments - i) * segment_height

            self.color_scale_canvas.create_rectangle(x_offset, y0, x_offset + gradient_bar_width, y1, fill=color, outline=color)

        label_x = x_offset + gradient_bar_width + 7
        # Top label (max_val)
        self.color_scale_canvas.create_text(label_x, AXIS_MARGIN, text=f"{max_val:.1f}", anchor=tk.NW, font=LABEL_FONT, fill=LABEL_COLOR)
        # Bottom label (min_val)
        self.color_scale_canvas.create_text(label_x, CANVAS_HEIGHT - AXIS_MARGIN, text=f"{min_val:.1f}", anchor=tk.SW, font=LABEL_FONT, fill=LABEL_COLOR)
        
        mid_val = min_val + range_val / 2
        mid_y = AXIS_MARGIN + (CANVAS_HEIGHT - 2 * AXIS_MARGIN) / 2
        self.color_scale_canvas.create_text(label_x, mid_y, text=f"{mid_val:.1f}", anchor=tk.W, font=LABEL_FONT, fill=LABEL_COLOR)
        
        gas_unit = "%" if self.current_gas_view.get() == "O2" else "ppm"
        self.color_scale_canvas.create_text(COLOR_SCALE_WIDTH/2, AXIS_MARGIN/2, text=f"GP {self.current_gas_view.get()} ({gas_unit})", anchor=tk.CENTER, font=LABEL_FONT, fill=LABEL_COLOR)


    def toggle_simulation(self):
        if self.sim_running: # "Clear Sim"
            self.sim_running = False
            if self.sim_job_id: self.root.after_cancel(self.sim_job_id); self.sim_job_id = None
            
            # Don't clear GP field, let it show last state or re-predict based on static truth
            self.update_gp_model_and_predict() # Update GP based on current (static) ground truth
            self.draw_field_visualization() # Redraw based on (now static) GP or truth
            self.draw_color_scale()
            
            self.sim_toggle_button.config(text="Initialize & Run Sim")
            self.sim_status_label_var.set("Sim Cleared. Editing enabled.")
            for child in self.drawing_controls_frame.winfo_children():
                if isinstance(child, ttk.Radiobutton) or isinstance(child, ttk.Button):
                    child.config(state=tk.NORMAL)
            # Enable parameter editing
            if self.selected_room_obj: self._show_element_params_frame() # Re-enable scales
            if self.selected_sensor_obj: self._show_element_params_frame()

        else: # "Initialize & Run Sim"
            if not self.rooms_list: self.sim_status_label_var.set("Draw rooms first!"); return
            if not SKLEARN_AVAILABLE: self.sim_status_label_var.set("Scikit-learn missing! GP Reconstruction disabled."); return
            
            self.sim_running = True
            self.prepare_visualization_map_and_fields() # This calls initialize_gas_fields
            self.gp_update_counter = 0
            
            self.update_gp_model_and_predict() # Initial GP prediction
            self.draw_field_visualization()
            self.draw_color_scale()
            
            self.sim_toggle_button.config(text="Clear Sim")
            # Status is set within update_gp_model_and_predict
            
            self.mode_var.set("select") # Force select mode
            for child in self.drawing_controls_frame.winfo_children():
                if isinstance(child, ttk.Radiobutton) and child.cget("value") != "select":
                    child.config(state=tk.DISABLED)
                elif isinstance(child, ttk.Button): # Disable delete etc.
                     child.config(state=tk.DISABLED)
            # Disable parameter editing
            if self.room_params_frame.winfo_ismapped():
                for child in self.room_params_frame.winfo_children():
                    if isinstance(child, (ttk.Scale, ttk.Spinbox, ttk.OptionMenu)): child.config(state=tk.DISABLED)
            if self.sensor_params_frame.winfo_ismapped():
                 for child in self.sensor_params_frame.winfo_children():
                    if isinstance(child, ttk.Scale): child.config(state=tk.DISABLED)


            if not self.sim_job_id: self.run_simulation_step()


    def draw_field_visualization(self): # Draws gp_reconstructed_field or ground_truth
        min_val = self.current_gp_display_min; max_val = self.current_gp_display_max
        
        # Determine which field to use for "truth" if GP is off or no sensors
        display_field = self.gp_reconstructed_field # This is already set by update_gp_model_and_predict

        for r_idx in range(self.sim_grid_rows):
            for c_idx in range(self.sim_grid_cols):
                cell_id = self.field_vis_cells.get((r_idx,c_idx))
                if cell_id:
                    # If cell is outside any room (mask=0), color it as Mars (or a default dim color)
                    # If sim is running, or if we always want to show the GP/truth field:
                    if self.map_mask[r_idx, c_idx] == 1: # Inside a room
                        concentration = display_field[r_idx, c_idx]
                        color = self.get_color_from_value(concentration, min_val, max_val)
                        self.drawing_canvas.itemconfig(cell_id, fill=color, outline=color)
                    else: # Outside all rooms (Mars)
                        # Use a fixed color for Mars, or sample the field there too
                        mars_val = MARS_O2_PERCENTAGE if self.current_gas_view.get() == "O2" else MARS_CO2_PPM
                        color = self.get_color_from_value(mars_val, min_val, max_val) # Color Mars based on scale
                        # Or a fixed dim color: color = "gray80"
                        self.drawing_canvas.itemconfig(cell_id, fill=color, outline=color) # Use outline for subtle grid
                        
        # Ensure rooms, sensors, doors are drawn on top of the heatmap
        self.drawing_canvas.tag_raise("user_shape")
        self.drawing_canvas.tag_raise("door")
        self.drawing_canvas.tag_raise("sensor_marker")


    def run_simulation_step(self):
        if not self.sim_running:
            if self.sim_job_id: self.root.after_cancel(self.sim_job_id); self.sim_job_id = None
            return

        # --- 1. Update Gas Levels in Rooms (Internal Logic) ---
        for room in self.rooms_list:
            room_volume_liters = room.get_volume_liters()
            if room_volume_liters <= 0: continue

            # a. Human Respiration
            if room.population > 0:
                # O2 consumption (convert % to absolute liters, then back to %)
                # Total O2 in room (L) = (room.o2_level / 100) * room_volume_liters
                # O2 consumed (L/hr) = (HUMAN_O2_CONSUMPTION_PER_HOUR_PERSON / 100) * typical_person_breathing_volume_L_per_hour
                # This is complex. Simpler: change percentage directly, scaled by inverse volume or density.
                # Let's use the direct percentage change from better-sample, assuming it's for a nominal volume.
                # Scale effect by (NominalVolume / ActualVolume)
                # For now, assume constants are fine as direct % change.
                
                o2_consumed_percent = HUMAN_O2_CONSUMPTION_PER_HOUR_PERSON * room.population * SIM_DT_HOURS
                co2_produced_ppm = HUMAN_CO2_PRODUCTION_PPM_PER_HOUR_PERSON * room.population * SIM_DT_HOURS

                room.o2_level = max(0, room.o2_level - o2_consumed_percent)
                room.co2_level = max(0, room.co2_level + co2_produced_ppm)

            # b. Breach Effects (exchange with Mars)
            if room.breach_level > 0:
                # Flow rate proportional to breach_level and pressure difference (implicit in concentration diff)
                # Effective flow rate for this step
                breach_exchange_fraction = room.breach_level * DEFAULT_BREACH_FLOW_RATE_PER_HOUR * SIM_DT_HOURS
                
                o2_to_mars = (room.o2_level - MARS_O2_PERCENTAGE) * breach_exchange_fraction
                co2_to_mars = (room.co2_level - MARS_CO2_PPM) * breach_exchange_fraction

                room.o2_level -= o2_to_mars
                room.co2_level -= co2_to_mars
                room.o2_level = max(0, room.o2_level)
                room.co2_level = max(0, room.co2_level)
        
        # c. Door Exchange (between connected rooms)
        # This needs to be done carefully to ensure conservation if volumes are different.
        # For each door, calculate exchange and apply changes simultaneously or store deltas.
        # Simplified: iterate doors, exchange based on current levels.
        for door in self.doors_list:
            room1, room2 = door.get_connected_rooms()
            if not room1: continue # Should not happen if door is valid

            flow_rate_this_step = (DOOR_FLOW_RATE_OPEN_PER_HOUR if door.is_open else DOOR_FLOW_RATE_CLOSED_PER_HOUR) * SIM_DT_HOURS
            
            o2_target_room2 = MARS_O2_PERCENTAGE
            co2_target_room2 = MARS_CO2_PPM
            
            if room2: # Connected to another room
                o2_target_room2 = room2.o2_level
                co2_target_room2 = room2.co2_level
            # else: it's an external door, targets are Mars (already set)

            # Exchange for O2
            o2_diff = o2_target_room2 - room1.o2_level
            o2_flow_to_room1 = o2_diff * flow_rate_this_step # This is fractional change
            
            room1.o2_level += o2_flow_to_room1
            if room2:
                # Approximation: assume equal volume exchange effect for simplicity
                # A proper model would use partial pressures and volumes.
                room2.o2_level -= o2_flow_to_room1 
                room2.o2_level = max(0, room2.o2_level)
            room1.o2_level = max(0, room1.o2_level)

            # Exchange for CO2
            co2_diff = co2_target_room2 - room1.co2_level
            co2_flow_to_room1 = co2_diff * flow_rate_this_step
            
            room1.co2_level += co2_flow_to_room1
            if room2:
                room2.co2_level -= co2_flow_to_room1
                room2.co2_level = max(0, room2.co2_level)
            room1.co2_level = max(0, room1.co2_level)


        # --- 2. Update Ground Truth Grid from Room States ---
        # Fill with Mars values first
        self.o2_field_ground_truth.fill(MARS_O2_PERCENTAGE)
        self.co2_field_ground_truth.fill(MARS_CO2_PPM)
        # Then overlay room values
        for r_idx in range(self.sim_grid_rows):
            for c_idx in range(self.sim_grid_cols):
                if self.map_mask[r_idx, c_idx] == 1: # If cell is part of any room
                    # Find which room this cell belongs to (or average if overlapping, though not ideal)
                    # For simplicity, take the first room found containing the cell center
                    cx_c, cy_c = self._sim_to_canvas_coords_center(r_idx, c_idx)
                    for room in self.rooms_list:
                        if room.contains_point(cx_c, cy_c):
                            self.o2_field_ground_truth[r_idx, c_idx] = room.o2_level
                            self.co2_field_ground_truth[r_idx, c_idx] = room.co2_level
                            break # Found the room for this cell

        # --- 3. Update GP Model periodically ---
        self.gp_update_counter += 1
        if self.gp_update_counter >= GP_UPDATE_EVERY_N_FRAMES:
            self.update_gp_model_and_predict()
            self.gp_update_counter = 0
        elif not SKLEARN_AVAILABLE or not self.sensors_list: # If GP isn't active, ensure reconstructed field mirrors truth
             self.update_gp_model_and_predict() # This will handle the fallback

        # --- 4. Update UI Elements ---
        if self.selected_room_obj: # Update displayed params if a room is selected
            self.room_o2_label.config(text=f"O2: {self.selected_room_obj.o2_level:.2f}%")
            self.room_co2_label.config(text=f"CO2: {self.selected_room_obj.co2_level:.0f} ppm")
        if self.selected_sensor_obj: # Update displayed sensor readings
            o2_read = self.selected_sensor_obj.last_o2_reading
            co2_read = self.selected_sensor_obj.last_co2_reading
            self.sensor_o2_reading_label.config(text=f"O2 Reading: {o2_read:.2f}%" if o2_read is not None else "O2 Reading: N/A")
            self.sensor_co2_reading_label.config(text=f"CO2 Reading: {co2_read:.0f} ppm" if co2_read is not None else "CO2 Reading: N/A")


        # --- 5. Draw Visualization ---
        self.draw_field_visualization()
        self.draw_color_scale()
        
        self.sim_job_id = self.root.after(int(SIM_STEP_REAL_TIME_SECONDS * 1000), self.run_simulation_step)


if __name__ == "__main__":
    app_root = tk.Tk()
    if not SKLEARN_AVAILABLE:
        print("--- WARNING: Scikit-learn (sklearn) is NOT installed. ---")
        print("--- The Gaussian Process reconstruction will be disabled. ---")
        print("--- To enable it, please install scikit-learn: pip install scikit-learn ---")
    if not SHAPELY_AVAILABLE:
        print("--- WARNING: Shapely is NOT installed. ---")
        print("--- Area calculations and some geometric operations might be affected. ---")
        print("--- To enable it, please install Shapely: pip install shapely ---")
        
    drawing_app = DrawingApp(app_root)
    app_root.mainloop()
