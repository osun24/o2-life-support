import tkinter as tk
from tkinter import ttk, colorchooser, messagebox
import math
import numpy as np
import random
from enum import Enum, auto

# --- Attempt to import optional libraries ---
try:
    from shapely.geometry import Polygon, Point
    from shapely.ops import unary_union, transform
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False
    class Polygon: pass
    class Point: pass
    def unary_union(x): return None
    def transform(f,g): return None
    print("--- WARNING: Shapely is NOT installed. ---")
    print("--- Area calculations and some geometric operations might be affected. ---")
    print("--- Overlap prevention for different room types will be DISABLED. ---")
    print("--- To enable it, please install Shapely: pip install shapely ---")


try:
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    class GaussianProcessRegressor: pass
    class RBF: pass
    class WhiteKernel: pass
    class ConstantKernel: pass
    print("--- WARNING: Scikit-learn (sklearn) is NOT installed. ---")
    print("--- The Gaussian Process reconstruction will be disabled. ---")
    print("--- To enable it, please install scikit-learn: pip install scikit-learn ---")

import matplotlib.cm as cm
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.widgets import Slider as MplSlider, Button as MplButton


# --- Constants for Habitat Design Tab ---
NORMAL_O2_PERCENTAGE = 21.0
NORMAL_CO2_PPM = 400.0
MARS_O2_PERCENTAGE = 0.13
MARS_CO2_PERCENTAGE = 95.0
MARS_CO2_PPM = MARS_CO2_PERCENTAGE * 10000
HUMAN_O2_CONSUMPTION_PER_HOUR_PERSON = 0.035
HUMAN_CO2_PRODUCTION_PER_HOUR_PERSON = 0.042
HUMAN_CO2_PRODUCTION_PPM_PER_HOUR_PERSON = HUMAN_CO2_PRODUCTION_PER_HOUR_PERSON * 10000
SIM_STEP_REAL_TIME_SECONDS = 0.1
SIM_TIME_SCALE_FACTOR = 300.0  # INCREASE FOR FASTER SIMULATION
SIM_DT_HOURS = SIM_STEP_REAL_TIME_SECONDS * SIM_TIME_SCALE_FACTOR
CELL_SIZE = 10
AXIS_MARGIN = 30
CANVAS_WIDTH = AXIS_MARGIN + 800 + CELL_SIZE
CANVAS_HEIGHT = AXIS_MARGIN + 800 + CELL_SIZE
COLOR_SCALE_WIDTH = 80
COLOR_SCALE_PADDING = 10
GRID_COLOR = "lightgray"
AXIS_LINE_COLOR = "black"
LABEL_COLOR = "dim gray"
LABEL_FONT = ("Arial", 8)
LABEL_INTERVAL = CELL_SIZE * 5
DEFAULT_OUTLINE_COLOR = "black"
DEFAULT_OUTLINE_WIDTH = 1
SELECTED_OUTLINE_COLOR = "blue"
SELECTED_OUTLINE_WIDTH = 2
SENSOR_DRAW_RADIUS_PIXELS = CELL_SIZE * 0.40
SENSOR_DEFAULT_O2_VARIANCE = 0.5
SENSOR_DEFAULT_CO2_VARIANCE = 20.0
SENSOR_OUTLINE_COLOR = "red"
SENSOR_SELECTED_OUTLINE_COLOR = "magenta"
SENSOR_SELECTED_OUTLINE_WIDTH = 2
GP_UPDATE_EVERY_N_FRAMES = 3
SENSOR_READING_NOISE_STD_O2 = math.sqrt(SENSOR_DEFAULT_O2_VARIANCE) if SKLEARN_AVAILABLE else 0
SENSOR_READING_NOISE_STD_CO2 = math.sqrt(SENSOR_DEFAULT_CO2_VARIANCE) if SKLEARN_AVAILABLE else 0

# LEAKKKK
LEAK_DIFFUSION_COEFF = 10      # kg O₂ · m⁻² · h⁻¹  (tune as desired)
LEAK_MAX_RADIUS_PX   = CELL_SIZE * 4

class RoomType(Enum):
    LIVING_QUARTERS = auto()
    GREENHOUSE_POTATOES = auto()
    GREENHOUSE_ALGAE = auto()
    SOLAR_PANELS = auto() # New room type
    NONE = auto()

    @classmethod
    def get_color(cls, room_type):
        colors = {
            cls.LIVING_QUARTERS: "#ADD8E6",
            cls.GREENHOUSE_POTATOES: "#90EE90",
            cls.GREENHOUSE_ALGAE: "#98FB98",
            cls.SOLAR_PANELS: "#606060", # Dark gray for solar panels
            cls.NONE: "#FFFFFF"
        }
        return colors.get(room_type, "#CCCCCC")

class Sensor:
    def __init__(self, x_canvas, y_canvas, o2_variance=SENSOR_DEFAULT_O2_VARIANCE, co2_variance=SENSOR_DEFAULT_CO2_VARIANCE, sensing_radius=CELL_SIZE * 0.75):
        self.x = x_canvas; self.y = y_canvas
        self.o2_variance = o2_variance; self.co2_variance = co2_variance
        self.sensing_radius = sensing_radius
        self.draw_radius = SENSOR_DRAW_RADIUS_PIXELS
        self.canvas_item_id = None; self.selected = False
        self.last_o2_reading = None; self.last_co2_reading = None

    def draw(self, canvas):
        if self.canvas_item_id: canvas.delete(self.canvas_item_id)
        self.canvas_item_id = canvas.create_oval(
            self.x - self.draw_radius, self.y - self.draw_radius, self.x + self.draw_radius, self.y + self.draw_radius,
            fill=SENSOR_OUTLINE_COLOR, outline=SENSOR_OUTLINE_COLOR, width=1, tags="sensor_marker"
        )
        if self.selected: self.select(canvas)

    def contains_point(self, px, py): return (px - self.x)**2 + (py - self.y)**2 <= self.draw_radius**2
    def select(self, canvas):
        self.selected = True
        if self.canvas_item_id:
            canvas.itemconfig(self.canvas_item_id, outline=SENSOR_SELECTED_OUTLINE_COLOR, fill=SENSOR_SELECTED_OUTLINE_COLOR, width=SENSOR_SELECTED_OUTLINE_WIDTH)
            canvas.tag_raise(self.canvas_item_id)
    def deselect(self, canvas):
        self.selected = False
        if self.canvas_item_id: canvas.itemconfig(self.canvas_item_id, outline=SENSOR_OUTLINE_COLOR, fill=SENSOR_OUTLINE_COLOR, width=1)

    def move_to(self, canvas, new_x, new_y):
        self.x = new_x
        self.y = new_y
        if self.canvas_item_id:
            canvas.coords(self.canvas_item_id,
                          self.x - self.draw_radius, self.y - self.draw_radius,
                          self.x + self.draw_radius, self.y + self.draw_radius)

    def read_gas_levels(self, true_o2, true_co2):
        self.last_o2_reading = max(0, np.random.normal(true_o2, math.sqrt(self.o2_variance)))
        self.last_co2_reading = max(0, np.random.normal(true_co2, math.sqrt(self.co2_variance)))
        return self.last_o2_reading, self.last_co2_reading
    def update_params(self, o2_var, co2_var): self.o2_variance = o2_var; self.co2_variance = co2_var
    def update_coords_from_canvas(self, canvas):
        if self.canvas_item_id:
            coords = canvas.coords(self.canvas_item_id)
            if coords:
                self.x = (coords[0] + coords[2]) / 2
                self.y = (coords[1] + coords[3]) / 2

class Leak:
    _id_counter = 0
    def __init__(self, x, y, radius=CELL_SIZE, app_ref=None):
        self.id = Leak._id_counter; Leak._id_counter += 1
        self.x, self.y = x, y
        self.radius = radius
        self.canvas_item_id = None
        self.app_ref = app_ref

    def draw(self, canvas):
        if self.canvas_item_id:
            canvas.delete(self.canvas_item_id)
        self.canvas_item_id = canvas.create_oval(
            self.x - self.radius, self.y - self.radius,
            self.x + self.radius, self.y + self.radius,
            outline="red", width=2, dash=(3,2),
            tags=("leak", f"leak_{self.id}")
        )
        canvas.tag_raise(self.canvas_item_id)

    def contains_point(self, px, py):
        return (px - self.x)**2 + (py - self.y)**2 <= self.radius**2

class RoomShape:
    _id_counter = 0
    def __init__(self, x, y, room_type=RoomType.NONE):
        self.id = RoomShape._id_counter; RoomShape._id_counter += 1
        self.x = x; self.y = y; self.room_type = room_type
        self.color = RoomType.get_color(self.room_type)
        self.canvas_item_id = None; self.selected = False
        self.o2_level = NORMAL_O2_PERCENTAGE; self.co2_level = NORMAL_CO2_PPM

    def draw(self, canvas): raise NotImplementedError
    def contains_point(self, px, py): raise NotImplementedError
    def select(self, canvas):
        self.selected = True
        if self.canvas_item_id:
            canvas.itemconfig(self.canvas_item_id, outline=SELECTED_OUTLINE_COLOR, width=SELECTED_OUTLINE_WIDTH)
            canvas.tag_raise(self.canvas_item_id)
    def deselect(self, canvas):
        self.selected = False
        if self.canvas_item_id: canvas.itemconfig(self.canvas_item_id, outline=self.color, width=DEFAULT_OUTLINE_WIDTH) # Reverted to self.color for default outline
    def move_to(self, canvas, nx, ny): raise NotImplementedError
    def resize(self, canvas, p1, p2): raise NotImplementedError
    def update_coords_from_canvas(self, canvas): pass
    def calculate_area_pixels(self): raise NotImplementedError
    def get_volume_liters(self):
        area_px2 = self.calculate_area_pixels()
        if area_px2 is None or area_px2 <= 0: return 1000 # Default volume if area is zero or invalid
        area_m2 = area_px2 / (CELL_SIZE**2) if CELL_SIZE > 0 else 0
        return area_m2 * 2.5 * 1000 # Assume 2.5m height, convert m^3 to Liters
    def update_room_type(self, new_type, canvas):
        self.room_type = new_type; self.color = RoomType.get_color(new_type)
        if self.canvas_item_id: canvas.itemconfig(self.canvas_item_id, fill=self.color, outline=self.color if not self.selected else SELECTED_OUTLINE_COLOR) # Update outline color too
    def get_center_canvas_coords(self): raise NotImplementedError
    def get_shapely_polygon(self):
        if SHAPELY_AVAILABLE: raise NotImplementedError("get_shapely_polygon must be implemented in subclasses.")
        return None

class RoomRectangle(RoomShape):
    def __init__(self, x, y, width, height, room_type=RoomType.NONE, app_ref=None):
        super().__init__(x, y, room_type)
        self.width = width
        self.height = height
        self.app_ref = app_ref
    def draw(self, canvas):
        if self.canvas_item_id:
            canvas.delete(self.canvas_item_id)

        fill_color = self.color
        if self.app_ref and getattr(self.app_ref, 'sim_running', False) and self.room_type != RoomType.SOLAR_PANELS: # Solar panels don't show O2 color
             # Check current gas view to decide on coloring
            if self.app_ref.current_gas_view.get() == "O2":
                 fill_color = self.app_ref.get_o2_color(self.o2_level)
            # Add similar logic for CO2 if you want to color rooms by CO2 level
            # elif self.app_ref.current_gas_view.get() == "CO2":
            #     fill_color = self.app_ref.get_co2_color(self.co2_level) # You'd need to implement get_co2_color
        
        outline_color = SELECTED_OUTLINE_COLOR if self.selected else self.color # Use room color for outline
        outline_width = SELECTED_OUTLINE_WIDTH if self.selected else DEFAULT_OUTLINE_WIDTH
        
        self.canvas_item_id = canvas.create_rectangle(
            self.x, self.y, self.x + self.width, self.y + self.height,
            fill=fill_color, outline=outline_color, width=outline_width, tags=("user_shape", f"room_{self.id}")
        )
        if self.selected:
            self.select(canvas) # Ensure selection visuals are applied

    def contains_point(self, px, py): return self.x <= px <= self.x + self.width and self.y <= py <= self.y + self.height
    def move_to(self, canvas, new_x, new_y):
        self.x = new_x; self.y = new_y
        if self.canvas_item_id: canvas.coords(self.canvas_item_id, self.x, self.y, self.x + self.width, self.y + self.height)
    def resize(self, canvas, new_corner_x, new_corner_y):
        self.width = max(CELL_SIZE, new_corner_x - self.x); self.height = max(CELL_SIZE, new_corner_y - self.y)
        if self.canvas_item_id: canvas.coords(self.canvas_item_id, self.x, self.y, self.x + self.width, self.y + self.height)
    def update_coords_from_canvas(self, canvas):
        if self.canvas_item_id:
            coords = canvas.coords(self.canvas_item_id)
            if coords: self.x,self.y,self.width,self.height = coords[0],coords[1],abs(coords[2]-coords[0]),abs(coords[3]-coords[1])
    def calculate_area_pixels(self): return self.width * self.height
    def get_center_canvas_coords(self): return self.x + self.width/2, self.y + self.height/2
    def get_shapely_polygon(self):
        if SHAPELY_AVAILABLE: return Polygon([(self.x,self.y),(self.x+self.width,self.y),(self.x+self.width,self.y+self.height),(self.x,self.y+self.height)])
        return None

class RoomCircle(RoomShape):
    def __init__(self, center_x, center_y, radius, room_type=RoomType.NONE, app_ref=None):
        super().__init__(center_x, center_y, room_type) # center_x, center_y are self.x, self.y
        self.radius = radius
        self.app_ref = app_ref
    def draw(self, canvas):
        if self.canvas_item_id:
            canvas.delete(self.canvas_item_id)
        
        fill_color = self.color
        if self.app_ref and getattr(self.app_ref, 'sim_running', False) and self.room_type != RoomType.SOLAR_PANELS:
            if self.app_ref.current_gas_view.get() == "O2":
                 fill_color = self.app_ref.get_o2_color(self.o2_level)
            # elif self.app_ref.current_gas_view.get() == "CO2":
            #     fill_color = self.app_ref.get_co2_color(self.co2_level)

        outline_color = SELECTED_OUTLINE_COLOR if self.selected else self.color
        outline_width = SELECTED_OUTLINE_WIDTH if self.selected else DEFAULT_OUTLINE_WIDTH
        
        self.canvas_item_id = canvas.create_oval(
            self.x - self.radius, self.y - self.radius, self.x + self.radius, self.y + self.radius,
            fill=fill_color, outline=outline_color, width=outline_width, tags=("user_shape", f"room_{self.id}")
        )
        if self.selected:
            self.select(canvas)

    def contains_point(self, px, py): return (px - self.x)**2 + (py - self.y)**2 <= self.radius**2
    def move_to(self, canvas, new_center_x, new_center_y):
        self.x = new_center_x; self.y = new_center_y
        if self.canvas_item_id: canvas.coords(self.canvas_item_id, self.x-self.radius, self.y-self.radius, self.x+self.radius, self.y+self.radius)
    def resize(self, canvas, edge_x, edge_y):
        self.radius = max(CELL_SIZE/2, math.sqrt((edge_x-self.x)**2 + (edge_y-self.y)**2))
        if self.canvas_item_id: canvas.coords(self.canvas_item_id, self.x-self.radius, self.y-self.radius, self.x+self.radius, self.y+self.radius)
    def update_coords_from_canvas(self, canvas):
        if self.canvas_item_id:
            coords = canvas.coords(self.canvas_item_id)
            if coords: self.x,self.y,self.radius = (coords[0]+coords[2])/2, (coords[1]+coords[3])/2, abs(coords[2]-coords[0])/2
    def calculate_area_pixels(self): return math.pi * self.radius**2
    def get_center_canvas_coords(self): return self.x, self.y
    def get_shapely_polygon(self):
        if SHAPELY_AVAILABLE: return Point(self.x, self.y).buffer(self.radius)
        return None

class DrawingApp(ttk.Frame):
    def __init__(self, parent_notebook, oxygen_tab_ref=None, potatoes_tab_ref=None, solar_tab_ref=None, overall_energy_tab_ref=None): # ADDED overall_energy_tab_ref
        super().__init__(parent_notebook)
        self.oxygen_tab_ref = oxygen_tab_ref
        self.potatoes_tab_ref = potatoes_tab_ref
        self.solar_tab_ref = solar_tab_ref
        self.overall_energy_tab_ref = overall_energy_tab_ref # STORE overall_energy_tab_ref

        self.sim_time_hours = 0.0
        self.o2_profile = None

        self.leaks_list = []

        self.current_living_quarters_area_m2 = 0.0
        self.current_potato_gh_area_m2 = 0.0
        self.current_algae_gh_area_m2 = 0.0
        self.current_solar_panel_area_m2 = 0.0

        self.current_mode = "select"; self.rooms_list = []; self.selected_room_obj = None
        self.sensors_list = []; self.selected_sensor_obj = None
        self.is_dragging = False; self.was_resizing_session = False; self.drag_action_occurred = False
        self.drag_offset_x = 0; self.drag_offset_y = 0
        self.drag_start_state = None
        self.sim_grid_rows = (CANVAS_HEIGHT-AXIS_MARGIN)//CELL_SIZE
        self.sim_grid_cols = (CANVAS_WIDTH-AXIS_MARGIN)//CELL_SIZE
        self.o2_field_ground_truth = np.full((self.sim_grid_rows,self.sim_grid_cols), MARS_O2_PERCENTAGE, dtype=float)
        self.co2_field_ground_truth = np.full((self.sim_grid_rows,self.sim_grid_cols), MARS_CO2_PPM, dtype=float)
        self.map_mask = np.zeros((self.sim_grid_rows,self.sim_grid_cols), dtype=int)
        self.sim_running = False; self.sim_job_id = None; self.field_vis_cells = {}
        self.gp_model_o2 = None; self.gp_model_co2 = None
        self.gp_reconstructed_field = np.zeros((self.sim_grid_rows,self.sim_grid_cols), dtype=float)
        self.XY_gp_prediction_grid = self._create_gp_prediction_grid()
        self.gp_update_counter = 0; self.diffusion_update_counter = 0
        self.current_gas_view = tk.StringVar(value="O2"); self.current_gp_display_min = 0.0; self.current_gp_display_max = NORMAL_O2_PERCENTAGE
        if SKLEARN_AVAILABLE:
            k_o2 = ConstantKernel(1.0,(1e-3,1e3))*RBF(length_scale=CELL_SIZE*3,length_scale_bounds=(CELL_SIZE*0.5,CELL_SIZE*15)) + WhiteKernel(noise_level=SENSOR_READING_NOISE_STD_O2**2,noise_level_bounds=(1e-2,1e2))
            self.gp_model_o2 = GaussianProcessRegressor(kernel=k_o2,alpha=1e-7,optimizer='fmin_l_bfgs_b',n_restarts_optimizer=3,normalize_y=True)
            k_co2 = ConstantKernel(1.0,(1e-3,1e3))*RBF(length_scale=CELL_SIZE*3,length_scale_bounds=(CELL_SIZE*0.5,CELL_SIZE*15)) + WhiteKernel(noise_level=SENSOR_READING_NOISE_STD_CO2**2,noise_level_bounds=(1e-2,1e2))
            self.gp_model_co2 = GaussianProcessRegressor(kernel=k_co2,alpha=1e-7,optimizer='fmin_l_bfgs_b',n_restarts_optimizer=3,normalize_y=True)
        self._setup_ui(); self.initialize_gas_fields(); self._update_room_type_areas_display()
        tl = self.winfo_toplevel()
        if tl:
             tl.bind("<Delete>", lambda e: self.handle_key_press_if_active(e,self.delete_selected_item), add="+")
             tl.bind("<BackSpace>", lambda e: self.handle_key_press_if_active(e,self.delete_selected_item), add="+")
             tl.bind("<Escape>", lambda e: self.handle_key_press_if_active(e,self.handle_escape_key_logic), add="+")

        self.colony_size = 50

    def get_potato_greenhouse_area(self): return self.current_potato_gh_area_m2
    def get_algae_greenhouse_area(self): return self.current_algae_gh_area_m2
    def get_solar_panel_area(self): return self.current_solar_panel_area_m2

    def _check_room_overlap(self, room_being_checked, proposed_polygon):
        if not SHAPELY_AVAILABLE or not proposed_polygon:
            return False, None
        for existing_room in self.rooms_list:
            if existing_room == room_being_checked:
                continue
            existing_polygon = existing_room.get_shapely_polygon()
            if not existing_polygon:
                continue
            if proposed_polygon.intersects(existing_polygon):
                try:
                    intersection_area = proposed_polygon.intersection(existing_polygon).area
                    if intersection_area > 1e-3: # Minimal overlap tolerance
                        # Allow overlap IF they are the SAME type OR one of them is NONE
                        if (room_being_checked.room_type != RoomType.NONE and
                            existing_room.room_type != RoomType.NONE and
                            room_being_checked.room_type != existing_room.room_type):
                            return True, existing_room # Invalid overlap: different, non-NONE types
                except Exception: pass # Ignore geometric errors, assume no critical overlap
        return False, None


    def handle_key_press_if_active(self,e,cb,*a):
        try:
            tl=self.winfo_toplevel()
            if hasattr(tl,'notebook_widget_ref') and tl.notebook_widget_ref.select()==str(self): cb(*a)
        except tk.TclError: pass
    def handle_escape_key_logic(self):
        if self.sim_running: self.sim_status_label_var.set("Sim Running. Editing locked."); return
        if self.current_mode not in ["select","rectangle","circle","add_sensor"]:
            self.mode_var.set("select"); self.set_current_mode()
        elif self.selected_room_obj: self.selected_room_obj.deselect(self.drawing_canvas); self.selected_room_obj=None
        elif self.selected_sensor_obj: self.selected_sensor_obj.deselect(self.drawing_canvas); self.selected_sensor_obj=None
        self._show_element_params_frame(); self._update_room_type_areas_display()
    def get_room_by_id(self,rid): return next((r for r in self.rooms_list if r.id == rid), None)
    def _setup_ui(self):
        main_f = ttk.Frame(self, padding="10")
        main_f.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        horz_f = ttk.Frame(main_f)
        horz_f.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.drawing_controls_frame = ttk.LabelFrame(horz_f, text="Habitat Element Controls", padding="10")
        self.drawing_controls_frame.pack(side=tk.LEFT, padx=5, fill=tk.Y, expand=False)
        elem_param_f = ttk.Frame(horz_f)
        elem_param_f.pack(side=tk.LEFT, padx=15, fill=tk.Y, expand=False)
        self.room_params_frame = ttk.LabelFrame(elem_param_f, text="Selected Room Parameters", padding="10")
        self.sensor_params_frame = ttk.LabelFrame(elem_param_f, text="Selected Sensor Parameters", padding="10")
        canvas_area_f = ttk.Frame(horz_f)
        canvas_area_f.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(0,10))
        self.drawing_canvas = tk.Canvas(canvas_area_f, bg="white", relief=tk.SUNKEN, borderwidth=1)
        self.drawing_canvas.pack(side=tk.LEFT, padx=(0, COLOR_SCALE_PADDING), pady=0, expand=True, fill=tk.BOTH)
        self.drawing_canvas.bind("<Configure>", self._on_canvas_resize)
        self.color_scale_canvas = tk.Canvas(canvas_area_f, width=COLOR_SCALE_WIDTH, height=CANVAS_HEIGHT, bg="whitesmoke", relief=tk.SUNKEN, borderwidth=1)
        self.color_scale_canvas.pack(side=tk.RIGHT, pady=0, fill=tk.Y)
        bottom_sim_f = ttk.Frame(main_f)
        bottom_sim_f.pack(side=tk.BOTTOM, fill=tk.X, pady=(5,0))
        self.gp_display_controls_frame = ttk.LabelFrame(bottom_sim_f, text="GP Inferred Field Display", padding="5")
        self.gp_display_controls_frame.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.sim_toggle_frame = ttk.LabelFrame(bottom_sim_f, text="Simulation Control", padding="5")
        self.sim_toggle_frame.pack(side=tk.LEFT, padx=5, fill=tk.X)
        ttk.Label(self.drawing_controls_frame,text="Mode:").grid(row=0,column=0,columnspan=2,padx=2,pady=2,sticky=tk.W)
        self.mode_var = tk.StringVar(value=self.current_mode)
        modes=[("Select","select"),("Draw Room (Rect)","rectangle"),("Draw Room (Circle)","circle"),("Add Sensor","add_sensor"), ("Add Leak","add_leak")]
        cr=0
        for i,(t,mv) in enumerate(modes): ttk.Radiobutton(self.drawing_controls_frame,text=t,variable=self.mode_var,value=mv,command=self.set_current_mode).grid(row=i+1,column=0,columnspan=2,padx=2,pady=2,sticky=tk.W); cr=i+1
        cr+=1; self.delete_button=ttk.Button(self.drawing_controls_frame,text="Delete Selected",command=self.delete_selected_item); self.delete_button.grid(row=cr,column=0,padx=5,pady=5,sticky=tk.W)
        self.clear_sensors_button=ttk.Button(self.drawing_controls_frame,text="Clear All Sensors",command=self.clear_all_sensors); self.clear_sensors_button.grid(row=cr,column=1,padx=5,pady=5,sticky=tk.W)
        cr+=1; self.union_area_label_var=tk.StringVar(value="Total Room Area: N/A"); ttk.Label(self.drawing_controls_frame,textvariable=self.union_area_label_var).grid(row=cr,column=0,columnspan=2,padx=5,pady=5,sticky=tk.W)
        cr+=1; self.living_quarters_area_var=tk.StringVar(value="Living Quarters: 0.00 m²"); ttk.Label(self.drawing_controls_frame,textvariable=self.living_quarters_area_var).grid(row=cr,column=0,columnspan=2,padx=5,pady=2,sticky=tk.W)
        cr+=1; self.potato_area_var=tk.StringVar(value="Potato GH: 0.00 m²"); ttk.Label(self.drawing_controls_frame,textvariable=self.potato_area_var).grid(row=cr,column=0,columnspan=2,padx=5,pady=2,sticky=tk.W)
        cr+=1; self.algae_area_var=tk.StringVar(value="Algae GH: 0.00 m²"); ttk.Label(self.drawing_controls_frame,textvariable=self.algae_area_var).grid(row=cr,column=0,columnspan=2,padx=5,pady=2,sticky=tk.W)
        cr+=1; self.solar_panel_area_var = tk.StringVar(value="Solar Panel Area: 0.00 m²"); ttk.Label(self.drawing_controls_frame, textvariable=self.solar_panel_area_var).grid(row=cr, column=0, columnspan=2, padx=5, pady=2, sticky=tk.W)
        self.selected_room_id_label=ttk.Label(self.room_params_frame,text="Room ID: -"); self.selected_room_id_label.grid(row=0,column=0,columnspan=2,sticky=tk.W,padx=2,pady=2)
        ttk.Label(self.room_params_frame,text="Room Type:").grid(row=1,column=0,sticky=tk.W,padx=2); self.room_type_var=tk.StringVar()
        self.room_type_options=[rt.name for rt in RoomType]; self.room_type_menu=ttk.OptionMenu(self.room_params_frame,self.room_type_var,RoomType.NONE.name,*self.room_type_options,command=self._update_selected_room_type); self.room_type_menu.grid(row=1,column=1,sticky=tk.EW,padx=2)
        self.room_o2_label=ttk.Label(self.room_params_frame,text="O2: - %"); self.room_o2_label.grid(row=4,column=0,columnspan=3,sticky=tk.W,padx=2,pady=2)
        self.room_co2_label=ttk.Label(self.room_params_frame,text="CO2: - ppm"); self.room_co2_label.grid(row=5,column=0,columnspan=3,sticky=tk.W,padx=2,pady=2)
        self.selected_sensor_id_label=ttk.Label(self.sensor_params_frame,text="Sensor ID: -"); self.selected_sensor_id_label.grid(row=0,column=0,columnspan=3,sticky=tk.W,padx=2,pady=2)
        ttk.Label(self.sensor_params_frame,text="O2 Variance:").grid(row=1,column=0,sticky=tk.W,padx=2); self.sensor_o2_var_var=tk.DoubleVar(value=SENSOR_DEFAULT_O2_VARIANCE); self.sensor_o2_var_scale=ttk.Scale(self.sensor_params_frame,from_=0.01,to=5.0,variable=self.sensor_o2_var_var,orient=tk.HORIZONTAL,length=100,command=self._update_selected_sensor_params); self.sensor_o2_var_scale.grid(row=1,column=1,sticky=tk.EW,padx=2); self.sensor_o2_var_label=ttk.Label(self.sensor_params_frame,text=f"{SENSOR_DEFAULT_O2_VARIANCE:.2f}"); self.sensor_o2_var_label.grid(row=1,column=2,sticky=tk.W,padx=2)
        ttk.Label(self.sensor_params_frame,text="CO2 Variance:").grid(row=2,column=0,sticky=tk.W,padx=2); self.sensor_co2_var_var=tk.DoubleVar(value=SENSOR_DEFAULT_CO2_VARIANCE); self.sensor_co2_var_scale=ttk.Scale(self.sensor_params_frame,from_=1.0,to=200.0,variable=self.sensor_co2_var_var,orient=tk.HORIZONTAL,length=100,command=self._update_selected_sensor_params); self.sensor_co2_var_scale.grid(row=2,column=1,sticky=tk.EW,padx=2); self.sensor_co2_var_label=ttk.Label(self.sensor_params_frame,text=f"{SENSOR_DEFAULT_CO2_VARIANCE:.1f}"); self.sensor_co2_var_label.grid(row=2,column=2,sticky=tk.W,padx=2)
        self.sensor_o2_reading_label=ttk.Label(self.sensor_params_frame,text="O2 Reading: - %"); self.sensor_o2_reading_label.grid(row=3,column=0,columnspan=3,sticky=tk.W,padx=2,pady=2)
        self.sensor_co2_reading_label=ttk.Label(self.sensor_params_frame,text="CO2 Reading: - ppm"); self.sensor_co2_reading_label.grid(row=4,column=0,columnspan=3,sticky=tk.W,padx=2,pady=2)
        ttk.Label(self.gp_display_controls_frame,text="View Gas:").pack(side=tk.LEFT,padx=(5,0)); ttk.Radiobutton(self.gp_display_controls_frame,text="O2",variable=self.current_gas_view,value="O2",command=self._on_gas_view_change).pack(side=tk.LEFT); ttk.Radiobutton(self.gp_display_controls_frame,text="CO2",variable=self.current_gas_view,value="CO2",command=self._on_gas_view_change).pack(side=tk.LEFT,padx=(0,10))
        self.field_scale_label_var=tk.StringVar(value=f"GP Scale: {self.current_gp_display_min:.1f}-{self.current_gp_display_max:.1f}"); ttk.Label(self.gp_display_controls_frame,textvariable=self.field_scale_label_var).pack(side=tk.LEFT,padx=5)
        self.sim_status_label_var=tk.StringVar(value="Sim Stopped. Editing enabled."); ttk.Label(self.sim_toggle_frame,textvariable=self.sim_status_label_var).pack(side=tk.LEFT,padx=5); self.sim_toggle_button=ttk.Button(self.sim_toggle_frame,text="Initialize & Run Sim",command=self.toggle_simulation); self.sim_toggle_button.pack(side=tk.LEFT,padx=5)
        self.day_label_var = tk.StringVar(value="Day: 0")
        self.day_label = ttk.Label(self.sim_toggle_frame, textvariable=self.day_label_var)
        self.day_label.pack(side=tk.LEFT, padx=5)
        self.colony_size_var = tk.IntVar(value=50)
        ttk.Label(self.sim_toggle_frame, text="Colony Size:").pack(side=tk.LEFT, padx=(10,2))
        self.colony_size_scale = ttk.Scale(self.sim_toggle_frame, from_=10, to=200, variable=self.colony_size_var, orient=tk.HORIZONTAL, length=150, command=self._on_colony_size_change )
        self.colony_size_scale.pack(side=tk.LEFT)
        self.colony_size_scale.set(50)
        self.draw_visual_grid_and_axes(); self.draw_color_scale(); self.drawing_canvas.bind("<Button-1>",self.handle_mouse_down); self.drawing_canvas.bind("<B1-Motion>",self.handle_mouse_drag); self.drawing_canvas.bind("<ButtonRelease-1>",self.handle_mouse_up)
        self._update_room_type_areas_display(); self._show_element_params_frame()

    def _on_canvas_resize(self, event):
        global CANVAS_WIDTH, CANVAS_HEIGHT
        CANVAS_WIDTH, CANVAS_HEIGHT = event.width, event.height
        self.sim_grid_rows = (CANVAS_HEIGHT - AXIS_MARGIN) // CELL_SIZE
        self.sim_grid_cols = (CANVAS_WIDTH - AXIS_MARGIN) // CELL_SIZE
        self.o2_field_ground_truth = np.full((self.sim_grid_rows, self.sim_grid_cols), MARS_O2_PERCENTAGE, dtype=float)
        self.co2_field_ground_truth = np.full((self.sim_grid_rows, self.sim_grid_cols), MARS_CO2_PPM, dtype=float)
        self.map_mask = np.zeros((self.sim_grid_rows, self.sim_grid_cols), dtype=int)
        self.XY_gp_prediction_grid = self._create_gp_prediction_grid()
        self.prepare_visualization_map_and_fields()
        self.draw_visual_grid_and_axes()
        self.draw_color_scale()

    def _on_colony_size_change(self, val):
        size = int(float(val))
        self.colony_size_var.set(size)
        self.colony_size = size
        self.sim_status_label_var.set(f"Colony size set to {size}. Re-init sim if running.")
        if self.oxygen_tab_ref and hasattr(self.oxygen_tab_ref, 'update_plot'):
            self.oxygen_tab_ref.update_plot()
        if self.potatoes_tab_ref and hasattr(self.potatoes_tab_ref, 'update_plot'):
            self.potatoes_tab_ref.update_plot()

    def _update_room_type_areas_display(self):
        areas={ RoomType.LIVING_QUARTERS:0.0, RoomType.GREENHOUSE_POTATOES:0.0, RoomType.GREENHOUSE_ALGAE:0.0, RoomType.SOLAR_PANELS: 0.0 }
        for room in self.rooms_list:
            if isinstance(room.room_type,RoomType) and room.room_type in areas:
                px_area=room.calculate_area_pixels()
                if px_area>0: area_m2=px_area/(CELL_SIZE**2) if CELL_SIZE>0 else 0; areas[room.room_type]+=area_m2

        self.current_living_quarters_area_m2 = areas.get(RoomType.LIVING_QUARTERS,0.0)
        self.current_potato_gh_area_m2 = areas.get(RoomType.GREENHOUSE_POTATOES,0.0)
        self.current_algae_gh_area_m2 = areas.get(RoomType.GREENHOUSE_ALGAE,0.0)
        self.current_solar_panel_area_m2 = areas.get(RoomType.SOLAR_PANELS, 0.0)

        self.living_quarters_area_var.set(f"Living Qtrs: {self.current_living_quarters_area_m2:.2f} m²")
        self.potato_area_var.set(f"Potato GH: {self.current_potato_gh_area_m2:.2f} m²")
        self.algae_area_var.set(f"Algae GH: {self.current_algae_gh_area_m2:.2f} m²")
        self.solar_panel_area_var.set(f"Solar Panels: {self.current_solar_panel_area_m2:.2f} m²")
        self.update_union_area_display()

        if self.oxygen_tab_ref and hasattr(self.oxygen_tab_ref,'refresh_with_new_areas'): self.oxygen_tab_ref.refresh_with_new_areas()
        if self.potatoes_tab_ref and hasattr(self.potatoes_tab_ref,'refresh_with_new_areas'): self.potatoes_tab_ref.refresh_with_new_areas()
        if self.solar_tab_ref and hasattr(self.solar_tab_ref, 'refresh_with_new_area'): self.solar_tab_ref.refresh_with_new_area()
        if self.overall_energy_tab_ref and hasattr(self.overall_energy_tab_ref, 'refresh_plot'): # ADDED
            self.overall_energy_tab_ref.refresh_plot()


    def _create_gp_prediction_grid(self): return np.array([[AXIS_MARGIN+c*CELL_SIZE+CELL_SIZE/2, AXIS_MARGIN+r*CELL_SIZE+CELL_SIZE/2] for r in range(self.sim_grid_rows) for c in range(self.sim_grid_cols)])
    def _update_selected_room_type(self, sel_type_str):
        if self.selected_room_obj:
            try: new_type=RoomType[sel_type_str]
            except KeyError: new_type=RoomType.NONE

            if SHAPELY_AVAILABLE:
                original_type = self.selected_room_obj.room_type
                self.selected_room_obj.room_type = new_type # Temporarily change for check
                current_polygon = self.selected_room_obj.get_shapely_polygon()
                if current_polygon:
                    invalid_overlap, _ = self._check_room_overlap(self.selected_room_obj, current_polygon)
                    if invalid_overlap:
                        messagebox.showwarning("Overlap Error", f"Changing to {new_type.name} would cause an invalid overlap with a different room type.")
                        self.selected_room_obj.room_type = original_type # Revert
                        self.room_type_var.set(original_type.name)
                        return
            # If no Shapely or no overlap, proceed with update
            self.selected_room_obj.update_room_type(new_type,self.drawing_canvas)
            self.sim_status_label_var.set("Room type changed.")
            self.prepare_visualization_map_and_fields()
            self._update_room_type_areas_display() # This will also refresh OverallEnergyTab

    def _update_selected_sensor_params(self,val_str=None):
        if self.selected_sensor_obj:
            o2v,co2v=self.sensor_o2_var_var.get(),self.sensor_co2_var_var.get(); self.selected_sensor_obj.update_params(o2v,co2v)
            self.sensor_o2_var_label.config(text=f"{o2v:.2f}"); self.sensor_co2_var_label.config(text=f"{co2v:.1f}"); self.sim_status_label_var.set("Sensor params changed. Re-init sim if running.")
    def _show_element_params_frame(self):
        self.room_params_frame.pack_forget(); self.sensor_params_frame.pack_forget()
        if self.selected_room_obj:
            self.room_params_frame.pack(side=tk.TOP,padx=5,pady=5,fill=tk.X); self.selected_room_id_label.config(text=f"Room ID: {self.selected_room_obj.id}"); self.room_type_var.set(self.selected_room_obj.room_type.name); self.room_o2_label.config(text=f"O2: {self.selected_room_obj.o2_level:.2f}%"); self.room_co2_label.config(text=f"CO2: {self.selected_room_obj.co2_level:.0f} ppm")
        elif self.selected_sensor_obj:
            self.sensor_params_frame.pack(side=tk.TOP,padx=5,pady=5,fill=tk.X); s_idx=self.sensors_list.index(self.selected_sensor_obj) if self.selected_sensor_obj in self.sensors_list else -1; self.selected_sensor_id_label.config(text=f"Sensor ID: S{s_idx}"); self.sensor_o2_var_var.set(self.selected_sensor_obj.o2_variance); self.sensor_co2_var_var.set(self.selected_sensor_obj.co2_variance); self.sensor_o2_var_label.config(text=f"{self.selected_sensor_obj.o2_variance:.2f}"); self.sensor_co2_var_label.config(text=f"{self.selected_sensor_obj.co2_variance:.1f}"); o2r,co2r=self.selected_sensor_obj.last_o2_reading,self.selected_sensor_obj.last_co2_reading; self.sensor_o2_reading_label.config(text=f"O2 Read: {o2r:.2f}%" if o2r is not None else "N/A"); self.sensor_co2_reading_label.config(text=f"CO2 Read: {co2r:.0f} ppm" if co2r is not None else "N/A")
    def _sim_to_canvas_coords_center(self,r,c): return AXIS_MARGIN+c*CELL_SIZE+CELL_SIZE/2, AXIS_MARGIN+r*CELL_SIZE+CELL_SIZE/2
    def update_union_area_display(self):
        if not SHAPELY_AVAILABLE: self.union_area_label_var.set("Total Union Area: (Shapely N/A)"); return
        if not self.rooms_list: self.union_area_label_var.set("Total Union Area: 0.00 m²"); return
        room_polys=[r.get_shapely_polygon() for r in self.rooms_list if r.get_shapely_polygon() is not None and r.room_type != RoomType.NONE] # Exclude NONE type rooms from union area calculation
        if not room_polys: self.union_area_label_var.set("Total Union Area: 0.00 m²"); return
        try:
            # Filter out non-geometric types if any shapely polygon is None (though previous list comprehension should handle)
            valid_polys = [p for p in room_polys if p is not None and not p.is_empty]
            if not valid_polys:
                 self.union_area_label_var.set("Total Union Area: 0.00 m²"); return
            union=unary_union(valid_polys); px_area=union.area; area_m2=px_area/(CELL_SIZE**2) if CELL_SIZE>0 else 0
            self.union_area_label_var.set(f"Total Union Area: {area_m2:.2f} m²")
        except Exception as e:
            print(f"Shapely union error: {e}")
            px_area=sum(r.calculate_area_pixels() for r in self.rooms_list if r.room_type != RoomType.NONE); area_m2=px_area/(CELL_SIZE**2) if CELL_SIZE>0 else 0; self.union_area_label_var.set(f"Total Sum Area: {area_m2:.2f} m² (Union Err)")

    def set_current_mode(self):
        om=self.current_mode; self.current_mode=self.mode_var.get()
        if self.sim_running and self.current_mode!="select": self.mode_var.set("select"); self.current_mode="select"; self.sim_status_label_var.set("Sim Running. Editing locked.")
        if om=="select":
            if self.selected_room_obj and self.current_mode!="select": self.selected_room_obj.deselect(self.drawing_canvas); self.selected_room_obj=None
            if self.selected_sensor_obj and self.current_mode!="select": self.selected_sensor_obj.deselect(self.drawing_canvas); self.selected_sensor_obj=None
            self._show_element_params_frame()
        self.is_dragging=False; self.was_resizing_session=False; self.drag_action_occurred=False
    def draw_visual_grid_and_axes(self):
        self.drawing_canvas.delete("grid","axis_label","grid_axis_line")
        self.drawing_canvas.create_line(AXIS_MARGIN,AXIS_MARGIN,CANVAS_WIDTH-CELL_SIZE,AXIS_MARGIN,fill=AXIS_LINE_COLOR,width=1,tags="grid_axis_line")
        self.drawing_canvas.create_line(AXIS_MARGIN,AXIS_MARGIN,AXIS_MARGIN,CANVAS_HEIGHT-CELL_SIZE,fill=AXIS_LINE_COLOR,width=1,tags="grid_axis_line")
        for xc in range(AXIS_MARGIN,CANVAS_WIDTH-CELL_SIZE+1,CELL_SIZE):
            if (xc-AXIS_MARGIN)%LABEL_INTERVAL==0: self.drawing_canvas.create_text(xc,AXIS_MARGIN-10,text=str(xc-AXIS_MARGIN),anchor=tk.S,font=LABEL_FONT,fill=LABEL_COLOR,tags="axis_label")
        for yc in range(AXIS_MARGIN,CANVAS_HEIGHT-CELL_SIZE+1,CELL_SIZE):
            if (yc-AXIS_MARGIN)%LABEL_INTERVAL==0: self.drawing_canvas.create_text(AXIS_MARGIN-10,yc,text=str(yc-AXIS_MARGIN),anchor=tk.E,font=LABEL_FONT,fill=LABEL_COLOR,tags="axis_label")
        self.drawing_canvas.tag_lower("grid_axis_line"); self.drawing_canvas.tag_lower("axis_label"); self.drawing_canvas.tag_raise("user_shape"); self.drawing_canvas.tag_raise("sensor_marker"); self.drawing_canvas.tag_raise("leak")
    def _canvas_to_sim_coords(self,cx,cy):
        if cx<AXIS_MARGIN or cy<AXIS_MARGIN: return None,None
        col=int((cx-AXIS_MARGIN)//CELL_SIZE); row=int((cy-AXIS_MARGIN)//CELL_SIZE)
        if 0<=row<self.sim_grid_rows and 0<=col<self.sim_grid_cols: return row,col
        return None,None
    def _sim_to_canvas_coords(self,r,c): return AXIS_MARGIN+c*CELL_SIZE, AXIS_MARGIN+r*CELL_SIZE
    def handle_mouse_down(self,e):
        eff_x,eff_y=self.drawing_canvas.canvasx(e.x),self.drawing_canvas.canvasy(e.y)
        if self.sim_running: self.sim_status_label_var.set("Sim Running. Editing locked."); return

        if self.current_mode == "add_leak":
            new_leak = Leak(eff_x, eff_y, CELL_SIZE*1.5, app_ref=self)
            self.leaks_list.append(new_leak)
            new_leak.draw(self.drawing_canvas)
            self.mode_var.set("select"); self.set_current_mode()
            self.sim_status_label_var.set(f"Leak L{new_leak.id} added.")
            return
        if self.current_mode=="add_sensor": self.handle_add_sensor_click(eff_x,eff_y); return
        self.is_dragging=True; self.was_resizing_session=False; self.drag_action_occurred=False
        if self.current_mode=="select":
            ci=None
            # Priority: selected sensor, any sensor, selected room, any room, any leak
            if self.selected_sensor_obj and self.selected_sensor_obj.contains_point(eff_x,eff_y): ci=self.selected_sensor_obj
            else: ci=next((s for s in reversed(self.sensors_list) if s.contains_point(eff_x,eff_y)), None)

            if not ci:
                if self.selected_room_obj and self.selected_room_obj.contains_point(eff_x,eff_y): ci=self.selected_room_obj
                else: ci=next((r for r in reversed(self.rooms_list) if r.contains_point(eff_x,eff_y)), None)
            
            # Check for leaks if nothing else is selected yet (leaks are on top visually but lower selection priority)
            if not ci:
                 ci = next((lk for lk in reversed(self.leaks_list) if lk.contains_point(eff_x, eff_y)), None)


            if self.selected_room_obj and self.selected_room_obj!=ci: self.selected_room_obj.deselect(self.drawing_canvas); self.selected_room_obj=None
            if self.selected_sensor_obj and self.selected_sensor_obj!=ci: self.selected_sensor_obj.deselect(self.drawing_canvas); self.selected_sensor_obj=None
            # No selection concept for leaks for now, handled by delete button logic

            if isinstance(ci,Sensor):
                self.selected_sensor_obj=ci; ci.select(self.drawing_canvas)
                self.drag_offset_x,self.drag_offset_y=eff_x-ci.x,eff_y-ci.y
            elif isinstance(ci,RoomShape):
                self.selected_room_obj=ci; ci.select(self.drawing_canvas)
                self.drag_offset_x,self.drag_offset_y=eff_x-ci.x,eff_y-ci.y
                self.drag_start_state = {'x': ci.x, 'y': ci.y,
                                         'width': getattr(ci, 'width', None),
                                         'height': getattr(ci, 'height', None),
                                         'radius': getattr(ci, 'radius', None)}
            elif isinstance(ci, Leak): # If a leak was clicked, no drag, just for info or delete
                self.sim_status_label_var.set(f"Leak L{ci.id} clicked. Use Delete for leaks.")
                # Do not set is_dragging = True for leaks
                self.is_dragging = False # Explicitly prevent dragging leaks
            else: self.drag_offset_x,self.drag_offset_y=0,0
            self._show_element_params_frame()
        elif self.current_mode=="rectangle": self.add_new_room(RoomRectangle(eff_x,eff_y,CELL_SIZE*4,CELL_SIZE*3,RoomType.LIVING_QUARTERS, app_ref = self))
        elif self.current_mode=="circle": self.add_new_room(RoomCircle(eff_x,eff_y,CELL_SIZE*2,RoomType.LIVING_QUARTERS, app_ref = self))

    def add_new_room(self,new_room_obj):
        if self.sim_running: self.sim_status_label_var.set("Cannot add rooms while sim running."); return

        if SHAPELY_AVAILABLE:
            new_room_polygon = new_room_obj.get_shapely_polygon()
            if new_room_polygon:
                invalid_overlap, _ = self._check_room_overlap(new_room_obj, new_room_polygon)
                if invalid_overlap:
                    messagebox.showwarning("Overlap Error", "New room cannot overlap with an existing room of a different type.")
                    self.mode_var.set("select"); self.set_current_mode()
                    return

        self.rooms_list.append(new_room_obj)
        if self.selected_room_obj: self.selected_room_obj.deselect(self.drawing_canvas)
        if self.selected_sensor_obj: self.selected_sensor_obj.deselect(self.drawing_canvas); self.selected_sensor_obj=None
        self.selected_room_obj=new_room_obj; self._show_element_params_frame(); self.prepare_visualization_map_and_fields()
        if self.selected_room_obj: self.selected_room_obj.select(self.drawing_canvas)
        self.mode_var.set("select"); self.set_current_mode(); self._update_room_type_areas_display()

    def handle_add_sensor_click(self,cx,cy):
        if self.sim_running: self.sim_status_label_var.set("Cannot add sensors while sim running."); return
        ns=Sensor(cx,cy); self.sensors_list.append(ns); s_idx=self.sensors_list.index(ns) if ns in self.sensors_list else -1
        self.sim_status_label_var.set(f"Sensor S{s_idx} added. Total: {len(self.sensors_list)}.")
        if self.selected_sensor_obj: self.selected_sensor_obj.deselect(self.drawing_canvas)
        if self.selected_room_obj: self.selected_room_obj.deselect(self.drawing_canvas); self.selected_room_obj=None
        self.selected_sensor_obj=ns; self.prepare_visualization_map_and_fields()
        if self.selected_sensor_obj: self.selected_sensor_obj.select(self.drawing_canvas)
        self._show_element_params_frame(); self.mode_var.set("select"); self.set_current_mode()

    def handle_mouse_drag(self,e):
        if self.sim_running or not self.is_dragging or self.current_mode!="select": return # Dragging only in select mode and if dragging started
        si=self.selected_room_obj if self.selected_room_obj else self.selected_sensor_obj
        if not si: return # Only drag selected rooms or sensors
        self.drag_action_occurred=True; eff_x,eff_y=self.drawing_canvas.canvasx(e.x),self.drawing_canvas.canvasy(e.y)
        if isinstance(si,RoomShape):
            if (e.state&0x0001)!=0: # Shift key for resize
                self.was_resizing_session=True
                si.resize(self.drawing_canvas,eff_x,eff_y)
            else: # No shift, so move
                si.move_to(self.drawing_canvas,eff_x-self.drag_offset_x,eff_y-self.drag_offset_y)
        elif isinstance(si,Sensor): # Sensors only move
            si.move_to(self.drawing_canvas,eff_x-self.drag_offset_x,eff_y-self.drag_offset_y)

    def handle_mouse_up(self, e):
        if self.sim_running: return

        action_finalized_message = ""
        if self.is_dragging and self.drag_action_occurred and self.selected_room_obj and self.drag_start_state:
            current_polygon = self.selected_room_obj.get_shapely_polygon()
            reverted_to_original = False

            if SHAPELY_AVAILABLE and current_polygon:
                invalid_overlap, collided_room = self._check_room_overlap(self.selected_room_obj, current_polygon)

                if invalid_overlap:
                    # Basic revert logic:
                    self.selected_room_obj.x, self.selected_room_obj.y = self.drag_start_state['x'], self.drag_start_state['y']
                    if isinstance(self.selected_room_obj, RoomRectangle):
                        self.selected_room_obj.width, self.selected_room_obj.height = self.drag_start_state['width'], self.drag_start_state['height']
                    elif isinstance(self.selected_room_obj, RoomCircle):
                        self.selected_room_obj.radius = self.drag_start_state['radius']
                    
                    # Redraw the room in its original position
                    self.selected_room_obj.draw(self.drawing_canvas)
                    if self.selected_room_obj.selected: # Ensure it's still visually selected
                        self.selected_room_obj.select(self.drawing_canvas)

                    messagebox.showwarning("Overlap Error", "Move/resize caused invalid overlap. Reverting to original state.")
                    action_finalized_message = "Room reverted to original state."
                    reverted_to_original = True
                else: # No invalid overlap
                     action_finalized_message = "Room " + ("resized." if self.was_resizing_session else "moved.")
            else: # Shapely not available or no polygon, accept the move/resize
                action_finalized_message = "Room " + ("resized." if self.was_resizing_session else "moved.") + " (Overlap check skipped)."
            
            if action_finalized_message:
                self.sim_status_label_var.set(action_finalized_message)
            
            self.prepare_visualization_map_and_fields()
            self._update_room_type_areas_display() # This also refreshes overall energy tab

        elif self.is_dragging and self.drag_action_occurred and self.selected_sensor_obj:
            self.selected_sensor_obj.update_coords_from_canvas(self.drawing_canvas) # Finalize sensor position
            self.prepare_visualization_map_and_fields()
            self.sim_status_label_var.set("Sensor moved.")

        self.is_dragging=False; self.was_resizing_session=False; self.drag_action_occurred=False
        self.drag_start_state = None

    def delete_selected_item(self,*a):
        if self.sim_running: self.sim_status_label_var.set("Cannot delete while sim running."); return
        msg=""; item_was_room=False; item_was_sensor = False

        # Check for selected leak first (if a leak was the last thing clicked before delete)
        # This requires knowing which leak was "selected" - we don't have self.selected_leak_obj
        # For simplicity, let's assume if no room/sensor is selected, we check if cursor is over a leak
        deleted_item = False
        if self.selected_room_obj:
            item_was_room=True
            if self.selected_room_obj in self.rooms_list:
                self.drawing_canvas.delete(self.selected_room_obj.canvas_item_id)
                self.rooms_list.remove(self.selected_room_obj)
            self.selected_room_obj=None; msg="Room deleted."; deleted_item = True
        elif self.selected_sensor_obj:
            item_was_sensor=True
            if self.selected_sensor_obj in self.sensors_list:
                self.drawing_canvas.delete(self.selected_sensor_obj.canvas_item_id)
                self.sensors_list.remove(self.selected_sensor_obj)
            self.selected_sensor_obj=None; msg="Sensor deleted."; deleted_item = True
        else: # No room or sensor selected, check for leaks under cursor (or last clicked if tracked)
            # For now, let's just prompt to select a leak if nothing else is selected.
            # A more robust way would be to find a leak under the current mouse position if delete is pressed.
            # Or, select leaks like other items. For now, we'll require explicit selection for rooms/sensors.
            # To delete leaks without selection: iterate and remove if a condition is met (e.g. mouse over)
            # For now, leaks deletion will be manual if we don't implement leak selection.
            # Let's try a simple check: if mouse is over a leak when delete is pressed.
            # This needs mouse position. Let's assume the user clicked the leak then pressed delete.
            # The `handle_mouse_down` doesn't set a `self.selected_leak_obj`.
            # A simpler approach for now: Delete button for rooms/sensors. Leaks might need a "Clear Leaks" button or individual click-to-delete.
            # For this integration, let's assume delete works on selected rooms/sensors.
            # If user wants to delete leaks, they'd need to be selectable or have a dedicated "clear leaks" function.
             # Let's try to delete the most recently added leak if no room/sensor is selected
            if self.leaks_list: # and not self.selected_room_obj and not self.selected_sensor_obj: (implicit from else)
                leak_to_delete = self.leaks_list.pop() # Deletes the last added leak
                self.drawing_canvas.delete(leak_to_delete.canvas_item_id)
                msg = f"Last leak (L{leak_to_delete.id}) deleted."
                deleted_item = True
            else:
                 msg = "No item selected to delete."


        if deleted_item:
            self.prepare_visualization_map_and_fields()
            if item_was_room : self._update_room_type_areas_display() #This refreshes overall energy too
            self.sim_status_label_var.set(msg)
        self._show_element_params_frame() # Update parameter display

    def clear_all_sensors(self):
        if self.sim_running: self.sim_status_label_var.set("Cannot clear sensors while sim running."); return
        for sensor in self.sensors_list:
            if sensor.canvas_item_id: self.drawing_canvas.delete(sensor.canvas_item_id)
        self.sensors_list.clear();
        if self.selected_sensor_obj: self.selected_sensor_obj=None
        self.prepare_visualization_map_and_fields(); self._show_element_params_frame(); self.sim_status_label_var.set("All sensors cleared.")

    def initialize_gas_fields(self):
        self.o2_field_ground_truth.fill(MARS_O2_PERCENTAGE); self.co2_field_ground_truth.fill(MARS_CO2_PPM)
        for r in self.rooms_list:
            r.o2_level,r.co2_level=NORMAL_O2_PERCENTAGE,NORMAL_CO2_PPM # Initialize room levels
            for ri in range(self.sim_grid_rows):
                for ci in range(self.sim_grid_cols):
                    cx,cy=self._sim_to_canvas_coords_center(ri,ci)
                    if r.contains_point(cx,cy): self.o2_field_ground_truth[ri,ci],self.co2_field_ground_truth[ri,ci]=r.o2_level,r.co2_level
        self.update_map_mask()
    def update_map_mask(self):
        self.map_mask.fill(0) # 0 for outside, 1 for inside a room
        for ri in range(self.sim_grid_rows):
            for ci in range(self.sim_grid_cols):
                cx,cy=self._sim_to_canvas_coords_center(ri,ci)
                for ro in self.rooms_list:
                    if ro.room_type != RoomType.NONE and ro.contains_point(cx,cy): # Only consider non-NONE rooms for mask
                        self.map_mask[ri,ci]=1; break
    def prepare_visualization_map_and_fields(self):
        self.update_map_mask()
        if not self.sim_running: self.initialize_gas_fields() # Initialize if sim not running
        # Clear old visualization cells
        for iid in self.field_vis_cells.values(): self.drawing_canvas.delete(iid)
        self.field_vis_cells.clear()
        # Create new visualization cells for the GP field
        for r_idx in range(self.sim_grid_rows):
            for c_idx in range(self.sim_grid_cols):
                x0,y0=self._sim_to_canvas_coords(r_idx,c_idx);
                vid=self.drawing_canvas.create_rectangle(x0,y0,x0+CELL_SIZE,y0+CELL_SIZE,fill="",outline="",tags="gp_field_cell")
                self.field_vis_cells[(r_idx,c_idx)]=vid
        self.drawing_canvas.tag_lower("gp_field_cell") # Ensure GP field is below grid/shapes
        self.draw_visual_grid_and_axes()
        for r_obj in self.rooms_list: r_obj.draw(self.drawing_canvas) # Redraw rooms
        for s_obj in self.sensors_list: s_obj.draw(self.drawing_canvas) # Redraw sensors
        for leak_obj in self.leaks_list: leak_obj.draw(self.drawing_canvas) # Redraw leaks

    def _apply_leaks(self):
        for leak in self.leaks_list:
            sr, sc = self._canvas_to_sim_coords(leak.x, leak.y)
            if sr is None or sc is None: continue

            room_here = next((r for r in self.rooms_list if r.contains_point(leak.x, leak.y) and r.room_type != RoomType.NONE), None)
            if not room_here: continue # Leak must be inside a defined room

            # O₂ loss calculation (simplified)
            A_m2 = math.pi * (leak.radius / CELL_SIZE)**2 # Leak area in m^2
            # Pressure difference term is complex. Simplified: assume leak rate proportional to O2 difference
            delta_C_o2_percent = (room_here.o2_level - MARS_O2_PERCENTAGE)
            
            # Simplified mass flux (kg/hr) - needs calibration or more physics
            # LEAK_DIFFUSION_COEFF is kg O2 / m^2 / hr / (% O2 diff / 100) -- this needs careful unit check
            # Let's assume LEAK_DIFFUSION_COEFF means: kg O2 leaked per m^2 per hour for a 100% O2 difference.
            # So, mass_flux_kg_per_hr = LEAK_DIFFUSION_COEFF * A_m2 * (delta_C_o2_percent / 100.0)
            # More direct: if LEAK_DIFFUSION_COEFF is simplified rate like 0.1 kg/m2/hr for 21% difference.
            # Let's use a very simplified fixed percentage loss rate for now if room O2 > Mars O2
            if room_here.o2_level > MARS_O2_PERCENTAGE:
                # Mass of O2 lost in this step (SIM_DT_HOURS)
                # This is a placeholder for a more physically based leak model.
                # Example: lose 0.01% of the difference per hour, scaled by leak area
                leak_rate_factor = 0.001 * (A_m2 / (math.pi * (CELL_SIZE*1.5/CELL_SIZE)**2) ) # Normalized area effect
                percent_o2_lost_this_step = leak_rate_factor * delta_C_o2_percent * SIM_DT_HOURS
                
                room_here.o2_level = max(MARS_O2_PERCENTAGE, room_here.o2_level - percent_o2_lost_this_step)

                # Update all map cells inside the room to room's new O2
                for ri in range(self.sim_grid_rows):
                    for ci in range(self.sim_grid_cols):
                        cx,cy=self._sim_to_canvas_coords_center(ri,ci)
                        if room_here.contains_point(cx,cy):
                            self.o2_field_ground_truth[ri, ci] = room_here.o2_level
                # CO2 could also leak in if we model that. For now, only O2 leaks out.


    def _on_gas_view_change(self): self.update_gp_model_and_predict(); self.draw_field_visualization(); self.draw_color_scale()
    def collect_sensor_data_for_gp(self):
        sX,sy=[],[]; gas_f=self.o2_field_ground_truth if self.current_gas_view.get()=="O2" else self.co2_field_ground_truth
        for so in self.sensors_list:
            sr,sc=self._canvas_to_sim_coords(so.x,so.y); true_val=(MARS_O2_PERCENTAGE if self.current_gas_view.get()=="O2" else MARS_CO2_PPM)
            s_in_r=next((r for r in self.rooms_list if r.contains_point(so.x,so.y) and r.room_type != RoomType.NONE),None) # Sensor must be in a non-NONE room
            if s_in_r: true_val=s_in_r.o2_level if self.current_gas_view.get()=="O2" else s_in_r.co2_level
            elif sr is not None and sc is not None and 0<=sr<self.sim_grid_rows and 0<=sc<self.sim_grid_cols: # Sensor is outside but on map
                 true_val=gas_f[sr,sc]

            var=so.o2_variance if self.current_gas_view.get()=="O2" else so.co2_variance; noisy_r=max(0,np.random.normal(true_val,math.sqrt(var)))
            sX.append([so.x,so.y]); sy.append(noisy_r)

            true_o2_s,true_co2_s=MARS_O2_PERCENTAGE,MARS_CO2_PPM
            if s_in_r: true_o2_s,true_co2_s=s_in_r.o2_level,s_in_r.co2_level
            elif sr is not None and sc is not None and 0<=sr<self.sim_grid_rows and 0<=sc<self.sim_grid_cols: true_o2_s,true_co2_s=self.o2_field_ground_truth[sr,sc],self.co2_field_ground_truth[sr,sc]
            so.read_gas_levels(true_o2_s,true_co2_s) # Store last readings in sensor
        return np.array(sX),np.array(sy)

    def update_gp_model_and_predict(self):
        truth_f=self.o2_field_ground_truth if self.current_gas_view.get()=="O2" else self.co2_field_ground_truth; suffix=""
        if not SKLEARN_AVAILABLE: self.gp_reconstructed_field=truth_f.copy(); suffix=f" (No Sklearn - Truth for {self.current_gas_view.get()})"
        elif not self.sensors_list: self.gp_reconstructed_field=truth_f.copy(); suffix=f" (No Sensors - Truth for {self.current_gas_view.get()})"
        else:
            gp_model=self.gp_model_o2 if self.current_gas_view.get()=="O2" else self.gp_model_co2; sX,sy=self.collect_sensor_data_for_gp()
            if sX.shape[0]>0 and sy.shape[0]>0 and sX.shape[0]==sy.shape[0]:
                try:
                    gp_model.fit(sX,sy); pred_flat=gp_model.predict(self.XY_gp_prediction_grid); self.gp_reconstructed_field=pred_flat.reshape((self.sim_grid_rows,self.sim_grid_cols))
                    min_c,max_c=(0,(NORMAL_O2_PERCENTAGE*1.5 if self.current_gas_view.get()=="O2" else MARS_CO2_PPM*1.1)); np.clip(self.gp_reconstructed_field,min_c,max_c,out=self.gp_reconstructed_field); suffix=f" (GP for {self.current_gas_view.get()})"
                except Exception as e: print(f"GP Error: {e}"); self.gp_reconstructed_field=truth_f.copy(); suffix=f" (GP Error - Truth for {self.current_gas_view.get()})"
            else: self.gp_reconstructed_field=truth_f.copy(); suffix=f" (No Sensor Data - Truth for {self.current_gas_view.get()})"
        sim_state="Sim Running." if self.sim_running else "Sim Stopped."; self.sim_status_label_var.set(sim_state+suffix); self._update_display_scale(self.gp_reconstructed_field)

    def _update_display_scale(self,f_data):
        def_max=NORMAL_O2_PERCENTAGE if self.current_gas_view.get()=="O2" else NORMAL_CO2_PPM*5 # Adjusted default CO2 max for better scale
        if f_data.size>0: self.current_gp_display_min,self.current_gp_display_max=np.min(f_data),np.max(f_data)
        else: self.current_gp_display_min,self.current_gp_display_max=0.0,def_max
        if self.current_gp_display_max<=self.current_gp_display_min:
            val=self.current_gp_display_min; adj1,adj2=(0.1,1.0) if self.current_gas_view.get()=="O2" else (10.0,100.0)
            self.current_gp_display_min=max(0,val-0.5*abs(val)-adj1); self.current_gp_display_max=val+0.5*abs(val)+adj1
            if abs(self.current_gp_display_max-self.current_gp_display_min)<(0.01 if self.current_gas_view.get()=="O2" else 1.0): self.current_gp_display_max=self.current_gp_display_min+adj2
        self.field_scale_label_var.set(f"GP Scale ({self.current_gas_view.get()}): {self.current_gp_display_min:.1f}-{self.current_gp_display_max:.1f}")

    def get_color_from_value(self,val,min_v,max_v): # Used for GP field cells
        norm_v=0.5 if max_v<=min_v else np.clip((val-min_v)/(max_v-min_v),0,1)
        # O2: Red (low) -> Yellow (mid) -> Green (high)
        # CO2: Green (low) -> Yellow (mid) -> Red (high)
        cmap_n='RdYlGn' if self.current_gas_view.get()=="O2" else 'RdYlGn_r' # _r reverses colormap for CO2
        try: return mcolors.to_hex(cm.get_cmap(cmap_n)(norm_v))
        except Exception as e: print(f"Color Error: {e}"); return "#FFFFFF" # Default white on error

    def draw_color_scale(self):
        self.color_scale_canvas.delete("all"); min_v,max_v=self.current_gp_display_min,self.current_gp_display_max
        if max_v<=min_v: adj=(1.0 if self.current_gas_view.get()=="O2" else 100.0); max_v=min_v+(0 if abs(min_v)<1e-6 and abs(max_v)<1e-6 else adj) # Ensure max_v > min_v
        range_v=max_v-min_v; range_v=range_v if abs(range_v)>= (0.001 if self.current_gas_view.get()=="O2" else 1.0) else (1.0 if self.current_gas_view.get()=="O2" else 100.0) # Prevent zero range

        n_seg=50; seg_h=(CANVAS_HEIGHT-2*AXIS_MARGIN)/n_seg; bar_w=20; x_off=15
        for i in range(n_seg):
            y0,y1=AXIS_MARGIN+i*seg_h,AXIS_MARGIN+(i+1)*seg_h
            # Value for color mapping needs to correspond to visual top-to-bottom scale
            val_map = max_v - (i / n_seg) * range_v # Top of scale bar is max_v
            color_seg=self.get_color_from_value(val_map,min_v,max_v); self.color_scale_canvas.create_rectangle(x_off,y0,x_off+bar_w,y1,fill=color_seg,outline=color_seg)

        lbl_x=x_off+bar_w+7;
        self.color_scale_canvas.create_text(lbl_x,AXIS_MARGIN,text=f"{max_v:.1f}",anchor=tk.NW,font=LABEL_FONT,fill=LABEL_COLOR) # Max at top
        self.color_scale_canvas.create_text(lbl_x,CANVAS_HEIGHT-AXIS_MARGIN,text=f"{min_v:.1f}",anchor=tk.SW,font=LABEL_FONT,fill=LABEL_COLOR) # Min at bottom
        mid_v=min_v+range_v/2; mid_y=AXIS_MARGIN+(CANVAS_HEIGHT-2*AXIS_MARGIN)/2; self.color_scale_canvas.create_text(lbl_x,mid_y,text=f"{mid_v:.1f}",anchor=tk.W,font=LABEL_FONT,fill=LABEL_COLOR)
        unit="%" if self.current_gas_view.get()=="O2" else "ppm"; self.color_scale_canvas.create_text(COLOR_SCALE_WIDTH/2,AXIS_MARGIN/2-5,text=f"GP {self.current_gas_view.get()}",anchor=tk.S,font=LABEL_FONT,fill=LABEL_COLOR); self.color_scale_canvas.create_text(COLOR_SCALE_WIDTH/2,AXIS_MARGIN/2+5,text=f"({unit})",anchor=tk.N,font=LABEL_FONT,fill=LABEL_COLOR)

    def toggle_simulation(self):
        if self.sim_running:
            self.sim_running=False;
            if self.sim_job_id: self.after_cancel(self.sim_job_id); self.sim_job_id=None
            self.update_gp_model_and_predict(); self.draw_field_visualization(); self.draw_color_scale(); self.sim_toggle_button.config(text="Initialize & Run Sim")
            for c in self.drawing_controls_frame.winfo_children():
                if isinstance(c,(ttk.Radiobutton,ttk.Button,ttk.Scale,ttk.Spinbox,ttk.OptionMenu)): c.config(state=tk.NORMAL)
            for frame_to_enable in [self.room_params_frame, self.sensor_params_frame]:
                 if frame_to_enable.winfo_ismapped(): # Check if frame is visible
                    for c in frame_to_enable.winfo_children():
                        if isinstance(c,(ttk.Scale,ttk.Spinbox,ttk.OptionMenu)): c.config(state=tk.NORMAL)
            self.colony_size_scale.config(state=tk.NORMAL) # Enable colony slider
            self._show_element_params_frame()
        else:
            if not self.rooms_list: self.sim_status_label_var.set("Draw rooms first!"); return
            # Removed SKLEARN_AVAILABLE check for starting sim, GP will just show truth if not available
            self.sim_running=True;
            if self.oxygen_tab_ref: # Ensure oxygen_tab_ref exists
                people = self.oxygen_tab_ref.generate_new_colony(self.colony_size)
                days   = self.oxygen_tab_ref.initial_days # Or a dynamic value
                algae_area  = self.get_algae_greenhouse_area()
                potato_area = self.get_potato_greenhouse_area()
                self.o2_profile, _, _, _ = self.oxygen_tab_ref.simulate_oxygen_over_time(
                    people, days, algae_area, potato_area
                )
            else: # Fallback if oxygen_tab_ref is not set
                self.o2_profile = np.full(100, NORMAL_O2_PERCENTAGE) # Default profile
                print("Warning: Oxygen tab reference not found, using default O2 profile.")

            self.sim_time_hours = 0.0
            if self.selected_room_obj: self.selected_room_obj.deselect(self.drawing_canvas); self.selected_room_obj=None
            if self.selected_sensor_obj: self.selected_sensor_obj.deselect(self.drawing_canvas); self.selected_sensor_obj=None
            self._show_element_params_frame() # Hide params frames

            self.prepare_visualization_map_and_fields(); self.gp_update_counter=0; self.update_gp_model_and_predict(); self.draw_field_visualization(); self.draw_color_scale(); self.sim_toggle_button.config(text="Stop & Clear Sim") # Changed button text
            self.mode_var.set("select") # Force select mode
            for c in self.drawing_controls_frame.winfo_children():
                if isinstance(c,ttk.Radiobutton) and c.cget("value")!="select": c.config(state=tk.DISABLED)
                elif isinstance(c,ttk.Button) and c != self.sim_toggle_button : c.config(state=tk.DISABLED) # Keep sim toggle enabled
            for frame_to_disable in [self.room_params_frame, self.sensor_params_frame]:
                if frame_to_disable.winfo_ismapped():
                    for c in frame_to_disable.winfo_children():
                        if isinstance(c,(ttk.Scale,ttk.Spinbox,ttk.OptionMenu)): c.config(state=tk.DISABLED)
            self.colony_size_scale.config(state=tk.DISABLED) # Disable colony slider during sim
            if not self.sim_job_id: self.run_simulation_step()

    def draw_field_visualization(self): # For GP field cells
        min_v,max_v=self.current_gp_display_min,self.current_gp_display_max; disp_f=self.gp_reconstructed_field
        for ri in range(self.sim_grid_rows):
            for ci in range(self.sim_grid_cols):
                cid=self.field_vis_cells.get((ri,ci))
                if cid:
                    # For GP field, color depends on map_mask (inside/outside rooms)
                    # If outside a defined room (mask=0), use Mars ambient, else use GP reconstructed value
                    val_to_color = (MARS_O2_PERCENTAGE if self.current_gas_view.get()=="O2" else MARS_CO2_PPM) \
                                   if self.map_mask[ri,ci]==0 else disp_f[ri,ci]
                    color=self.get_color_from_value(val_to_color, min_v,max_v)
                    self.drawing_canvas.itemconfig(cid,fill=color,outline=color)
        self.drawing_canvas.tag_raise("user_shape"); self.drawing_canvas.tag_raise("sensor_marker"); self.drawing_canvas.tag_raise("leak")

    def run_simulation_step(self):
        if not self.sim_running:
            if self.sim_job_id: self.after_cancel(self.sim_job_id); self.sim_job_id = None
            return

        self.sim_time_hours += SIM_DT_HOURS
        current_day_idx = min(len(self.o2_profile) - 1, int(self.sim_time_hours / 24.0)) if self.o2_profile is not None and len(self.o2_profile) > 0 else 0
        self.day_label_var.set(f"Day: {current_day_idx}")

        target_o2_from_profile = self.o2_profile[current_day_idx] if self.o2_profile is not None and current_day_idx < len(self.o2_profile) else NORMAL_O2_PERCENTAGE

        # Update room O2 levels based on the profile (simplified)
        for room in self.rooms_list:
            if room.room_type != RoomType.NONE and room.room_type != RoomType.SOLAR_PANELS: # Non-functional rooms don't change
                # Here, you might want a more gradual change or room-specific logic
                room.o2_level = target_o2_from_profile # Directly set from profile for now
                # CO2 could be linked to O2 consumption/production if modeled
                # room.co2_level = ...

        # Rebuild ground truth fields from room states
        self.o2_field_ground_truth.fill(MARS_O2_PERCENTAGE)
        self.co2_field_ground_truth.fill(MARS_CO2_PPM)
        for ri_grid in range(self.sim_grid_rows):
            for ci_grid in range(self.sim_grid_cols):
                cx_center, cy_center = self._sim_to_canvas_coords_center(ri_grid, ci_grid)
                for room_obj in self.rooms_list:
                    if room_obj.room_type != RoomType.NONE and room_obj.contains_point(cx_center, cy_center):
                        self.o2_field_ground_truth[ri_grid, ci_grid] = room_obj.o2_level
                        self.co2_field_ground_truth[ri_grid, ci_grid] = room_obj.co2_level
                        break # Cell is in this room

        self._apply_leaks() # Apply leaks after setting base room levels

        self.gp_update_counter += 1
        if (self.gp_update_counter >= GP_UPDATE_EVERY_N_FRAMES or not SKLEARN_AVAILABLE or not self.sensors_list):
            self.update_gp_model_and_predict() # This also updates sensor readings internally
            self.gp_update_counter = 0

        # Refresh on-screen labels for selected items
        if self.selected_room_obj:
            self.room_o2_label.config(text=f"O2: {self.selected_room_obj.o2_level:.2f}%")
            self.room_co2_label.config(text=f"CO2: {self.selected_room_obj.co2_level:.0f} ppm")
        if self.selected_sensor_obj: # Sensor readings were updated in update_gp_model_and_predict via collect_sensor_data
            o2r, co2r = self.selected_sensor_obj.last_o2_reading, self.selected_sensor_obj.last_co2_reading
            self.sensor_o2_reading_label.config(text=f"O2 Read: {o2r:.2f}%" if o2r is not None else "N/A")
            self.sensor_co2_reading_label.config(text=f"CO2 Read: {co2r:.0f} ppm" if co2r is not None else "N/A")

        # Redraw dynamic parts of the canvas
        for room_obj_draw in self.rooms_list: # Redraw rooms to reflect O2 color changes
            room_obj_draw.draw(self.drawing_canvas)
        self.draw_field_visualization() # Redraw GP field
        self.draw_color_scale() # Redraw color scale if its range changed

        # Update other tabs
        if self.oxygen_tab_ref and hasattr(self.oxygen_tab_ref, 'update_plot'): self.oxygen_tab_ref.update_plot()
        if self.potatoes_tab_ref and hasattr(self.potatoes_tab_ref, 'update_plot'): self.potatoes_tab_ref.update_plot()
        if self.solar_tab_ref and hasattr(self.solar_tab_ref, 'plot_energy'): self.solar_tab_ref.plot_energy() # Solar tab might not need per-step if area doesn't change
        if self.overall_energy_tab_ref and hasattr(self.overall_energy_tab_ref, 'refresh_plot'): # ADDED
            self.overall_energy_tab_ref.refresh_plot()


        self.sim_job_id = self.after(int(SIM_STEP_REAL_TIME_SECONDS * 1000), self.run_simulation_step)

    def get_o2_color(self, o2_level, min_o2=MARS_O2_PERCENTAGE, max_o2=NORMAL_O2_PERCENTAGE): # Used for room fill colors
        # Clamp o2_level to avoid errors with Normalize
        o2_level_clamped = np.clip(o2_level, min_o2, max_o2)
        norm = mcolors.Normalize(vmin=min_o2, vmax=max_o2)
        cmap = cm.get_cmap('RdYlGn') # Red (low O2) -> Yellow -> Green (high O2)
        rgba = cmap(norm(o2_level_clamped))
        return mcolors.to_hex(rgba)


try: raise ImportError("Placeholders for Person and oxygen_production if not defined elsewhere")
except ImportError:
    class Person:
        def __init__(self,ocr=0.83): self._ocr=ocr # kg O2 per day
        def oxygen_consumption(self): return self._ocr # kg O2 per day
    def oxygen_production(algae_a,potato_a): # kg O2 per day
        # These are example rates, adjust as needed
        # algae: 0.1 kg O2 / m^2 / day
        # potato: 0.05 kg O2 / m^2 / day (net, considering plant respiration)
        return algae_a*0.1 + potato_a*0.05

CO2_PER_O2_MASS_RATIO=44.0095/31.9988 # Molar mass CO2 / Molar mass O2

class OxygenVisualizerTab(ttk.Frame):
    def __init__(self, master, drawing_app_ref, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.drawing_app_ref = drawing_app_ref
        self.initial_days = 100 # Default initial simulation duration for this tab's internal model
        self.current_colony_list = [] # Will be populated by drawing_app_ref or default
        self.fig,self.ax = plt.subplots(figsize=(10,6)); self.canvas=FigureCanvasTkAgg(self.fig,master=self); self.canvas.get_tk_widget().pack(side=tk.TOP,fill=tk.BOTH,expand=True)
        self.fig.subplots_adjust(left=0.1,bottom=0.15, top=0.9) # Adjusted bottom for potential slider later

        # Initialize plot elements one time
        self.line, = self.ax.plot([], [], lw=2, label='Oxygen Reserve (kg)') # O2 reserve over time
        self.consumption_line = self.ax.axhline(y=0, color='r', ls='--', label='Daily O₂ Consumption Buffer')
        self.production_line = self.ax.axhline(y=0, color='g', ls='--', label='Daily O₂ Production Buffer')
        # self.co2_consumption_line = self.ax.axhline(y=0, color='c', ls=':', label='Daily CO₂ Consumption by Plants Buffer') # CO2 might be complex
        self.balance_line = self.ax.axhline(y=0, color='black', ls='-', alpha=0.3) # Zero line for net change reference

        self.net_text = self.ax.text(0.7, 0.9, '', transform=self.ax.transAxes, bbox=dict(fc='white', alpha=0.7))
        self.status_text = self.ax.text(0.8, 0.8, '', transform=self.ax.transAxes, fontsize=12, fontweight='bold', bbox=dict(fc='white', alpha=0.7))

        self.ax.set_xlabel('Sols (Mars Days)'); self.ax.set_ylabel('Oxygen Mass (kg)')
        self.ax.legend(loc='upper left', fontsize='small'); self.ax.grid(True)
        self.ax.set_title('Habitat Oxygen & CO₂ Dynamics')

        self.refresh_with_new_areas() # Initial call

    def refresh_with_new_areas(self): # Called when areas change in DrawingApp
        if self.drawing_app_ref and hasattr(self.drawing_app_ref, 'get_algae_greenhouse_area'):
            self.update_plot()
        else:
            self.after(100, self.refresh_with_new_areas) # Retry if drawing_app_ref not ready

    def generate_new_colony(self,s): return [Person() for _ in range(int(s))]

    def simulate_oxygen_over_time(self,people_list, num_days, algae_area_m2, potato_area_m2):
        num_days=int(num_days)
        daily_o2_consumption_total = sum(p.oxygen_consumption() for p in people_list) # kg/day
        daily_o2_production_total = oxygen_production(algae_area_m2, potato_area_m2) # kg/day

        # CO2 production by humans is linked to O2 consumption (e.g., Respiratory Quotient ~0.8-1.0)
        # daily_co2_production_humans_kg = daily_o2_consumption_total * CO2_PER_O2_MASS_RATIO * 0.85 # Approx.
        # CO2 consumption by plants (photosynthesis) is linked to O2 production
        # daily_co2_consumption_plants_kg = daily_o2_production_total * CO2_PER_O2_MASS_RATIO

        net_daily_o2_change = daily_o2_production_total - daily_o2_consumption_total # kg/day

        # Initial reserve: e.g., 30 days of consumption needs
        initial_o2_reserve_kg = daily_o2_consumption_total * 30 if daily_o2_consumption_total > 0 else 100 # Arbitrary fallback
        o2_levels_over_time = [initial_o2_reserve_kg]

        if num_days > 0:
            for _ in range(1, num_days + 1):
                # Add some variability/efficiency factor to change
                variability = np.random.normal(1.0, 0.05) # +/- 5% daily variation
                change_this_day = net_daily_o2_change * variability
                new_level = o2_levels_over_time[-1] + change_this_day
                o2_levels_over_time.append(max(0, new_level)) # Cannot go below 0

        return np.array(o2_levels_over_time[:num_days+1]), daily_o2_consumption_total, daily_o2_production_total, 0 # Placeholder for CO2 consumption by plants

    def update_plot(self,val=None):
        if not (self.drawing_app_ref and hasattr(self.drawing_app_ref, 'sim_time_hours')):
            return # Not ready

        current_colony_size = self.drawing_app_ref.colony_size
        if not self.current_colony_list or len(self.current_colony_list) != current_colony_size:
            self.current_colony_list = self.generate_new_colony(current_colony_size)

        current_sim_day = int(self.drawing_app_ref.sim_time_hours // 24)
        # Simulate for a bit longer than current day for plotting horizon, or use a fixed plot duration
        plot_duration_days = max(current_sim_day + 1, self.initial_days) # Ensure we plot at least initial_days or up to current progress

        algae_m2 = self.drawing_app_ref.get_algae_greenhouse_area()
        potato_m2 = self.drawing_app_ref.get_potato_greenhouse_area()

        o2_reserve_history, o2_cons_daily, o2_prod_daily, _ = self.simulate_oxygen_over_time(
            self.current_colony_list, plot_duration_days, algae_m2, potato_m2
        )
        sols_axis = np.arange(plot_duration_days + 1)

        self.line.set_xdata(sols_axis)
        self.line.set_ydata(o2_reserve_history)

        # Update buffer lines (representing daily rates scaled to a buffer amount, e.g., 30x for visual comparison)
        buffer_scale = 30 # e.g., visualize 30-day equivalent of daily rates
        self.consumption_line.set_ydata([o2_cons_daily * buffer_scale, o2_cons_daily * buffer_scale])
        self.production_line.set_ydata([o2_prod_daily * buffer_scale, o2_prod_daily * buffer_scale])
        self.consumption_line.set_label(f'O₂ Cons Buf ({buffer_scale}d): {o2_cons_daily:.2f} kg/d')
        self.production_line.set_label(f'O₂ Prod Buf ({buffer_scale}d): {o2_prod_daily:.2f} kg/d')

        net_o2_daily_rate = o2_prod_daily - o2_cons_daily
        self.net_text.set_text(f'Net Daily O₂: {net_o2_daily_rate:.2f} kg/d')
        self.net_text.set_bbox(dict(facecolor='lightgreen' if net_o2_daily_rate>=0 else 'lightcoral',alpha=0.7))

        status_str, status_color = "UNSUSTAINABLE (O₂)", "darkred"
        if o2_cons_daily > 0 and (o2_prod_daily / o2_cons_daily) >= 1.1: # Sustainable if prod is 10% > cons
            status_str, status_color = "SUSTAINABLE (O₂)", "darkgreen"
        elif net_o2_daily_rate >= 0: # Marginal if net is non-negative but not strongly sustainable
            status_str, status_color = "MARGINAL (O₂)", "darkorange"
        self.status_text.set_text(status_str); self.status_text.set_color(status_color)

        self.ax.set_title(f'O₂ Dynamics (Col: {current_colony_size}, Algae: {algae_m2:.1f}m², Potato: {potato_m2:.1f}m²)')

        # Auto-scaling Y axis
        self.ax.relim(); self.ax.autoscale_view(True,True,True)
        min_y, max_y = self.ax.get_ylim()
        self.ax.set_ylim(min(min_y, -10), max(max_y, 100)) # Ensure 0 is visible and some padding


        # Set X axis to a relevant window around the current simulation day
        window_sols = 60 # Display a window of 60 sols
        plot_end_sol = max(sols_axis[-1] if len(sols_axis) > 0 else 1, window_sols)
        plot_start_sol = max(0, plot_end_sol - window_sols)
        self.ax.set_xlim([plot_start_sol, plot_end_sol])


        self.ax.legend(loc='upper left',fontsize='small'); self.fig.canvas.draw_idle()


P_POTATO_YIELD_PER_SQ_METER_PER_CYCLE=5.0; P_CHLORELLA_YIELD_PER_SQ_METER_PER_CYCLE=0.1
P_POTATO_HARVEST_CYCLE_DAYS=100; P_CHLORELLA_CYCLE_DAYS=7
P_AVG_DAILY_POTATO_YIELD_PER_M2=P_POTATO_YIELD_PER_SQ_METER_PER_CYCLE/P_POTATO_HARVEST_CYCLE_DAYS
P_AVG_DAILY_CHLORELLA_YIELD_PER_M2=P_CHLORELLA_YIELD_PER_SQ_METER_PER_CYCLE/P_CHLORELLA_CYCLE_DAYS
P_KCAL_PER_KG_POTATO=770; P_KCAL_PER_KG_CHLORELLA=3500; P_KCAL_PER_PERSON_PER_DAY=2000
P_INITIAL_MAX_DAYS=100; P_INITIAL_NUM_PEOPLE=4

class PotatoesCaloriesTab(ttk.Frame):
    def __init__(self, master, drawing_app_ref, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.drawing_app_ref = drawing_app_ref
        self.fig,self.ax=plt.subplots(figsize=(10,6)); self.canvas=FigureCanvasTkAgg(self.fig,master=self); self.canvas.get_tk_widget().pack(side=tk.TOP,fill=tk.BOTH,expand=True)
        self.fig.subplots_adjust(left=0.1,bottom=0.15,right=0.95,top=0.85) # Adjusted bottom for legend
        days_init=np.array([0,P_INITIAL_MAX_DAYS]); init_pot_kcal,init_chl_kcal,init_dem_kcal,init_net_kcal = 0,0,0,0
        self.l_pot, = self.ax.plot(days_init,[init_pot_kcal]*2,label='Daily Potato Calories',color='saddlebrown',lw=2)
        self.l_chl, = self.ax.plot(days_init,[init_chl_kcal]*2,label='Daily Chlorella Calories',color='forestgreen',lw=2)
        self.l_dem, = self.ax.plot(days_init,[init_dem_kcal]*2,label='Daily People Demand',color='crimson',ls='--',lw=2)
        self.l_net, = self.ax.plot(days_init,[init_net_kcal]*2,label='Net Daily Calories',color='blue',ls=':',lw=2.5)
        txt_box=dict(boxstyle='round,pad=0.3',fc='aliceblue',alpha=0.95,ec='silver'); self.stat_good=dict(boxstyle='round,pad=0.4',fc='honeydew',alpha=0.95,ec='darkgreen'); self.stat_bad=dict(boxstyle='round,pad=0.4',fc='mistyrose',alpha=0.95,ec='darkred')

        # Using figure text for dynamic stats to avoid overlap with plot elements
        y_start_text = 0.97
        self.txt_pot=self.fig.text(0.02,y_start_text,'',fontsize=8,va='top',bbox=txt_box)
        self.txt_chl=self.fig.text(0.02,y_start_text-0.035,'',fontsize=8,va='top',bbox=txt_box)
        self.txt_spc=self.fig.text(0.02,y_start_text-0.07,'',fontsize=8,va='top',bbox=txt_box)
        self.txt_dem=self.fig.text(0.35,y_start_text,'',fontsize=8,va='top',bbox=txt_box)
        self.txt_ppl=self.fig.text(0.35,y_start_text-0.035,'',fontsize=8,va='top',bbox=txt_box)
        self.txt_net=self.fig.text(0.35,y_start_text-0.07,'',fontsize=8,va='top',bbox=txt_box)
        self.txt_stat=self.fig.text(0.7,y_start_text-0.02,'',fontsize=9,fontweight='bold',va='top') # Centered title-like status

        self.ax.set_xlabel('Sols (Mars Days)',fontsize=12); self.ax.set_ylabel('Daily Calories (kcal/day)',fontsize=12); self.ax.set_title('Daily Caloric Production vs. Demand',fontsize=14,y=1.08); self.ax.grid(True,which='major',ls='--',lw=0.5)
        self.ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.18), ncol=4, fontsize='small') # Adjusted legend position

        self.refresh_with_new_areas() # Initial call

    def refresh_with_new_areas(self):
        if self.drawing_app_ref and hasattr(self.drawing_app_ref, 'get_algae_greenhouse_area'):
            self.update_plot()
        else:
            self.after(100, self.refresh_with_new_areas)

    def update_plot(self,val=None):
        if not (self.drawing_app_ref and hasattr(self.drawing_app_ref, 'sim_time_hours')):
            return # Not ready

        ppl = self.drawing_app_ref.colony_size
        current_sim_day = int(self.drawing_app_ref.sim_time_hours // 24)
        plot_duration_sols = max(current_sim_day +1, 1) # Plot at least one sol

        pot_m2=(self.drawing_app_ref.get_potato_greenhouse_area())
        chl_m2=(self.drawing_app_ref.get_algae_greenhouse_area())

        sols_data_array=np.array([0,plot_duration_sols]) # For horizontal lines

        k_pot=pot_m2*P_AVG_DAILY_POTATO_YIELD_PER_M2*P_KCAL_PER_KG_POTATO;
        k_chl=chl_m2*P_AVG_DAILY_CHLORELLA_YIELD_PER_M2*P_KCAL_PER_KG_CHLORELLA
        k_dem=ppl*P_KCAL_PER_PERSON_PER_DAY;
        k_net=k_pot+k_chl-k_dem

        self.l_pot.set_data(sols_data_array,[k_pot]*2); self.l_chl.set_data(sols_data_array,[k_chl]*2);
        self.l_dem.set_data(sols_data_array,[k_dem]*2); self.l_net.set_data(sols_data_array,[k_net]*2)

        all_y_values=[k_pot,k_chl,k_dem,k_net,0];
        min_yp,max_yp = min(all_y_values), max(all_y_values)
        y_padding = (max_yp - min_yp) * 0.15 if (max_yp - min_yp) > 100 else 50 # Ensure some padding
        final_min_y = min_yp - y_padding
        final_max_y = max_yp + y_padding
        if final_min_y == final_max_y: final_max_y += 100 # Prevent zero range

        self.ax.set_ylim([final_min_y,final_max_y])
        self.ax.set_xlim([0,plot_duration_sols])


        self.txt_pot.set_text(f'Potato Supply: {k_pot:,.0f} kcal/d'); self.txt_chl.set_text(f'Chlorella Supply: {k_chl:,.0f} kcal/d')
        self.txt_spc.set_text(f'Potato GH: {pot_m2:.1f} m² | Algae GH: {chl_m2:.1f} m²'); self.txt_dem.set_text(f'People Demand: {k_dem:,.0f} kcal/d')
        self.txt_ppl.set_text(f'{int(ppl)} People'); self.txt_net.set_text(f'Net Balance: {k_net:,.0f} kcal/d')
        s_txt,s_col,s_box=('Sustainable','darkgreen',self.stat_good) if k_net>=0 else ('Unsustainable','darkred',self.stat_bad)
        self.txt_stat.set_text(f'Overall System:\n{s_txt}'); self.txt_stat.set_color(s_col); self.txt_stat.set_bbox(s_box)

        self.fig.canvas.draw_idle()


class EnergySimulationTabBase(ttk.Frame):
    def __init__(self, master, title, input_label_text, slider_unit,
                 initial_slider_max=100, create_slider_controls=True, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.user_input_var = tk.DoubleVar(value=0)

        self.fig, self.ax = plt.subplots(figsize=(10, 5))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=5)
        self.canvas_widget.bind("<Configure>", self._on_canvas_resize)
        self.fig.subplots_adjust(bottom=0.2, top=0.9) # Adjusted bottom for controls

        self.controls_frame = ttk.Frame(self)
        self.controls_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5, padx=10)

        ttk.Label(self.controls_frame, text=title, font=("Courier", 14)).pack(pady=(0,5))

        if create_slider_controls:
            input_controls_frame = ttk.Frame(self.controls_frame); input_controls_frame.pack(pady=2)
            ttk.Label(input_controls_frame, text=input_label_text, font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
            self.slider = tk.Scale(input_controls_frame, from_=0, to=initial_slider_max, length=250, orient=tk.HORIZONTAL, variable=self.user_input_var, command=self.plot_energy_triggered)
            self.slider.pack(side=tk.LEFT, padx=5)

            limit_frame = ttk.Frame(self.controls_frame); limit_frame.pack(pady=2)
            ttk.Label(limit_frame, text=f"Set Slider Max ({slider_unit}):", font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
            self.entry_limit = ttk.Entry(limit_frame, font=("Arial", 9), width=7); self.entry_limit.pack(side=tk.LEFT, padx=5)
            self.entry_limit.insert(0, str(initial_slider_max))
            ttk.Button(limit_frame, text="Update Max", command=self.update_limit, style="Small.TButton").pack(side=tk.LEFT, padx=5) # Add style if defined
            self.status_label = ttk.Label(self.controls_frame, text="Adjust slider.", font=("Arial", 8))
            self.status_label.pack(pady=(2,0))
            self.plot_energy() # Initial plot
        else:
            self.data_source_label_var = tk.StringVar(value=input_label_text)
            self.data_source_label = ttk.Label(self.controls_frame, textvariable=self.data_source_label_var, font=("Arial", 10))
            self.data_source_label.pack(pady=5)
            self.status_label = ttk.Label(self.controls_frame, text="Area derived from Habitat Design.", font=("Arial", 8))
            self.status_label.pack(pady=(2,0))
            # Initial plot will be triggered by refresh from drawing_app

    def plot_energy_triggered(self, val=None): # Wrapper for slider command
        self.plot_energy(val)
        # After this tab's plot updates, if it's one of the source tabs for OverallEnergyTab,
        # it should trigger OverallEnergyTab's refresh.
        # This is better handled by DrawingApp or MainApplication to avoid circular dependencies.
        # For now, DrawingApp's sim step / area update will trigger overall refresh.

    def _on_canvas_resize(self, event):
        width, height = event.width, event.height
        dpi = self.fig.get_dpi()
        self.fig.set_size_inches(width / dpi, height / dpi)
        self.canvas.draw_idle() # Use draw_idle for Configure events

    def plot_energy(self, val=None): raise NotImplementedError("Subclasses must implement plot_energy.")
    def update_limit(self):
        if hasattr(self, 'entry_limit'):
            try:
                new_lim = float(self.entry_limit.get())
                is_valid = (new_lim > 0) if self.__class__.__name__ != "SabatierEnergyTab" else (new_lim >=0)
                if is_valid:
                    if hasattr(self, 'slider'): self.slider.config(to=new_lim)
                    self.status_label.config(text=f"Slider max: {new_lim:.0f}.", foreground="black")
                else: self.status_label.config(text="Limit must be >0 (or >=0 for Sabatier).", foreground="red")
            except ValueError: self.status_label.config(text="Invalid number for limit.", foreground="red")

class SolarEnergyTab(EnergySimulationTabBase):
    def __init__(self, master, drawing_app_ref, *args, **kwargs):
        super().__init__(master, "Mars Solar Energy Calculator",
                         "Panel Area: 0.00 m² (from Habitat)", "m²",
                         initial_slider_max=100,
                         create_slider_controls=False, # Opt-out of slider
                         *args, **kwargs)
        self.drawing_app_ref = drawing_app_ref
        self.y_energy_kj_data = None # To store the full series for OverallEnergyTab
        self.refresh_with_new_area()

    def refresh_with_new_area(self): # Called by DrawingApp when solar panel area changes
        if self.drawing_app_ref and hasattr(self.drawing_app_ref, 'get_solar_panel_area'):
            self.plot_energy() # This will use the new area
        else:
            self.after(100, self.refresh_with_new_area)

    def plot_energy(self, val=None): # val is not used as area comes from DrawingApp
        self.ax.clear()
        current_input_area = 0.0
        if self.drawing_app_ref and hasattr(self.drawing_app_ref, 'get_solar_panel_area'):
            current_input_area = self.drawing_app_ref.get_solar_panel_area()

        if hasattr(self, 'data_source_label_var'):
             self.data_source_label_var.set(f"Panel Area: {current_input_area:.2f} m² (from Habitat)")

        # Simulate for a fixed period, e.g., 668 sols (Martian year)
        sols_to_simulate = 668
        dust_factor = np.clip(np.random.normal(0.7, 0.15, size=sols_to_simulate), 0.2, 1.0) # Dust effect
        panel_efficiency = np.clip(np.random.normal(0.235, 0.02, size=sols_to_simulate), 0.18, 0.27) # Panel efficiency variation
        MARTIAN_AVG_IRRADIANCE_WM2 = 586 # W/m^2
        SECONDS_IN_EFFECTIVE_SOLAR_DAY = 88775 * 0.5 # Approx half a sol for power generation
        x_sols_array = np.arange(1, sols_to_simulate + 1)

        self.y_energy_kj_data = (MARTIAN_AVG_IRRADIANCE_WM2 * current_input_area * panel_efficiency * dust_factor * SECONDS_IN_EFFECTIVE_SOLAR_DAY * 0.001) # kJ per sol

        self.ax.plot(x_sols_array, self.y_energy_kj_data, color="orange", alpha=0.8, label='Daily Solar Energy (kJ/sol)') # Changed to plot from scatter
        self.ax.set_title(f"Solar Energy for {current_input_area:.2f} m² Panels", fontsize=10)
        self.ax.set_xlabel("Sols (Mars Days)", fontsize=9); self.ax.set_ylabel("Energy Output (kJ/sol)", fontsize=9)
        self.ax.tick_params(axis='both', which='major', labelsize=8)
        self.ax.legend(fontsize=8); self.ax.grid(True, alpha=0.3);
        self.ax.set_xlim([0, sols_to_simulate]) # Set x-limit to simulation duration
        self.ax.relim(); self.ax.autoscale_view(True, False, True) # Autoscale Y, keep X fixed after set_xlim
        self.canvas.draw_idle()

        if hasattr(self, 'status_label'):
            avg_energy = np.mean(self.y_energy_kj_data) if len(self.y_energy_kj_data) > 0 else 0
            self.status_label.config(text=f"Avg: {avg_energy:,.0f} kJ/sol (Area: {current_input_area:.2f} m²)", foreground="black")


class NuclearEnergyTab(EnergySimulationTabBase):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, "Mars Nuclear Energy Calculator", "Pu-239 Amount (kg):", "kg", 10, *args, **kwargs)
        self.y_energy_kj_data = None # To store the full series

    def plot_energy(self, val=None):
        self.ax.clear(); current_in = self.user_input_var.get()
        BASE_KJ_PER_KG_PER_SOL = 80000 # Simplified constant output rate
        sols_to_simulate = 668 # Match solar tab for consistency
        efficiency_decay = np.clip(np.random.normal(0.85, 0.03, size=sols_to_simulate), 0.75, 0.90) # Slight variation
        x_sols_array = np.arange(1, sols_to_simulate + 1)
        self.y_energy_kj_data = current_in * BASE_KJ_PER_KG_PER_SOL * efficiency_decay # kJ per sol

        self.ax.plot(x_sols_array, self.y_energy_kj_data, color="limegreen", alpha=0.8, label='Daily Nuclear Energy (kJ/sol)')
        self.ax.set_title(f"Nuclear Energy for {current_in:.1f} kg Pu-239", fontsize=10); self.ax.set_xlabel("Sols (Mars Days)", fontsize=9); self.ax.set_ylabel("Energy Output (kJ/sol)", fontsize=9)
        self.ax.tick_params(axis='both', which='major', labelsize=8)
        self.ax.legend(fontsize=8); self.ax.grid(True, alpha=0.3);
        self.ax.set_xlim([0, sols_to_simulate]);
        self.ax.relim(); self.ax.autoscale_view(True, False, True)
        self.canvas.draw_idle()
        avg_energy = np.mean(self.y_energy_kj_data) if len(self.y_energy_kj_data) > 0 else 0
        self.status_label.config(text=f"Avg: {avg_energy:,.0f} kJ/sol for {current_in:.1f} kg Pu-239.", foreground="black")

class SabatierEnergyTab(EnergySimulationTabBase):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, "Mars Methane (Sabatier) Energy", "H₂O for Sabatier (kg/sol):", "kg H₂O", 100, *args, **kwargs)
        self.daily_energy_output_kj_data = None # To store the full series

    def plot_energy(self, val=None):
        self.ax.clear(); water_input_kg_per_sol = self.user_input_var.get()
        MOLAR_MASS_CH4_G_PER_MOL, MOLAR_MASS_H2O_G_PER_MOL = 16.04, 18.01528
        # Sabatier: CO2 + 4H2 -> CH4 + 2H2O. H2 often from electrolysis of H2O: 2H2O -> 2H2 + O2
        # So, to get 4 H2, we need 4 H2O (if H2 comes from H2O electrolysis and we are tracking input H2O for H2 part)
        # Or, if the input is H2O fed *directly* to a system that includes electrolysis for H2:
        # For CH4, we need 4 moles of H2. If these 4 moles of H2 come from electrolysis of 2 * (2H2O) -> 2 * (2H2),
        # it implies 4 moles of H2O are ultimately involved if the H2 is sourced this way.
        # However, the reaction is often quoted with supplied H2.
        # Let's assume the "water_input_kg_per_sol" is water used to PRODUCE the H2 needed.
        # 2H2O -> 2H2 + O2. So, 2 moles H2O gives 2 moles H2.
        # CO2 + 4H2 -> CH4 + 2H2O. Need 4 moles H2. So need 4 moles H2O to make 4 moles H2.
        moles_h2o_input = (water_input_kg_per_sol * 1000) / MOLAR_MASS_H2O_G_PER_MOL # Moles of H2O used to make H2
        moles_h2_produced_from_input_h2o = moles_h2o_input # Assuming 1:1 molar H2O to H2 for simplicity of input tracking
        
        # Stoichiometry: 4 moles H2 produce 1 mole CH4
        moles_ch4_produced = moles_h2_produced_from_input_h2o / 4
        mass_ch4_kg_produced_daily = (moles_ch4_produced * MOLAR_MASS_CH4_G_PER_MOL) / 1000

        ENERGY_PER_KG_CH4_KJ = 55000 # Approx. LHV of Methane
        sols_to_simulate = 668
        sabatier_overall_efficiency = np.clip(np.random.normal(0.50, 0.05, size=sols_to_simulate), 0.35, 0.65) # Efficiency of conversion and energy capture
        x_sols_array = np.arange(1, sols_to_simulate + 1)
        self.daily_energy_output_kj_data = mass_ch4_kg_produced_daily * ENERGY_PER_KG_CH4_KJ * sabatier_overall_efficiency

        self.ax.plot(x_sols_array, self.daily_energy_output_kj_data, color="mediumpurple", alpha=0.8, label='Daily Sabatier System Energy (kJ/sol)')
        self.ax.set_title(f"Sabatier Energy from {water_input_kg_per_sol:.1f} kg H₂O/sol for H₂ production", fontsize=10)
        self.ax.set_xlabel("Sols (Mars Days)", fontsize=9); self.ax.set_ylabel("Net Energy Output (kJ/sol)", fontsize=9)
        self.ax.tick_params(axis='both', which='major', labelsize=8)
        self.ax.legend(fontsize=8); self.ax.grid(True, alpha=0.3);
        self.ax.set_xlim([0, sols_to_simulate]);
        self.ax.relim(); self.ax.autoscale_view(True, False, True)
        self.canvas.draw_idle()
        avg_energy = np.mean(self.daily_energy_output_kj_data) if len(self.daily_energy_output_kj_data) > 0 else 0
        self.status_label.config(text=f"Avg: {avg_energy:,.0f} kJ/sol for {water_input_kg_per_sol:.1f} kg H₂O/sol.", foreground="black")


# +++++++++++++++++ NEW OVERALL ENERGY TAB ++++++++++++++++++++++++
class OverallEnergyTab(ttk.Frame):
    def __init__(self, master, drawing_app_ref, solar_tab_ref, nuclear_tab_ref, sabatier_tab_ref, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.drawing_app_ref = drawing_app_ref
        self.solar_tab_ref = solar_tab_ref
        self.nuclear_tab_ref = nuclear_tab_ref
        self.sabatier_tab_ref = sabatier_tab_ref

        # Constants for energy consumption calculation from the first script
        self.UNIV_GAS_CONSTANT = 8.314  # J/molK
        self.ABS_TEMP_EARTH = 296  # Kelvin (desired internal temperature)
        self.ABS_TEMP_MARS = 213  # Kelvin (Mars average external temperature)
        self.MARS_ATM_PRESSURE_ATM = 0.00592154  # atm
        self.EARTH_ATM_PRESSURE_ATM = 0.9997533  # atm (desired internal pressure)
        self.SPECIFIC_HEAT_CAPACITY_AIR = 1005  # J/kgK (for air)
        self.MOLAR_MASS_AIR_KG_PER_MOL = 0.02896 # kg/mol for dry air
        self.ATM_TO_PA = 101325 # Pascals per atmosphere

        self.fig, self.ax = plt.subplots(figsize=(10, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=5)
        self.fig.subplots_adjust(left=0.1, bottom=0.15, right=0.95, top=0.9)

        self.line_solar, = self.ax.plot([], [], label='Solar Gen (kJ/sol)', color='orange', lw=1.5)
        self.line_nuclear, = self.ax.plot([], [], label='Nuclear Gen (kJ/sol)', color='limegreen', lw=1.5)
        self.line_sabatier, = self.ax.plot([], [], label='Sabatier Gen (kJ/sol)', color='mediumpurple', lw=1.5)
        self.line_total_gen, = self.ax.plot([],[], label='Total Gen (kJ/sol)', color='black', lw=2)
        self.line_consumption, = self.ax.plot([], [], label='Consumption (kJ/sol)', color='red', linestyle='--', lw=2)
        self.line_net, = self.ax.plot([], [], label='Net Energy (kJ/sol)', color='blue', linestyle=':', lw=2.5)

        self.ax.set_xlabel("Sols (Mars Days)")
        self.ax.set_ylabel("Energy (kJ/sol)")
        self.ax.set_title("Overall Daily Energy Balance")
        self.ax.legend(loc='upper left', fontsize='small')
        self.ax.grid(True, linestyle=':', alpha=0.7)

        controls_frame = ttk.Frame(self)
        controls_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5, padx=10)
        self.info_label = ttk.Label(controls_frame, text="Aggregated daily energy. Consumption based on current habitat volume.", font=("Arial", 9))
        self.info_label.pack(pady=5)
        self.consumption_details_label = ttk.Label(controls_frame, text="Pressurization: N/A kJ, Heating: N/A kJ", font=("Arial", 9))
        self.consumption_details_label.pack(pady=2)


    def calculate_daily_consumption_kj(self):
        total_volume_m3 = 0
        if self.drawing_app_ref and self.drawing_app_ref.rooms_list:
            for room in self.drawing_app_ref.rooms_list:
                if room.room_type not in [RoomType.NONE, RoomType.SOLAR_PANELS]: # Only pressurized/heated rooms
                    total_volume_m3 += room.get_volume_liters() / 1000.0 # Convert Liters to m^3

        if total_volume_m3 <= 1e-6: # Effectively zero volume
            self.consumption_details_label.config(text="Pressurization: 0 kJ, Heating: 0 kJ (No volume)")
            return 0

        # Moles of air per m^3 at desired Earth-like conditions
        moles_air_per_m3_at_earth_conditions = (self.EARTH_ATM_PRESSURE_ATM * self.ATM_TO_PA) / \
                                             (self.UNIV_GAS_CONSTANT * self.ABS_TEMP_EARTH)
        
        number_moles_total_air = total_volume_m3 * moles_air_per_m3_at_earth_conditions
        mass_air_total_kg = number_moles_total_air * self.MOLAR_MASS_AIR_KG_PER_MOL

        # Energy for Pressurization (Work) - from Mars atm to Earth atm
        # This is the energy to compress the initial Mars air present in the volume, then add more air.
        # Or, energy to fill an empty volume from 0 to Earth pressure.
        # The formula W = nRTln(P2/P1) usually applies to isothermal compression of a fixed amount of gas.
        # For filling a habitat, it's more complex. Let's use a simplified interpretation for the initial fill.
        # The script's original work calculation seems to be for pressurizing existing Mars air UP TO Earth pressure.
        # A more common calculation for initial pressurization might be PV work.
        # Let's use the provided script's intention:
        # Number of moles in the volume if it were at Mars pressure and Earth temp (for Q calc later perhaps)
        # This is not ideal, as the starting point is Mars pressure AND Mars temp.
        # For pressurization energy: this is likely the energy cost to bring the air from Mars P to Earth P.
        # Let n be the moles of air AT FINAL Earth pressure and temp.
        work_j = (number_moles_total_air * self.UNIV_GAS_CONSTANT * self.ABS_TEMP_EARTH *
                  np.log(self.EARTH_ATM_PRESSURE_ATM / self.MARS_ATM_PRESSURE_ATM))
        
        # Energy for Heating (Q) - to heat the mass of air from Mars temp to Earth temp
        heat_j = (mass_air_total_kg * self.SPECIFIC_HEAT_CAPACITY_AIR *
                  (self.ABS_TEMP_EARTH - self.ABS_TEMP_MARS))
        
        work_kj = work_j * 0.001
        heat_kj = heat_j * 0.001
        
        # These are one-time costs. For "daily" consumption, we need to model heat loss and air leakage.
        # For this simulation, let's assume this is a recurring "maintenance" cost per day.
        # This is a MAJOR simplification. A real model would use Q_loss = U*A*deltaT for heating
        # and re-pressurization based on leak rate for pressure.
        # For now, we interpret the values from the script as daily needs.
        daily_total_consumption = work_kj + heat_kj
        self.consumption_details_label.config(text=f"Pressurization: {work_kj:,.0f} kJ, Heating: {heat_kj:,.0f} kJ (Daily Maintenance Assumption)")
        return daily_total_consumption

    def refresh_plot(self):
        if not (self.drawing_app_ref and self.solar_tab_ref and
                self.nuclear_tab_ref and self.sabatier_tab_ref and
                hasattr(self.drawing_app_ref, 'sim_time_hours')):
            self.after(100, self.refresh_plot)
            return

        current_sim_time_hours = self.drawing_app_ref.sim_time_hours
        current_day_index = int(current_sim_time_hours // 24) # 0-based index
        
        # Determine plot length: either up to current day or a fixed max like other tabs (e.g. 668)
        # Let's use the DrawingApp's simulation progress for the x-axis extent
        max_sols_to_plot = max(1, current_day_index + 1) # Plot up to current sim day
        sols_array = np.arange(1, max_sols_to_plot + 1) # 1-based for x-axis

        solar_gen_daily = np.zeros(max_sols_to_plot)
        nuclear_gen_daily = np.zeros(max_sols_to_plot)
        sabatier_gen_daily = np.zeros(max_sols_to_plot)

        if hasattr(self.solar_tab_ref, 'y_energy_kj_data') and self.solar_tab_ref.y_energy_kj_data is not None:
            full_solar_data = self.solar_tab_ref.y_energy_kj_data
            solar_gen_daily = np.array([full_solar_data[min(i, len(full_solar_data)-1)] for i in range(max_sols_to_plot)])

        if hasattr(self.nuclear_tab_ref, 'y_energy_kj_data') and self.nuclear_tab_ref.y_energy_kj_data is not None:
            full_nuclear_data = self.nuclear_tab_ref.y_energy_kj_data
            nuclear_gen_daily = np.array([full_nuclear_data[min(i, len(full_nuclear_data)-1)] for i in range(max_sols_to_plot)])

        if hasattr(self.sabatier_tab_ref, 'daily_energy_output_kj_data') and self.sabatier_tab_ref.daily_energy_output_kj_data is not None:
            full_sabatier_data = self.sabatier_tab_ref.daily_energy_output_kj_data
            sabatier_gen_daily = np.array([full_sabatier_data[min(i, len(full_sabatier_data)-1)] for i in range(max_sols_to_plot)])
            
        total_generation_daily = solar_gen_daily + nuclear_gen_daily + sabatier_gen_daily
        consumption_kj_per_day = self.calculate_daily_consumption_kj()
        consumption_array = np.full(max_sols_to_plot, consumption_kj_per_day)
        net_energy_daily = total_generation_daily - consumption_array

        self.line_solar.set_data(sols_array, solar_gen_daily)
        self.line_nuclear.set_data(sols_array, nuclear_gen_daily)
        self.line_sabatier.set_data(sols_array, sabatier_gen_daily)
        self.line_total_gen.set_data(sols_array, total_generation_daily)
        self.line_consumption.set_data(sols_array, consumption_array)
        self.line_net.set_data(sols_array, net_energy_daily)

        self.ax.relim()
        self.ax.autoscale_view()
        
        # Dynamic X-axis windowing
        window_sols = 60 # Show a window of e.g. 60 sols
        plot_end_sol = max(sols_array[-1] if len(sols_array) > 0 else 1, window_sols)
        plot_start_sol = max(1, plot_end_sol - window_sols +1) # Ensure window width if possible
        self.ax.set_xlim([plot_start_sol, plot_end_sol])
        
        # Ensure Y axis includes zero and has some padding
        all_plotted_values = np.concatenate([solar_gen_daily, nuclear_gen_daily, sabatier_gen_daily, total_generation_daily, consumption_array, net_energy_daily, [0]])
        min_y_plot = np.min(all_plotted_values)
        max_y_plot = np.max(all_plotted_values)
        y_range = max_y_plot - min_y_plot
        padding = y_range * 0.1 if y_range > 10 else 10 # Add 10% padding or a fixed amount
        
        self.ax.set_ylim([min_y_plot - padding, max_y_plot + padding])


        self.canvas.draw_idle()
# +++++++++++++++++ END NEW OVERALL ENERGY TAB +++++++++++++++++++++


class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Integrated Mars Life Support & Habitat Dashboard")
        self.geometry("1000x750") # Increased default size

        self.notebook_widget_ref = ttk.Notebook(self)
        self.notebook_widget_ref.pack(expand=True, fill='both', padx=5, pady=5)

        # Initialize tabs that DrawingApp might need to update first
        self.oxygen_tab = OxygenVisualizerTab(self.notebook_widget_ref, drawing_app_ref=None)
        self.potatoes_tab = PotatoesCaloriesTab(self.notebook_widget_ref, drawing_app_ref=None)
        self.solar_tab = SolarEnergyTab(self.notebook_widget_ref, drawing_app_ref=None)
        self.nuclear_tab = NuclearEnergyTab(self.notebook_widget_ref) # Independent for now
        self.sabatier_tab = SabatierEnergyTab(self.notebook_widget_ref) # Independent for now

        # Initialize OverallEnergyTab - needs refs to energy source tabs
        # This tab will be passed to DrawingApp later
        self.overall_energy_tab = OverallEnergyTab(self.notebook_widget_ref,
                                                   drawing_app_ref=None, # Will be set after habitat_design_tab is created
                                                   solar_tab_ref=self.solar_tab,
                                                   nuclear_tab_ref=self.nuclear_tab,
                                                   sabatier_tab_ref=self.sabatier_tab)

        # Initialize DrawingApp and pass references to the other tabs
        self.habitat_design_tab = DrawingApp(self.notebook_widget_ref,
                                             oxygen_tab_ref=self.oxygen_tab,
                                             potatoes_tab_ref=self.potatoes_tab,
                                             solar_tab_ref=self.solar_tab,
                                             overall_energy_tab_ref=self.overall_energy_tab) # Pass overall_energy_tab

        # Now that habitat_design_tab exists, set its reference in tabs that need it
        self.oxygen_tab.drawing_app_ref = self.habitat_design_tab
        self.potatoes_tab.drawing_app_ref = self.habitat_design_tab
        self.solar_tab.drawing_app_ref = self.habitat_design_tab # Solar tab gets area from drawing app
        self.overall_energy_tab.drawing_app_ref = self.habitat_design_tab # Overall energy needs it for volume


        # Add tabs to notebook in desired order
        self.notebook_widget_ref.add(self.habitat_design_tab, text="Habitat Design & Atmos")
        self.notebook_widget_ref.add(self.oxygen_tab, text="System O₂ & CO₂")
        self.notebook_widget_ref.add(self.potatoes_tab, text="Food & Calorie Sim")
        self.notebook_widget_ref.add(self.solar_tab, text="Solar Energy")
        self.notebook_widget_ref.add(self.nuclear_tab, text="Nuclear Energy")
        self.notebook_widget_ref.add(self.sabatier_tab, text="Sabatier Process Energy")
        self.notebook_widget_ref.add(self.overall_energy_tab, text="Overall Energy Balance") # ADDED Overall Energy Tab


        # Initial refresh for tabs dependent on DrawingApp areas or other initial states
        self.oxygen_tab.refresh_with_new_areas()
        self.potatoes_tab.refresh_with_new_areas()
        self.solar_tab.refresh_with_new_area() # This will call its plot_energy
        self.nuclear_tab.plot_energy() # Call plot_energy to populate its data
        self.sabatier_tab.plot_energy() # Call plot_energy to populate its data
        self.overall_energy_tab.refresh_plot() # Initial plot for overall energy

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        if hasattr(self, 'habitat_design_tab') and self.habitat_design_tab.sim_running:
            if messagebox.askokcancel("Quit", "Simulation is running in the Habitat tab. Stop simulation and quit?"):
                self.habitat_design_tab.sim_running = False
                if self.habitat_design_tab.sim_job_id:
                    self.habitat_design_tab.after_cancel(self.habitat_design_tab.sim_job_id)
                self.destroy()
        else:
            self.destroy()

if __name__ == "__main__":
    app = MainApplication()
    app.mainloop()