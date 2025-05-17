import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Slider

# ─── PARAMETERS ─────────────────────────────────────────────────────────────
nx, ny = 50, 50             # grid size
dx = dy = 1.0               # cell dimensions
dt = 1.0                    # time step
D_o2 = 0.1                  # diffusion coefficient
cons_rate = 0.0001          # per person per dt per total‐grid cell
init_o2 = 0.21              # 21% O₂
sensor_error = 0.005        # σ of sensor
l_scale = 10.0              # spatial kernel length‐scale

# initial state
o2 = np.full((nx, ny), init_o2)
sensors = [(10,10), (40,10), (10,40), (40,40)]
population = 100
leak_rate = 0.01
leak_location = (nx//2, ny//2)

# precompute grid coords
x = np.arange(nx)
y = np.arange(ny)
X, Y = np.meshgrid(x, y, indexing='ij')

# ─── SIMULATION FUNCTIONS ───────────────────────────────────────────────────
def simulate_step(true_o2):
    # diffusion
    lap = (np.roll(true_o2,1,0) + np.roll(true_o2,-1,0)
         + np.roll(true_o2,1,1) + np.roll(true_o2,-1,1)
         - 4*true_o2)
    true_o2 = true_o2 + D_o2 * lap * dt/(dx*dy)
    # leak at single cell
    i,j = leak_location
    true_o2[i,j] = max(0, true_o2[i,j] - leak_rate * dt)
    # uniform human consumption
    true_o2 -= cons_rate * population * dt/(nx*ny)
    return np.clip(true_o2, 0, 1)

def sense(true_o2):
    return [true_o2[i,j] + np.random.normal(0, sensor_error)
            for i,j in sensors]

def bayesian_map(readings):
    wm = np.zeros_like(o2)
    wsum = np.zeros_like(o2)
    for r,(i,j) in zip(readings, sensors):
        dist2 = (X - i)**2 + (Y - j)**2
        K = np.exp(-dist2/(2*l_scale**2))
        w = K / sensor_error**2
        wm  += w * r
        wsum += w
    return wm / (wsum + 1e-12)

# ─── SET UP PLOT & INTERACTIVITY ────────────────────────────────────────────
fig, ax = plt.subplots()
cax = ax.imshow(o2, vmin=0, vmax=init_o2, origin='lower')
fig.colorbar(cax, ax=ax, label='O₂ fraction')

def update(frame):
    global o2
    o2 = simulate_step(o2)
    meas = sense(o2)
    heat = bayesian_map(meas)
    cax.set_data(heat)
    return [cax]

# sliders for leak rate & population
ax_leak = plt.axes([0.25, 0.02, 0.65, 0.02])
s_leak = Slider(ax_leak, 'Leak rate', 0, 0.1, valinit=leak_rate)
s_leak.on_changed(lambda v: globals().update(leak_rate=v))

ax_pop = plt.axes([0.25, 0.05, 0.65, 0.02])
s_pop = Slider(ax_pop, 'Population', 0, 500, valinit=population)
s_pop.on_changed(lambda v: globals().update(population=int(v)))

# click to reposition leak
def onclick(event):
    if event.inaxes == ax:
        x_, y_ = int(event.xdata+0.5), int(event.ydata+0.5)
        global leak_location
        leak_location = (np.clip(x_,0,nx-1), np.clip(y_,0,ny-1))
fig.canvas.mpl_connect('button_press_event', onclick)

ani = FuncAnimation(fig, update, interval=100, blit=True)
plt.show()