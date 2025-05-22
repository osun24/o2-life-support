import tkinter as tk
from tkinter import ttk
import math

# Attempt to import Shapely
try:
    from shapely.geometry import Polygon, Point
    from shapely.ops import unary_union
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False
    print("Shapely library not found. For accurate union area, please install it: pip install shapely")


# --- Constants ---
CELL_SIZE = 30
AXIS_MARGIN = 30
CANVAS_WIDTH = AXIS_MARGIN + 600 + CELL_SIZE
CANVAS_HEIGHT = AXIS_MARGIN + 480 + CELL_SIZE
GRID_COLOR = "lightgray"
AXIS_LINE_COLOR = "black"
LABEL_COLOR = "dim gray"
LABEL_FONT = ("Arial", 8)
LABEL_INTERVAL = CELL_SIZE * 3

DEFAULT_RECT_COLOR = "lightblue"
DEFAULT_CIRCLE_COLOR = "lightcoral"
SELECTED_OUTLINE_COLOR = "green"
SELECTED_OUTLINE_WIDTH = 2
DEFAULT_OUTLINE_COLOR = "black"
DEFAULT_OUTLINE_WIDTH = 1

# --- Shape Classes (Identical to the previous version) ---
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
        self.canvas_item_id = canvas.create_rectangle(self.x, self.y, self.x + self.width, self.y + self.height,
                                                      fill=self.color, outline=DEFAULT_OUTLINE_COLOR, width=DEFAULT_OUTLINE_WIDTH)
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
        self.canvas_item_id = canvas.create_oval(self.x - self.radius, self.y - self.radius, self.x + self.radius, self.y + self.radius,
                                                 fill=self.color, outline=DEFAULT_OUTLINE_COLOR, width=DEFAULT_OUTLINE_WIDTH)
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
        self.root.title("Tkinter Drawing Tool - Shapely Union Area")

        self.current_mode = "select"
        self.shapes_list = []
        self.selected_shape_obj = None
        self.is_dragging = False
        self.was_resizing_session = False # Tracks if the specific drag was a resize
        self.drag_action_occurred = False # Tracks if any drag (move or resize) happened

        self.shape_drag_offset_x = 0
        self.shape_drag_offset_y = 0

        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(control_frame, text="Mode:").pack(side=tk.LEFT, padx=5)
        self.mode_var = tk.StringVar(value=self.current_mode)
        modes = [("Select (Drag=Move, Shift+Drag=Resize)", "select"),
                 ("Draw Rectangle", "rectangle"), ("Draw Circle", "circle")]
        for text, mode_val in modes:
            ttk.Radiobutton(control_frame, text=text, variable=self.mode_var, value=mode_val, command=self.set_current_mode).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="Delete Selected", command=self.delete_selected_shape).pack(side=tk.LEFT, padx=10)

        self.union_area_label_var = tk.StringVar(value="Union Area: N/A")
        if not SHAPELY_AVAILABLE:
            self.union_area_label_var.set("Union Area: (Install Shapely for this feature)")
        ttk.Label(control_frame, textvariable=self.union_area_label_var, width=40).pack(side=tk.LEFT, padx=10)

        self.drawing_canvas = tk.Canvas(self.root, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg="white", relief=tk.SUNKEN, borderwidth=1)
        self.drawing_canvas.pack(padx=10, pady=10, expand=True, fill=tk.BOTH)
        self.draw_visual_grid_and_axes()

        self.drawing_canvas.bind("<Button-1>", self.handle_mouse_down)
        self.drawing_canvas.bind("<B1-Motion>", self.handle_mouse_drag)
        self.drawing_canvas.bind("<ButtonRelease-1>", self.handle_mouse_up)
        self.root.bind("<Delete>", self.handle_delete_key_press)
        self.root.bind("<BackSpace>", self.handle_delete_key_press)
        self.update_union_area_display()

    def update_union_area_display(self):
        if not SHAPELY_AVAILABLE:
            total_individual_area = 0.0
            for shape_obj in self.shapes_list:
                total_individual_area += shape_obj.calculate_area()
            self.union_area_label_var.set(f"Sum of Areas: {total_individual_area:.2f} units² (Shapely needed for union)")
            return

        if not self.shapes_list:
            self.union_area_label_var.set("Union Area: 0.00 units²")
            return

        shapely_geometries = []
        for shape_obj in self.shapes_list:
            try:
                if isinstance(shape_obj, Rectangle):
                    if shape_obj.width > 0 and shape_obj.height > 0:
                        shapely_rect = Polygon([(shape_obj.x, shape_obj.y), (shape_obj.x + shape_obj.width, shape_obj.y),
                                                (shape_obj.x + shape_obj.width, shape_obj.y + shape_obj.height), (shape_obj.x, shape_obj.y + shape_obj.height)])
                        if shapely_rect.is_valid: shapely_geometries.append(shapely_rect)
                elif isinstance(shape_obj, Circle):
                    if shape_obj.radius > 0:
                        shapely_circle = Point(shape_obj.x, shape_obj.y).buffer(shape_obj.radius)
                        if shapely_circle.is_valid: shapely_geometries.append(shapely_circle)
            except Exception: pass

        if not shapely_geometries:
            self.union_area_label_var.set("Union Area: 0.00 units² (or no valid shapes)")
            return
        try:
            united_geometry = unary_union(shapely_geometries)
            self.union_area_label_var.set(f"Union Area: {united_geometry.area:.2f} units²")
        except Exception: self.union_area_label_var.set("Union Area: Error")

    def set_current_mode(self):
        old_mode = self.current_mode
        self.current_mode = self.mode_var.get()
        if self.selected_shape_obj and old_mode == "select" and self.current_mode != "select":
            self.selected_shape_obj.deselect(self.drawing_canvas)
            self.selected_shape_obj = None
        self.is_dragging = False; self.was_resizing_session = False; self.drag_action_occurred = False

    def draw_visual_grid_and_axes(self):
        self.drawing_canvas.delete("grid", "axis_label", "grid_axis_line")
        self.drawing_canvas.create_line(AXIS_MARGIN, AXIS_MARGIN, CANVAS_WIDTH, AXIS_MARGIN, fill=AXIS_LINE_COLOR, width=1, tags="grid_axis_line")
        self.drawing_canvas.create_line(AXIS_MARGIN, AXIS_MARGIN, AXIS_MARGIN, CANVAS_HEIGHT, fill=AXIS_LINE_COLOR, width=1, tags="grid_axis_line")
        for y_coord in range(AXIS_MARGIN + CELL_SIZE, CANVAS_HEIGHT, CELL_SIZE): self.drawing_canvas.create_line(AXIS_MARGIN, y_coord, CANVAS_WIDTH, y_coord, fill=GRID_COLOR, tags="grid")
        for x_coord in range(AXIS_MARGIN + CELL_SIZE, CANVAS_WIDTH, CELL_SIZE): self.drawing_canvas.create_line(x_coord, AXIS_MARGIN, x_coord, CANVAS_HEIGHT, fill=GRID_COLOR, tags="grid")
        for x_coord_on_canvas in range(AXIS_MARGIN, CANVAS_WIDTH, CELL_SIZE):
            if (x_coord_on_canvas - AXIS_MARGIN) % LABEL_INTERVAL == 0: self.drawing_canvas.create_text(x_coord_on_canvas, AXIS_MARGIN - 10, text=str(x_coord_on_canvas - AXIS_MARGIN), anchor=tk.S, font=LABEL_FONT, fill=LABEL_COLOR, tags="axis_label")
        for y_coord_on_canvas in range(AXIS_MARGIN, CANVAS_HEIGHT, CELL_SIZE):
            if (y_coord_on_canvas - AXIS_MARGIN) % LABEL_INTERVAL == 0: self.drawing_canvas.create_text(AXIS_MARGIN - 10, y_coord_on_canvas, text=str(y_coord_on_canvas - AXIS_MARGIN), anchor=tk.E, font=LABEL_FONT, fill=LABEL_COLOR, tags="axis_label")
        self.drawing_canvas.tag_lower("grid"); self.drawing_canvas.tag_lower("grid_axis_line", "grid"); self.drawing_canvas.tag_lower("axis_label")

    def handle_mouse_down(self, event):
        self.is_dragging = True
        self.was_resizing_session = False
        self.drag_action_occurred = False # Reset for new drag
        effective_event_x = event.x; effective_event_y = event.y

        if self.current_mode == "select":
            clicked_on_shape = None
            for shape_obj in reversed(self.shapes_list):
                if shape_obj.contains_point(effective_event_x, effective_event_y): clicked_on_shape = shape_obj; break
            if clicked_on_shape:
                if self.selected_shape_obj and self.selected_shape_obj != clicked_on_shape: self.selected_shape_obj.deselect(self.drawing_canvas)
                self.selected_shape_obj = clicked_on_shape; self.selected_shape_obj.select(self.drawing_canvas)
                self.shape_drag_offset_x = effective_event_x - self.selected_shape_obj.x; self.shape_drag_offset_y = effective_event_y - self.selected_shape_obj.y
            else:
                if self.selected_shape_obj: self.selected_shape_obj.deselect(self.drawing_canvas); self.selected_shape_obj = None
                self.shape_drag_offset_x = 0; self.shape_drag_offset_y = 0
        elif self.current_mode == "rectangle": self.add_new_shape(Rectangle(effective_event_x, effective_event_y, CELL_SIZE * 3, CELL_SIZE * 2, DEFAULT_RECT_COLOR))
        elif self.current_mode == "circle": self.add_new_shape(Circle(effective_event_x, effective_event_y, CELL_SIZE * 1.5, DEFAULT_CIRCLE_COLOR))
            
    def add_new_shape(self, shape_obj):
        shape_obj.draw(self.drawing_canvas); self.shapes_list.append(shape_obj)
        if self.selected_shape_obj: self.selected_shape_obj.deselect(self.drawing_canvas)
        self.selected_shape_obj = shape_obj; self.selected_shape_obj.select(self.drawing_canvas)
        self.mode_var.set("select"); self.current_mode = "select"
        self.update_union_area_display()

    def handle_mouse_drag(self, event):
        if not self.is_dragging or not self.selected_shape_obj or self.current_mode != "select": return
        
        self.drag_action_occurred = True # Mark that a drag is happening
        effective_event_x = event.x; effective_event_y = event.y
        is_shift_pressed = (event.state & 0x0001) != 0

        if is_shift_pressed:
            self.was_resizing_session = True # This specific drag is a resize
            if isinstance(self.selected_shape_obj, Rectangle): self.selected_shape_obj.resize(self.drawing_canvas, effective_event_x, effective_event_y)
            elif isinstance(self.selected_shape_obj, Circle): self.selected_shape_obj.resize(self.drawing_canvas, effective_event_x, effective_event_y)
        else: # Move mode
            # self.was_resizing_session remains false or is already false
            new_shape_ref_x = effective_event_x - self.shape_drag_offset_x; new_shape_ref_y = effective_event_y - self.shape_drag_offset_y
            self.selected_shape_obj.move_to(self.drawing_canvas, new_shape_ref_x, new_shape_ref_y)

    def handle_mouse_up(self, event):
        # Check if any drag action (move or resize) actually occurred for the selected shape
        if self.is_dragging and self.selected_shape_obj and self.drag_action_occurred:
            if self.was_resizing_session:
                self.selected_shape_obj.update_coords_from_canvas(self.drawing_canvas)
            # Whether it was a move or a resize, the geometry might have changed relative to others
            self.update_union_area_display() 
        
        self.is_dragging = False
        self.was_resizing_session = False
        self.drag_action_occurred = False # Reset for next interaction sequence

    def delete_selected_shape(self):
        if self.selected_shape_obj:
            self.drawing_canvas.delete(self.selected_shape_obj.canvas_item_id)
            if self.selected_shape_obj in self.shapes_list: self.shapes_list.remove(self.selected_shape_obj)
            self.selected_shape_obj = None
            self.update_union_area_display()

    def handle_delete_key_press(self, event): self.delete_selected_shape()

if __name__ == "__main__":
    app_root = tk.Tk()
    drawing_app = DrawingApp(app_root)
    app_root.mainloop()
