import random
from tkinter import *
import tkinter.ttk as ttk # For a more modern look if desired, though not strictly used here yet
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# --- Global variable for slider value ---
# Using a Tkinter DoubleVar to hold the slider's value
area_var = None

def plot():
    global area_var # Ensure we are using the global area_var
    ax.clear()
    try:
        # Get the user input (solar panel area) from the slider
        user_input_area = area_var.get()
    except Exception as e:
        if status_label: # Check if status_label exists
            status_label.config(text=f"Error getting area: {e}", fg="red")
        return

    # np.random.normal(loc: center, stdev, size)
    # Regenerate random efficiencies each time plot is called for variability
    dustEfficiencyVariance = np.random.normal(0.7, 0.2/3, size=668) # Mean 0.7, std dev implies range roughly 0.5-0.9
    panelEfficiency = np.random.normal(0.235, (0.27-0.20)/6, size=668) # Mean 0.235, std dev for range 0.20-0.27
    
    # Ensure efficiencies are within plausible physical bounds (e.g., 0 to 1)
    dustEfficiencyVariance = np.clip(dustEfficiencyVariance, 0.1, 0.9) # Clip to 10%-90%
    panelEfficiency = np.clip(panelEfficiency, 0.15, 0.27) # Clip to 15%-27%

    MARTIAN_IRR = 586  # W/m^2
    # SECONDS_PER_HALF_SOL = 88775 * 0.5 # Approx. seconds of sunlight if averaging 50% over a Sol
    # More direct: Average hours of full sun equivalent per Sol (e.g. 12 hours for simplicity, can be adjusted)
    # Or use total seconds in a sol if MARTIAN_IRR is average over the sol including night.
    # Let's assume MARTIAN_IRR is peak/daytime, and we are interested in daily energy.
    # A sol is ~24.65 hours. Assume panels collect for half that effectively, or adjust MARTIAN_IRR to be sol-averaged.
    # For consistency with prior context (from other files), let's use total seconds in a sol and assume
    # the efficiencies already account for day/night averaging if needed, or that IRR is an effective daily average.
    # However, the original 88775 * 0.5 (SECONDS) likely meant "effective seconds of generation per sol"
    EFFECTIVE_SECONDS_PER_SOL = 88775 * 0.5 # Or adjust this factor based on assumptions

    x_sols = np.arange(1, 669)  # 668 sols (1 to 668)
    
    # Energy (kJ) = Martian_Irradiance (W/m^2) * Panel_Area (m^2) * Panel_Efficiency * Dust_Efficiency * Time (s) * 0.001 (J to kJ)
    y_energy_kj = MARTIAN_IRR * user_input_area * panelEfficiency * dustEfficiencyVariance * EFFECTIVE_SECONDS_PER_SOL * 0.001
    
    # Scatter plot of daily energy production over the Martian year
    ax.scatter(x_sols, y_energy_kj, s=20, color="orange", alpha=0.7, label=f'Area: {user_input_area:.1f} m²')
    
    # Optional: Add a line for average energy
    avg_energy = np.mean(y_energy_kj)
    ax.axhline(avg_energy, color='red', linestyle='--', linewidth=1, label=f'Avg: {avg_energy:.0f} kJ')

    ax.set_title(f"Daily Solar Energy Production on Mars ({user_input_area:.1f} m² panels)")
    ax.set_xlabel("Sols (Martian Days)")
    ax.set_ylabel("Energy Output (kJ per Sol)") # Updated label
    ax.legend()
    ax.grid(True, alpha=0.4)
    canvas.draw()
    
    if status_label: # Check if status_label exists
        status_label.config(text=f"Plot updated for {user_input_area:.1f} m² solar panels.", fg="green")

def update_area_label(value):
    # This function is called by the slider's command to update the display label
    if current_area_label: # Check if current_area_label exists
        current_area_label.config(text=f"{float(value):.1f} m²")

# --- Create main window ---
window = Tk()
window.geometry("1000x850") # Adjusted height slightly
window.title("Mars Solar Energy Plotter with Slider")

# --- Matplotlib Figure and Canvas ---
fig, ax = plt.subplots(figsize=(10, 5.5)) # Adjusted figure size for better fit
canvas = FigureCanvasTkAgg(fig, master=window)
canvas_widget = canvas.get_tk_widget()
canvas_widget.pack(pady=10, padx=10, fill=BOTH, expand=True)

# --- Control Frame ---
control_frame = Frame(window)
control_frame.pack(pady=10, padx=10, fill=X)

# Title Label (moved to top for better flow)
app_title_label = Label(control_frame, text="Mars Solar Energy Simulation")
app_title_label.config(font=("Courier", 20, "bold"))
app_title_label.pack(pady=(0,15))

# --- Slider Input Section ---
slider_input_frame = Frame(control_frame)
slider_input_frame.pack(pady=5)

Label(slider_input_frame, text="Solar Panel Area (m²):", font=("Arial", 12)).pack(side=LEFT, padx=(0,5))

area_var = DoubleVar() # Define as Tkinter DoubleVar
area_var.set(10.0)  # Default value for the slider (e.g., 10 m^2)

# Label to display current slider value
current_area_label = Label(slider_input_frame, text=f"{area_var.get():.1f} m²", font=("Arial", 12), width=8)
current_area_label.pack(side=LEFT, padx=(0,10))

area_slider = Scale(
    slider_input_frame,
    from_=0.1,
    to=100.0,  # Max area on slider (e.g., 100 m^2)
    resolution=0.1,
    orient=HORIZONTAL,
    length=300, # Length of the slider
    variable=area_var,
    command=update_area_label # Update label dynamically as slider moves
)
area_slider.pack(side=LEFT, padx=5)

# --- Plot Button ---
plot_button = Button(slider_input_frame, text="Plot Graph", command=plot,
                    font=("Arial", 12, "bold"), bg="lightblue", relief=RAISED)
plot_button.pack(side=LEFT, padx=(15,0), ipady=2)


# --- Status and Info Labels ---
status_label_frame = Frame(control_frame)
status_label_frame.pack(pady=(10,0), fill=X)

status_label = Label(status_label_frame, text="Adjust slider for panel area and click 'Plot Graph'",
                    font=("Arial", 10), fg="blue")
status_label.pack()

info_label = Label(status_label_frame, text="Graph shows simulated daily energy over one Martian year (668 sols). Efficiency varies daily.",
                  font=("Arial", 9), fg="gray")
info_label.pack()


# --- Initial plot ---
# Call plot once at the beginning to show a graph with the default slider value
plot()

window.mainloop()
