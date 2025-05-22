import tkinter as tk
from tkinter import ttk
import math

# --- Constants ---
CELL_SIZE = 30
CANVAS_WIDTH = 660
CANVAS_HEIGHT = 510
GRID_COLOR = "lightgray"
DEFAULT_RECT_COLOR = "lightblue"
DEFAULT_CIRCLE_COLOR = "lightcoral"
SELECTED_OUTLINE_COLOR = "green"
SELECTED_OUTLINE_WIDTH = 2
DEFAULT_OUTLINE_COLOR = "black"
DEFAULT_OUTLINE_WIDTH = 1

# --- Shape Classes ---
class Shape:
    """Base class for shapes."""
    def __init__(self, x, y, color):
        self.x = x  # For rect: top-left x; for circle: center x
        self.y = y  # For rect: top-left y; for circle: center y
        self.color = color
        self.canvas_item_id = None
        self.selected = False

    def draw(self, canvas):
        raise NotImplementedError

    def contains_point(self, px, py):
        raise NotImplementedError

    def select(self, canvas):
        self.selected = True
        if self.canvas_item_id:
            canvas.itemconfig(self.canvas_item_id,
                              outline=SELECTED_OUTLINE_COLOR,
                              width=SELECTED_OUTLINE_WIDTH)
            canvas.tag_raise(self.canvas_item_id)

    def deselect(self, canvas):
        self.selected = False
        if self.canvas_item_id:
            canvas.itemconfig(self.canvas_item_id,
                              outline=DEFAULT_OUTLINE_COLOR,
                              width=DEFAULT_OUTLINE_WIDTH)

    def move_to(self, canvas, new_ref_x, new_ref_y):
        raise NotImplementedError

    def resize(self, canvas, param1, param2):
        """Resizes the shape. Params depend on shape type."""
        raise NotImplementedError # To be implemented by subclasses

    def update_coords_from_canvas(self, canvas):
        """Updates shape's internal geometric attributes based on its canvas item's current coordinates."""
        pass # To be implemented by subclasses


class Rectangle(Shape):
    def __init__(self, x, y, width, height, color):
        super().__init__(x, y, color) # x, y is top-left
        self.width = width
        self.height = height

    def draw(self, canvas):
        self.canvas_item_id = canvas.create_rectangle(
            self.x, self.y,
            self.x + self.width, self.y + self.height,
            fill=self.color, outline=DEFAULT_OUTLINE_COLOR, width=DEFAULT_OUTLINE_WIDTH
        )

    def contains_point(self, px, py):
        return self.x <= px <= self.x + self.width and \
               self.y <= py <= self.y + self.height

    def move_to(self, canvas, new_x, new_y):
        self.x = new_x
        self.y = new_y
        if self.canvas_item_id:
            canvas.coords(self.canvas_item_id,
                          self.x, self.y,
                          self.x + self.width, self.y + self.height)

    def resize(self, canvas, new_corner_x, new_corner_y):
        """Resizes based on a new bottom-right corner, maintaining top-left (self.x, self.y)."""
        self.width = max(CELL_SIZE // 2, new_corner_x - self.x)
        self.height = max(CELL_SIZE // 2, new_corner_y - self.y)
        if self.canvas_item_id:
            canvas.coords(self.canvas_item_id, self.x, self.y, self.x + self.width, self.y + self.height)

    def update_coords_from_canvas(self, canvas):
        if self.canvas_item_id:
            coords = canvas.coords(self.canvas_item_id)
            if coords: # Ensure coords exist
                self.x = coords[0]
                self.y = coords[1]
                self.width = coords[2] - coords[0]
                self.height = coords[3] - coords[1]


class Circle(Shape):
    def __init__(self, center_x, center_y, radius, color):
        super().__init__(center_x, center_y, color) # x, y is center
        self.radius = radius

    def draw(self, canvas):
        self.canvas_item_id = canvas.create_oval(
            self.x - self.radius, self.y - self.radius,
            self.x + self.radius, self.y + self.radius,
            fill=self.color, outline=DEFAULT_OUTLINE_COLOR, width=DEFAULT_OUTLINE_WIDTH
        )

    def contains_point(self, px, py):
        return (px - self.x)**2 + (py - self.y)**2 <= self.radius**2

    def move_to(self, canvas, new_center_x, new_center_y):
        self.x = new_center_x
        self.y = new_center_y
        if self.canvas_item_id:
            canvas.coords(self.canvas_item_id,
                          self.x - self.radius, self.y - self.radius,
                          self.x + self.radius, self.y + self.radius)

    def resize(self, canvas, edge_x, edge_y):
        """Resizes based on a point (edge_x, edge_y) on its new circumference, maintaining center (self.x, self.y)."""
        new_radius = math.sqrt((edge_x - self.x)**2 + (edge_y - self.y)**2)
        self.radius = max(CELL_SIZE // 4, new_radius)
        if self.canvas_item_id:
            canvas.coords(self.canvas_item_id,
                          self.x - self.radius, self.y - self.radius,
                          self.x + self.radius, self.y + self.radius)

    def update_coords_from_canvas(self, canvas):
        if self.canvas_item_id:
            coords = canvas.coords(self.canvas_item_id)
            if coords: # Ensure coords exist
                self.x = (coords[0] + coords[2]) / 2 # Recalculate center x
                self.y = (coords[1] + coords[3]) / 2 # Recalculate center y
                self.radius = (coords[2] - coords[0]) / 2


# --- Main Application ---
class DrawingApp:
    def __init__(self, master_root):
        self.root = master_root
        self.root.title("Tkinter Drawing Tool - Move, Resize, Delete")

        self.current_mode = "select"
        self.shapes_list = []
        self.selected_shape_obj = None
        self.is_dragging = False
        self.was_resizing_session = False # Flag to know if last drag was a resize
        
        self.shape_drag_offset_x = 0
        self.shape_drag_offset_y = 0

        # --- UI Frame for Controls ---
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(control_frame, text="Mode:").pack(side=tk.LEFT, padx=5)
        
        self.mode_var = tk.StringVar(value=self.current_mode)
        modes = [("Select (Drag=Move, Shift+Drag=Resize)", "select"),
                 ("Draw Rectangle", "rectangle"),
                 ("Draw Circle", "circle")]
        for text, mode_val in modes:
            rb = ttk.Radiobutton(control_frame, text=text, variable=self.mode_var,
                                 value=mode_val, command=self.set_current_mode)
            rb.pack(side=tk.LEFT, padx=2)

        delete_button = ttk.Button(control_frame, text="Delete Selected", command=self.delete_selected_shape)
        delete_button.pack(side=tk.LEFT, padx=10)

        # --- Canvas Setup ---
        self.drawing_canvas = tk.Canvas(self.root, width=CANVAS_WIDTH, height=CANVAS_HEIGHT,
                                        bg="white", relief=tk.SUNKEN, borderwidth=1)
        self.drawing_canvas.pack(padx=10, pady=10, expand=True, fill=tk.BOTH)
        self.draw_visual_grid()

        # --- Event Bindings ---
        self.drawing_canvas.bind("<Button-1>", self.handle_mouse_down)
        self.drawing_canvas.bind("<B1-Motion>", self.handle_mouse_drag)
        self.drawing_canvas.bind("<ButtonRelease-1>", self.handle_mouse_up)
        self.root.bind("<Delete>", self.handle_delete_key_press)
        self.root.bind("<BackSpace>", self.handle_delete_key_press)


    def set_current_mode(self):
        self.current_mode = self.mode_var.get()
        if self.selected_shape_obj and self.current_mode != "select":
            self.selected_shape_obj.deselect(self.drawing_canvas)
            self.selected_shape_obj = None
        self.is_dragging = False
        self.was_resizing_session = False

    def draw_visual_grid(self):
        for i in range(0, CANVAS_WIDTH, CELL_SIZE):
            self.drawing_canvas.create_line(i, 0, i, CANVAS_HEIGHT, fill=GRID_COLOR, tags="grid")
        for i in range(0, CANVAS_HEIGHT, CELL_SIZE):
            self.drawing_canvas.create_line(0, i, CANVAS_WIDTH, i, fill=GRID_COLOR, tags="grid")
        self.drawing_canvas.tag_lower("grid")

    def handle_mouse_down(self, event):
        self.is_dragging = True
        self.was_resizing_session = False # Reset resize flag for new drag session

        if self.current_mode == "select":
            clicked_on_shape = None
            for shape_obj in reversed(self.shapes_list):
                if shape_obj.contains_point(event.x, event.y):
                    clicked_on_shape = shape_obj
                    break
            
            if clicked_on_shape:
                if self.selected_shape_obj and self.selected_shape_obj != clicked_on_shape:
                    self.selected_shape_obj.deselect(self.drawing_canvas)
                
                self.selected_shape_obj = clicked_on_shape
                self.selected_shape_obj.select(self.drawing_canvas)
                
                self.shape_drag_offset_x = event.x - self.selected_shape_obj.x
                self.shape_drag_offset_y = event.y - self.selected_shape_obj.y
            else:
                if self.selected_shape_obj:
                    self.selected_shape_obj.deselect(self.drawing_canvas)
                    self.selected_shape_obj = None
                self.shape_drag_offset_x = 0
                self.shape_drag_offset_y = 0

        elif self.current_mode == "rectangle":
            x_coord, y_coord = event.x, event.y
            new_shape = Rectangle(x_coord, y_coord, CELL_SIZE * 3, CELL_SIZE * 2, DEFAULT_RECT_COLOR)
            self.add_new_shape(new_shape)

        elif self.current_mode == "circle":
            x_coord, y_coord = event.x, event.y
            new_shape = Circle(x_coord, y_coord, CELL_SIZE * 1.5, DEFAULT_CIRCLE_COLOR)
            self.add_new_shape(new_shape)
            
    def add_new_shape(self, shape_obj):
        shape_obj.draw(self.drawing_canvas)
        self.shapes_list.append(shape_obj)
        if self.selected_shape_obj:
            self.selected_shape_obj.deselect(self.drawing_canvas)
        self.selected_shape_obj = shape_obj
        self.selected_shape_obj.select(self.drawing_canvas)
        self.mode_var.set("select") # Switch to select mode
        self.current_mode = "select"
        # Offsets will be calculated if the user clicks on this new shape to drag it

    def handle_mouse_drag(self, event):
        if not self.is_dragging or not self.selected_shape_obj or self.current_mode != "select":
            return

        # Check for Shift key (state mask 0x0001 for Shift)
        is_shift_pressed = (event.state & 0x0001) != 0

        if is_shift_pressed:
            # RESIZE mode
            self.was_resizing_session = True # Mark that resize happened in this drag session
            if isinstance(self.selected_shape_obj, Rectangle):
                self.selected_shape_obj.resize(self.drawing_canvas, event.x, event.y)
            elif isinstance(self.selected_shape_obj, Circle):
                self.selected_shape_obj.resize(self.drawing_canvas, event.x, event.y)
        else:
            # MOVE mode
            new_shape_ref_x = event.x - self.shape_drag_offset_x
            new_shape_ref_y = event.y - self.shape_drag_offset_y
            self.selected_shape_obj.move_to(self.drawing_canvas, new_shape_ref_x, new_shape_ref_y)

    def handle_mouse_up(self, event):
        if self.is_dragging and self.selected_shape_obj:
            if self.was_resizing_session: # If a resize occurred during this drag
                self.selected_shape_obj.update_coords_from_canvas(self.drawing_canvas)
            # For moving, the object's x,y are already updated in move_to
        
        self.is_dragging = False
        self.was_resizing_session = False # Reset for next interaction

    def delete_selected_shape(self):
        if self.selected_shape_obj:
            self.drawing_canvas.delete(self.selected_shape_obj.canvas_item_id)
            if self.selected_shape_obj in self.shapes_list:
                 self.shapes_list.remove(self.selected_shape_obj)
            self.selected_shape_obj = None

    def handle_delete_key_press(self, event):
        self.delete_selected_shape()

if __name__ == "__main__":
    app_root = tk.Tk()
    drawing_app = DrawingApp(app_root)
    app_root.mainloop()