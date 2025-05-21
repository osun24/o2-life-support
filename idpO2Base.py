# oxygen_field_sim.py
# --------------------------------------------------------------
# Interactive field‑based oxygen simulation with Bayesian reconstruction.
# Users change parameters via text boxes and click **Start**. The
# colorbar adapts every GP refresh to span the current min–max inferred
# concentration.
# --------------------------------------------------------------

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import TextBox, Button
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel
from scipy.spatial.distance import cdist


# --------------------------------------------------------------
# Helper functions
# --------------------------------------------------------------

def initialize_field(L, grid_res, alpha=1.0):
    """Initialize a 2D Dirichlet-distributed field."""
    size = grid_res * grid_res
    # initiate a Dirichlet distribution (2D PDF) --> instead of particles bc particles are SLOW
    field = np.random.dirichlet([alpha] * size).reshape((grid_res, grid_res))
    field *= L * L  # scale to total O₂ amount if needed
    return field


def sensor_concentrations(field, sensors, L, grid_res, noise_std=0.01):
    """Sample the field at sensor locations, with noise."""
    x_lin = np.linspace(0, L, grid_res)
    y_lin = np.linspace(0, L, grid_res)
    X, Y = np.meshgrid(x_lin, y_lin)
    concentrations = []
    for x, y, r in sensors:
        mask = (X - x)**2 + (Y - y)**2 <= r**2
        val = field[mask].mean() + np.random.normal(0, noise_std)
        concentrations.append(val)
    return np.array(concentrations)


def update_field(field, leak_pos=None, leak_strength=0.01):
    """Optionally bias the field toward a leak location."""
    if leak_pos is not None:
        grid_res = field.shape[0]
        x_lin = np.linspace(0, 1, grid_res)
        y_lin = np.linspace(0, 1, grid_res)
        X, Y = np.meshgrid(x_lin, y_lin)
        leak = np.exp(-((X-leak_pos[0])**2 + (Y-leak_pos[1])**2) / 0.01)
        field += leak_strength * leak
        field /= field.sum()  # Renormalize
    return field


# --------------------------------------------------------------
# Main simulation routine
# --------------------------------------------------------------

def run_sim(fig, ax, L=10.0, n_particles=500, grid_res=50, n_steps=200,
            diff_coeff=0.1, dt=0.05, leak_pos=None, leak_strength=0.01):
    """Set up and launch the field-based GP animation."""

    # Simulation / GP constants
    sensor_radius = 0.1 * L
    sensors = np.array([
        [0.3 * L, 0.3 * L, sensor_radius],
        [0.7 * L, 0.3 * L, sensor_radius],
        [0.5 * L, 0.7 * L, sensor_radius],
    ])
    kernel = RBF(length_scale=0.2 * L) + WhiteKernel(noise_level=1e-4)
    gp = GaussianProcessRegressor(kernel=kernel, normalize_y=True)
    GP_UPDATE_EVERY = 5

    # Initial O2 field
    np.random.seed(42)
    field = initialize_field(L, grid_res, alpha=1.0)

    # Grid of prediction points
    x_lin = np.linspace(0, L, grid_res)
    y_lin = np.linspace(0, L, grid_res)
    X_grid, Y_grid = np.meshgrid(x_lin, y_lin)
    XY_grid = np.column_stack([X_grid.ravel(), Y_grid.ravel()])

    # ---------------- Visual elements -------------------------
    ax.cla()
    ax.set_xlim(0, L)
    ax.set_ylim(0, L)
    ax.set_aspect('equal')
    # No scatter for particles
    heat_img = ax.imshow(np.zeros((grid_res, grid_res)), origin='lower',
                         extent=(0, L, 0, L), cmap='viridis', alpha=0.7)

    # Dynamic colorbar
    if hasattr(run_sim, 'cbar') and run_sim.cbar:
        run_sim.cbar.remove()
    run_sim.cbar = fig.colorbar(heat_img, ax=ax, fraction=0.046, pad=0.04,
                                label='O₂ molecules per m² (dynamic)')

    for x, y, r in sensors:
        ax.add_patch(plt.Circle((x, y), r, color='red', fill=False, lw=1.5))
    ax.set_title('Oxygen field & inferred concentration')

    # ---------------- Animation update ------------------------
    def update(frame):
        nonlocal field
        # Update field (simulate leak if present)
        field = update_field(field, leak_pos=leak_pos, leak_strength=leak_strength)

        # Sensor readings
        conc = sensor_concentrations(field, sensors, L, grid_res)

        if frame % GP_UPDATE_EVERY == 0:
            gp.fit(sensors[:, :2], conc)
            mean_field = gp.predict(XY_grid).reshape(grid_res, grid_res)
            heat_img.set_data(mean_field)
            heat_img.set_clim(vmin=mean_field.min(), vmax=mean_field.max())
            run_sim.cbar.update_normal(heat_img)

        return (heat_img,)

    ani = animation.FuncAnimation(fig, update, frames=n_steps, interval=50,
                                  blit=True)
    run_sim.ani = ani  # prevent garbage collection
    fig.canvas.draw_idle()


# --------------------------------------------------------------
# UI wrapper
# --------------------------------------------------------------

def main():
    fig = plt.figure(figsize=(7, 8))
    ax_sim = fig.add_axes([0.05, 0.25, 0.9, 0.7])

    # Text boxes for user parameters
    tb_axes = [fig.add_axes([x, 0.15, 0.25, 0.05]) for x in (0.05, 0.37, 0.69)]
    tb_particles = TextBox(tb_axes[0], 'Particles', initial='500')
    tb_boxsize = TextBox(tb_axes[1], 'Box size', initial='10')
    tb_gridres = TextBox(tb_axes[2], 'Grid res', initial='50')

    # Start button
    btn_ax = fig.add_axes([0.42, 0.05, 0.16, 0.06])
    btn_start = Button(btn_ax, 'Start')

    def on_start(event):
        try:
            n_p = int(tb_particles.text)
            L_val = float(tb_boxsize.text)
            g_res = int(tb_gridres.text)
        except ValueError:
            print('Invalid input: please enter numeric values.')
            return
        run_sim(fig, ax_sim, L=L_val, n_particles=n_p, grid_res=g_res)

    btn_start.on_clicked(on_start)
    plt.show()


if __name__ == '__main__':
    main()
