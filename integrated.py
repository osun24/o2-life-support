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
    # ... (rest of Shapely warning)

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
    # ... (rest of sklearn warning)

import matplotlib.cm # Keep this way for direct access
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.widgets import Slider as MplSlider, Button as MplButton

# --- Constants ---
# Habitat Design Tab
NORMAL_O2_PERCENTAGE = 21.0
NORMAL_CO2_PPM = 400.0
MARS_O2_PERCENTAGE = 0.13
MARS_CO2_PERCENTAGE = 95.0
MARS_CO2_PPM = MARS_CO2_PERCENTAGE * 10000
# Human consumption/production per person (can be used with universal population)
HUMAN_O2_CONSUMPTION_KG_DAY_PERSON = 0.83 # kg O2 / day / person (used in Oxygen tab, consistent)
HUMAN_CO2_PRODUCTION_KG_DAY_PERSON = 1.0 # kg CO2 / day / person (approx, can be refined)

SIM_STEP_REAL_TIME_SECONDS = 0.1
SIM_TIME_SCALE_FACTOR = 300.0  # INCREASE FOR FASTER SIMULATION
SIM_DT_HOURS = SIM_STEP_REAL_TIME_SECONDS * SIM_TIME_SCALE_FACTOR
CELL_SIZE = 10
AXIS_MARGIN = 30
_GLOBAL_CANVAS_WIDTH = AXIS_MARGIN + 800 + CELL_SIZE
_GLOBAL_CANVAS_HEIGHT = AXIS_MARGIN + 800 + CELL_SIZE
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
LEAK_DIFFUSION_COEF = 0.35 # KG O2
SENSOR_READING_NOISE_STD_O2 = math.sqrt(SENSOR_DEFAULT_O2_VARIANCE) if SKLEARN_AVAILABLE else 0
SENSOR_READING_NOISE_STD_CO2 = math.sqrt(SENSOR_DEFAULT_CO2_VARIANCE) if SKLEARN_AVAILABLE else 0

# Universal Simulation Parameters
INITIAL_UNIVERSAL_POPULATION = 4 # New universal population default

class RoomType(Enum):
    LIVING_QUARTERS = auto()
    GREENHOUSE_POTATOES = auto()
    GREENHOUSE_ALGAE = auto()
    SOLAR_PANELS = auto()
    NONE = auto()

    @classmethod
    def get_color(cls, room_type):
        colors = {
            cls.LIVING_QUARTERS: "#ADD8E6",
            cls.GREENHOUSE_POTATOES: "#90EE90",
            cls.GREENHOUSE_ALGAE: "#98FB98",
            cls.SOLAR_PANELS: "#606060",
            cls.NONE: "#FFFFFF"
        }
        return colors.get(room_type, "#CCCCCC")

class Sensor:
    # ... (Sensor class remains the same) ...
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

class RoomShape:
    # ... (RoomShape class remains the same) ...
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
        if self.canvas_item_id: canvas.itemconfig(self.canvas_item_id, outline=self.color, width=DEFAULT_OUTLINE_WIDTH)
    def move_to(self, canvas, nx, ny): raise NotImplementedError
    def resize(self, canvas, p1, p2): raise NotImplementedError
    def update_coords_from_canvas(self, canvas): pass
    def calculate_area_pixels(self): raise NotImplementedError
    def get_volume_liters(self):
        area_px2 = self.calculate_area_pixels()
        if area_px2 is None or area_px2 <= 0: return 1000
        area_m2 = area_px2 / (CELL_SIZE**2) if CELL_SIZE > 0 else 0
        return area_m2 * 2.5 * 1000 # Assuming 2.5m height
    def update_room_type(self, new_type, canvas):
        self.room_type = new_type; self.color = RoomType.get_color(new_type)
        if self.canvas_item_id: canvas.itemconfig(self.canvas_item_id, fill=self.color)
    def get_center_canvas_coords(self): raise NotImplementedError
    def get_shapely_polygon(self):
        if SHAPELY_AVAILABLE: raise NotImplementedError("get_shapely_polygon must be implemented in subclasses.")
        return None

class RoomRectangle(RoomShape):
    # ... (RoomRectangle class remains the same) ...
    def __init__(self, x, y, width, height, room_type=RoomType.NONE):
        super().__init__(x, y, room_type)
        self.width = width
        self.height = height
    def draw(self, canvas):
        if self.canvas_item_id: canvas.delete(self.canvas_item_id)
        self.canvas_item_id = canvas.create_rectangle(self.x, self.y, self.x + self.width, self.y + self.height,
            fill=self.color, outline=DEFAULT_OUTLINE_COLOR, width=DEFAULT_OUTLINE_WIDTH, tags=("user_shape", f"room_{self.id}"))
        if self.selected: self.select(canvas)
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
    # ... (RoomCircle class remains the same) ...
    def __init__(self, center_x, center_y, radius, room_type=RoomType.NONE):
        super().__init__(center_x, center_y, room_type)
        self.radius = radius
    def draw(self, canvas):
        if self.canvas_item_id: canvas.delete(self.canvas_item_id)
        self.canvas_item_id = canvas.create_oval(self.x-self.radius, self.y-self.radius, self.x+self.radius, self.y+self.radius,
            fill=self.color, outline=DEFAULT_OUTLINE_COLOR, width=DEFAULT_OUTLINE_WIDTH, tags=("user_shape", f"room_{self.id}"))
        if self.selected: self.select(canvas)
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
    def __init__(self, parent_notebook, oxygen_tab_ref=None, potatoes_tab_ref=None, solar_tab_ref=None, water_consumption_tab_ref=None):
        super().__init__(parent_notebook)
        global SKLEARN_AVAILABLE # <<< ADD THIS LINE
        print(f"DrawingApp __init__ starting. SKLEARN_AVAILABLE: {SKLEARN_AVAILABLE}") # Diagnostic print
        self.oxygen_tab_ref = oxygen_tab_ref
        self.potatoes_tab_ref = potatoes_tab_ref
        self.solar_tab_ref = solar_tab_ref
        self.water_consumption_tab_ref = water_consumption_tab_ref

        self.population_count_var = tk.IntVar(value=INITIAL_UNIVERSAL_POPULATION)
        self.population_count = self.population_count_var.get()
        self.population_count_var.trace_add("write", self._on_population_changed_callback)


        self.current_living_quarters_area_m2 = 0.0
        self.current_potato_gh_area_m2 = 0.0
        self.current_algae_gh_area_m2 = 0.0
        self.current_solar_panel_area_m2 = 0.0

        self.current_mode = "select"; self.rooms_list = []; self.selected_room_obj = None
        self.sensors_list = []; self.selected_sensor_obj = None
        self.is_dragging = False; self.was_resizing_session = False; self.drag_action_occurred = False
        self.drag_offset_x = 0; self.drag_offset_y = 0
        self.drag_start_state = None

        self._canvas_actual_width = _GLOBAL_CANVAS_WIDTH
        self._canvas_actual_height = _GLOBAL_CANVAS_HEIGHT
        self.sim_grid_rows = (self._canvas_actual_height - AXIS_MARGIN) // CELL_SIZE if CELL_SIZE > 0 else 0
        self.sim_grid_cols = (self._canvas_actual_width - AXIS_MARGIN) // CELL_SIZE if CELL_SIZE > 0 else 0

        self.o2_field_ground_truth = np.full((self.sim_grid_rows,self.sim_grid_cols), MARS_O2_PERCENTAGE, dtype=float) if self.sim_grid_rows > 0 and self.sim_grid_cols > 0 else np.array([[]])
        self.co2_field_ground_truth = np.full((self.sim_grid_rows,self.sim_grid_cols), MARS_CO2_PPM, dtype=float) if self.sim_grid_rows > 0 and self.sim_grid_cols > 0 else np.array([[]])
        self.map_mask = np.zeros((self.sim_grid_rows,self.sim_grid_cols), dtype=int) if self.sim_grid_rows > 0 and self.sim_grid_cols > 0 else np.array([[]])
        
        self.sim_running = False; self.sim_job_id = None; self.field_vis_cells = {}
        print(f"DrawingApp __init__: self.sim_running = {self.sim_running}")


        self.gp_model_o2 = None; self.gp_model_co2 = None
        self.gp_reconstructed_field = np.zeros((self.sim_grid_rows,self.sim_grid_cols), dtype=float) if self.sim_grid_rows > 0 and self.sim_grid_cols > 0 else np.array([[]])
        self.XY_gp_prediction_grid = self._create_gp_prediction_grid()
        self.gp_update_counter = 0; self.diffusion_update_counter = 0
        self.current_gas_view = tk.StringVar(value="O2"); self.current_gp_display_min = 0.0; self.current_gp_display_max = NORMAL_O2_PERCENTAGE
        
        if SKLEARN_AVAILABLE:
            try:
                k_o2 = ConstantKernel(1.0,(1e-3,1e3))*RBF(length_scale=CELL_SIZE*3,length_scale_bounds=(CELL_SIZE*0.5,CELL_SIZE*15)) + WhiteKernel(noise_level=SENSOR_READING_NOISE_STD_O2**2,noise_level_bounds=(1e-2,1e2))
                self.gp_model_o2 = GaussianProcessRegressor(kernel=k_o2,alpha=1e-7,optimizer='fmin_l_bfgs_b',n_restarts_optimizer=3,normalize_y=True)
                k_co2 = ConstantKernel(1.0,(1e-3,1e3))*RBF(length_scale=CELL_SIZE*3,length_scale_bounds=(CELL_SIZE*0.5,CELL_SIZE*15)) + WhiteKernel(noise_level=SENSOR_READING_NOISE_STD_CO2**2,noise_level_bounds=(1e-2,1e2))
                self.gp_model_co2 = GaussianProcessRegressor(kernel=k_co2,alpha=1e-7,optimizer='fmin_l_bfgs_b',n_restarts_optimizer=3,normalize_y=True)
            except Exception as e:
                print(f"Error initializing GaussianProcessRegressor: {e}")
                SKLEARN_AVAILABLE = False # Fallback if GPR init fails
                self.gp_model_o2 = None
                self.gp_model_co2 = None


        self._setup_ui()
        if self.sim_grid_rows > 0 and self.sim_grid_cols > 0 : self.initialize_gas_fields()
        self._update_room_type_areas_display() # This also calls prepare_visualization
        
        tl = self.winfo_toplevel()
        if tl:
            tl.bind("<Delete>", lambda e: self.handle_key_press_if_active(e,self.delete_selected_item), add="+")
            tl.bind("<BackSpace>", lambda e: self.handle_key_press_if_active(e,self.delete_selected_item), add="+")
            tl.bind("<Escape>", lambda e: self.handle_key_press_if_active(e,self.handle_escape_key_logic), add="+")
        print(f"DrawingApp __init__ finished.")

    def _create_gp_prediction_grid(self):
        if self.sim_grid_rows <= 0 or self.sim_grid_cols <= 0: 
            return np.array([]) # Return empty array if grid is not valid
        
        # Create a list of [x, y] coordinates for the center of each grid cell
        # These are canvas coordinates
        grid_points = []
        for r_idx in range(self.sim_grid_rows):
            for c_idx in range(self.sim_grid_cols):
                center_x = AXIS_MARGIN + c_idx * CELL_SIZE + CELL_SIZE / 2
                center_y = AXIS_MARGIN + r_idx * CELL_SIZE + CELL_SIZE / 2
                grid_points.append([center_x, center_y])
        
        return np.array(grid_points)

    def get_population_count(self):
        return self.population_count

    def _on_population_changed_callback(self, *args):
        try:
            new_pop = self.population_count_var.get()
            if new_pop != self.population_count:
                self.population_count = new_pop
                print(f"Population changed to: {self.population_count}")
                self._notify_tabs_of_population_change()
        except tk.TclError:
             # This can happen if the var is being set during widget destruction
            pass


    def _notify_tabs_of_population_change(self):
        if self.oxygen_tab_ref and hasattr(self.oxygen_tab_ref,'refresh_with_new_areas'):
            self.oxygen_tab_ref.refresh_with_new_areas() # This method internally calls update_plot
        if self.potatoes_tab_ref and hasattr(self.potatoes_tab_ref,'refresh_with_new_areas'):
            self.potatoes_tab_ref.refresh_with_new_areas() # This method internally calls update_plot
        if self.water_consumption_tab_ref and hasattr(self.water_consumption_tab_ref, 'refresh_plot'):
            self.water_consumption_tab_ref.refresh_plot()
        # Solar and Nuclear tabs are not currently dependent on population.


    def get_potato_greenhouse_area(self): return self.current_potato_gh_area_m2
    def get_algae_greenhouse_area(self): return self.current_algae_gh_area_m2
    def get_solar_panel_area(self): return self.current_solar_panel_area_m2

    def _check_room_overlap(self, room_being_checked, proposed_polygon):
        # ... (no changes) ...
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
                    if intersection_area > 1e-3:
                        if (room_being_checked.room_type != RoomType.NONE and
                            existing_room.room_type != RoomType.NONE and
                            room_being_checked.room_type != existing_room.room_type):
                            return True, existing_room
                except Exception:
                    pass
        return False, None

    def handle_key_press_if_active(self,e,cb,*a):
        # ... (no changes) ...
        try:
            tl=self.winfo_toplevel()
            if hasattr(tl,'notebook_widget_ref') and tl.notebook_widget_ref.select()==str(self): cb(*a)
        except tk.TclError: pass
    def handle_escape_key_logic(self):
        # ... (no changes) ...
        if self.sim_running: self.sim_status_label_var.set("Sim Running. Editing locked."); return
        if self.current_mode not in ["select","rectangle","circle","add_sensor"]:
            self.mode_var.set("select"); self.set_current_mode()
        elif self.selected_room_obj: self.selected_room_obj.deselect(self.drawing_canvas); self.selected_room_obj=None
        elif self.selected_sensor_obj: self.selected_sensor_obj.deselect(self.drawing_canvas); self.selected_sensor_obj=None
        self._show_element_params_frame(); self._update_room_type_areas_display()

    def get_room_by_id(self,rid): return next((r for r in self.rooms_list if r.id == rid), None)

    def _setup_ui(self):
        main_f = ttk.Frame(self,padding="2"); main_f.pack(side=tk.TOP,fill=tk.BOTH,expand=True)
        top_ctrl_f = ttk.Frame(main_f); top_ctrl_f.pack(side=tk.TOP,fill=tk.X,pady=(0,10))
        self.drawing_controls_frame = ttk.LabelFrame(top_ctrl_f,text="Habitat Element Controls",padding="10"); self.drawing_controls_frame.pack(side=tk.LEFT,padx=5,fill=tk.Y,expand=True)
        elem_param_f = ttk.Frame(top_ctrl_f); elem_param_f.pack(side=tk.LEFT,padx=15,fill=tk.BOTH,expand=True)
        self.room_params_frame = ttk.LabelFrame(elem_param_f,text="Selected Room Parameters",padding="10")
        self.sensor_params_frame = ttk.LabelFrame(elem_param_f,text="Selected Sensor Parameters",padding="10")
        canvas_area_f = ttk.Frame(main_f); canvas_area_f.pack(side=tk.TOP,fill=tk.BOTH,expand=True,pady=(0,10))
        self.drawing_canvas = tk.Canvas(canvas_area_f, width=_GLOBAL_CANVAS_WIDTH, height=_GLOBAL_CANVAS_HEIGHT, bg="white", relief=tk.SUNKEN, borderwidth=1)
        self.drawing_canvas.pack(side=tk.LEFT, padx=(0, COLOR_SCALE_PADDING), pady=0, expand=True, fill=tk.BOTH)
        self.drawing_canvas.bind("<Configure>", self._on_canvas_resize)
        self.color_scale_canvas = tk.Canvas(canvas_area_f,width=COLOR_SCALE_WIDTH,height=_GLOBAL_CANVAS_HEIGHT,bg="whitesmoke",relief=tk.SUNKEN,borderwidth=1); self.color_scale_canvas.pack(side=tk.RIGHT,pady=0,fill=tk.Y)
        bottom_sim_f = ttk.Frame(main_f); bottom_sim_f.pack(side=tk.BOTTOM,fill=tk.X,pady=(5,0))
        self.gp_display_controls_frame = ttk.LabelFrame(bottom_sim_f,text="GP Inferred Field Display",padding="5"); self.gp_display_controls_frame.pack(side=tk.LEFT,padx=5,fill=tk.X,expand=True)
        self.sim_toggle_frame = ttk.LabelFrame(bottom_sim_f,text="Simulation Control",padding="5"); self.sim_toggle_frame.pack(side=tk.LEFT,padx=5,fill=tk.X)
        
        # Mode Radiobuttons
        ttk.Label(self.drawing_controls_frame,text="Mode:").grid(row=0,column=0,columnspan=2,padx=2,pady=2,sticky=tk.W)
        self.mode_var = tk.StringVar(value=self.current_mode)
        modes=[("Select","select"),("Draw Room (Rect)","rectangle"),("Draw Room (Circle)","circle"),("Add Sensor","add_sensor")]
        current_row=0
        for i,(t,mv) in enumerate(modes): 
            ttk.Radiobutton(self.drawing_controls_frame,text=t,variable=self.mode_var,value=mv,command=self.set_current_mode).grid(row=i+1,column=0,columnspan=2,padx=2,pady=2,sticky=tk.W)
            current_row=i+1
        
        current_row+=1 # Increment row for next control
        # Population Control
        ttk.Label(self.drawing_controls_frame, text="Population:").grid(row=current_row, column=0, padx=5, pady=5, sticky=tk.W)
        self.population_spinbox = ttk.Spinbox(self.drawing_controls_frame, from_=0, to=50, textvariable=self.population_count_var, width=5, command=self._on_population_changed_callback)
        self.population_spinbox.grid(row=current_row, column=1, padx=5, pady=5, sticky=tk.W)
        # self.population_count_var.trace_add('write', self._on_population_changed_callback) # Spinbox command handles it

        current_row+=1
        self.delete_button=ttk.Button(self.drawing_controls_frame,text="Delete Selected",command=self.delete_selected_item)
        self.delete_button.grid(row=current_row,column=0,padx=5,pady=5,sticky=tk.W)
        self.clear_sensors_button=ttk.Button(self.drawing_controls_frame,text="Clear All Sensors",command=self.clear_all_sensors)
        self.clear_sensors_button.grid(row=current_row,column=1,padx=5,pady=5,sticky=tk.W)
        
        current_row+=1
        self.union_area_label_var=tk.StringVar(value="Total Room Area: N/A")
        ttk.Label(self.drawing_controls_frame,textvariable=self.union_area_label_var).grid(row=current_row,column=0,columnspan=2,padx=5,pady=5,sticky=tk.W)
        
        current_row+=1
        self.living_quarters_area_var=tk.StringVar(value="Living Quarters: 0.00 m²")
        ttk.Label(self.drawing_controls_frame,textvariable=self.living_quarters_area_var).grid(row=current_row,column=0,columnspan=2,padx=5,pady=2,sticky=tk.W)
        
        current_row+=1
        self.potato_area_var=tk.StringVar(value="Potato GH: 0.00 m²")
        ttk.Label(self.drawing_controls_frame,textvariable=self.potato_area_var).grid(row=current_row,column=0,columnspan=2,padx=5,pady=2,sticky=tk.W)
        
        current_row+=1
        self.algae_area_var=tk.StringVar(value="Algae GH: 0.00 m²")
        ttk.Label(self.drawing_controls_frame,textvariable=self.algae_area_var).grid(row=current_row,column=0,columnspan=2,padx=5,pady=2,sticky=tk.W)
        
        current_row+=1
        self.solar_panel_area_var = tk.StringVar(value="Solar Panel Area: 0.00 m²")
        ttk.Label(self.drawing_controls_frame, textvariable=self.solar_panel_area_var).grid(row=current_row, column=0, columnspan=2, padx=5, pady=2, sticky=tk.W)

        # ... (rest of _setup_ui for room_params_frame, sensor_params_frame, gp_display, sim_toggle)
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


        self.draw_visual_grid_and_axes()
        self.draw_color_scale()
        self.drawing_canvas.bind("<Button-1>",self.handle_mouse_down)
        self.drawing_canvas.bind("<B1-Motion>",self.handle_mouse_drag)
        self.drawing_canvas.bind("<ButtonRelease-1>",self.handle_mouse_up)
        self._update_room_type_areas_display() # Initial call to update areas and dependent tabs
        self._show_element_params_frame()


    def _on_canvas_resize(self, event):
        # ... (no changes) ...
        self._canvas_actual_width = event.width
        self._canvas_actual_height = event.height

        if CELL_SIZE > 0:
            new_rows = (self._canvas_actual_height - AXIS_MARGIN) // CELL_SIZE
            new_cols = (self._canvas_actual_width - AXIS_MARGIN) // CELL_SIZE
        else:
            new_rows = 0
            new_cols = 0

        if new_rows > 0 and new_cols > 0 and \
           (new_rows != self.sim_grid_rows or new_cols != self.sim_grid_cols):
            self.sim_grid_rows = new_rows
            self.sim_grid_cols = new_cols
            self.o2_field_ground_truth = np.full((self.sim_grid_rows, self.sim_grid_cols), MARS_O2_PERCENTAGE, dtype=float)
            self.co2_field_ground_truth = np.full((self.sim_grid_rows, self.sim_grid_cols), MARS_CO2_PPM, dtype=float)
            self.map_mask = np.zeros((self.sim_grid_rows, self.sim_grid_cols), dtype=int)
            self.gp_reconstructed_field = np.zeros((self.sim_grid_rows, self.sim_grid_cols), dtype=float)
            self.XY_gp_prediction_grid = self._create_gp_prediction_grid()

        self.draw_visual_grid_and_axes()
        self.draw_color_scale()
        self.prepare_visualization_map_and_fields()


    def _update_room_type_areas_display(self):
        # ... (Calculates areas) ...
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

        # Notify tabs about area changes (population changes are handled by _on_population_changed)
        if self.oxygen_tab_ref and hasattr(self.oxygen_tab_ref,'refresh_with_new_areas'):
            self.oxygen_tab_ref.refresh_with_new_areas()
        if self.potatoes_tab_ref and hasattr(self.potatoes_tab_ref,'refresh_with_new_areas'):
            self.potatoes_tab_ref.refresh_with_new_areas()
        if self.solar_tab_ref and hasattr(self.solar_tab_ref, 'refresh_with_new_area'):
            self.solar_tab_ref.refresh_with_new_area()
        if self.water_consumption_tab_ref and hasattr(self.water_consumption_tab_ref, 'refresh_plot'):
            self.water_consumption_tab_ref.refresh_plot() # Also refresh water tab for area changes

    # ... (rest of DrawingApp methods like _create_gp_prediction_grid, _update_selected_room_type etc. remain largely unchanged for this request)
    # ... just ensure they don't conflict with the new population logic
    def _update_selected_room_type(self, sel_type_str):
        if self.selected_room_obj:
            try: new_type=RoomType[sel_type_str]
            except KeyError: new_type=RoomType.NONE
            if SHAPELY_AVAILABLE:
                original_type = self.selected_room_obj.room_type
                self.selected_room_obj.room_type = new_type # Temporarily set
                current_polygon = self.selected_room_obj.get_shapely_polygon()
                if current_polygon:
                    invalid_overlap, _ = self._check_room_overlap(self.selected_room_obj, current_polygon)
                    if invalid_overlap:
                        messagebox.showwarning("Overlap Error", f"Changing to {new_type.name} would cause an invalid overlap with a different room type.")
                        self.selected_room_obj.room_type = original_type # Revert
                        self.room_type_var.set(original_type.name) # Revert dropdown
                        return
            self.selected_room_obj.update_room_type(new_type,self.drawing_canvas)
            self.sim_status_label_var.set("Room type changed.")
            self.prepare_visualization_map_and_fields()
            self._update_room_type_areas_display()

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
        room_polys=[r.get_shapely_polygon() for r in self.rooms_list if r.get_shapely_polygon() is not None]
        if not room_polys: self.union_area_label_var.set("Total Union Area: 0.00 m²"); return
        try:
            union=unary_union(room_polys); px_area=union.area; area_m2=px_area/(CELL_SIZE**2) if CELL_SIZE>0 else 0
            self.union_area_label_var.set(f"Total Union Area: {area_m2:.2f} m²")
        except Exception: px_area=sum(r.calculate_area_pixels() for r in self.rooms_list); area_m2=px_area/(CELL_SIZE**2) if CELL_SIZE>0 else 0; self.union_area_label_var.set(f"Total Sum Area: {area_m2:.2f} m² (Union Err)")

    def set_current_mode(self):
        om=self.current_mode; self.current_mode=self.mode_var.get()
        if self.sim_running and self.current_mode!="select": self.mode_var.set("select"); self.current_mode="select"; self.sim_status_label_var.set("Sim Running. Editing locked.")
        if om=="select": # If deselected a drawing/add mode, or just clicked select mode
            if self.selected_room_obj and self.current_mode!="select": self.selected_room_obj.deselect(self.drawing_canvas); self.selected_room_obj=None
            if self.selected_sensor_obj and self.current_mode!="select": self.selected_sensor_obj.deselect(self.drawing_canvas); self.selected_sensor_obj=None
            self._show_element_params_frame() # Refresh params possibly
        self.is_dragging=False; self.was_resizing_session=False; self.drag_action_occurred=False

    def draw_visual_grid_and_axes(self):
        self.drawing_canvas.delete("grid","axis_label","grid_axis_line")
        canvas_w, canvas_h = self._canvas_actual_width, self._canvas_actual_height
        self.drawing_canvas.create_line(AXIS_MARGIN,AXIS_MARGIN,canvas_w-CELL_SIZE,AXIS_MARGIN,fill=AXIS_LINE_COLOR,width=1,tags="grid_axis_line")
        self.drawing_canvas.create_line(AXIS_MARGIN,AXIS_MARGIN,AXIS_MARGIN,canvas_h-CELL_SIZE,fill=AXIS_LINE_COLOR,width=1,tags="grid_axis_line")
        for xc in range(AXIS_MARGIN,int(canvas_w-CELL_SIZE+1),CELL_SIZE):
            if (xc-AXIS_MARGIN)%LABEL_INTERVAL==0: self.drawing_canvas.create_text(xc,AXIS_MARGIN-10,text=str(xc-AXIS_MARGIN),anchor=tk.S,font=LABEL_FONT,fill=LABEL_COLOR,tags="axis_label")
        for yc in range(AXIS_MARGIN,int(canvas_h-CELL_SIZE+1),CELL_SIZE):
            if (yc-AXIS_MARGIN)%LABEL_INTERVAL==0: self.drawing_canvas.create_text(AXIS_MARGIN-10,yc,text=str(yc-AXIS_MARGIN),anchor=tk.E,font=LABEL_FONT,fill=LABEL_COLOR,tags="axis_label")
        self.drawing_canvas.tag_lower("grid_axis_line"); self.drawing_canvas.tag_lower("axis_label"); self.drawing_canvas.tag_raise("user_shape"); self.drawing_canvas.tag_raise("sensor_marker")

    def _canvas_to_sim_coords(self,cx,cy):
        if cx<AXIS_MARGIN or cy<AXIS_MARGIN: return None,None
        col=int((cx-AXIS_MARGIN)//CELL_SIZE); row=int((cy-AXIS_MARGIN)//CELL_SIZE)
        if 0<=row<self.sim_grid_rows and 0<=col<self.sim_grid_cols: return row,col
        return None,None
    def _sim_to_canvas_coords(self,r,c): return AXIS_MARGIN+c*CELL_SIZE, AXIS_MARGIN+r*CELL_SIZE
    def handle_mouse_down(self,e):
        eff_x,eff_y=self.drawing_canvas.canvasx(e.x),self.drawing_canvas.canvasy(e.y)
        if self.sim_running: self.sim_status_label_var.set("Sim Running. Editing locked."); return
        if self.current_mode=="add_sensor": self.handle_add_sensor_click(eff_x,eff_y); return
        self.is_dragging=True; self.was_resizing_session=False; self.drag_action_occurred=False
        if self.current_mode=="select":
            ci=None
            if self.selected_sensor_obj and self.selected_sensor_obj.contains_point(eff_x,eff_y): ci=self.selected_sensor_obj
            else: ci=next((s for s in reversed(self.sensors_list) if s.contains_point(eff_x,eff_y)), None)
            if not ci:
                if self.selected_room_obj and self.selected_room_obj.contains_point(eff_x,eff_y): ci=self.selected_room_obj
                else: ci=next((r for r in reversed(self.rooms_list) if r.contains_point(eff_x,eff_y)), None)

            if self.selected_room_obj and self.selected_room_obj!=ci: self.selected_room_obj.deselect(self.drawing_canvas); self.selected_room_obj=None
            if self.selected_sensor_obj and self.selected_sensor_obj!=ci: self.selected_sensor_obj.deselect(self.drawing_canvas); self.selected_sensor_obj=None

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
            else: self.drag_offset_x,self.drag_offset_y=0,0
            self._show_element_params_frame()
        elif self.current_mode=="rectangle": self.add_new_room(RoomRectangle(eff_x,eff_y,CELL_SIZE*4,CELL_SIZE*3,RoomType.LIVING_QUARTERS))
        elif self.current_mode=="circle": self.add_new_room(RoomCircle(eff_x,eff_y,CELL_SIZE*2,RoomType.LIVING_QUARTERS))

    def add_new_room(self,new_room_obj):
        # ... (no changes) ...
        if self.sim_running: self.sim_status_label_var.set("Cannot add rooms while sim running."); return

        if SHAPELY_AVAILABLE:
            new_room_polygon = new_room_obj.get_shapely_polygon()
            if new_room_polygon:
                if new_room_obj.room_type != RoomType.NONE:
                    invalid_overlap, _ = self._check_room_overlap(new_room_obj, new_room_polygon)
                    if invalid_overlap:
                        messagebox.showwarning("Overlap Error", "New room cannot overlap with an existing room of a different significant type.")
                        return
        self.rooms_list.append(new_room_obj)
        if self.selected_room_obj: self.selected_room_obj.deselect(self.drawing_canvas)
        if self.selected_sensor_obj: self.selected_sensor_obj.deselect(self.drawing_canvas); self.selected_sensor_obj=None
        self.selected_room_obj=new_room_obj; self._show_element_params_frame(); self.prepare_visualization_map_and_fields()
        if self.selected_room_obj: self.selected_room_obj.select(self.drawing_canvas)
        self.mode_var.set("select"); self.set_current_mode(); self._update_room_type_areas_display()

    def handle_add_sensor_click(self,cx,cy):
        # ... (no changes) ...
        if self.sim_running: self.sim_status_label_var.set("Cannot add sensors while sim running."); return
        ns=Sensor(cx,cy); self.sensors_list.append(ns); s_idx=self.sensors_list.index(ns) if ns in self.sensors_list else -1
        self.sim_status_label_var.set(f"Sensor S{s_idx} added. Total: {len(self.sensors_list)}.")
        if self.selected_sensor_obj: self.selected_sensor_obj.deselect(self.drawing_canvas)
        if self.selected_room_obj: self.selected_room_obj.deselect(self.drawing_canvas); self.selected_room_obj=None
        self.selected_sensor_obj=ns; self.prepare_visualization_map_and_fields()
        if self.selected_sensor_obj: self.selected_sensor_obj.select(self.drawing_canvas)
        self._show_element_params_frame(); self.mode_var.set("select"); self.set_current_mode()

    def handle_mouse_drag(self,e):
        # ... (no changes) ...
        if self.sim_running or not self.is_dragging or self.current_mode!="select": return
        si=self.selected_room_obj if self.selected_room_obj else self.selected_sensor_obj
        if not si: return
        self.drag_action_occurred=True; eff_x,eff_y=self.drawing_canvas.canvasx(e.x),self.drawing_canvas.canvasy(e.y)
        if isinstance(si,RoomShape):
            if (e.state&0x0001)!=0: # Shift key for resize
                self.was_resizing_session=True
                si.resize(self.drawing_canvas,eff_x,eff_y)
            else:
                si.move_to(self.drawing_canvas,eff_x-self.drag_offset_x,eff_y-self.drag_offset_y)
        elif isinstance(si,Sensor):
            si.move_to(self.drawing_canvas,eff_x-self.drag_offset_x,eff_y-self.drag_offset_y)

    def handle_mouse_up(self, e):
        # ... (no changes) ...
        if self.sim_running: return
        action_finalized_message = ""
        if self.is_dragging and self.drag_action_occurred and self.selected_room_obj and self.drag_start_state:
            current_polygon = self.selected_room_obj.get_shapely_polygon()
            if SHAPELY_AVAILABLE and current_polygon and self.selected_room_obj.room_type != RoomType.NONE:
                invalid_overlap, collided_room = self._check_room_overlap(self.selected_room_obj, current_polygon)
                if invalid_overlap:
                    pushed_successfully = False
                    if not self.was_resizing_session and collided_room:
                        try:
                            intersection = current_polygon.intersection(collided_room.get_shapely_polygon())
                            if not intersection.is_empty and hasattr(intersection, 'bounds'):
                                overlap_bounds = intersection.bounds; overlap_width = overlap_bounds[2] - overlap_bounds[0]; overlap_height = overlap_bounds[3] - overlap_bounds[1]
                                center_moving_x, center_moving_y = current_polygon.centroid.x, current_polygon.centroid.y
                                center_collided_x, center_collided_y = collided_room.get_shapely_polygon().centroid.x, collided_room.get_shapely_polygon().centroid.y
                                dx_push, dy_push = 0, 0
                                if overlap_width < overlap_height and overlap_width > 1e-2 : dx_push = overlap_width + 1;
                                elif overlap_height > 1e-2: dy_push = overlap_height + 1;
                                if center_moving_x < center_collided_x and dx_push > 0: dx_push *= -1
                                elif center_moving_x > center_collided_x and dx_push < 0: dx_push *= -1 # ensure push away
                                if center_moving_y < center_collided_y and dy_push > 0: dy_push *= -1
                                elif center_moving_y > center_collided_y and dy_push < 0: dy_push *= -1 # ensure push away

                                if abs(dx_push) > 0 or abs(dy_push) > 0:
                                    original_x_before_push, original_y_before_push = self.selected_room_obj.x, self.selected_room_obj.y
                                    self.selected_room_obj.move_to(self.drawing_canvas, self.selected_room_obj.x + dx_push, self.selected_room_obj.y + dy_push)
                                    pushed_polygon = self.selected_room_obj.get_shapely_polygon()
                                    still_invalid_after_push, _ = self._check_room_overlap(self.selected_room_obj, pushed_polygon)
                                    if not still_invalid_after_push: action_finalized_message = "Room position adjusted."; pushed_successfully=True
                                    else: self.selected_room_obj.move_to(self.drawing_canvas, original_x_before_push, original_y_before_push)
                        except Exception: pass
                    if not pushed_successfully:
                        self.selected_room_obj.x, self.selected_room_obj.y = self.drag_start_state['x'], self.drag_start_state['y']
                        if isinstance(self.selected_room_obj, RoomRectangle): self.selected_room_obj.width, self.selected_room_obj.height = self.drag_start_state['width'], self.drag_start_state['height']
                        elif isinstance(self.selected_room_obj, RoomCircle): self.selected_room_obj.radius = self.drag_start_state['radius']
                        self.selected_room_obj.draw(self.drawing_canvas)
                        messagebox.showwarning("Overlap Error", "Move/resize caused overlap. Reverting."); action_finalized_message="Room reverted."
                else: action_finalized_message="Room moved/resized."
            elif not (SHAPELY_AVAILABLE and self.selected_room_obj.room_type != RoomType.NONE): action_finalized_message="Room moved/resized."
            if action_finalized_message: self.sim_status_label_var.set(action_finalized_message)
            self.prepare_visualization_map_and_fields(); self._update_room_type_areas_display()
        elif self.is_dragging and self.drag_action_occurred and self.selected_sensor_obj:
            self.selected_sensor_obj.update_coords_from_canvas(self.drawing_canvas); self.prepare_visualization_map_and_fields(); self.sim_status_label_var.set("Sensor moved.")
        self.is_dragging=False; self.was_resizing_session=False; self.drag_action_occurred=False; self.drag_start_state = None

    def delete_selected_item(self,*a):
        # ... (no changes) ...
        if self.sim_running: self.sim_status_label_var.set("Cannot delete while sim running."); return
        msg=""; item_was_room=False
        item_to_delete_canvas_id = None
        if self.selected_room_obj:
            item_was_room=True
            item_to_delete_canvas_id = self.selected_room_obj.canvas_item_id
            if self.selected_room_obj in self.rooms_list: self.rooms_list.remove(self.selected_room_obj)
            self.selected_room_obj=None; msg="Room deleted."
        elif self.selected_sensor_obj:
            item_to_delete_canvas_id = self.selected_sensor_obj.canvas_item_id
            if self.selected_sensor_obj in self.sensors_list: self.sensors_list.remove(self.selected_sensor_obj)
            self.selected_sensor_obj=None; msg="Sensor deleted."
        if item_to_delete_canvas_id:
            self.drawing_canvas.delete(item_to_delete_canvas_id)
        if msg:
            self.prepare_visualization_map_and_fields() 
            if item_was_room : self._update_room_type_areas_display()
            self.sim_status_label_var.set(msg)
        self._show_element_params_frame()

    def clear_all_sensors(self):
        # ... (no changes) ...
        if self.sim_running: self.sim_status_label_var.set("Cannot clear sensors while sim running."); return
        for sensor in self.sensors_list:
            if sensor.canvas_item_id:
                self.drawing_canvas.delete(sensor.canvas_item_id)
        self.sensors_list.clear();
        if self.selected_sensor_obj: self.selected_sensor_obj=None
        self.prepare_visualization_map_and_fields(); self._show_element_params_frame(); self.sim_status_label_var.set("All sensors cleared.")


    def initialize_gas_fields(self):
        # ... (no changes) ...
        if self.sim_grid_rows <=0 or self.sim_grid_cols <=0: return
        self.o2_field_ground_truth.fill(MARS_O2_PERCENTAGE); self.co2_field_ground_truth.fill(MARS_CO2_PPM)
        for r_obj in self.rooms_list:
            r_obj.o2_level,r_obj.co2_level=NORMAL_O2_PERCENTAGE,NORMAL_CO2_PPM # Reset room levels on init
            for ri in range(self.sim_grid_rows):
                for ci in range(self.sim_grid_cols):
                    cx,cy=self._sim_to_canvas_coords_center(ri,ci)
                    if r_obj.contains_point(cx,cy): self.o2_field_ground_truth[ri,ci],self.co2_field_ground_truth[ri,ci]=r_obj.o2_level,r_obj.co2_level
        self.update_map_mask()

    def update_map_mask(self):
        # ... (no changes) ...
        if self.sim_grid_rows <=0 or self.sim_grid_cols <=0: self.map_mask = np.array([[]]); return
        self.map_mask.fill(0) 
        for ri in range(self.sim_grid_rows):
            for ci in range(self.sim_grid_cols):
                cx,cy=self._sim_to_canvas_coords_center(ri,ci)
                for ro in self.rooms_list:
                    if ro.contains_point(cx,cy):
                        self.map_mask[ri,ci]=1 
                        break

    def prepare_visualization_map_and_fields(self):
        # ... (no changes, this was correct) ...
        self.update_map_mask()
        if not self.sim_running and self.sim_grid_rows > 0 and self.sim_grid_cols > 0: self.initialize_gas_fields()
        for iid in self.field_vis_cells.values(): self.drawing_canvas.delete(iid)
        self.field_vis_cells.clear()
        if self.sim_grid_rows > 0 and self.sim_grid_cols > 0:
            for r_idx in range(self.sim_grid_rows):
                for c_idx in range(self.sim_grid_cols):
                    x0,y0=self._sim_to_canvas_coords(r_idx,c_idx)
                    vid=self.drawing_canvas.create_rectangle(x0,y0,x0+CELL_SIZE,y0+CELL_SIZE,fill="",outline="",tags="gp_field_cell")
                    self.field_vis_cells[(r_idx,c_idx)]=vid
            self.drawing_canvas.tag_lower("gp_field_cell")
        self.draw_visual_grid_and_axes()
        for r_obj in self.rooms_list: r_obj.draw(self.drawing_canvas)
        for s_obj in self.sensors_list: s_obj.draw(self.drawing_canvas)
        if self.sim_running or (not SKLEARN_AVAILABLE or not self.sensors_list):
             self.update_gp_model_and_predict() 
        self.draw_field_visualization() 
        self.draw_color_scale()

    def _on_gas_view_change(self):
        # ... (no changes) ...
        self.update_gp_model_and_predict(); self.draw_field_visualization(); self.draw_color_scale()

    def collect_sensor_data_for_gp(self):
        # ... (no changes) ...
        sX,sy=[],[]; gas_f=self.o2_field_ground_truth if self.current_gas_view.get()=="O2" else self.co2_field_ground_truth
        if self.sim_grid_rows <= 0 or self.sim_grid_cols <= 0 : return np.array(sX), np.array(sy)
        current_true_o2_for_sensor = MARS_O2_PERCENTAGE; current_true_co2_for_sensor = MARS_CO2_PPM
        for so in self.sensors_list:
            sensor_row, sensor_col = self._canvas_to_sim_coords(so.x, so.y); sensor_is_in_room = False
            for room in self.rooms_list:
                if room.contains_point(so.x, so.y):
                    current_true_o2_for_sensor = room.o2_level; current_true_co2_for_sensor = room.co2_level
                    sensor_is_in_room = True; break
            if not sensor_is_in_room:
                if sensor_row is not None and sensor_col is not None and \
                   0 <= sensor_row < self.sim_grid_rows and 0 <= sensor_col < self.sim_grid_cols:
                    current_true_o2_for_sensor = self.o2_field_ground_truth[sensor_row, sensor_col]
                    current_true_co2_for_sensor = self.co2_field_ground_truth[sensor_row, sensor_col]
            target_true_value = current_true_o2_for_sensor if self.current_gas_view.get()=="O2" else current_true_co2_for_sensor
            variance = so.o2_variance if self.current_gas_view.get()=="O2" else so.co2_variance
            noisy_reading = max(0, np.random.normal(target_true_value, math.sqrt(variance)))
            sX.append([so.x,so.y]); sy.append(noisy_reading)
            so.read_gas_levels(current_true_o2_for_sensor, current_true_co2_for_sensor)
        return np.array(sX),np.array(sy)

    def update_gp_model_and_predict(self):
        # ... (no changes) ...
        global SKLEARN_AVAILABLE # Allow modification if GPR fails critically
        if self.sim_grid_rows <= 0 or self.sim_grid_cols <= 0 or self.XY_gp_prediction_grid.size == 0:
            suffix = " (Grid not ready)"; sim_state="Sim Running." if self.sim_running else "Sim Stopped."
            self.sim_status_label_var.set(sim_state+suffix); self.gp_reconstructed_field.fill(0)
            self._update_display_scale(self.gp_reconstructed_field); return

        truth_f=self.o2_field_ground_truth if self.current_gas_view.get()=="O2" else self.co2_field_ground_truth; suffix=""
        if not SKLEARN_AVAILABLE: self.gp_reconstructed_field=truth_f.copy(); suffix=f" (No Sklearn - Truth for {self.current_gas_view.get()})"
        elif not self.sensors_list: self.gp_reconstructed_field=truth_f.copy(); suffix=f" (No Sensors - Truth for {self.current_gas_view.get()})"
        else:
            gp_model=self.gp_model_o2 if self.current_gas_view.get()=="O2" else self.gp_model_co2
            if gp_model is None : # SKLEARN_AVAILABLE might have been true but GPR init failed
                 self.gp_reconstructed_field=truth_f.copy(); suffix=f" (GP Model Error - Truth for {self.current_gas_view.get()})"
                 SKLEARN_AVAILABLE = False # Prevent further GP attempts
            else:
                sX,sy=self.collect_sensor_data_for_gp()
                if sX.shape[0]>0 and sy.shape[0]>0 and sX.shape[0]==sy.shape[0]:
                    try:
                        gp_model.fit(sX,sy); pred_flat=gp_model.predict(self.XY_gp_prediction_grid); self.gp_reconstructed_field=pred_flat.reshape((self.sim_grid_rows,self.sim_grid_cols))
                        min_c,max_c=0,(NORMAL_O2_PERCENTAGE*1.5 if self.current_gas_view.get()=="O2" else MARS_CO2_PPM*1.1); np.clip(self.gp_reconstructed_field,min_c,max_c,out=self.gp_reconstructed_field); suffix=f" (GP for {self.current_gas_view.get()})"
                    except Exception as e: print(f"GP Fit/Predict Error: {e}"); self.gp_reconstructed_field=truth_f.copy(); suffix=f" (GP Error - Truth for {self.current_gas_view.get()})"
                else: self.gp_reconstructed_field=truth_f.copy(); suffix=f" (No Sensor Data - Truth for {self.current_gas_view.get()})"
        sim_state="Sim Running." if self.sim_running else "Sim Stopped."; self.sim_status_label_var.set(sim_state+suffix); self._update_display_scale(self.gp_reconstructed_field)


    def _update_display_scale(self,f_data):
        # ... (no changes) ...
        def_max=NORMAL_O2_PERCENTAGE if self.current_gas_view.get()=="O2" else NORMAL_CO2_PPM*5
        if f_data.size>0:
            min_val, max_val = np.min(f_data), np.max(f_data)
            if self.current_gas_view.get() == "O2": self.current_gp_display_min = min(min_val, MARS_O2_PERCENTAGE * 0.8, NORMAL_O2_PERCENTAGE * 0.8); self.current_gp_display_max = max(max_val, MARS_O2_PERCENTAGE * 1.2, NORMAL_O2_PERCENTAGE * 1.2)
            elif self.current_gas_view.get() == "CO2": self.current_gp_display_min = min(min_val, NORMAL_CO2_PPM * 0.5, MARS_CO2_PPM * 0.9); self.current_gp_display_max = max(max_val, NORMAL_CO2_PPM * 10, MARS_CO2_PPM * 1.05)
            else: self.current_gp_display_min,self.current_gp_display_max = min_val, max_val
        else: self.current_gp_display_min,self.current_gp_display_max=0.0,def_max
        if self.current_gp_display_max<=self.current_gp_display_min:
            val=self.current_gp_display_min; adj1,adj2=(0.1,1.0) if self.current_gas_view.get()=="O2" else (10.0,100.0)
            self.current_gp_display_min=max(0,val-0.5*abs(val)-adj1); self.current_gp_display_max=val+0.5*abs(val)+adj1
            if abs(self.current_gp_display_max-self.current_gp_display_min)<0.01 if self.current_gas_view.get()=="O2" else 1.0: self.current_gp_display_max=self.current_gp_display_min+adj2
        if self.current_gp_display_min > self.current_gp_display_max: self.current_gp_display_min = self.current_gp_display_max - (1.0 if self.current_gas_view.get()=="O2" else 100.0)
        if self.current_gp_display_min < 0 and self.current_gas_view.get()=="O2": self.current_gp_display_min = 0.0
        self.field_scale_label_var.set(f"GP Scale ({self.current_gas_view.get()}): {self.current_gp_display_min:.1f}-{self.current_gp_display_max:.1f}")

    def get_color_from_value(self,val,min_v,max_v):
        # ... (no changes, except using matplotlib.colormaps) ...
        norm_v=0.5 if max_v<=min_v else np.clip((val-min_v)/(max_v-min_v),0,1)
        cmap_n='RdYlGn' if self.current_gas_view.get()=="O2" else 'YlOrRd'
        cmap = matplotlib.colormaps.get_cmap(cmap_n) # Updated
        return mcolors.to_hex(cmap(norm_v))

    def draw_color_scale(self):
        # ... (no changes) ...
        self.color_scale_canvas.delete("all"); current_canvas_height = self._canvas_actual_height
        min_v,max_v=self.current_gp_display_min,self.current_gp_display_max
        if max_v <= min_v: adj = (1.0 if self.current_gas_view.get() == "O2" else 100.0); max_v = min_v + adj;
        if min_v == max_v and min_v == 0: max_v = adj
        range_v=max_v-min_v; range_v=range_v if abs(range_v)>=1e-6 else (1.0 if self.current_gas_view.get()=="O2" else 100.0)
        n_seg=50; seg_h=(current_canvas_height-2*AXIS_MARGIN)/n_seg if current_canvas_height > 2*AXIS_MARGIN and n_seg > 0 else 1; bar_w=20; x_off=15
        if current_canvas_height <= 2*AXIS_MARGIN or n_seg <=0: self.color_scale_canvas.create_text(COLOR_SCALE_WIDTH/2, current_canvas_height/2, text="N/A", font=LABEL_FONT, fill=LABEL_COLOR); return
        for i in range(n_seg):
            y0,y1=AXIS_MARGIN+i*seg_h,AXIS_MARGIN+(i+1)*seg_h
            val_map = min_v + ((n_seg - 1 - i) / (n_seg -1 if n_seg > 1 else 1)) * range_v if n_seg > 1 else min_v
            color_seg=self.get_color_from_value(val_map,min_v,max_v); self.color_scale_canvas.create_rectangle(x_off,y0,x_off+bar_w,y1,fill=color_seg,outline=color_seg)
        lbl_x=x_off+bar_w+7
        self.color_scale_canvas.create_text(lbl_x,AXIS_MARGIN,text=f"{max_v:.1f}",anchor=tk.NW,font=LABEL_FONT,fill=LABEL_COLOR)
        self.color_scale_canvas.create_text(lbl_x,current_canvas_height-AXIS_MARGIN,text=f"{min_v:.1f}",anchor=tk.SW,font=LABEL_FONT,fill=LABEL_COLOR)
        if current_canvas_height > 2*AXIS_MARGIN + 20: mid_v=min_v+range_v/2; mid_y=AXIS_MARGIN+(current_canvas_height-2*AXIS_MARGIN)/2; self.color_scale_canvas.create_text(lbl_x,mid_y,text=f"{mid_v:.1f}",anchor=tk.W,font=LABEL_FONT,fill=LABEL_COLOR)
        unit="%" if self.current_gas_view.get()=="O2" else "ppm"; self.color_scale_canvas.create_text(COLOR_SCALE_WIDTH/2,AXIS_MARGIN/2-5,text=f"GP {self.current_gas_view.get()}",anchor=tk.S,font=LABEL_FONT,fill=LABEL_COLOR); self.color_scale_canvas.create_text(COLOR_SCALE_WIDTH/2,AXIS_MARGIN/2+5,text=f"({unit})",anchor=tk.N,font=LABEL_FONT,fill=LABEL_COLOR)

    def toggle_simulation(self):
        print(f"toggle_simulation called. Current self.sim_running: {self.sim_running}") # Diagnostic
        if self.sim_running:
            # ... (stop logic, no changes needed here for population) ...
            self.sim_running=False;
            if self.sim_job_id: self.after_cancel(self.sim_job_id); self.sim_job_id=None
            self.update_gp_model_and_predict() 
            self.draw_field_visualization(); self.draw_color_scale();
            self.sim_toggle_button.config(text="Initialize & Run Sim")
            for c in self.drawing_controls_frame.winfo_children():
                if isinstance(c,(ttk.Radiobutton,ttk.Button,ttk.Scale,ttk.Spinbox,ttk.OptionMenu)): c.config(state=tk.NORMAL) # Re-enable population spinbox
            for frame_to_enable in [self.room_params_frame, self.sensor_params_frame]:

                    for c in frame_to_enable.winfo_children():
                        if isinstance(c,(ttk.Scale,ttk.Spinbox,ttk.OptionMenu)): c.config(state=tk.NORMAL)
            self._show_element_params_frame() 
        else:
            print("toggle_simulation: Entering block to START simulation.") # Diagnostic
            if not self.rooms_list: self.sim_status_label_var.set("Draw rooms first!"); return
            if not SKLEARN_AVAILABLE: self.sim_status_label_var.set("Scikit-learn missing! Cannot run simulation."); return
            if self.sim_grid_rows <= 0 or self.sim_grid_cols <= 0 : self.sim_status_label_var.set("Grid not ready!"); return
            
            self.sim_running=True;
            self.prepare_visualization_map_and_fields() 
            self.gp_update_counter=0;
            self.update_gp_model_and_predict(); 
            self.draw_field_visualization(); self.draw_color_scale();
            self.sim_toggle_button.config(text="Stop Sim"); self.mode_var.set("select")
            
            for c in self.drawing_controls_frame.winfo_children():
                if isinstance(c,ttk.Radiobutton) and c.cget("value")!="select": c.config(state=tk.DISABLED)
                elif isinstance(c, (ttk.Button, ttk.Spinbox)) and c != self.sim_toggle_button : c.config(state=tk.DISABLED) # Disable population spinbox too
            for frame_to_disable in [self.room_params_frame, self.sensor_params_frame]:
                if frame_to_disable.winfo_ismapped():
                    for c in frame_to_disable.winfo_children():
                        if isinstance(c,(ttk.Scale,ttk.Spinbox,ttk.OptionMenu)): c.config(state=tk.DISABLED)
            
            if not self.sim_job_id: self.run_simulation_step()

    def draw_field_visualization(self):
        # ... (no changes) ...
        if self.sim_grid_rows <= 0 or self.sim_grid_cols <= 0: return
        min_v,max_v=self.current_gp_display_min,self.current_gp_display_max; disp_f=self.gp_reconstructed_field
        for ri in range(self.sim_grid_rows):
            for ci in range(self.sim_grid_cols):
                cid=self.field_vis_cells.get((ri,ci))
                if cid:
                    if (0 <= ri < self.map_mask.shape[0] and 0 <= ci < self.map_mask.shape[1] and
                        0 <= ri < disp_f.shape[0] and 0 <= ci < disp_f.shape[1] and
                        0 <= ri < self.o2_field_ground_truth.shape[0] and 0 <= ci < self.o2_field_ground_truth.shape[1] and
                        0 <= ri < self.co2_field_ground_truth.shape[0] and 0 <= ci < self.co2_field_ground_truth.shape[1]):
                        color_val = disp_f[ri,ci]
                        if self.map_mask[ri,ci] == 0: 
                            color_val = MARS_O2_PERCENTAGE if self.current_gas_view.get()=="O2" else MARS_CO2_PPM
                        color=self.get_color_from_value(color_val,min_v,max_v)
                        self.drawing_canvas.itemconfig(cid,fill=color,outline=color if CELL_SIZE > 3 else "")
                    else: self.drawing_canvas.itemconfig(cid,fill="grey",outline="grey")
        self.drawing_canvas.tag_raise("user_shape"); self.drawing_canvas.tag_raise("sensor_marker")


    def run_simulation_step(self):
        print(f"run_simulation_step called. self.sim_running: {self.sim_running}") # Diagnostic
        if not self.sim_running: 
            print("run_simulation_step: Exiting because sim_running is False.") # Diagnostic
            if self.sim_job_id: self.after_cancel(self.sim_job_id); self.sim_job_id=None
            return
        # ... (rest of run_simulation_step, no changes for population here unless you add specific logic) ...
        if self.sim_grid_rows <=0 or self.sim_grid_cols <=0:
            self.sim_job_id=self.after(int(SIM_STEP_REAL_TIME_SECONDS*1000),self.run_simulation_step)
            return

        self.o2_field_ground_truth.fill(MARS_O2_PERCENTAGE) 
        self.co2_field_ground_truth.fill(MARS_CO2_PPM)  

        for ri_grid in range(self.sim_grid_rows):
            for ci_grid in range(self.sim_grid_cols):
                if self.map_mask[ri_grid,ci_grid]==1: 
                    cx_center,cy_center=self._sim_to_canvas_coords_center(ri_grid,ci_grid)
                    for r_obj in self.rooms_list:
                        if r_obj.contains_point(cx_center,cy_center):
                            # --- Placeholder for per-room simulation based on population ---
                            # if r_obj.room_type == RoomType.LIVING_QUARTERS:
                            #     # Example: o2_consumed_kg = self.population_count * HUMAN_O2_CONSUMPTION_KG_DAY_PERSON * (SIM_DT_HOURS / 24.0)
                            #     # Convert kg to % change in room volume etc.
                            #     # r_obj.o2_level -= calculated_o2_decrease_percent
                            #     # r_obj.co2_level += calculated_co2_increase_ppm
                            #     pass # Implement actual gas changes here
                            self.o2_field_ground_truth[ri_grid,ci_grid] = r_obj.o2_level
                            self.co2_field_ground_truth[ri_grid,ci_grid] = r_obj.co2_level
                            break 
        self.gp_update_counter+=1
        if SKLEARN_AVAILABLE and self.sensors_list and self.gp_update_counter>=GP_UPDATE_EVERY_N_FRAMES:
            self.update_gp_model_and_predict() 
            self.gp_update_counter=0
        elif not SKLEARN_AVAILABLE or not self.sensors_list: 
            self.update_gp_model_and_predict() 
        if self.selected_room_obj:
            self.room_o2_label.config(text=f"O2: {self.selected_room_obj.o2_level:.2f}%")
            self.room_co2_label.config(text=f"CO2: {self.selected_room_obj.co2_level:.0f} ppm")
        if self.selected_sensor_obj:
            o2r,co2r=self.selected_sensor_obj.last_o2_reading,self.selected_sensor_obj.last_co2_reading
            self.sensor_o2_reading_label.config(text=f"O2 Read: {o2r:.2f}%" if o2r is not None else "N/A")
            self.sensor_co2_reading_label.config(text=f"CO2 Read: {co2r:.0f} ppm" if co2r is not None else "N/A")
        self.draw_field_visualization()
        self.draw_color_scale() 
        self.sim_job_id=self.after(int(SIM_STEP_REAL_TIME_SECONDS*1000),self.run_simulation_step)


# Placeholder for OxygenPerson if oxygen.py is not found
try:
    from oxygen import Person as OxygenPersonImport, oxygen_production as oxygen_dot_py_production # Renamed to avoid conflict
    class OxygenPerson(OxygenPersonImport): # Use the imported one if available
        pass
except ImportError:
    print("Warning: 'oxygen.py' not found. Using placeholder OxygenPerson.")
    class OxygenPerson:
        def __init__(self, oxygen_consumption_rate_kg_day=HUMAN_O2_CONSUMPTION_KG_DAY_PERSON):
            self._oxygen_consumption_rate_kg_day = oxygen_consumption_rate_kg_day
        def oxygen_consumption(self): # Method name consistent with existing tab
            return self._oxygen_consumption_rate_kg_day

    def oxygen_dot_py_production(algae_area_m2, potato_area_m2): # Placeholder if not imported
        o2_from_algae = algae_area_m2 * 0.1 # Placeholder: kg O2 / m2 / day
        o2_from_potatoes = potato_area_m2 * 0.05 # Placeholder: kg O2 / m2 / day
        return o2_from_algae + o2_from_potatoes

CO2_PER_O2_MASS_RATIO = 44.0095 / 31.9988

class OxygenVisualizerTab(ttk.Frame):
    def __init__(self, master, drawing_app_ref, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.drawing_app_ref = drawing_app_ref
        # self.initial_colony_size is now managed by DrawingApp
        # self.current_colony_list will be generated based on universal count
        # self.current_colony_actual_size will track the universal count

        self.fig,self.ax = plt.subplots(figsize=(10,6)) # Adjusted for no colony slider
        self.canvas_widget = FigureCanvasTkAgg(self.fig,master=self)
        self.canvas_widget.get_tk_widget().pack(side=tk.TOP,fill=tk.BOTH,expand=True)
        
        # Only days slider and reset button needed from Matplotlib widgets
        self.sliders={};
        # Adjusted layout: more space since colony slider is gone
        slider_rects={'days':[0.15,0.10,0.65,0.03],'reset':[0.82,0.03,0.1,0.04]}
        self.fig.subplots_adjust(left=0.1,bottom=0.20) # Adjusted bottom margin
        
        # No colony slider here
        ax_d=self.fig.add_axes(slider_rects['days']); self.sliders['days']=MplSlider(ax=ax_d,label='Sim Days',valmin=30,valmax=365,valinit=100,valstep=1)
        ax_r=self.fig.add_axes(slider_rects['reset']); self.sliders['reset_button']=MplButton(ax_r,'Reset Plot')
        
        self.sliders['days'].on_changed(self.update_plot)
        self.sliders['reset_button'].on_clicked(self.reset_plot)
        
        self.line = None; self.consumption_line = None; self.production_line = None
        self.co2_consumption_line = None; self.balance_line = None
        self.net_text = None; self.status_text = None
        
        # Label to display current population from DrawingApp
        self.population_label_var = tk.StringVar()
        population_display_frame = ttk.Frame(self) # Use a Tkinter frame for this label
        population_display_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=2)
        ttk.Label(population_display_frame, textvariable=self.population_label_var, font=("Arial", 10)).pack(pady=2)

        self.refresh_with_new_areas() # Initial plot

    def refresh_with_new_areas(self): # This is called by DrawingApp for area or population changes
        if self.drawing_app_ref and \
           hasattr(self.drawing_app_ref, 'get_algae_greenhouse_area') and \
           hasattr(self.drawing_app_ref, 'get_potato_greenhouse_area') and \
           hasattr(self.drawing_app_ref, 'get_population_count'):
            self.update_plot()
        else:
            self.after(100, self.refresh_with_new_areas)

    def generate_new_colony(self,s): return [OxygenPerson() for _ in range(int(s))]

    def simulate_oxygen_over_time(self,people_list,days_sim,algae_area_m2,potato_area_m2):
        # ... (simulation logic remains the same, uses people_list passed to it) ...
        days_sim=int(days_sim)
        total_o2_consumption_kg_day = sum(p.oxygen_consumption() for p in people_list)
        total_o2_production_kg_day = oxygen_dot_py_production(algae_area_m2, potato_area_m2)
        co2_consumed_by_plants_kg_day = total_o2_production_kg_day * CO2_PER_O2_MASS_RATIO
        net_o2_change_kg_day = total_o2_production_kg_day - total_o2_consumption_kg_day
        initial_o2_reserve_kg = (total_o2_consumption_kg_day if total_o2_consumption_kg_day > 0 else (0.8 * len(people_list) if people_list else 1)) * 15 
        o2_levels_kg = [initial_o2_reserve_kg]
        if days_sim > 0:
            for _ in range(1, days_sim + 1):
                daily_variation_factor = np.random.normal(1.0, 0.02) 
                change_in_o2_kg = net_o2_change_kg_day * daily_variation_factor
                current_o2_level_kg = o2_levels_kg[-1] + change_in_o2_kg
                o2_levels_kg.append(max(0, current_o2_level_kg)) 
        return np.array(o2_levels_kg[:days_sim+1] if days_sim >= 0 else [initial_o2_reserve_kg]), \
               total_o2_consumption_kg_day, total_o2_production_kg_day, co2_consumed_by_plants_kg_day


    def update_plot(self,val=None):
        if not (self.drawing_app_ref and hasattr(self.drawing_app_ref, 'get_algae_greenhouse_area') and \
                hasattr(self.drawing_app_ref, 'get_potato_greenhouse_area') and \
                hasattr(self.drawing_app_ref, 'get_population_count')):
            if hasattr(self, 'fig'): self.fig.canvas.draw_idle()
            return

        current_colony_size = self.drawing_app_ref.get_population_count()
        self.population_label_var.set(f"Current Population (Universal): {current_colony_size}") # Update label

        sim_duration_days = int(self.sliders['days'].val)
        algae_gh_area_m2 = self.drawing_app_ref.get_algae_greenhouse_area()
        potato_gh_area_m2 = self.drawing_app_ref.get_potato_greenhouse_area()
        
        # Regenerate colony list based on the new universal population count
        current_colony_list = self.generate_new_colony(current_colony_size)

        time_points_days = np.linspace(0, sim_duration_days, sim_duration_days + 1 if sim_duration_days >= 0 else 1)
        o2_levels, o2_cons_rate, o2_prod_rate, co2_cons_by_plants_rate = self.simulate_oxygen_over_time(current_colony_list, sim_duration_days, algae_gh_area_m2, potato_gh_area_m2)
        safe_o2_levels = np.nan_to_num(o2_levels, nan=0.0)

        if self.line is None: 
            self.ax.clear()
            self.line, = self.ax.plot(time_points_days, safe_o2_levels, lw=2, label='Oxygen Reserve (kg)')
            self.consumption_line = self.ax.axhline(y=o2_cons_rate*30,color='red',ls='--',label=f'O₂ Cons. Rate Buffer (30d): {o2_cons_rate:.2f} kg/d')
            self.production_line = self.ax.axhline(y=o2_prod_rate*30,color='green',ls='--',label=f'O₂ Prod. Rate Buffer (30d): {o2_prod_rate:.2f} kg/d')
            self.co2_consumption_line = self.ax.axhline(y=co2_cons_by_plants_rate*30,color='cyan',ls=':',label=f'CO₂ Plant Cons. Buffer (30d): {co2_cons_by_plants_rate:.2f} kg/d')
            self.balance_line = self.ax.axhline(y=0, color='black',ls='-',alpha=0.5, label='Zero Reserve')
            self.net_text = self.ax.text(0.05,0.95,'',transform=self.ax.transAxes,va='top',bbox=dict(fc='white',alpha=0.7, boxstyle='round,pad=0.3'))
            self.status_text = self.ax.text(0.05,0.85,'',transform=self.ax.transAxes,va='top',fontsize=10,fontweight='bold',bbox=dict(fc='white',alpha=0.7, boxstyle='round,pad=0.3'))
            self.ax.set_xlabel('Simulation Days'); self.ax.set_ylabel('Oxygen Level / Buffer Equivalent (kg)'); self.ax.legend(loc='best',fontsize='small'); self.ax.grid(True,linestyle=':',alpha=0.7)
        else: 
            self.line.set_data(time_points_days,safe_o2_levels)
            self.consumption_line.set_ydata([o2_cons_rate*30,o2_cons_rate*30]); self.consumption_line.set_label(f'O₂ Cons. Rate Buffer (30d): {o2_cons_rate:.2f} kg/d')
            self.production_line.set_ydata([o2_prod_rate*30,o2_prod_rate*30]); self.production_line.set_label(f'O₂ Prod. Rate Buffer (30d): {o2_prod_rate:.2f} kg/d')
            self.co2_consumption_line.set_ydata([co2_cons_by_plants_rate*30,co2_cons_by_plants_rate*30]); self.co2_consumption_line.set_label(f'CO₂ Plant Cons. Buffer (30d): {co2_cons_by_plants_rate:.2f} kg/d')

        net_o2_daily = o2_prod_rate - o2_cons_rate; self.net_text.set_text(f'Net Daily O₂: {net_o2_daily:.2f} kg/d'); self.net_text.set_bbox(dict(facecolor='lightgreen' if net_o2_daily >=0 else 'lightcoral',alpha=0.8,boxstyle='round,pad=0.3'))
        status_str, status_color = "UNSUSTAINABLE (O₂ Deficit)","darkred"
        if o2_cons_rate > 0: 
            if net_o2_daily > 0 and (o2_prod_rate / o2_cons_rate) >= 1.05: status_str, status_color = "SUSTAINABLE (O₂ Surplus)","darkgreen"
            elif net_o2_daily >= 0 : status_str, status_color = "MARGINAL (O₂ Balanced)","darkorange"
        elif o2_prod_rate > 0: status_str, status_color = "O₂ PRODUCING (No Consumption)","blue"
        else: status_str, status_color = "INERT (No O₂ Activity)","grey"
        self.status_text.set_text(status_str); self.status_text.set_color(status_color)
        
        self.ax.set_title(f'Oxygen Dynamics (Population: {current_colony_size}, Algae: {algae_gh_area_m2:.1f}m², Potato: {potato_gh_area_m2:.1f}m²)',fontsize=10)
        self.ax.set_xlim([0, sim_duration_days if sim_duration_days > 0 else 1])
        all_y_values = list(safe_o2_levels) + [0, o2_cons_rate * 30, o2_prod_rate * 30, co2_cons_by_plants_rate * 30]; min_y_val = min(all_y_values); max_y_val = max(all_y_values)
        y_padding = (max_y_val - min_y_val) * 0.1 if (max_y_val - min_y_val) > 1 else 10
        final_min_y = min_y_val - y_padding; final_max_y = max_y_val + y_padding
        if final_min_y == final_max_y : final_min_y -=50; final_max_y +=50 
        self.ax.set_ylim([final_min_y, final_max_y]); self.ax.legend(loc='best', fontsize='x-small'); self.fig.canvas.draw_idle()

    def reset_plot(self,event=None):
        # self.sliders['colony'].reset() # No longer exists
        self.sliders['days'].reset()
        self.ax.clear(); self.line=None; self.consumption_line=None; self.production_line=None
        self.co2_consumption_line=None; self.balance_line=None; self.net_text=None; self.status_text=None
        self.update_plot()


P_POTATO_YIELD_PER_SQ_METER_PER_CYCLE=5.0; P_CHLORELLA_YIELD_PER_SQ_METER_PER_CYCLE=0.1
P_POTATO_HARVEST_CYCLE_DAYS=100; P_CHLORELLA_CYCLE_DAYS=7
P_AVG_DAILY_POTATO_YIELD_PER_M2=P_POTATO_YIELD_PER_SQ_METER_PER_CYCLE/P_POTATO_HARVEST_CYCLE_DAYS
P_AVG_DAILY_CHLORELLA_YIELD_PER_M2=P_CHLORELLA_YIELD_PER_SQ_METER_PER_CYCLE/P_CHLORELLA_CYCLE_DAYS
P_KCAL_PER_KG_POTATO=770; P_KCAL_PER_KG_CHLORELLA=3500; P_KCAL_PER_PERSON_PER_DAY=2500
# P_INITIAL_MAX_DAYS is already defined effectively by the slider default
# P_INITIAL_NUM_PEOPLE is now INITIAL_UNIVERSAL_POPULATION

class PotatoesCaloriesTab(ttk.Frame):
    def __init__(self, master, drawing_app_ref, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.drawing_app_ref = drawing_app_ref
        
        plt.style.use('seaborn-v0_8-whitegrid')
        self.fig,self.ax=plt.subplots(figsize=(10,6)) # Adjusted for no people slider
        self.canvas_widget = FigureCanvasTkAgg(self.fig,master=self)
        self.canvas_widget.get_tk_widget().pack(side=tk.TOP,fill=tk.BOTH,expand=True)
        
        # Adjust for fewer sliders
        self.fig.subplots_adjust(left=0.1,bottom=0.18,right=0.95,top=0.82) # Increased top, adjusted bottom
        
        days_init=np.array([0,100]); init_pot_kcal,init_chl_kcal,init_dem_kcal,init_net_kcal = 0,0,0,0
        self.l_pot, = self.ax.plot(days_init,[init_pot_kcal]*2,label='Daily Potato Calories',color='saddlebrown',lw=2)
        self.l_chl, = self.ax.plot(days_init,[init_chl_kcal]*2,label='Daily Chlorella Calories',color='forestgreen',lw=2)
        self.l_dem, = self.ax.plot(days_init,[init_dem_kcal]*2,label='Daily People Demand',color='crimson',ls='--',lw=2)
        self.l_net, = self.ax.plot(days_init,[init_net_kcal]*2,label='Net Daily Calories',color='blue',ls=':',lw=2.5)
        
        txt_box=dict(boxstyle='round,pad=0.3',fc='aliceblue',alpha=0.95,ec='silver')
        self.stat_good=dict(boxstyle='round,pad=0.4',fc='honeydew',alpha=0.95,ec='darkgreen')
        self.stat_bad=dict(boxstyle='round,pad=0.4',fc='mistyrose',alpha=0.95,ec='darkred')
        
        y_txt_base = 0.97
        self.txt_pot=self.fig.text(0.03,y_txt_base,'',fontsize=8,va='top',bbox=txt_box)
        self.txt_chl=self.fig.text(0.03,y_txt_base-0.035,'',fontsize=8,va='top',bbox=txt_box)
        self.txt_spc=self.fig.text(0.03,y_txt_base-0.07,'',fontsize=8,va='top',bbox=txt_box)
        self.txt_dem=self.fig.text(0.28,y_txt_base,'',fontsize=8,va='top',bbox=txt_box)
        self.txt_ppl=self.fig.text(0.28,y_txt_base-0.035,'',fontsize=8,va='top',bbox=txt_box) # Will display universal pop
        self.txt_net=self.fig.text(0.28,y_txt_base-0.07,'',fontsize=8,va='top',bbox=txt_box)
        self.txt_stat=self.fig.text(0.53,y_txt_base,'',fontsize=9,fontweight='bold',va='top')
        
        self.ax.set_xlabel('Time (Days)',fontsize=12); self.ax.set_ylabel('Daily Calories (kcal/day)',fontsize=12)
        self.ax.set_title('Daily Caloric Production vs. Demand',fontsize=14,y=1.03) # Adjusted y for title
        self.ax.grid(True,which='major',ls='--',lw=0.5)
        self.ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.22), ncol=2, fontsize='small')

        self.sliders={};
        s_r={'days':[0.15,0.05,0.7,0.03]} # Only days slider
        self.sliders['days']=MplSlider(ax=self.fig.add_axes(s_r['days']),label='Max Graph Days',valmin=30,valmax=1095,valinit=100,valstep=15,color="lightcoral")
        self.sliders['days'].on_changed(self.update_plot)
        
        self.refresh_with_new_areas()

    def refresh_with_new_areas(self): # Called by DrawingApp
        if self.drawing_app_ref and \
           hasattr(self.drawing_app_ref, 'get_algae_greenhouse_area') and \
           hasattr(self.drawing_app_ref, 'get_potato_greenhouse_area') and \
           hasattr(self.drawing_app_ref, 'get_population_count'):
            self.update_plot()
        else:
            self.after(100, self.refresh_with_new_areas)

    def update_plot(self,val=None):
        if not self.drawing_app_ref: return
        
        ppl = self.drawing_app_ref.get_population_count() # Get universal population
        days = int(self.sliders['days'].val)
        pot_m2=(self.drawing_app_ref.get_potato_greenhouse_area() if hasattr(self.drawing_app_ref, 'get_potato_greenhouse_area') else 0)
        chl_m2=(self.drawing_app_ref.get_algae_greenhouse_area() if hasattr(self.drawing_app_ref, 'get_algae_greenhouse_area') else 0)
        
        self.ax.set_xlim([0,days if days > 0 else 1]); d_data=np.array([0,days if days > 0 else 1])
        k_pot=pot_m2*P_AVG_DAILY_POTATO_YIELD_PER_M2*P_KCAL_PER_KG_POTATO
        k_chl=chl_m2*P_AVG_DAILY_CHLORELLA_YIELD_PER_M2*P_KCAL_PER_KG_CHLORELLA
        k_dem=ppl*P_KCAL_PER_PERSON_PER_DAY; k_net=k_pot+k_chl-k_dem
        
        self.l_pot.set_data(d_data,[k_pot]*2); self.l_chl.set_data(d_data,[k_chl]*2)
        self.l_dem.set_data(d_data,[k_dem]*2); self.l_net.set_data(d_data,[k_net]*2)
        
        all_y_vals = [k_pot, k_chl, k_dem, k_net, 0]; min_yp,max_yp=min(all_y_vals), max(all_y_vals)
        y_range = max_yp - min_yp;
        if y_range == 0: y_range = abs(max_yp) * 0.2 + 100 
        pad_abs = y_range * 0.15; fin_min_y = min_yp - pad_abs; fin_max_y = max_yp + pad_abs
        if abs(fin_max_y - fin_min_y) < 500: 
            center_y = (fin_max_y + fin_min_y) / 2; span_y = 500
            if min_yp < 0 or k_net < 0 : 
                span_y = max(500, abs(k_net)*2.2, abs(min_yp)*2.2)
                center_y = 0 if abs(center_y) < span_y / 4 else center_y 
            fin_min_y = center_y - span_y/2; fin_max_y = center_y + span_y/2
        self.ax.set_ylim([fin_min_y,fin_max_y])
        
        self.txt_pot.set_text(f'Potato Supply: {k_pot:,.0f} kcal/d')
        self.txt_chl.set_text(f'Chlorella Supply: {k_chl:,.0f} kcal/d')
        self.txt_spc.set_text(f'Potato Area: {pot_m2:.1f} m²\nChlorella Area: {chl_m2:.1f} m²')
        self.txt_dem.set_text(f'People Demand: {k_dem:,.0f} kcal/d')
        self.txt_ppl.set_text(f'{int(ppl)} People (Universal)') # Indicate universal source
        self.txt_net.set_text(f'Net Balance: {k_net:,.0f} kcal/d')
        
        s_txt,s_col,s_box=('SUSTAINABLE','darkgreen',self.stat_good) if k_net>=0 else ('UNSUSTAINABLE','darkred',self.stat_bad)
        self.txt_stat.set_text(f'Overall System:\n{s_txt}'); self.txt_stat.set_color(s_col); self.txt_stat.set_bbox(s_box)
        
        self.ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.22), ncol=2, fontsize='small')
        self.fig.canvas.draw_idle()


class WaterConsumptionTab(ttk.Frame):
    POTATO_LITERS_PER_M2_PER_DAY = 0.234101 
    ALGAE_LITERS_PER_M2_PER_DAY = 1500/28  
    INITIAL_MAX_DAYS_WATER = 730 
    # INITIAL_NUM_PEOPLE_WATER is now INITIAL_UNIVERSAL_POPULATION from DrawingApp

    def __init__(self, master, drawing_app_ref, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.drawing_app_ref = drawing_app_ref

        plt.style.use('seaborn-v0_8-whitegrid') 
        self.fig, self.ax = plt.subplots(figsize=(12, 8.5)) 
        self.fig.subplots_adjust(left=0.1, bottom=0.15, right=0.75, top=0.82) # Adjusted bottom for no slider

        self.canvas_widget = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas_widget.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        days_range_initial = np.array([0, self.INITIAL_MAX_DAYS_WATER])
        # Initial plot with placeholder population until first refresh
        _pop = INITIAL_UNIVERSAL_POPULATION 
        initial_water_potato = 10.0 * self.POTATO_LITERS_PER_M2_PER_DAY * _pop
        initial_water_chlorella = 5.0 * self.ALGAE_LITERS_PER_M2_PER_DAY * _pop
        initial_water_total = initial_water_potato + initial_water_chlorella

        self.line_potato, = self.ax.plot(days_range_initial, [initial_water_potato, initial_water_potato], label='Daily Potato Water', color='saddlebrown', linewidth=2)
        self.line_chlorella, = self.ax.plot(days_range_initial, [initial_water_chlorella, initial_water_chlorella], label='Daily Chlorella Water', color='forestgreen', linewidth=2)
        self.line_total, = self.ax.plot(days_range_initial, [initial_water_total, initial_water_total], label='Total Crop Water', color='crimson', linestyle='--', linewidth=2)

        text_box_props = dict(boxstyle='round,pad=0.3', fc='aliceblue', alpha=0.95, ec='silver')
        y_text_row1, y_text_row2, y_text_row3 = 0.95, 0.90, 0.85
        x_text_col1, x_text_col2 = 0.08, 0.45 

        self.text_potato = self.fig.text(x_text_col1, y_text_row1, '', fontsize=9, va='top', bbox=text_box_props)
        self.text_chlorella = self.fig.text(x_text_col1, y_text_row2, '', fontsize=9, va='top', bbox=text_box_props)
        self.text_area_info = self.fig.text(x_text_col1, y_text_row3, '', fontsize=9, va='top', bbox=text_box_props)
        self.text_total = self.fig.text(x_text_col2, y_text_row1, '', fontsize=9, va='top', bbox=text_box_props)
        self.text_people_count_info = self.fig.text(x_text_col2, y_text_row2, '', fontsize=9, va='top', bbox=text_box_props)

        self.ax.set_xlabel('Time (Days)', fontsize=14)
        self.ax.set_ylabel('Daily Water Consumption (L/day)', fontsize=14)
        self.ax.set_title('Daily Water Consumption for Crop Irrigation', fontsize=16, y=1.03)
        self.ax.grid(True, which='major', linestyle='--', linewidth=0.5)
        
        handles, labels = self.ax.get_legend_handles_labels()
        self.legend = self.fig.legend(handles, labels, loc='upper left', bbox_to_anchor=(0.77, 0.80), ncol=1, fontsize=9, title="Water Types", title_fontsize=10)

        # Remove Matplotlib people slider - population comes from DrawingApp
        # Add Tkinter labels to display area and population info at the bottom
        controls_frame = ttk.Frame(self) 
        controls_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5, padx=10)
        
        self.label_population_var = tk.StringVar(value="Population: N/A")
        ttk.Label(controls_frame, textvariable=self.label_population_var, font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        
        self.label_potato_area_var = tk.StringVar(value="Potato Area: N/A m²")
        ttk.Label(controls_frame, textvariable=self.label_potato_area_var).pack(side=tk.LEFT, padx=5)

        self.label_chlorella_area_var = tk.StringVar(value="Chlorella Area: N/A m²")
        ttk.Label(controls_frame, textvariable=self.label_chlorella_area_var).pack(side=tk.LEFT, padx=5)
        
        self.refresh_plot() 

    def refresh_plot(self, val=None):
        if not self.drawing_app_ref or \
           not hasattr(self.drawing_app_ref, 'get_potato_greenhouse_area') or \
           not hasattr(self.drawing_app_ref, 'get_population_count'):
            if hasattr(self, 'fig'): self.fig.canvas.draw_idle()
            return

        potato_m2 = self.drawing_app_ref.get_potato_greenhouse_area()
        chlorella_m2 = self.drawing_app_ref.get_algae_greenhouse_area()
        num_people = self.drawing_app_ref.get_population_count() # Universal population
        
        self.label_population_var.set(f"Population (Universal): {num_people}")
        self.label_potato_area_var.set(f"Potato Area: {potato_m2:.2f} m²")
        self.label_chlorella_area_var.set(f"Chlorella Area: {chlorella_m2:.2f} m²")

        current_max_days = self.INITIAL_MAX_DAYS_WATER 
        self.ax.set_xlim([0, current_max_days])
        days_data_for_lines = np.array([0, current_max_days])

        daily_potato_water = potato_m2 * self.POTATO_LITERS_PER_M2_PER_DAY * num_people
        daily_chlorella_water = chlorella_m2 * self.ALGAE_LITERS_PER_M2_PER_DAY * num_people
        daily_total_water = daily_potato_water + daily_chlorella_water

        self.line_potato.set_data(days_data_for_lines, [daily_potato_water, daily_potato_water])
        self.line_chlorella.set_data(days_data_for_lines, [daily_chlorella_water, daily_chlorella_water])
        self.line_total.set_data(days_data_for_lines, [daily_total_water, daily_total_water])

        all_y_values = [daily_potato_water, daily_chlorella_water, daily_total_water, 0]
        min_y = min(all_y_values) if all_y_values else 0
        max_y = max(all_y_values) if all_y_values else 100
        padding_y_upper = (max_y - min_y) * 0.15 if (max_y - min_y) > 0 else max_y * 0.2 + 100
        padding_y_lower = (max_y - min_y) * 0.15 if (max_y - min_y) > 0 else 100
        final_min_y = 0 if min_y >= 0 else (min_y - padding_y_lower)
        final_max_y = max_y + padding_y_upper
        if abs(final_max_y - final_min_y) < 500: 
            center = (final_max_y + final_min_y) / 2; span_needed = 500
            if final_min_y == 0 and center < span_needed / 2 : final_max_y = span_needed
            else: final_min_y = center - span_needed / 2; final_max_y = center + span_needed / 2
            if final_min_y < 0 and min_y >=0 : final_min_y = 0
        self.ax.set_ylim([final_min_y, final_max_y])

        self.text_potato.set_text(f'Potato Water: {daily_potato_water:,.1f} L/day')
        self.text_chlorella.set_text(f'Chlorella Water: {daily_chlorella_water:,.1f} L/day')
        self.text_area_info.set_text(f'Potato Area: {potato_m2:.1f} m²\nChlorella Area: {chlorella_m2:.1f} m²') # Removed (Habitat) as it's clear from context
        self.text_total.set_text(f'Total Crop Water: {daily_total_water:,.1f} L/day')
        self.text_people_count_info.set_text(f'{int(num_people)} People (Scales Plant Water)') # Clarify scaling
        self.fig.canvas.draw_idle()


class EnergySimulationTabBase(ttk.Frame):
    # ... (EnergySimulationTabBase remains the same) ...
    def __init__(self, master, title, input_label_text, slider_unit,
                 initial_slider_max=100, create_slider_controls=True, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.user_input_var = tk.DoubleVar(value=0)
        self.fig, self.ax = plt.subplots(figsize=(10, 4.5))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=5)
        self.controls_frame = ttk.Frame(self)
        self.controls_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5, padx=10)
        ttk.Label(self.controls_frame, text=title, font=("Courier", 14)).pack(pady=(0,5))
        if create_slider_controls:
            input_controls_frame = ttk.Frame(self.controls_frame); input_controls_frame.pack(pady=2)
            ttk.Label(input_controls_frame, text=input_label_text, font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
            self.slider = tk.Scale(input_controls_frame, from_=0, to=initial_slider_max, length=250, orient=tk.HORIZONTAL, variable=self.user_input_var, command=self.plot_energy)
            self.slider.pack(side=tk.LEFT, padx=5)
            limit_frame = ttk.Frame(self.controls_frame); limit_frame.pack(pady=2)
            ttk.Label(limit_frame, text=f"Set Slider Max ({slider_unit}):", font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
            self.entry_limit = ttk.Entry(limit_frame, font=("Arial", 9), width=7); self.entry_limit.pack(side=tk.LEFT, padx=5)
            self.entry_limit.insert(0, str(initial_slider_max))
            ttk.Button(limit_frame, text="Update Max", command=self.update_limit, style="Small.TButton").pack(side=tk.LEFT, padx=5)
            self.status_label = ttk.Label(self.controls_frame, text="Adjust slider.", font=("Arial", 8));
            self.status_label.pack(pady=(2,0))
            self.plot_energy() 
        else: 
            self.data_source_label_var = tk.StringVar(value=input_label_text)
            self.data_source_label = ttk.Label(self.controls_frame, textvariable=self.data_source_label_var, font=("Arial", 10))
            self.data_source_label.pack(pady=5)
            self.status_label = ttk.Label(self.controls_frame, text="Area derived from Habitat Design.", font=("Arial", 8))
            self.status_label.pack(pady=(2,0))

    def plot_energy(self, val=None): raise NotImplementedError("Subclasses must implement plot_energy.")
    def update_limit(self):
        if hasattr(self, 'entry_limit'):
            try:
                new_lim = float(self.entry_limit.get())
                is_valid = (new_lim >= 0)
                if self.__class__.__name__ == "NuclearEnergyTab" and new_lim <=0 : is_valid = False
                if is_valid:
                    if hasattr(self, 'slider'): self.slider.config(to=new_lim)
                    self.status_label.config(text=f"Slider max updated to: {new_lim:.1f}.", foreground="black")
                    self.plot_energy() 
                else: self.status_label.config(text="Limit must be >0 for Nuclear, >=0 for others.", foreground="red")
            except ValueError: self.status_label.config(text="Invalid number for limit.", foreground="red")

class SolarEnergyTab(EnergySimulationTabBase):
    # ... (SolarEnergyTab remains the same) ...
    def __init__(self, master, drawing_app_ref, *args, **kwargs):
        super().__init__(master, "Mars Solar Energy Calculator", "Panel Area: 0.00 m² (from Habitat)", "m²", initial_slider_max=100, create_slider_controls=False, *args, **kwargs)
        self.drawing_app_ref = drawing_app_ref
        self.refresh_with_new_area() 
    def refresh_with_new_area(self): 
        if self.drawing_app_ref and hasattr(self.drawing_app_ref, 'get_solar_panel_area'): self.plot_energy()
        else: self.after(100, self.refresh_with_new_area) 
    def plot_energy(self, val=None): 
        self.ax.clear(); current_input_area = 0.0
        if self.drawing_app_ref and hasattr(self.drawing_app_ref, 'get_solar_panel_area'): current_input_area = self.drawing_app_ref.get_solar_panel_area()
        if hasattr(self, 'data_source_label_var'): self.data_source_label_var.set(f"Panel Area: {current_input_area:.2f} m² (from Habitat)")
        dust_eff = np.random.normal(0.7, 0.2/3, size=668); panel_eff = np.random.normal(0.235, (0.27-0.235)/3, size=668)
        MARTIAN_IRR, SECONDS_HALF_SOL = 586, 88775 * 0.5 
        x_sols = np.arange(1, 669)
        y_energy_kj = (MARTIAN_IRR * current_input_area * panel_eff * dust_eff * SECONDS_HALF_SOL * 0.001) 
        self.ax.scatter(x_sols, y_energy_kj, s=15, color="orange", alpha=0.6, label='Solar Energy (kJ/sol)')
        self.ax.set_title(f"Estimated Solar Energy for {current_input_area:.2f} m² Panels", fontsize=10)
        self.ax.set_xlabel("Sols (Mars Days)", fontsize=9); self.ax.set_ylabel("Energy Output (kJ/sol)", fontsize=9)
        self.ax.tick_params(axis='both', which='major', labelsize=8)
        self.ax.legend(fontsize=8); self.ax.grid(True, alpha=0.3)
        self.canvas.draw_idle()
        if hasattr(self, 'status_label'): self.status_label.config(text=f"Plot updated for {current_input_area:.2f} m² from Habitat Design.", foreground="black")

class NuclearEnergyTab(EnergySimulationTabBase):
    # ... (NuclearEnergyTab remains the same) ...
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, "Mars Nuclear Energy Calculator", "Pu-239 Amount (kg):", "kg", 10, *args, **kwargs)
    def plot_energy(self, val=None): 
        self.ax.clear(); current_in = self.user_input_var.get() 
        BASE_KJ_PER_KG_PER_SOL = 80000 
        efficiency = np.clip(np.random.normal(0.85, 0.05, size=668), 0.7, 0.95) 
        x_sols = np.arange(1, 669)
        y_energy_kj = current_in * BASE_KJ_PER_KG_PER_SOL * efficiency
        self.ax.scatter(x_sols, y_energy_kj, s=15, color="limegreen", alpha=0.6, label='Nuclear Energy (kJ/sol)')
        self.ax.set_title(f"Estimated Nuclear Energy for {current_in:.1f} kg Pu-239", fontsize=10)
        self.ax.set_xlabel("Sols (Mars Days)", fontsize=9); self.ax.set_ylabel("Energy Output (kJ/sol)", fontsize=9)
        self.ax.tick_params(axis='both', which='major', labelsize=8)
        self.ax.legend(fontsize=8); self.ax.grid(True, alpha=0.3)
        self.canvas.draw_idle()
        if hasattr(self, 'status_label'): self.status_label.config(text=f"Plot updated for {current_in:.1f} kg Pu-239.", foreground="black")

class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Integrated Mars Life Support & Habitat Dashboard")
        self.geometry("1250x1000") 

        container = ttk.Frame(self); container.pack(fill='both', expand=True)
        canvas = tk.Canvas(container)
        vsb = ttk.Scrollbar(container, orient='vertical', command=canvas.yview); vsb.pack(side='right', fill='y')
        hsb = ttk.Scrollbar(container, orient='horizontal', command=canvas.xview); hsb.pack(side='bottom', fill='x')
        canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set); canvas.pack(side='left', fill='both', expand=True)
        scrollable_frame = ttk.Frame(canvas)
        self.scrollable_frame_window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor='nw', tags="scrollable_frame_window")
        def on_viewport_configure(event): canvas.itemconfig(self.scrollable_frame_window_id, width=event.width); canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.bind("<Configure>", on_viewport_configure)
        def on_scrollable_content_configure(event): canvas.configure(scrollregion=canvas.bbox("all"))
        scrollable_frame.bind("<Configure>", on_scrollable_content_configure)

        self.notebook_widget_ref = ttk.Notebook(scrollable_frame)
        self.notebook_widget_ref.pack(expand=True, fill='both', padx=5, pady=5)

        self.oxygen_tab = OxygenVisualizerTab(self.notebook_widget_ref, drawing_app_ref=None)
        self.potatoes_tab = PotatoesCaloriesTab(self.notebook_widget_ref, drawing_app_ref=None)
        self.solar_tab = SolarEnergyTab(self.notebook_widget_ref, drawing_app_ref=None)
        self.water_consumption_tab = WaterConsumptionTab(self.notebook_widget_ref, drawing_app_ref=None)

        self.habitat_design_tab = DrawingApp(self.notebook_widget_ref,
                                             oxygen_tab_ref=self.oxygen_tab,
                                             potatoes_tab_ref=self.potatoes_tab,
                                             solar_tab_ref=self.solar_tab,
                                             water_consumption_tab_ref=self.water_consumption_tab) 

        self.oxygen_tab.drawing_app_ref = self.habitat_design_tab
        self.potatoes_tab.drawing_app_ref = self.habitat_design_tab
        self.solar_tab.drawing_app_ref = self.habitat_design_tab
        self.water_consumption_tab.drawing_app_ref = self.habitat_design_tab

        self.notebook_widget_ref.add(self.habitat_design_tab, text="Habitat Design & Atmos")
        self.notebook_widget_ref.add(self.oxygen_tab, text="System O₂ & CO₂")
        self.notebook_widget_ref.add(self.potatoes_tab, text="Food & Calorie")
        self.notebook_widget_ref.add(self.water_consumption_tab, text="Crop Water Use") 
        self.notebook_widget_ref.add(self.solar_tab, text="Solar Energy")
        self.nuclear_tab = NuclearEnergyTab(self.notebook_widget_ref)
        self.notebook_widget_ref.add(self.nuclear_tab, text="Nuclear Energy")
        
        self.oxygen_tab.refresh_with_new_areas()
        self.potatoes_tab.refresh_with_new_areas()
        self.solar_tab.refresh_with_new_area()
        self.water_consumption_tab.refresh_plot() 

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        # Make sure DrawingApp is fully initialized before other tabs try to access it potentially too early
        self.habitat_design_tab.after_idle(self.habitat_design_tab._notify_tabs_of_population_change)


    def on_closing(self):
        # ... (no changes) ...
        if hasattr(self, 'habitat_design_tab') and self.habitat_design_tab.sim_running:
            if messagebox.askokcancel("Quit", "Simulation is running. Stop and quit?"):
                self.habitat_design_tab.sim_running = False
                if self.habitat_design_tab.sim_job_id:
                    self.habitat_design_tab.after_cancel(self.habitat_design_tab.sim_job_id)
                self.destroy()
        else:
            self.destroy()

if __name__ == "__main__":
    app = MainApplication()
    app.mainloop()