import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import matplotlib.patches as patches
import matplotlib.path as mpath
import random
from scipy.stats import norm
import time
from typing import Dict, List, Tuple, Optional, Union
import threading
import argparse
from collections import defaultdict
from enum import Enum, auto
from shapely.geometry import Point, Polygon

# Constants
NORMAL_O2_PERCENTAGE = 21.0
NORMAL_CO2_PPM = 400.0
MARS_O2_PERCENTAGE = 0.13
MARS_CO2_PERCENTAGE = 95.0
HUMAN_O2_CONSUMPTION_PER_HOUR = 0.02  # percentage points per hour per person
HUMAN_CO2_PRODUCTION_PER_HOUR = 35.0  # ppm per hour per person

class RoomType(Enum):
    LIVING_QUARTERS = auto()
    LABORATORY = auto()
    GREENHOUSE = auto()
    COMMAND_CENTER = auto()
    AIRLOCK = auto()
    CORRIDOR = auto()
    STORAGE = auto()
    MEDICAL_BAY = auto()
    
    @classmethod
    def get_color(cls, room_type):
        colors = {
            cls.LIVING_QUARTERS: (0.8, 0.8, 1.0),  # Light blue
            cls.LABORATORY: (1.0, 1.0, 0.7),       # Light yellow
            cls.GREENHOUSE: (0.7, 1.0, 0.7),       # Light green
            cls.COMMAND_CENTER: (1.0, 0.7, 0.7),   # Light red
            cls.AIRLOCK: (0.7, 0.7, 0.7),          # Gray
            cls.CORRIDOR: (0.9, 0.9, 0.9),         # Light gray
            cls.STORAGE: (0.8, 0.7, 0.6),          # Brown
            cls.MEDICAL_BAY: (1.0, 0.8, 0.8),      # Light pink
        }
        return colors.get(room_type, (1.0, 1.0, 1.0))  # Default white


class Door:
    def __init__(self, room1_id: int, room2_id: int, position: Tuple[float, float], 
                 width: float = 2.0, is_open: bool = True):
        self.room1_id = room1_id
        self.room2_id = room2_id
        self.position = position
        self.width = width
        self.is_open = is_open
        self.flow_rate = 0.2 if is_open else 0.0  # Gas exchange rate when open
        
    def toggle(self):
        self.is_open = not self.is_open
        self.flow_rate = 0.2 if self.is_open else 0.0


class Room:
    def __init__(self, room_id: int, vertices: List[Tuple[float, float]], room_type: RoomType = None):
        self.id = room_id
        self.vertices = vertices
        self.room_type = room_type or RoomType.LIVING_QUARTERS
        
        # Calculate bounding box
        x_coords = [v[0] for v in vertices]
        y_coords = [v[1] for v in vertices]
        self.x = min(x_coords)
        self.y = min(y_coords)
        self.width = max(x_coords) - self.x
        self.height = max(y_coords) - self.y
        
        # Center coordinates
        self.center_x = self.x + self.width / 2
        self.center_y = self.y + self.height / 2
        
        # Create polygon for containment tests
        self.polygon = Polygon(vertices)
        
        # Area calculation - useful for volume-based calculations
        self.area = self.polygon.area
        
        self.o2_level = NORMAL_O2_PERCENTAGE
        self.co2_level = NORMAL_CO2_PPM
        self.sensors = []
        self.population = 0
        self.breaches = []
        
        # For visualization
        self.base_color = RoomType.get_color(self.room_type)
        self.label = room_type.name.replace("_", " ") if room_type else "ROOM"
        
    def add_sensor(self, sensor):
        self.sensors.append(sensor)
        
    def add_breach(self, breach):
        self.breaches.append(breach)
        
    def remove_breach(self, breach):
        if breach in self.breaches:
            self.breaches.remove(breach)
            
    def is_point_inside(self, x, y):
        return self.polygon.contains(Point(x, y))
                
    def get_patch(self, alpha=0.7, color_override=None):
        path = mpath.Path(self.vertices)
        color = color_override or self.base_color
        return patches.PathPatch(path, facecolor=color, edgecolor='black', 
                              linewidth=1, alpha=alpha)


class MarsEnvironment:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.o2_level = MARS_O2_PERCENTAGE
        self.co2_level = MARS_CO2_PERCENTAGE * 10000  # Convert from percentage to ppm
        self.sensors = []
        
    def add_sensor(self, sensor):
        self.sensors.append(sensor)


class Sensor:
    def __init__(self, sensor_id: str, location: Tuple[int, int], 
                variance_o2: float = 0.5, variance_co2: float = 20.0):
        self.id = sensor_id
        self.x, self.y = location
        self.variance_o2 = variance_o2
        self.variance_co2 = variance_co2
        self.last_o2_reading = None
        self.last_co2_reading = None
        
    def read_o2(self, true_value: float) -> float:
        reading = np.random.normal(true_value, self.variance_o2)
        self.last_o2_reading = max(0, reading)
        return self.last_o2_reading
        
    def read_co2(self, true_value: float) -> float:
        reading = np.random.normal(true_value, self.variance_co2)
        self.last_co2_reading = max(0, reading)
        return self.last_co2_reading


class Breach:
    def __init__(self, x: int, y: int, radius: float, flow_rate: float):
        self.x = x
        self.y = y
        self.radius = radius
        self.flow_rate = flow_rate  # percentage points per hour
        self.creation_time = time.time()


class HealthEffects:
    @staticmethod
    def calculate_health_effects(o2_level: float, co2_level: float) -> Dict:
        effects = {
            "headache": 0.0,
            "dizziness": 0.0,
            "productivity": 100.0,
            "morale": 100.0
        }
        
        # O2 effects
        if o2_level < 19.5:
            effects["dizziness"] = 20.0 * (19.5 - o2_level)
            effects["productivity"] -= 10.0 * (19.5 - o2_level)
            
        if o2_level < 16.0:
            effects["headache"] = 30.0 * (16.0 - o2_level)
            effects["productivity"] -= 30.0 * (16.0 - o2_level)
            effects["morale"] -= 20.0 * (16.0 - o2_level)
            
        # CO2 effects    
        if co2_level > 1000.0:
            effects["headache"] += (co2_level - 1000.0) / 500.0 * 10.0
            effects["productivity"] -= (co2_level - 1000.0) / 500.0 * 5.0
            effects["morale"] -= (co2_level - 1000.0) / 1000.0 * 10.0
            
        if co2_level > 5000.0:
            effects["dizziness"] += (co2_level - 5000.0) / 1000.0 * 20.0
            
        # Normalize values
        effects["headache"] = min(100.0, max(0.0, effects["headache"]))
        effects["dizziness"] = min(100.0, max(0.0, effects["dizziness"]))
        effects["productivity"] = min(100.0, max(0.0, effects["productivity"]))
        effects["morale"] = min(100.0, max(0.0, effects["morale"]))
        
        return effects


class BayesianFusion:
    @staticmethod
    def fuse_sensor_readings(sensors: List[Sensor], measure_type: str) -> Tuple[float, float]:
        if not sensors:
            return None, None
            
        if measure_type == "o2":
            readings = [s.last_o2_reading for s in sensors if s.last_o2_reading is not None]
            variances = [s.variance_o2 for s in sensors if s.last_o2_reading is not None]
        else:  # co2
            readings = [s.last_co2_reading for s in sensors if s.last_co2_reading is not None]
            variances = [s.variance_co2 for s in sensors if s.last_co2_reading is not None]
            
        if not readings:
            return None, None
            
        # Bayesian fusion formula for Gaussian distributions
        precision_sum = sum(1/var for var in variances)
        fused_value = sum(r/var for r, var in zip(readings, variances)) / precision_sum
        fused_variance = 1 / precision_sum
        
        return fused_value, fused_variance


class ColonySimulation:
    def __init__(self, grid_width: int = 50, grid_height: int = 50):
        self.grid_width = grid_width
        self.grid_height = grid_height
        self.rooms = []
        self.doors = []
        self.mars_env = MarsEnvironment(grid_width, grid_height)
        self.time_step = 0
        self.time_scale = 1.0  # 1 sim hour = 1 real second
        self.running = False
        self.room_id_counter = 1
        self.sensor_id_counter = 1
        
    def add_room(self, vertices: List[Tuple[float, float]], room_type: RoomType = None) -> Room:
        room = Room(self.room_id_counter, vertices, room_type)
        self.room_id_counter += 1
        self.rooms.append(room)
        return room
    
    def add_door(self, room1_id: int, room2_id: int, position: Tuple[float, float], 
                 width: float = 2.0, is_open: bool = True) -> Door:
        door = Door(room1_id, room2_id, position, width, is_open)
        self.doors.append(door)
        return door
        
    def add_sensor(self, x: int, y: int) -> Optional[Sensor]:
        room = self.find_room_at_point(x, y)
        sensor_id = f"S{self.sensor_id_counter}"
        self.sensor_id_counter += 1
        
        sensor = Sensor(sensor_id, (x, y))
        
        if room:
            room.add_sensor(sensor)
        else:
            self.mars_env.add_sensor(sensor)
            
        return sensor
        
    def find_room_at_point(self, x: int, y: int) -> Optional[Room]:
        for room in self.rooms:
            if room.is_point_inside(x, y):
                return room
        return None
        
    def add_breach(self, x: int, y: int, radius: float, flow_rate: float) -> None:
        room = self.find_room_at_point(x, y)
        if room:
            breach = Breach(x, y, radius, flow_rate)
            room.add_breach(breach)
    
    def toggle_door(self, x: int, y: int, radius: float = 3.0) -> bool:
        """Toggle door state if clicked near a door's position"""
        for door in self.doors:
            dx = door.position[0] - x
            dy = door.position[1] - y
            distance = np.sqrt(dx*dx + dy*dy)
            if distance <= radius:
                door.toggle()
                return True
        return False
            
    def update_simulation(self, dt_hours: float) -> None:
        # Update human-caused changes
        for room in self.rooms:
            if room.population > 0:
                # O2 consumption - scale by room size for realism
                o2_consumed = HUMAN_O2_CONSUMPTION_PER_HOUR * room.population * dt_hours
                # Smaller rooms will see faster O2 depletion
                size_factor = 100 / max(room.area, 10)  # Prevent division by very small values
                room.o2_level = max(0, room.o2_level - o2_consumed * size_factor)
                
                # CO2 production
                co2_produced = HUMAN_CO2_PRODUCTION_PER_HOUR * room.population * dt_hours
                room.co2_level += co2_produced * size_factor
        
        # Update breach effects
        for room in self.rooms:
            for breach in list(room.breaches):
                # Exchange gases with Mars atmosphere
                o2_flow = (self.mars_env.o2_level - room.o2_level) * breach.flow_rate * dt_hours
                co2_flow = (self.mars_env.co2_level - room.co2_level) * breach.flow_rate * dt_hours
                
                room.o2_level += o2_flow
                room.co2_level += co2_flow
        
        # Update gas exchange through doors
        for door in self.doors:
            if door.flow_rate > 0:  # Door is open or has a leak
                room1 = None
                room2 = None
                
                # Find the two rooms connected by this door
                for room in self.rooms:
                    if room.id == door.room1_id:
                        room1 = room
                    elif room.id == door.room2_id:
                        room2 = room
                
                if room1 and room2:
                    # Gas exchange between rooms
                    o2_diff = room2.o2_level - room1.o2_level
                    co2_diff = room2.co2_level - room1.co2_level
                    
                    # Calculate flow based on difference and door attributes
                    o2_flow = o2_diff * door.flow_rate * dt_hours
                    co2_flow = co2_diff * door.flow_rate * dt_hours
                    
                    # Apply the changes
                    room1.o2_level += o2_flow
                    room2.o2_level -= o2_flow
                    room1.co2_level += co2_flow
                    room2.co2_level -= co2_flow
                
        # Update sensors
        for room in self.rooms:
            for sensor in room.sensors:
                sensor.read_o2(room.o2_level)
                sensor.read_co2(room.co2_level)
                
        for sensor in self.mars_env.sensors:
            sensor.read_o2(self.mars_env.o2_level)
            sensor.read_co2(self.mars_env.co2_level)
            
    def set_population(self, room_id: int, population: int) -> bool:
        for room in self.rooms:
            if room.id == room_id:
                room.population = max(0, population)
                return True
        return False
    
    def run_simulation_thread(self, update_interval: float = 0.1):
        self.running = True
        last_time = time.time()
        
        while self.running:
            current_time = time.time()
            dt_real = current_time - last_time
            dt_sim = dt_real * self.time_scale  # Convert to simulation hours
            
            self.update_simulation(dt_sim)
            self.time_step += dt_sim
            
            last_time = current_time
            time.sleep(update_interval)
            
    def start_simulation(self):
        self.sim_thread = threading.Thread(target=self.run_simulation_thread)
        self.sim_thread.daemon = True
        self.sim_thread.start()
        
    def stop_simulation(self):
        self.running = False
        if hasattr(self, 'sim_thread'):
            self.sim_thread.join(1.0)


class ColonyVisualizer:
    def __init__(self, simulation: ColonySimulation):
        # ...existing code for initialization...
        self.simulation = simulation
        self.fig, self.axs = plt.subplots(2, 2, figsize=(15, 10))
        self.fig.tight_layout(pad=3.0)
        
        # Configure subplots
        self.o2_ax = self.axs[0, 0]
        self.co2_ax = self.axs[0, 1]
        self.health_ax = self.axs[1, 0]
        self.status_ax = self.axs[1, 1]
        
        # Set titles
        self.o2_ax.set_title('Oxygen Levels (%)')
        self.co2_ax.set_title('CO2 Levels (ppm)')
        self.health_ax.set_title('Health Effects')
        self.status_ax.set_title('Colony Status')
        
        # Initialize plots
        self._init_plots()
        
        # Connect event handlers
        self.fig.canvas.mpl_connect('button_press_event', self._on_click)
        
        # UI setup
        plt.subplots_adjust(bottom=0.2)
        self.breach_button_ax = plt.axes([0.10, 0.05, 0.12, 0.05])
        self.breach_button = plt.Button(self.breach_button_ax, 'Add Breach')
        self.breach_button.on_clicked(self._add_breach_callback)
        
        self.add_person_ax = plt.axes([0.25, 0.05, 0.12, 0.05])
        self.add_person_button = plt.Button(self.add_person_ax, 'Add Person')
        self.add_person_button.on_clicked(self._add_person_callback)
        
        self.remove_person_ax = plt.axes([0.40, 0.05, 0.12, 0.05])
        self.remove_person_button = plt.Button(self.remove_person_ax, 'Remove Person')
        self.remove_person_button.on_clicked(self._remove_person_callback)
        
        self.add_sensor_ax = plt.axes([0.55, 0.05, 0.12, 0.05])
        self.add_sensor_button = plt.Button(self.add_sensor_ax, 'Add Sensor')
        self.add_sensor_button.on_clicked(self._add_sensor_callback)
        
        self.toggle_door_ax = plt.axes([0.70, 0.05, 0.12, 0.05])
        self.toggle_door_button = plt.Button(self.toggle_door_ax, 'Toggle Door')
        self.toggle_door_button.on_clicked(self._toggle_door_callback)

        # Initialize animation
        self.anim = FuncAnimation(self.fig, self._update_plots, interval=500, blit=False)
        
        # Current UI mode
        self.ui_mode = None
        
    def _init_plots(self):
        # Clear axes
        for ax in self.axs.flat:
            ax.clear()
        
        # Draw Mars backdrop
        self._draw_mars_backdrop(self.o2_ax)
        self._draw_mars_backdrop(self.co2_ax)
        
        # Set up heatmap limits
        self.o2_ax.set_xlim(0, self.simulation.grid_width)
        self.o2_ax.set_ylim(0, self.simulation.grid_height)
        self.co2_ax.set_xlim(0, self.simulation.grid_width)
        self.co2_ax.set_ylim(0, self.simulation.grid_height)
        
        # Health effects plot initialization
        self.health_ax.set_xlim(0, 100)
        self.health_ax.set_ylim(0, 100)
        self.health_bars = self.health_ax.bar(
            ['Headache', 'Dizziness', 'Productivity', 'Morale'],
            [0, 0, 100, 100],
            color=['red', 'orange', 'green', 'blue']
        )
        
        # Room status initialization
        self.status_ax.axis('off')
    
    def _draw_mars_backdrop(self, ax):
        """Draw a Mars-like backdrop for the colony"""
        # Red-orange Mars surface
        mars_rect = patches.Rectangle((0, 0), self.simulation.grid_width, 
                                    self.simulation.grid_height,
                                    facecolor='#E27B58', alpha=0.3)
        ax.add_patch(mars_rect)
        
        # Add some random crater patterns
        for _ in range(20):
            x = random.uniform(5, self.simulation.grid_width-5)
            y = random.uniform(5, self.simulation.grid_height-5)
            size = random.uniform(0.5, 3)
            circle = plt.Circle((x, y), size, facecolor='#C26545', alpha=0.3)
            ax.add_patch(circle)
        
    def _update_plots(self, frame):
        # Update O2 heatmap
        self.o2_ax.clear()
        self.o2_ax.set_title('Oxygen Levels (%)')
        self.o2_ax.set_xlim(0, self.simulation.grid_width)
        self.o2_ax.set_ylim(0, self.simulation.grid_height)
        
        # Draw Mars backdrop
        self._draw_mars_backdrop(self.o2_ax)
        
        # Draw rooms with O2 levels as colors
        for room in self.simulation.rooms:
            # Color mapping: 0% O2 = red, 21% O2 = green
            o2_normalized = room.o2_level / NORMAL_O2_PERCENTAGE
            o2_color = (1.0 - min(1.0, o2_normalized), min(1.0, o2_normalized), 0)
            base_color = room.base_color
            
            # Blend base color with O2 indicator color
            blend_color = (
                base_color[0] * 0.5 + o2_color[0] * 0.5,
                base_color[1] * 0.5 + o2_color[1] * 0.5,
                base_color[2] * 0.5
            )
            
            rect = room.get_patch(color_override=blend_color)
            self.o2_ax.add_patch(rect)
            
            # Add text for room info
            self.o2_ax.text(room.center_x, room.center_y - 2, 
                          f"{room.label}", 
                          ha='center', va='center', fontsize=7)
            self.o2_ax.text(room.center_x, room.center_y, 
                          f"O₂: {room.o2_level:.1f}%", 
                          ha='center', va='center', fontweight='bold')
            self.o2_ax.text(room.center_x, room.center_y + 2, 
                          f"People: {room.population}", 
                          ha='center', va='center', fontsize=8)
            
            # Show breaches
            for breach in room.breaches:
                circle = plt.Circle((breach.x, breach.y), breach.radius, 
                                   color='red', alpha=0.7)
                self.o2_ax.add_patch(circle)
                
            # Show sensors
            for sensor in room.sensors:
                self.o2_ax.plot(sensor.x, sensor.y, 'bo', markersize=5)
                self.o2_ax.text(sensor.x, sensor.y + 1, f"{sensor.id}: {sensor.last_o2_reading:.1f}%", 
                              ha='center', va='center', fontsize=8)
        
        # Draw doors 
        for door in self.simulation.doors:
            door_color = 'green' if door.is_open else 'red'
            door_circ = plt.Circle(door.position, door.width/2, color=door_color, alpha=0.8)
            self.o2_ax.add_patch(door_circ)
        
        # Update CO2 heatmap
        self.co2_ax.clear()
        self.co2_ax.set_title('CO2 Levels (ppm)')
        self.co2_ax.set_xlim(0, self.simulation.grid_width)
        self.co2_ax.set_ylim(0, self.simulation.grid_height)
        
        # Draw Mars backdrop
        self._draw_mars_backdrop(self.co2_ax)
        
        # Draw rooms with CO2 levels as colors
        for room in self.simulation.rooms:
            # Color mapping: normal CO2 = green, high CO2 = red
            co2_normalized = min(1.0, (room.co2_level - NORMAL_CO2_PPM) / 5000)
            co2_color = (min(1.0, co2_normalized), 1.0 - min(1.0, co2_normalized), 0)
            base_color = room.base_color
            
            # Blend base color with CO2 indicator color
            blend_color = (
                base_color[0] * 0.5 + co2_color[0] * 0.5,
                base_color[1] * 0.5 + co2_color[1] * 0.5,
                base_color[2] * 0.5
            )
            
            rect = room.get_patch(color_override=blend_color)
            self.co2_ax.add_patch(rect)
            
            # Add text for CO2 ppm
            self.co2_ax.text(room.center_x, room.center_y - 2, 
                           f"{room.label}", 
                           ha='center', va='center', fontsize=7)
            self.co2_ax.text(room.center_x, room.center_y, 
                           f"CO₂: {room.co2_level:.0f} ppm", 
                           ha='center', va='center', fontweight='bold')
            self.co2_ax.text(room.center_x, room.center_y + 2, 
                           f"People: {room.population}", 
                           ha='center', va='center', fontsize=8)
            
            # Show sensors
            for sensor in room.sensors:
                self.co2_ax.plot(sensor.x, sensor.y, 'bo', markersize=5)
                self.co2_ax.text(sensor.x, sensor.y + 1, f"{sensor.id}: {sensor.last_co2_reading:.0f}", 
                               ha='center', va='center', fontsize=8)
        
        # Draw doors
        for door in self.simulation.doors:
            door_color = 'green' if door.is_open else 'red'
            door_circ = plt.Circle(door.position, door.width/2, color=door_color, alpha=0.8)
            self.co2_ax.add_patch(door_circ)
        
        # Update health effects
        self.health_ax.clear()
        self.health_ax.set_title('Health Effects')
        self.health_ax.set_ylim(0, 100)
        
        # Find average health effects across all inhabited rooms
        avg_effects = {"headache": 0.0, "dizziness": 0.0, "productivity": 100.0, "morale": 100.0}
        inhabited_rooms = [r for r in self.simulation.rooms if r.population > 0]
        
        if inhabited_rooms:
            for effect in avg_effects:
                values = []
                for room in inhabited_rooms:
                    effects = HealthEffects.calculate_health_effects(room.o2_level, room.co2_level)
                    values.append(effects[effect])
                avg_effects[effect] = sum(values) / len(values)
        
        # Create bars for each effect
        bars = self.health_ax.bar(
            ['Headache', 'Dizziness', 'Productivity', 'Morale'],
            [avg_effects['headache'], avg_effects['dizziness'], 
             avg_effects['productivity'], avg_effects['morale']],
            color=['red', 'orange', 'green', 'blue']
        )
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            self.health_ax.text(bar.get_x() + bar.get_width()/2., height,
                             f'{height:.1f}',
                             ha='center', va='bottom')
        
        # Update status info
        self.status_ax.clear()
        self.status_ax.axis('off')
        self.status_ax.set_title('Colony Status')
        
        status_text = f"Simulation Time: {self.simulation.time_step:.2f} hours\n\n"
        status_text += "Room Status:\n"
        
        for room in self.simulation.rooms:
            status_text += f"{room.label} (Room {room.id}): {room.population} people, "
            status_text += f"{len(room.breaches)} breaches\n"
            
            # Add Bayesian fusion results if multiple sensors
            if len(room.sensors) > 1:
                fused_o2, variance_o2 = BayesianFusion.fuse_sensor_readings(room.sensors, "o2")
                fused_co2, variance_co2 = BayesianFusion.fuse_sensor_readings(room.sensors, "co2")
                
                if fused_o2 is not None:
                    status_text += f"  Fused O2: {fused_o2:.2f}% (±{np.sqrt(variance_o2):.2f})\n"
                if fused_co2 is not None:
                    status_text += f"  Fused CO2: {fused_co2:.0f} ppm (±{np.sqrt(variance_co2):.0f})\n"
        
        status_text += "\nDoor Status:\n"
        for i, door in enumerate(self.simulation.doors):
            status_text += f"Door {i+1}: {'OPEN' if door.is_open else 'CLOSED'} "
            status_text += f"(Rooms {door.room1_id}-{door.room2_id})\n"
        
        self.status_ax.text(0.05, 0.95, status_text, transform=self.status_ax.transAxes,
                          verticalalignment='top', fontsize=9)
                          
        return []
        
    def _on_click(self, event):
        if not event.inaxes:
            return
            
        x, y = event.xdata, event.ydata
        
        # Handle clicks based on current UI mode
        if self.ui_mode == 'add_breach' and (event.inaxes == self.o2_ax or event.inaxes == self.co2_ax):
            room = self.simulation.find_room_at_point(x, y)
            if room:
                breach_radius = 1.0
                flow_rate = 0.5
                self.simulation.add_breach(x, y, breach_radius, flow_rate)
                print(f"Added breach at ({x:.1f}, {y:.1f}) in room {room.id}")
            self.ui_mode = None
        
        elif self.ui_mode == 'add_sensor' and (event.inaxes == self.o2_ax or event.inaxes == self.co2_ax):
            sensor = self.simulation.add_sensor(int(x), int(y))
            if sensor:
                print(f"Added sensor {sensor.id} at ({x:.1f}, {y:.1f})")
            self.ui_mode = None
            
        elif self.ui_mode == 'add_person' and (event.inaxes == self.o2_ax or event.inaxes == self.co2_ax):
            room = self.simulation.find_room_at_point(x, y)
            if room:
                room.population += 1
                print(f"Added person to {room.label} (Room {room.id}). New population: {room.population}")
            self.ui_mode = None
            
        elif self.ui_mode == 'remove_person' and (event.inaxes == self.o2_ax or event.inaxes == self.co2_ax):
            room = self.simulation.find_room_at_point(x, y)
            if room and room.population > 0:
                room.population -= 1
                print(f"Removed person from {room.label} (Room {room.id}). New population: {room.population}")
            self.ui_mode = None
            
        elif self.ui_mode == 'toggle_door' and (event.inaxes == self.o2_ax or event.inaxes == self.co2_ax):
            if self.simulation.toggle_door(x, y):
                print(f"Toggled door at ({x:.1f}, {y:.1f})")
            self.ui_mode = None
            
    def _add_breach_callback(self, event):
        print("Click on a room to add a breach")
        self.ui_mode = 'add_breach'
        
    def _add_person_callback(self, event):
        print("Click on a room to add a person")
        self.ui_mode = 'add_person'
        
    def _remove_person_callback(self, event):
        print("Click on a room to remove a person")
        self.ui_mode = 'remove_person'
        
    def _add_sensor_callback(self, event):
        print("Click anywhere to add a sensor")
        self.ui_mode = 'add_sensor'
        
    def _toggle_door_callback(self, event):
        print("Click on a door to toggle its open/closed state")
        self.ui_mode = 'toggle_door'
        
    def show(self):
        plt.show()


def create_sample_colony():
    sim = ColonySimulation(grid_width=100, grid_height=80)
    
    # Create complex room layout with different room types
    # Command Center (Hexagon)
    command_vertices = [
        (50, 20), (60, 20), (65, 30), 
        (60, 40), (50, 40), (45, 30)
    ]
    command = sim.add_room(command_vertices, RoomType.COMMAND_CENTER)
    
    # Living Quarters (Rectangle)
    living1 = sim.add_room([(10, 10), (30, 10), (30, 25), (10, 25)], RoomType.LIVING_QUARTERS)
    living2 = sim.add_room([(70, 10), (90, 10), (90, 25), (70, 25)], RoomType.LIVING_QUARTERS)
    
    # Laboratory (L-shaped)
    lab_vertices = [
        (10, 35), (30, 35), (30, 45), (20, 45),
        (20, 55), (10, 55)
    ]
    lab = sim.add_room(lab_vertices, RoomType.LABORATORY)
    
    # Medical Bay (Rectangle)
    medical = sim.add_room([(70, 35), (90, 35), (90, 55), (70, 55)], RoomType.MEDICAL_BAY)
    
    # Greenhouse (Trapezoid)
    greenhouse_vertices = [
        (35, 50), (65, 50), (60, 70), (40, 70)
    ]
    greenhouse = sim.add_room(greenhouse_vertices, RoomType.GREENHOUSE)
    
    # Storage room (Rectangle)
    storage = sim.add_room([(35, 30), (45, 30), (45, 45), (35, 45)], RoomType.STORAGE)
    
    # Airlock (Small Square)
    airlock = sim.add_room([(47, 50), (53, 50), (53, 55), (47, 55)], RoomType.AIRLOCK)
    
    # Corridors (connecting rooms)
    # Horizontal corridor connecting living quarters to command center
    corridor1 = sim.add_room([(30, 15), (45, 15), (45, 20), (30, 20)], RoomType.CORRIDOR)
    corridor2 = sim.add_room([(65, 15), (70, 15), (70, 20), (65, 20)], RoomType.CORRIDOR)
    
    # Vertical corridor connecting command to greenhouse
    corridor3 = sim.add_room([(52, 40), (57, 40), (57, 50), (52, 50)], RoomType.CORRIDOR)
    
    # Corridors connecting lab and medical bay to other rooms
    corridor4 = sim.add_room([(30, 40), (35, 40), (35, 35), (30, 35)], RoomType.CORRIDOR)
    corridor5 = sim.add_room([(65, 40), (70, 40), (70, 35), (65, 35)], RoomType.CORRIDOR)
    
    # Add doors between rooms
    sim.add_door(command.id, corridor1.id, (45, 17.5))
    sim.add_door(command.id, corridor2.id, (65, 17.5))
    sim.add_door(command.id, corridor3.id, (55, 40))
    sim.add_door(command.id, corridor4.id, (45, 35))
    sim.add_door(command.id, corridor5.id, (65, 35))
    
    sim.add_door(living1.id, corridor1.id, (30, 17.5))
    sim.add_door(living2.id, corridor2.id, (70, 17.5))
    
    sim.add_door(corridor3.id, airlock.id, (55, 50))
    sim.add_door(airlock.id, greenhouse.id, (50, 55))
    
    sim.add_door(lab.id, corridor4.id, (30, 35))
    sim.add_door(medical.id, corridor5.id, (70, 35))
    
    sim.add_door(corridor4.id, storage.id, (35, 40))
    sim.add_door(corridor5.id, storage.id, (45, 40))
    
    # Add airlock door to outside (closed by default)
    sim.add_door(airlock.id, 0, (50, 50), is_open=False)  # 0 indicates "outside"
    
    # Add sensors
    sim.add_sensor(55, 30)  # Command center
    sim.add_sensor(15, 15)  # Living quarters 1
    sim.add_sensor(85, 15)  # Living quarters 2
    sim.add_sensor(15, 45)  # Laboratory
    sim.add_sensor(80, 45)  # Medical bay
    sim.add_sensor(50, 60)  # Greenhouse
    sim.add_sensor(40, 38)  # Storage
    sim.add_sensor(50, 53)  # Airlock
    sim.add_sensor(5, 5)    # Outside
    
    # Set initial populations
    sim.set_population(command.id, 3)  # Command center
    sim.set_population(living1.id, 2)  # Living quarters 1
    sim.set_population(living2.id, 2)  # Living quarters 2
    sim.set_population(lab.id, 1)      # Laboratory
    sim.set_population(medical.id, 1)  # Medical bay
    sim.set_population(greenhouse.id, 2) # Greenhouse
    
    return sim


def main():
    parser = argparse.ArgumentParser(description="Mars Colony Life Support Simulation")
    parser.add_argument("--auto-populate", action="store_true", help="Add initial population to rooms")
    args = parser.parse_args()
    
    # Create and configure the simulation
    simulation = create_sample_colony()
    
    # Start simulation in background thread
    simulation.start_simulation()
    
    # Create and show the visualizer
    visualizer = ColonyVisualizer(simulation)
    
    print("Mars Colony Life Support Simulation")
    print("-----------------------------------")
    print("UI Controls:")
    print("- Click 'Add Breach' button then click a room to create a breach")
    print("- Click 'Add Person'/'Remove Person' to modify room populations")
    print("- Click 'Add Sensor' to place additional sensors")
    print("- Click 'Toggle Door' to open/close doors between rooms")
    
    try:
        visualizer.show()
    finally:
        simulation.stop_simulation()


if __name__ == "__main__":
    main()
