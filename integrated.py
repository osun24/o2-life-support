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
SIM_TIME_SCALE_FACTOR = 1.0 / 36.0
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
        if self.canvas_item_id: canvas.itemconfig(self.canvas_item_id, outline=DEFAULT_OUTLINE_COLOR, width=DEFAULT_OUTLINE_WIDTH)
    def move_to(self, canvas, nx, ny): raise NotImplementedError
    def resize(self, canvas, p1, p2): raise NotImplementedError
    def update_coords_from_canvas(self, canvas): pass
    def calculate_area_pixels(self): raise NotImplementedError
    def get_volume_liters(self):
        area_px2 = self.calculate_area_pixels()
        if area_px2 is None or area_px2 <= 0: return 1000 
        area_m2 = area_px2 / (CELL_SIZE**2) if CELL_SIZE > 0 else 0
        return area_m2 * 2.5 * 1000 
    def update_room_type(self, new_type, canvas):
        self.room_type = new_type; self.color = RoomType.get_color(new_type)
        if self.canvas_item_id: canvas.itemconfig(self.canvas_item_id, fill=self.color)
    def get_center_canvas_coords(self): raise NotImplementedError
    def get_shapely_polygon(self):
        if SHAPELY_AVAILABLE: raise NotImplementedError("get_shapely_polygon must be implemented in subclasses.")
        return None 

class RoomRectangle(RoomShape):
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
    def __init__(self, parent_notebook, oxygen_tab_ref=None, potatoes_tab_ref=None, solar_tab_ref=None): 
        super().__init__(parent_notebook)
        self.oxygen_tab_ref = oxygen_tab_ref
        self.potatoes_tab_ref = potatoes_tab_ref
        self.solar_tab_ref = solar_tab_ref # Store solar tab reference

        self.current_living_quarters_area_m2 = 0.0
        self.current_potato_gh_area_m2 = 0.0
        self.current_algae_gh_area_m2 = 0.0
        self.current_solar_panel_area_m2 = 0.0 # New attribute for solar panel area
        
        self.current_mode = "select"; self.rooms_list = []; self.selected_room_obj = None
        self.sensors_list = []; self.selected_sensor_obj = None
        self.is_dragging = False; self.was_resizing_session = False; self.drag_action_occurred = False
        self.drag_offset_x = 0; self.drag_offset_y = 0
        self.drag_start_state = None 
        self.sim_grid_rows = (CANVAS_HEIGHT-AXIS_MARGIN)//CELL_SIZE; self.sim_grid_cols = (CANVAS_WIDTH-AXIS_MARGIN)//CELL_SIZE
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

    def get_potato_greenhouse_area(self): return self.current_potato_gh_area_m2
    def get_algae_greenhouse_area(self): return self.current_algae_gh_area_m2
    def get_solar_panel_area(self): return self.current_solar_panel_area_m2 # New getter

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
                    if intersection_area > 1e-3: 
                        if (room_being_checked.room_type != RoomType.NONE and
                            existing_room.room_type != RoomType.NONE and
                            room_being_checked.room_type != existing_room.room_type):
                            return True, existing_room 
                except Exception: pass 
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
        main_f = ttk.Frame(self,padding="10"); main_f.pack(side=tk.TOP,fill=tk.BOTH,expand=True)
        top_ctrl_f = ttk.Frame(main_f); top_ctrl_f.pack(side=tk.TOP,fill=tk.X,pady=(0,10))
        self.drawing_controls_frame = ttk.LabelFrame(top_ctrl_f,text="Habitat Element Controls",padding="10"); self.drawing_controls_frame.pack(side=tk.LEFT,padx=5,fill=tk.Y,expand=False)
        elem_param_f = ttk.Frame(top_ctrl_f); elem_param_f.pack(side=tk.LEFT,padx=15,fill=tk.BOTH,expand=True)
        self.room_params_frame = ttk.LabelFrame(elem_param_f,text="Selected Room Parameters",padding="10")
        self.sensor_params_frame = ttk.LabelFrame(elem_param_f,text="Selected Sensor Parameters",padding="10")
        canvas_area_f = ttk.Frame(main_f); canvas_area_f.pack(side=tk.TOP,fill=tk.BOTH,expand=True,pady=(0,10))
        self.drawing_canvas = tk.Canvas(canvas_area_f, bg="white", relief=tk.SUNKEN, borderwidth=1)
        self.drawing_canvas.pack(side=tk.LEFT, padx=(0, COLOR_SCALE_PADDING), pady=0, expand=True, fill=tk.BOTH)
        self.drawing_canvas.bind("<Configure>", self._on_canvas_resize)
        self.color_scale_canvas = tk.Canvas(canvas_area_f,width=COLOR_SCALE_WIDTH,height=CANVAS_HEIGHT,bg="whitesmoke",relief=tk.SUNKEN,borderwidth=1); self.color_scale_canvas.pack(side=tk.RIGHT,pady=0,fill=tk.Y)
        bottom_sim_f = ttk.Frame(main_f); bottom_sim_f.pack(side=tk.BOTTOM,fill=tk.X,pady=(5,0))
        self.gp_display_controls_frame = ttk.LabelFrame(bottom_sim_f,text="GP Inferred Field Display",padding="5"); self.gp_display_controls_frame.pack(side=tk.LEFT,padx=5,fill=tk.X,expand=True)
        self.sim_toggle_frame = ttk.LabelFrame(bottom_sim_f,text="Simulation Control",padding="5"); self.sim_toggle_frame.pack(side=tk.LEFT,padx=5,fill=tk.X)
        ttk.Label(self.drawing_controls_frame,text="Mode:").grid(row=0,column=0,columnspan=2,padx=2,pady=2,sticky=tk.W)
        self.mode_var = tk.StringVar(value=self.current_mode)
        modes=[("Select","select"),("Draw Room (Rect)","rectangle"),("Draw Room (Circle)","circle"),("Add Sensor","add_sensor")]
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
        self.draw_visual_grid_and_axes(); self.draw_color_scale(); self.drawing_canvas.bind("<Button-1>",self.handle_mouse_down); self.drawing_canvas.bind("<B1-Motion>",self.handle_mouse_drag); self.drawing_canvas.bind("<ButtonRelease-1>",self.handle_mouse_up)
        self._update_room_type_areas_display(); self._show_element_params_frame()
        
    # Resize canvas
    def _on_canvas_resize(self, event):
        # update globals (or you can switch to self.CANVAS_WIDTH etc.)
        global CANVAS_WIDTH, CANVAS_HEIGHT
        CANVAS_WIDTH, CANVAS_HEIGHT = event.width, event.height
        # re‐draw grid, color‐scale, and all elements at new size
        self.draw_visual_grid_and_axes()
        self.draw_color_scale()
        self.prepare_visualization_map_and_fields()

    def _update_room_type_areas_display(self):
        areas={
            RoomType.LIVING_QUARTERS:0.0, 
            RoomType.GREENHOUSE_POTATOES:0.0, 
            RoomType.GREENHOUSE_ALGAE:0.0,
            RoomType.SOLAR_PANELS: 0.0 # Added solar panels
        }
        for room in self.rooms_list:
            if isinstance(room.room_type,RoomType) and room.room_type in areas:
                px_area=room.calculate_area_pixels()
                if px_area>0: area_m2=px_area/(CELL_SIZE**2) if CELL_SIZE>0 else 0; areas[room.room_type]+=area_m2
        
        self.current_living_quarters_area_m2 = areas.get(RoomType.LIVING_QUARTERS,0.0)
        self.current_potato_gh_area_m2 = areas.get(RoomType.GREENHOUSE_POTATOES,0.0)
        self.current_algae_gh_area_m2 = areas.get(RoomType.GREENHOUSE_ALGAE,0.0)
        self.current_solar_panel_area_m2 = areas.get(RoomType.SOLAR_PANELS, 0.0) # Store solar panel area

        self.living_quarters_area_var.set(f"Living Qtrs: {self.current_living_quarters_area_m2:.2f} m²")
        self.potato_area_var.set(f"Potato GH: {self.current_potato_gh_area_m2:.2f} m²")
        self.algae_area_var.set(f"Algae GH: {self.current_algae_gh_area_m2:.2f} m²")
        self.solar_panel_area_var.set(f"Solar Panels: {self.current_solar_panel_area_m2:.2f} m²") # Update new label
        
        self.update_union_area_display() 
        
        if self.oxygen_tab_ref and hasattr(self.oxygen_tab_ref,'refresh_with_new_areas'): self.oxygen_tab_ref.refresh_with_new_areas()
        if self.potatoes_tab_ref and hasattr(self.potatoes_tab_ref,'refresh_with_new_areas'): self.potatoes_tab_ref.refresh_with_new_areas()
        if self.solar_tab_ref and hasattr(self.solar_tab_ref, 'refresh_with_new_area'): self.solar_tab_ref.refresh_with_new_area() # Notify solar tab


    def _create_gp_prediction_grid(self): return np.array([[AXIS_MARGIN+c*CELL_SIZE+CELL_SIZE/2, AXIS_MARGIN+r*CELL_SIZE+CELL_SIZE/2] for r in range(self.sim_grid_rows) for c in range(self.sim_grid_cols)])
    def _update_selected_room_type(self, sel_type_str):
        if self.selected_room_obj:
            try: new_type=RoomType[sel_type_str]
            except KeyError: new_type=RoomType.NONE
            
            if SHAPELY_AVAILABLE:
                original_type = self.selected_room_obj.room_type
                self.selected_room_obj.room_type = new_type 
                current_polygon = self.selected_room_obj.get_shapely_polygon()
                if current_polygon: 
                    invalid_overlap, _ = self._check_room_overlap(self.selected_room_obj, current_polygon)
                    if invalid_overlap:
                        messagebox.showwarning("Overlap Error", f"Changing to {new_type.name} would cause an invalid overlap with a different room type.")
                        self.selected_room_obj.room_type = original_type 
                        self.room_type_var.set(original_type.name) 
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
        if self.sim_running or not self.is_dragging or self.current_mode!="select": return
        si=self.selected_room_obj if self.selected_room_obj else self.selected_sensor_obj
        if not si: return
        self.drag_action_occurred=True; eff_x,eff_y=self.drawing_canvas.canvasx(e.x),self.drawing_canvas.canvasy(e.y)
        if isinstance(si,RoomShape):
            if (e.state&0x0001)!=0: 
                 self.was_resizing_session=True
                 si.resize(self.drawing_canvas,eff_x,eff_y)
            else: 
                 si.move_to(self.drawing_canvas,eff_x-self.drag_offset_x,eff_y-self.drag_offset_y)
        elif isinstance(si,Sensor): 
            si.move_to(self.drawing_canvas,eff_x-self.drag_offset_x,eff_y-self.drag_offset_y)
    
    def handle_mouse_up(self, e):
        if self.sim_running: return
        
        action_finalized_message = ""
        if self.is_dragging and self.drag_action_occurred and self.selected_room_obj and self.drag_start_state:
            # Room's attributes (x,y,w,h,r) were updated during drag by move_to/resize.
            # No need to call update_coords_from_canvas here yet.
            
            current_polygon = self.selected_room_obj.get_shapely_polygon()
            reverted_to_original = False

            if SHAPELY_AVAILABLE and current_polygon:
                invalid_overlap, collided_room = self._check_room_overlap(self.selected_room_obj, current_polygon)
                
                if invalid_overlap:
                    # Attempt a simple push-back
                    temp_room_x, temp_room_y = self.selected_room_obj.x, self.selected_room_obj.y
                    
                    intersection = current_polygon.intersection(collided_room.get_shapely_polygon())
                    pushed_successfully = False
                    if not intersection.is_empty and hasattr(intersection, 'bounds'):
                        overlap_bounds = intersection.bounds
                        overlap_width = overlap_bounds[2] - overlap_bounds[0]
                        overlap_height = overlap_bounds[3] - overlap_bounds[1]

                        center_moving_x, center_moving_y = current_polygon.centroid.x, current_polygon.centroid.y
                        center_collided_x, center_collided_y = collided_room.get_shapely_polygon().centroid.x, collided_room.get_shapely_polygon().centroid.y
                        
                        dx_push, dy_push = 0, 0
                        # Prioritize resolving smaller overlap
                        if overlap_width < overlap_height and overlap_width > 1e-2 : # Resolve X first
                            dx_push = -overlap_width if center_moving_x < center_collided_x else overlap_width
                        elif overlap_height > 1e-2: # Resolve Y
                            dy_push = -overlap_height if center_moving_y < center_collided_y else overlap_height
                        
                        if abs(dx_push) > 0 or abs(dy_push) > 0:
                            temp_room_x += dx_push
                            temp_room_y += dy_push

                            # Apply pushed position temporarily for re-check
                            original_x_before_push, original_y_before_push = self.selected_room_obj.x, self.selected_room_obj.y
                            self.selected_room_obj.x, self.selected_room_obj.y = temp_room_x, temp_room_y
                            # If it was a resize, the dimensions also changed, so the polygon is based on new size but pushed position
                            pushed_polygon = self.selected_room_obj.get_shapely_polygon()
                            
                            still_invalid_overlap, _ = self._check_room_overlap(self.selected_room_obj, pushed_polygon)
                            
                            if not still_invalid_overlap:
                                messagebox.showinfo("Adjusted", "Room position adjusted to avoid overlap.")
                                action_finalized_message = "Room position adjusted."
                                pushed_successfully = True
                            else: # Push failed or created new issue, revert fully
                                self.selected_room_obj.x, self.selected_room_obj.y = original_x_before_push, original_y_before_push # Revert push
                        
                    if not pushed_successfully: # Revert to drag_start_state if push failed or wasn't attempted
                        self.selected_room_obj.x, self.selected_room_obj.y = self.drag_start_state['x'], self.drag_start_state['y']
                        if isinstance(self.selected_room_obj, RoomRectangle):
                            self.selected_room_obj.width, self.selected_room_obj.height = self.drag_start_state['width'], self.drag_start_state['height']
                        elif isinstance(self.selected_room_obj, RoomCircle):
                            self.selected_room_obj.radius = self.drag_start_state['radius']
                        messagebox.showwarning("Overlap Error", "Could not resolve overlap. Reverting to original position.")
                        action_finalized_message = "Room reverted to original state."
                        reverted_to_original = True
                else: # No invalid overlap
                    action_finalized_message = "Room moved/resized."
            else: # Shapely not available or no polygon, accept the move
                 action_finalized_message = "Room moved/resized (overlap check skipped)."
            
            if action_finalized_message:
                 self.sim_status_label_var.set(action_finalized_message)
            
            self.prepare_visualization_map_and_fields() 
            self._update_room_type_areas_display()

        elif self.is_dragging and self.drag_action_occurred and self.selected_sensor_obj: 
            self.selected_sensor_obj.update_coords_from_canvas(self.drawing_canvas) 
            self.prepare_visualization_map_and_fields()
            self.sim_status_label_var.set("Sensor moved.")
            
        self.is_dragging=False; self.was_resizing_session=False; self.drag_action_occurred=False
        self.drag_start_state = None 

    def delete_selected_item(self,*a):
        if self.sim_running: self.sim_status_label_var.set("Cannot delete while sim running."); return
        msg=""; item_was_room=False
        if self.selected_room_obj:
            item_was_room=True
            if self.selected_room_obj in self.rooms_list: self.rooms_list.remove(self.selected_room_obj)
            self.selected_room_obj=None; msg="Room deleted." 
        elif self.selected_sensor_obj:
            if self.selected_sensor_obj in self.sensors_list: self.sensors_list.remove(self.selected_sensor_obj)
            self.selected_sensor_obj=None; msg="Sensor deleted."
        if msg: 
            self.prepare_visualization_map_and_fields()
            if item_was_room : self._update_room_type_areas_display() 
            self.sim_status_label_var.set(msg)
        self._show_element_params_frame()
    def clear_all_sensors(self):
        if self.sim_running: self.sim_status_label_var.set("Cannot clear sensors while sim running."); return
        self.sensors_list.clear();
        if self.selected_sensor_obj: self.selected_sensor_obj=None
        self.prepare_visualization_map_and_fields(); self._show_element_params_frame(); self.sim_status_label_var.set("All sensors cleared.")
    
    def initialize_gas_fields(self):
        self.o2_field_ground_truth.fill(MARS_O2_PERCENTAGE); self.co2_field_ground_truth.fill(MARS_CO2_PPM)
        for r in self.rooms_list:
            r.o2_level,r.co2_level=NORMAL_O2_PERCENTAGE,NORMAL_CO2_PPM
            for ri in range(self.sim_grid_rows):
                for ci in range(self.sim_grid_cols):
                    cx,cy=self._sim_to_canvas_coords_center(ri,ci)
                    if r.contains_point(cx,cy): self.o2_field_ground_truth[ri,ci],self.co2_field_ground_truth[ri,ci]=r.o2_level,r.co2_level
        self.update_map_mask()
    def update_map_mask(self):
        self.map_mask.fill(0)
        for ri in range(self.sim_grid_rows):
            for ci in range(self.sim_grid_cols):
                cx,cy=self._sim_to_canvas_coords_center(ri,ci)
                for ro in self.rooms_list:
                    if ro.contains_point(cx,cy): self.map_mask[ri,ci]=1; break
    def prepare_visualization_map_and_fields(self):
        self.update_map_mask()
        if not self.sim_running: self.initialize_gas_fields()
        for iid in self.field_vis_cells.values(): self.drawing_canvas.delete(iid)
        self.field_vis_cells.clear()
        for r in range(self.sim_grid_rows):
            for c in range(self.sim_grid_cols):
                x0,y0=self._sim_to_canvas_coords(r,c); vid=self.drawing_canvas.create_rectangle(x0,y0,x0+CELL_SIZE,y0+CELL_SIZE,fill="",outline="",tags="gp_field_cell"); self.field_vis_cells[(r,c)]=vid
        self.drawing_canvas.tag_lower("gp_field_cell"); self.draw_visual_grid_and_axes()
        for r_obj in self.rooms_list: r_obj.draw(self.drawing_canvas) 
        for s_obj in self.sensors_list: s_obj.draw(self.drawing_canvas)
    def _on_gas_view_change(self): self.update_gp_model_and_predict(); self.draw_field_visualization(); self.draw_color_scale()
    def collect_sensor_data_for_gp(self):
        sX,sy=[],[]; gas_f=self.o2_field_ground_truth if self.current_gas_view.get()=="O2" else self.co2_field_ground_truth
        for so in self.sensors_list:
            sr,sc=self._canvas_to_sim_coords(so.x,so.y); true_val=(MARS_O2_PERCENTAGE if self.current_gas_view.get()=="O2" else MARS_CO2_PPM)
            s_in_r=next((r for r in self.rooms_list if r.contains_point(so.x,so.y)),None)
            if s_in_r: true_val=s_in_r.o2_level if self.current_gas_view.get()=="O2" else s_in_r.co2_level
            elif sr is not None and sc is not None and 0<=sr<self.sim_grid_rows and 0<=sc<self.sim_grid_cols: true_val=gas_f[sr,sc]
            var=so.o2_variance if self.current_gas_view.get()=="O2" else so.co2_variance; noisy_r=max(0,np.random.normal(true_val,math.sqrt(var)))
            sX.append([so.x,so.y]); sy.append(noisy_r)
            true_o2_s,true_co2_s=MARS_O2_PERCENTAGE,MARS_CO2_PPM
            if s_in_r: true_o2_s,true_co2_s=s_in_r.o2_level,s_in_r.co2_level
            elif sr is not None and sc is not None and 0<=sr<self.sim_grid_rows and 0<=sc<self.sim_grid_cols: true_o2_s,true_co2_s=self.o2_field_ground_truth[sr,sc],self.co2_field_ground_truth[sr,sc]
            so.read_gas_levels(true_o2_s,true_co2_s)
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
                    min_c,max_c=0,(NORMAL_O2_PERCENTAGE*1.5 if self.current_gas_view.get()=="O2" else MARS_CO2_PPM*1.1); np.clip(self.gp_reconstructed_field,min_c,max_c,out=self.gp_reconstructed_field); suffix=f" (GP for {self.current_gas_view.get()})"
                except Exception as e: print(f"GP Error: {e}"); self.gp_reconstructed_field=truth_f.copy(); suffix=f" (GP Error - Truth for {self.current_gas_view.get()})"
            else: self.gp_reconstructed_field=truth_f.copy(); suffix=f" (No Sensor Data - Truth for {self.current_gas_view.get()})"
        sim_state="Sim Running." if self.sim_running else "Sim Stopped."; self.sim_status_label_var.set(sim_state+suffix); self._update_display_scale(self.gp_reconstructed_field)
    def _update_display_scale(self,f_data):
        def_max=NORMAL_O2_PERCENTAGE if self.current_gas_view.get()=="O2" else NORMAL_CO2_PPM*5
        if f_data.size>0: self.current_gp_display_min,self.current_gp_display_max=np.min(f_data),np.max(f_data)
        else: self.current_gp_display_min,self.current_gp_display_max=0.0,def_max
        if self.current_gp_display_max<=self.current_gp_display_min:
            val=self.current_gp_display_min; adj1,adj2=(0.1,1.0) if self.current_gas_view.get()=="O2" else (10.0,100.0)
            self.current_gp_display_min=max(0,val-0.5*abs(val)-adj1); self.current_gp_display_max=val+0.5*abs(val)+adj1
            if abs(self.current_gp_display_max-self.current_gp_display_min)<0.01 if self.current_gas_view.get()=="O2" else 1.0: self.current_gp_display_max=self.current_gp_display_min+adj2
        self.field_scale_label_var.set(f"GP Scale ({self.current_gas_view.get()}): {self.current_gp_display_min:.1f}-{self.current_gp_display_max:.1f}")
    def get_color_from_value(self,val,min_v,max_v):
        norm_v=0.5 if max_v<=min_v else np.clip((val-min_v)/(max_v-min_v),0,1)
        cmap_n='RdYlGn' if self.current_gas_view.get()=="O2" else 'YlOrRd'
        try: return mcolors.to_hex(cm.get_cmap(cmap_n)(norm_v))
        except Exception as e: print(f"Color Error: {e}"); return "#FFFFFF"
    def draw_color_scale(self):
        self.color_scale_canvas.delete("all"); min_v,max_v=self.current_gp_display_min,self.current_gp_display_max
        if max_v<=min_v: adj=(1.0 if self.current_gas_view.get()=="O2" else 100.0); max_v=min_v+(0 if abs(min_v)<1e-6 and abs(max_v)<1e-6 else adj)
        range_v=max_v-min_v; range_v=range_v if abs(range_v)>=1e-6 else (1.0 if self.current_gas_view.get()=="O2" else 100.0)
        n_seg=50; seg_h=(CANVAS_HEIGHT-2*AXIS_MARGIN)/n_seg; bar_w=20; x_off=15
        for i in range(n_seg):
            y0,y1=AXIS_MARGIN+i*seg_h,AXIS_MARGIN+(i+1)*seg_h
            val_map=max_v-(i/n_seg)*range_v
            if self.current_gas_view.get()=="CO2": val_map=min_v+((n_seg-1-i)/n_seg)*range_v 
            elif self.current_gas_view.get()=="O2": val_map=min_v+((n_seg-1-i)/n_seg)*range_v 
            color_seg=self.get_color_from_value(val_map,min_v,max_v); self.color_scale_canvas.create_rectangle(x_off,y0,x_off+bar_w,y1,fill=color_seg,outline=color_seg)
        lbl_x=x_off+bar_w+7; self.color_scale_canvas.create_text(lbl_x,AXIS_MARGIN,text=f"{max_v:.1f}",anchor=tk.NW,font=LABEL_FONT,fill=LABEL_COLOR); self.color_scale_canvas.create_text(lbl_x,CANVAS_HEIGHT-AXIS_MARGIN,text=f"{min_v:.1f}",anchor=tk.SW,font=LABEL_FONT,fill=LABEL_COLOR)
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
                if frame_to_enable.winfo_ismapped():
                    for c in frame_to_enable.winfo_children():
                        if isinstance(c,(ttk.Scale,ttk.Spinbox,ttk.OptionMenu)): c.config(state=tk.NORMAL)
            self._show_element_params_frame()
        else:
            if not self.rooms_list: self.sim_status_label_var.set("Draw rooms first!"); return
            if not SKLEARN_AVAILABLE: self.sim_status_label_var.set("Scikit-learn missing! GP Disabled."); return
            self.sim_running=True; self.prepare_visualization_map_and_fields(); self.gp_update_counter=0; self.update_gp_model_and_predict(); self.draw_field_visualization(); self.draw_color_scale(); self.sim_toggle_button.config(text="Clear Sim"); self.mode_var.set("select")
            for c in self.drawing_controls_frame.winfo_children():
                if isinstance(c,ttk.Radiobutton) and c.cget("value")!="select": c.config(state=tk.DISABLED)
                elif isinstance(c,ttk.Button): c.config(state=tk.DISABLED)
            for frame_to_disable in [self.room_params_frame, self.sensor_params_frame]:
                if frame_to_disable.winfo_ismapped():
                    for c in frame_to_disable.winfo_children():
                        if isinstance(c,(ttk.Scale,ttk.Spinbox,ttk.OptionMenu)): c.config(state=tk.DISABLED)
            if not self.sim_job_id: self.run_simulation_step()
    def draw_field_visualization(self):
        min_v,max_v=self.current_gp_display_min,self.current_gp_display_max; disp_f=self.gp_reconstructed_field
        for ri in range(self.sim_grid_rows):
            for ci in range(self.sim_grid_cols):
                cid=self.field_vis_cells.get((ri,ci))
                if cid:
                    color=self.get_color_from_value(disp_f[ri,ci] if self.map_mask[ri,ci]==1 else (MARS_O2_PERCENTAGE if self.current_gas_view.get()=="O2" else MARS_CO2_PPM),min_v,max_v)
                    self.drawing_canvas.itemconfig(cid,fill=color,outline=color)
        self.drawing_canvas.tag_raise("user_shape"); self.drawing_canvas.tag_raise("sensor_marker") 
    def run_simulation_step(self):
        if not self.sim_running:
            if self.sim_job_id: self.after_cancel(self.sim_job_id); self.sim_job_id=None
            return
        for r in self.rooms_list:
            if r.get_volume_liters()<=0: continue
        self.o2_field_ground_truth.fill(MARS_O2_PERCENTAGE); self.co2_field_ground_truth.fill(MARS_CO2_PPM)
        for ri in range(self.sim_grid_rows):
            for ci in range(self.sim_grid_cols):
                if self.map_mask[ri,ci]==1:
                    cx,cy=self._sim_to_canvas_coords_center(ri,ci)
                    for r in self.rooms_list:
                        if r.contains_point(cx,cy): self.o2_field_ground_truth[ri,ci],self.co2_field_ground_truth[ri,ci]=r.o2_level,r.co2_level; break
        self.gp_update_counter+=1
        if self.gp_update_counter>=GP_UPDATE_EVERY_N_FRAMES: self.update_gp_model_and_predict(); self.gp_update_counter=0
        elif not SKLEARN_AVAILABLE or not self.sensors_list: self.update_gp_model_and_predict()
        if self.selected_room_obj: self.room_o2_label.config(text=f"O2: {self.selected_room_obj.o2_level:.2f}%"); self.room_co2_label.config(text=f"CO2: {self.selected_room_obj.co2_level:.0f} ppm")
        if self.selected_sensor_obj: o2r,co2r=self.selected_sensor_obj.last_o2_reading,self.selected_sensor_obj.last_co2_reading; self.sensor_o2_reading_label.config(text=f"O2 Read: {o2r:.2f}%" if o2r is not None else "N/A"); self.sensor_co2_reading_label.config(text=f"CO2 Read: {co2r:.0f} ppm" if co2r is not None else "N/A")
        self.draw_field_visualization(); self.draw_color_scale(); self.sim_job_id=self.after(int(SIM_STEP_REAL_TIME_SECONDS*1000),self.run_simulation_step)

try: raise ImportError("Placeholders")
except ImportError:
    class Person:
        def __init__(self,ocr=0.83): self._ocr=ocr
        def oxygen_consumption(self): return self._ocr
    def oxygen_production(algae_a,potato_a): return algae_a*0.1+potato_a*0.05
CO2_PER_O2_MASS_RATIO=44.0095/31.9988

class OxygenVisualizerTab(ttk.Frame):
    def __init__(self, master, drawing_app_ref, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.drawing_app_ref = drawing_app_ref
        self.initial_days = 100; self.max_days = 365; self.initial_colony_size = 20
        self.current_colony_list = self.generate_new_colony(self.initial_colony_size)
        self.current_colony_actual_size = self.initial_colony_size
        self.fig,self.ax = plt.subplots(figsize=(10,6)); self.canvas=FigureCanvasTkAgg(self.fig,master=self); self.canvas.get_tk_widget().pack(side=tk.TOP,fill=tk.BOTH,expand=True)
        self.sliders={}; slider_rects={'colony':[0.15,0.15,0.65,0.03],'days':[0.15,0.10,0.65,0.03],'reset':[0.8,0.02,0.1,0.04]} 
        self.fig.subplots_adjust(left=0.1,bottom=0.25) 
        ax_c=self.fig.add_axes(slider_rects['colony']); self.sliders['colony']=MplSlider(ax=ax_c,label='Colony Size',valmin=10,valmax=50,valinit=self.initial_colony_size,valstep=1)
        ax_d=self.fig.add_axes(slider_rects['days']); self.sliders['days']=MplSlider(ax=ax_d,label='Sim Days',valmin=30,valmax=self.max_days,valinit=self.initial_days,valstep=1)
        ax_r=self.fig.add_axes(slider_rects['reset']); self.sliders['reset_button']=MplButton(ax_r,'Reset')
        self.sliders['colony'].on_changed(self.update_plot); self.sliders['days'].on_changed(self.update_plot); self.sliders['reset_button'].on_clicked(self.reset_plot)
        self.refresh_with_new_areas() 

    def refresh_with_new_areas(self):
        if self.drawing_app_ref and hasattr(self.drawing_app_ref, 'get_algae_greenhouse_area'): 
             self.update_plot()
        else: 
            self.after(100, self.refresh_with_new_areas)


    def generate_new_colony(self,s): return [Person() for _ in range(int(s))]
    def simulate_oxygen_over_time(self,people,days,algae_a,potato_a):
        days=int(days); cons_o2=sum(p.oxygen_consumption() for p in people); prod_o2=oxygen_production(algae_a,potato_a)
        cons_co2=prod_o2*CO2_PER_O2_MASS_RATIO; net_o2=prod_o2-cons_o2; init_res_basis=cons_o2 if cons_o2>0 else 0.8*len(people)
        init_o2_res=init_res_basis*15; o2_lvls=[init_o2_res]
        if days>0:
            for _ in range(1,days+1): var=np.random.normal(1.0,0.02); chg=net_o2*var; o2_lvls.append(max(0,(o2_lvls[-1] if o2_lvls[-1] is not None else 0)+chg))
        return np.array(o2_lvls[:days+1] if days>0 else [init_o2_res]),cons_o2,prod_o2,cons_co2
    def update_plot(self,val=None):
        if not hasattr(self, 'line'): 
            algae_area, potato_area = (self.drawing_app_ref.get_algae_greenhouse_area(), self.drawing_app_ref.get_potato_greenhouse_area()) if self.drawing_app_ref else (0,0)
            tp_init = np.linspace(0,self.initial_days,self.initial_days+1 if self.initial_days>0 else 1)
            o2_lvls_init, cons_o2_init, prod_o2_init, cons_co2_init = self.simulate_oxygen_over_time(self.current_colony_list, self.initial_days, algae_area, potato_area)
            self.line, = self.ax.plot(tp_init, o2_lvls_init, lw=2, label='Oxygen Level (Reserve)')
            self.consumption_line = self.ax.axhline(y=cons_o2_init*30, color='r', ls='--', label=f'O₂ Cons Buffer (30d): {cons_o2_init:.2f} kg/d')
            self.production_line = self.ax.axhline(y=prod_o2_init*30, color='g', ls='--', label=f'O₂ Prod Buffer (30d): {prod_o2_init:.2f} kg/d')
            self.co2_consumption_line = self.ax.axhline(y=cons_co2_init*30, color='c', ls=':', label=f'CO₂ Cons Buffer (30d): {cons_co2_init:.2f} kg/d')
            self.balance_line = self.ax.axhline(y=0, color='black', ls='-', alpha=0.3)
            net_o2_init = prod_o2_init - cons_o2_init
            y_net_txt_init = o2_lvls_init[-1]*0.9 if len(o2_lvls_init)>0 and o2_lvls_init[-1] is not None and o2_lvls_init[-1]>0 else 10
            self.net_text = self.ax.text(self.initial_days*0.7, y_net_txt_init, f'Net O₂: {net_o2_init:.2f} kg/d', bbox=dict(fc='white', alpha=0.7))
            stat_init, col_init = "UNSUSTAINABLE (O₂)", "darkred"
            if cons_o2_init > 0 and net_o2_init > 0 and prod_o2_init / cons_o2_init >= 1.1: stat_init, col_init = "SUSTAINABLE (O₂)", "darkgreen"
            elif net_o2_init > 0 : stat_init, col_init = "MARGINAL (O₂)", "darkorange"
            y_stat_txt_init = o2_lvls_init[-1]*1.1 if len(o2_lvls_init)>0 and o2_lvls_init[-1] is not None and o2_lvls_init[-1]>0 else 15
            self.status_text = self.ax.text(self.initial_days*0.8, y_stat_txt_init, stat_init, fontsize=12, fontweight='bold', color=col_init, bbox=dict(fc='white', alpha=0.7))
            self.ax.set_xlabel('Days'); self.ax.set_ylabel('Gas Level / Buffer (kg)')
            self.ax.legend(loc='upper left', fontsize='small'); self.ax.grid(True)

        new_col_val=int(self.sliders['colony'].val); days=int(self.sliders['days'].val)
        algae_a=(self.drawing_app_ref.get_algae_greenhouse_area() if self.drawing_app_ref else 0)
        potato_a=(self.drawing_app_ref.get_potato_greenhouse_area() if self.drawing_app_ref else 0)
        if new_col_val!=self.current_colony_actual_size: self.current_colony_list=self.generate_new_colony(new_col_val); self.current_colony_actual_size=new_col_val
        tp=np.linspace(0,days,days+1 if days>0 else 1); o2_l,cons_o2,prod_o2,cons_co2=self.simulate_oxygen_over_time(self.current_colony_list,days,algae_a,potato_a)
        safe_o2=np.nan_to_num(o2_l,nan=0.0); self.line.set_xdata(tp); self.line.set_ydata(safe_o2)
        self.consumption_line.set_ydata([cons_o2*30,cons_o2*30]); self.production_line.set_ydata([prod_o2*30,prod_o2*30]); self.co2_consumption_line.set_ydata([cons_co2*30,cons_co2*30])
        net_o2=prod_o2-cons_o2; self.consumption_line.set_label(f'O₂ Cons Buf (30d): {cons_o2:.2f} kg/d'); self.production_line.set_label(f'O₂ Prod Buf (30d): {prod_o2:.2f} kg/d'); self.co2_consumption_line.set_label(f'CO₂ Cons Buf (30d): {cons_co2:.2f} kg/d')
        cymax=self.ax.get_ylim()[1]; last_o2=safe_o2[-1] if len(safe_o2)>0 else 0
        y_net=last_o2*0.9 if days>0 and last_o2>0 else cymax*0.1; x_net=days*0.7 if days>0 else self.initial_days*0.7
        y_stat=last_o2*1.1 if days>0 and last_o2>0 else cymax*0.15; x_stat=days*0.9 if days>0 else self.initial_days*0.8
        self.net_text.set_text(f'Net O₂: {net_o2:.2f} kg/d'); self.net_text.set_position((x_net,y_net)); self.net_text.set_bbox(dict(facecolor='lightgreen' if net_o2>=0 else 'lightcoral',alpha=0.7))
        stat,col="UNSUSTAINABLE (O₂)", "darkred"
        if cons_o2>0 and net_o2>0 and (prod_o2/cons_o2)>=1.1: stat,col="SUSTAINABLE (O₂)", "darkgreen"
        elif net_o2>0: stat,col="MARGINAL (O₂)", "darkorange"
        self.status_text.set_text(stat); self.status_text.set_color(col); self.status_text.set_bbox(dict(fc='white',alpha=0.7)); self.status_text.set_position((x_stat,y_stat))
        self.ax.set_title(f'O₂ & CO₂ (Col: {self.current_colony_actual_size}, Days: {days}, Algae: {algae_a:.1f}m², Potato: {potato_a:.1f}m²)')
        self.ax.set_xlim([0,days if days>0 else 1]); all_b_vals=[0,cons_o2*30,prod_o2*30,cons_co2*30]; finite_o2=safe_o2[np.isfinite(safe_o2)]
        min_y_o2=np.min(finite_o2) if len(finite_o2)>0 else 0; min_y=min(min(all_b_vals),min_y_o2 if min_y_o2<0 else 0)
        max_o2=np.max(finite_o2) if len(finite_o2)>0 else 100; max_y=max(max(all_b_vals),max_o2 if max_o2>0 else 100)
        fin_min_y=min_y*1.1 if min_y<0 else (min_y*0.9 if min_y!=0 else -max_y*0.05 if max_y>0 else -5)
        fin_max_y=max_y*1.1 if max_y>0 else 100;
        if fin_min_y>=fin_max_y: fin_max_y=fin_min_y+100
        self.ax.set_ylim([fin_min_y,fin_max_y]); self.ax.legend(loc='upper left',fontsize='small'); self.fig.canvas.draw_idle()
    def reset_plot(self,e=None): self.current_colony_list=self.generate_new_colony(self.initial_colony_size); self.current_colony_actual_size=self.initial_colony_size; self.sliders['colony'].reset(); self.sliders['days'].reset(); self.update_plot()

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
        self.fig.subplots_adjust(left=0.1,bottom=0.25,right=0.95,top=0.85) 
        days_init=np.array([0,P_INITIAL_MAX_DAYS]); init_pot_kcal,init_chl_kcal,init_dem_kcal,init_net_kcal = 0,0,0,0 
        self.l_pot, = self.ax.plot(days_init,[init_pot_kcal]*2,label='Daily Potato Calories',color='saddlebrown',lw=2)
        self.l_chl, = self.ax.plot(days_init,[init_chl_kcal]*2,label='Daily Chlorella Calories',color='forestgreen',lw=2)
        self.l_dem, = self.ax.plot(days_init,[init_dem_kcal]*2,label='Daily People Demand',color='crimson',ls='--',lw=2)
        self.l_net, = self.ax.plot(days_init,[init_net_kcal]*2,label='Net Daily Calories',color='blue',ls=':',lw=2.5)
        txt_box=dict(boxstyle='round,pad=0.3',fc='aliceblue',alpha=0.95,ec='silver'); self.stat_good=dict(boxstyle='round,pad=0.4',fc='honeydew',alpha=0.95,ec='darkgreen'); self.stat_bad=dict(boxstyle='round,pad=0.4',fc='mistyrose',alpha=0.95,ec='darkred')
        y_txt,x1,x2,x3=0.97,0.15,0.70,0.86
        self.txt_pot=self.fig.text(x1,y_txt,'',fontsize=8,va='top',bbox=txt_box); self.txt_chl=self.fig.text(x1,y_txt-0.035,'',fontsize=8,va='top',bbox=txt_box); self.txt_spc=self.fig.text(x1,y_txt-0.07,'',fontsize=8,va='top',bbox=txt_box)
        self.txt_dem=self.fig.text(x2,y_txt,'',fontsize=8,va='top',bbox=txt_box); self.txt_ppl=self.fig.text(x2,y_txt-0.035,'',fontsize=8,va='top',bbox=txt_box); self.txt_net=self.fig.text(x2,y_txt-0.07,'',fontsize=8,va='top',bbox=txt_box); self.txt_stat=self.fig.text(x3,y_txt,'',fontsize=9,fontweight='bold',va='top')
        self.ax.set_xlabel('Time (Days)',fontsize=12); self.ax.set_ylabel('Daily Calories (kcal/day)',fontsize=12); self.ax.set_title('Daily Caloric Production vs. Demand',fontsize=14,y=1.03); self.ax.grid(True,which='major',ls='--',lw=0.5); self.ax.legend(loc='lower left',bbox_to_anchor=(0,-0.02),ncol=2,fontsize='small')
        self.sliders={}; s_r={'people':[0.15,0.15,0.7,0.03],'days':[0.15,0.10,0.7,0.03]} 
        self.sliders['people']=MplSlider(ax=self.fig.add_axes(s_r['people']),label='Num People',valmin=1,valmax=50,valinit=P_INITIAL_NUM_PEOPLE,valstep=1,color="skyblue")
        self.sliders['days']=MplSlider(ax=self.fig.add_axes(s_r['days']),label='Max Graph Days',valmin=30,valmax=1095,valinit=P_INITIAL_MAX_DAYS,valstep=15,color="lightcoral")
        for s in self.sliders.values(): s.on_changed(self.update_plot)
        self.refresh_with_new_areas() 

    def refresh_with_new_areas(self):
        if self.drawing_app_ref and hasattr(self.drawing_app_ref, 'get_algae_greenhouse_area'):
             self.update_plot()
        else:
            self.after(100, self.refresh_with_new_areas)

    def update_plot(self,val=None):
        ppl,days=self.sliders['people'].val,int(self.sliders['days'].val)
        pot_m2=(self.drawing_app_ref.get_potato_greenhouse_area() if self.drawing_app_ref else 0)
        chl_m2=(self.drawing_app_ref.get_algae_greenhouse_area() if self.drawing_app_ref else 0)
        self.ax.set_xlim([0,days]); d_data=np.array([0,days])
        k_pot=pot_m2*P_AVG_DAILY_POTATO_YIELD_PER_M2*P_KCAL_PER_KG_POTATO; k_chl=chl_m2*P_AVG_DAILY_CHLORELLA_YIELD_PER_M2*P_KCAL_PER_KG_CHLORELLA
        k_dem=ppl*P_KCAL_PER_PERSON_PER_DAY; k_net=k_pot+k_chl-k_dem
        self.l_pot.set_data(d_data,[k_pot]*2); self.l_chl.set_data(d_data,[k_chl]*2); self.l_dem.set_data(d_data,[k_dem]*2); self.l_net.set_data(d_data,[k_net]*2)
        all_y=[k_pot,k_chl,k_dem,k_net,0]; min_yp,max_yp=min(all_y) if all_y else 0,max(all_y) if all_y else 100 
        pad_u=(max_yp-min_yp)*0.15 or max_yp*0.2+100; pad_l=(max_yp-min_yp)*0.15 or 100
        fin_min_y=min(min_yp-pad_l,-pad_l if min_yp>-pad_l else min_yp-pad_l*0.1); fin_max_y=max_yp+pad_u
        if abs(fin_max_y-fin_min_y)<500:
            cen=(fin_max_y+fin_min_y)/2; span=500
            if min_yp<0 or k_net<0: span=max(500,abs(k_net)*2.2,abs(min_yp)*2.2); cen=0 if abs(cen)<span/4 else cen
            fin_min_y,fin_max_y=cen-span/2,cen+span/2
        self.ax.set_ylim([fin_min_y,fin_max_y])
        self.txt_pot.set_text(f'Potato Supply: {k_pot:,.0f} kcal/d'); self.txt_chl.set_text(f'Chlorella Supply: {k_chl:,.0f} kcal/d')
        self.txt_spc.set_text(f'Potato GH: {pot_m2:.1f} m² | Algae GH: {chl_m2:.1f} m²'); self.txt_dem.set_text(f'People Demand: {k_dem:,.0f} kcal/d')
        self.txt_ppl.set_text(f'{int(ppl)} People'); self.txt_net.set_text(f'Net Balance: {k_net:,.0f} kcal/d')
        s_txt,s_col,s_box=('Sustainable','darkgreen',self.stat_good) if k_net>=0 else ('Unsustainable','darkred',self.stat_bad)
        self.txt_stat.set_text(f'Overall System:\n{s_txt}'); self.txt_stat.set_color(s_col); self.txt_stat.set_bbox(s_box)
        self.fig.canvas.draw_idle()

class EnergySimulationTabBase(ttk.Frame): 
    def __init__(self, master, title, input_label_text, slider_unit, 
                 initial_slider_max=100, create_slider_controls=True, *args, **kwargs): # Added create_slider_controls
        super().__init__(master, *args, **kwargs)
        self.user_input_var = tk.DoubleVar(value=0) # Still might be used if create_slider_controls is true
        
        self.fig, self.ax = plt.subplots(figsize=(10, 5)) 
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=5)
        self.canvas_widget.bind("<Configure>", self._on_canvas_resize)
        self.fig.subplots_adjust(bottom=0.15, top=0.9) 

        self.controls_frame = ttk.Frame(self) # Made an attribute for SolarEnergyTab to access
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
            self.status_label = ttk.Label(self.controls_frame, text="Adjust slider.", font=("Arial", 8))
            self.status_label.pack(pady=(2,0)) 
            self.plot_energy() # Initial plot if slider exists
        else:
            # For tabs driven by external data, show a label about the data source
            self.data_source_label_var = tk.StringVar(value=input_label_text) # Use a StringVar
            self.data_source_label = ttk.Label(self.controls_frame, textvariable=self.data_source_label_var, font=("Arial", 10))
            self.data_source_label.pack(pady=5)
            self.status_label = ttk.Label(self.controls_frame, text="Area derived from Habitat Design.", font=("Arial", 8)) # Generic status
            self.status_label.pack(pady=(2,0))
            # Initial plot will be triggered by refresh from drawing_app

    def _on_canvas_resize(self, event):
        width, height = event.width, event.height
        dpi = self.fig.get_dpi()
        self.fig.set_size_inches(width / dpi, height / dpi)
        self.canvas.draw()
    
    def plot_energy(self, val=None): raise NotImplementedError("Subclasses must implement plot_energy.")
    def update_limit(self): # This method is only relevant if create_slider_controls was True
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
                         "Panel Area: 0.00 m² (from Habitat)", "m²", # Updated label text
                         initial_slider_max=100, # This won't be used for slider creation
                         create_slider_controls=False, # Opt-out of slider
                         *args, **kwargs)
        self.drawing_app_ref = drawing_app_ref
        # self.status_label is created by base, we can update it.
        self.refresh_with_new_area() # Initial plot based on habitat data

    def refresh_with_new_area(self):
        if self.drawing_app_ref and hasattr(self.drawing_app_ref, 'get_solar_panel_area'):
            self.plot_energy()
        else: # If drawing_app_ref not ready, try again shortly
            self.after(100, self.refresh_with_new_area)

    def plot_energy(self, val=None): # val from slider is no longer used
        self.ax.clear()
        current_input_area = 0.0 
        if self.drawing_app_ref and hasattr(self.drawing_app_ref, 'get_solar_panel_area'):
            current_input_area = self.drawing_app_ref.get_solar_panel_area()
        
        # Update the label text in base class if it was created
        if hasattr(self, 'data_source_label_var'):
             self.data_source_label_var.set(f"Panel Area: {current_input_area:.2f} m² (from Habitat)")

        dust = np.random.normal(0.7, 0.2/3, size=668); panel_eff = np.random.normal(0.235, (0.27-0.235)/3, size=668) 
        MARTIAN_IRRADIANCE, SECONDS_IN_HALF_SOL = 586, 88775 * 0.5; x_sols = np.arange(1, 669) 
        y_energy_kj = (MARTIAN_IRRADIANCE * current_input_area * panel_eff * dust * SECONDS_IN_HALF_SOL * 0.001) 
        
        self.ax.scatter(x_sols, y_energy_kj, s=15, color="orange", alpha=0.6, label='Solar Energy (kJ/sol)')
        self.ax.set_title(f"Solar Energy for {current_input_area:.2f} m² Panels", fontsize=10)
        self.ax.set_xlabel("Sols (Mars Days)", fontsize=9); self.ax.set_ylabel("Energy Output (kJ/sol)", fontsize=9) # kJ/sol
        self.ax.tick_params(axis='both', which='major', labelsize=8)
        self.ax.legend(fontsize=8); self.ax.grid(True, alpha=0.3); self.canvas.draw()
        if hasattr(self, 'status_label'):
            self.status_label.config(text=f"Using {current_input_area:.2f} m² from Habitat Design.", foreground="black")


class NuclearEnergyTab(EnergySimulationTabBase): 
    def __init__(self, master, *args, **kwargs): super().__init__(master, "Mars Nuclear Energy Calculator", "Pu-239 Amount (kg):", "kg", 10, *args, **kwargs)
    def plot_energy(self, val=None): # val is from the slider if it exists
        self.ax.clear(); current_in = self.user_input_var.get() # This tab still uses its own slider
        BASE_KJ_PER_KG_PER_SOL = 80000 
        efficiency = np.clip(np.random.normal(0.85, 0.05, size=668), 0.7, 0.95); x_sols = np.arange(1, 669)
        y_energy_kj = current_in * BASE_KJ_PER_KG_PER_SOL * efficiency 
        self.ax.scatter(x_sols, y_energy_kj, s=15, color="limegreen", alpha=0.6, label='Nuclear Energy (kJ/sol)') 
        self.ax.set_title(f"Nuclear Energy for {current_in:.1f} kg Pu-239", fontsize=10); self.ax.set_xlabel("Sols (Mars Days)", fontsize=9); self.ax.set_ylabel("Energy Output (kJ/sol)", fontsize=9)
        self.ax.tick_params(axis='both', which='major', labelsize=8)
        self.ax.legend(fontsize=8); self.ax.grid(True, alpha=0.3); self.canvas.draw()
        self.status_label.config(text=f"Plot updated for {current_in:.1f} kg Pu-239.", foreground="black")

class SabatierEnergyTab(EnergySimulationTabBase): 
    def __init__(self, master, *args, **kwargs): super().__init__(master, "Mars Methane (Sabatier) Energy", "H₂O for Sabatier (kg/sol):", "kg H₂O", 100, *args, **kwargs)
    def plot_energy(self, val=None): # val is from the slider
        self.ax.clear(); water_input_kg_per_sol = self.user_input_var.get() # This tab uses its own slider
        MOLAR_MASS_CH4, MOLAR_MASS_H2O = 16.04, 18.01528 
        moles_H2O_for_H2 = (water_input_kg_per_sol * 1000) / MOLAR_MASS_H2O
        moles_H2_produced = moles_H2O_for_H2 
        moles_CH4_produced = moles_H2_produced / 4 
        mass_CH4_kg_produced = (moles_CH4_produced * MOLAR_MASS_CH4) / 1000
        ENERGY_PER_KG_CH4_KJ = 55000 
        sabatier_system_efficiency = np.clip(np.random.normal(0.50, 0.1, size=668), 0.3, 0.7) 
        x_sols = np.arange(1, 669) 
        daily_energy_output_kj = mass_CH4_kg_produced * ENERGY_PER_KG_CH4_KJ * sabatier_system_efficiency
        self.ax.scatter(x_sols, daily_energy_output_kj, s=15, color="mediumpurple", alpha=0.6, label='Sabatier System Energy (kJ/sol)') 
        self.ax.set_title(f"Sabatier Energy from {water_input_kg_per_sol:.1f} kg H₂O/sol input", fontsize=10)
        self.ax.set_xlabel("Sols (Mars Days)", fontsize=9); self.ax.set_ylabel("Net Energy Output (kJ/sol)", fontsize=9)
        self.ax.tick_params(axis='both', which='major', labelsize=8)
        self.ax.legend(fontsize=8); self.ax.grid(True, alpha=0.3); self.canvas.draw()
        self.status_label.config(text=f"Plot updated for {water_input_kg_per_sol:.1f} kg H₂O/sol.", foreground="black")


class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Integrated Mars Life Support & Habitat Dashboard")
        self.geometry("1200x950") 

        # make the whole app scrollable
        container = ttk.Frame(self)
        container.pack(fill='both', expand=True)
        canvas = tk.Canvas(container)
        vsb = ttk.Scrollbar(container, orient='vertical',   command=canvas.yview)
        hsb = ttk.Scrollbar(container, orient='horizontal', command=canvas.xview)
        canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side='right',  fill='y')
        hsb.pack(side='bottom', fill='x')
        canvas.pack(side='left',  fill='both', expand=True)
        scrollable_frame = ttk.Frame(canvas)
        canvas.create_window((0,0), window=scrollable_frame, anchor='nw')
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        # place notebook in scrollable frame
        self.notebook_widget_ref = ttk.Notebook(scrollable_frame)
        self.notebook_widget_ref.pack(expand=True, fill='both', padx=5, pady=5)
        
        # Initialize tabs that DrawingApp might need to update
        self.oxygen_tab = OxygenVisualizerTab(self.notebook_widget_ref, drawing_app_ref=None) 
        self.potatoes_tab = PotatoesCaloriesTab(self.notebook_widget_ref, drawing_app_ref=None) 
        self.solar_tab = SolarEnergyTab(self.notebook_widget_ref, drawing_app_ref=None) # Solar tab also needs drawing_app_ref
        
        # Initialize DrawingApp and pass references to the other tabs
        self.habitat_design_tab = DrawingApp(self.notebook_widget_ref, 
                                             oxygen_tab_ref=self.oxygen_tab, 
                                             potatoes_tab_ref=self.potatoes_tab,
                                             solar_tab_ref=self.solar_tab) # Pass solar_tab_ref
        
        # Now that habitat_design_tab exists, set its reference in the other tabs
        self.oxygen_tab.drawing_app_ref = self.habitat_design_tab
        self.potatoes_tab.drawing_app_ref = self.habitat_design_tab
        self.solar_tab.drawing_app_ref = self.habitat_design_tab # Set ref for solar tab


        # Add tabs to notebook in desired order
        self.notebook_widget_ref.add(self.habitat_design_tab, text="Habitat Design & Atmos")
        self.notebook_widget_ref.add(self.oxygen_tab, text="System O₂ & CO₂")
        self.notebook_widget_ref.add(self.potatoes_tab, text="Food & Calorie Sim")
        self.notebook_widget_ref.add(self.solar_tab, text="Solar Energy") # Add SolarEnergyTab to notebook

        # Other energy tabs that are still independent
        self.nuclear_tab = NuclearEnergyTab(self.notebook_widget_ref)
        self.notebook_widget_ref.add(self.nuclear_tab, text="Nuclear Energy")
        self.sabatier_tab = SabatierEnergyTab(self.notebook_widget_ref)
        self.notebook_widget_ref.add(self.sabatier_tab, text="Sabatier Process Energy")
        
        # Initial refresh for tabs dependent on DrawingApp areas
        self.oxygen_tab.refresh_with_new_areas()
        self.potatoes_tab.refresh_with_new_areas()
        self.solar_tab.refresh_with_new_area() # Call its refresh method

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