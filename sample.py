import tkinter as tk
from tkinter import ttk
import numpy as np
import threading
import time
from shapely.geometry import Polygon, Point
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel

# ------ Simulation Core (from Program 1) ------
NORMAL_O2_PERCENTAGE = 21.0
NORMAL_CO2_PPM = 400.0
MARS_O2_PERCENTAGE = 0.13
MARS_CO2_PERCENTAGE = 95.0
HUMAN_O2_CONSUMPTION_PER_HOUR = 0.02
HUMAN_CO2_PRODUCTION_PER_HOUR = 35.0

class Room:
    def __init__(self, room_id, vertices, label="Room"):
        self.id = room_id
        self.polygon = Polygon(vertices)
        self.vertices = vertices
        self.center = self.polygon.centroid.coords[0]
        self.area = self.polygon.area
        self.o2 = NORMAL_O2_PERCENTAGE
        self.co2 = NORMAL_CO2_PPM
        self.population = 0
        self.sensors = []
        self.breaches = []
    def contains(self, x,y): return self.polygon.contains(Point(x,y))

class Door:
    def __init__(self, r1, r2):
        self.a, self.b = r1, r2
        self.open = True
        self.flow = 0.2

class SensorModel:
    def __init__(self, x,y):
        self.x,self.y = x,y
        self.var_o2=0.5; self.var_co2=20.0
        self.last_o2=None; self.last_co2=None
    def read(self, room):
        self.last_o2 = max(0, np.random.normal(room.o2, self.var_o2))
        self.last_co2 = max(0, np.random.normal(room.co2, self.var_co2))

class ColonySimulation:
    def __init__(self):
        self.rooms=[]; self.doors=[]; self.time=0
        self.running=False
    def add_room(self, verts):
        r=Room(len(self.rooms)+1, verts)
        self.rooms.append(r)
        return r
    def add_door(self, r1,r2):
        self.doors.append(Door(r1,r2))
    def update(self, dt):
        # population effects
        for room in self.rooms:
            if room.population>0:
                sz=100/max(room.area,10)
                room.o2 = max(0, room.o2 - HUMAN_O2_CONSUMPTION_PER_HOUR*room.population*dt*sz)
                room.co2 += HUMAN_CO2_PRODUCTION_PER_HOUR*room.population*dt*sz
        # breaches & door exchange omitted for brevity
        # sensor reads
        for room in self.rooms:
            for s in room.sensors: s.read(room)
        self.time += dt
    def start(self): self.running=True; threading.Thread(target=self._run).start()
    def stop(self): self.running=False
    def _run(self):
        last=time.time()
        while self.running:
            now=time.time(); dt=(now-last);
            self.update(dt); last=now; time.sleep(0.1)

# ------ Drawing UI & GP Integration (from Program 2) ------
CELL=10; MARGIN=30
class ShapeBase:
    def contains(self, x,y): pass
    def coords(self): pass

class RectangleShape(ShapeBase):
    def __init__(self,x,y,w,h): self.x,self.y,self.w,self.h=x,y,w,h
    def contains(self,x,y): return self.x<=x<=self.x+self.w and self.y<=y<=self.y+self.h
    def coords(self): return [(self.x,self.y),(self.x+self.w,self.y),(self.x+self.w,self.y+self.h),(self.x,self.y+self.h)]

class CircleShape(ShapeBase):
    def __init__(self,x,y,r): self.x,self.y,self.r=x,y,r
    def contains(self,x,y): return (x-self.x)**2+(y-self.y)**2<=self.r**2
    def coords(self):
        # approximate as polygon
        pts=[]
        for a in np.linspace(0,2*np.pi,16): pts.append((self.x+np.cos(a)*self.r, self.y+np.sin(a)*self.r))
        return pts

class IntegratedApp(tk.Tk):
    def __init__(self):
        super().__init__(); self.title("Mars Colony Life Support & GP Simulator")
        # Simulation core
        self.sim = ColonySimulation()
        # UI spaces
        self.canvas = tk.Canvas(self, width=600, height=400, bg="white")
        self.canvas.grid(row=0,column=0,rowspan=4)
        self.btn_frame = ttk.Frame(self); self.btn_frame.grid(row=0,column=1)
        ttk.Button(self.btn_frame, text="Draw Rectangle", command=self._set_rect).grid()
        ttk.Button(self.btn_frame, text="Draw Circle", command=self._set_circ).grid()
        ttk.Button(self.btn_frame, text="Add Sensor", command=self._set_sensor).grid()
        ttk.Button(self.btn_frame, text="Start Simulation", command=self.sim.start).grid()
        ttk.Button(self.btn_frame, text="Stop Simulation",  command=self.sim.stop).grid()

        self.mode="select"; self.shapes=[]; self.sensors=[]; self.selected=None
        self.canvas.bind("<Button-1>", self._on_click)
        self._setup_gp()
        self.after(100, self._update_canvas)
    def _setup_gp(self):
        kernel = ConstantKernel(1.0)*(RBF(20)) + WhiteKernel(1.0)
        self.gp = GaussianProcessRegressor(kernel=kernel, normalize_y=True)
    def _set_rect(self): self.mode="rect"
    def _set_circ(self): self.mode="circ"
    def _set_sensor(self): self.mode="sensor"
    def _on_click(self,e): x,y=e.x,e.y
        if self.mode=="rect":
            r=RectangleShape(x,y,80,50); self.shapes.append(r)
            verts=r.coords(); self.sim.add_room(verts)
            self.canvas.create_rectangle(*self.canvas.coords(self.canvas.create_rectangle(x,y,x+80,y+50)), outline="black")
        elif self.mode=="circ":
            c=CircleShape(x,y,30); self.shapes.append(c)
            verts=c.coords(); self.sim.add_room(verts)
            self.canvas.create_oval(x-30,y-30,x+30,y+30, outline="black")
        elif self.mode=="sensor":
            s=SensorModel(x,y); self.sensors.append(s)
            # find room
            for room in self.sim.rooms:
                if room.contains(x,y): room.sensors.append(s)
            self.canvas.create_oval(x-5,y-5,x+5,y+5, fill="blue")
        self.mode="select"
    def _update_canvas(self):
        # redraw heatmap of O2 inside rooms using GP
        if self.sensors and self.sim.rooms:
            X=[]; y=[]
            for s in self.sensors:
                X.append([s.x,s.y]); y.append(s.last_o2 or NORMAL_O2_PERCENTAGE)
            X,y=np.array(X),np.array(y)
            self.gp.fit(X,y)
            # sample grid
            for room in self.sim.rooms:
                cx,cy=room.center
                val,_ = self.gp.predict(np.array([[cx,cy]]), return_std=True)
                color = "#{:02x}{:02x}00".format(int(255*(1-val/NORMAL_O2_PERCENTAGE)), int(255*(val/NORMAL_O2_PERCENTAGE)))
                # draw a small circle at center
                self.canvas.create_oval(cx-10,cy-10,cx+10,cy+10, fill=color, outline="")
        self.after(500, self._update_canvas)

if __name__ == "__main__":
    IntegratedApp().mainloop()
