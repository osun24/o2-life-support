#!/usr/bin/env python3
# filepath: /Users/owensun/Downloads/Tektite-R_EV_Template/o2-life-support/oxygen_vis.py

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from oxygen import Person, oxygen_production # Assuming Person is still needed from oxygen.py

# Time and colony settings
initial_days = 100
max_days = 365
initial_colony_size = 20

# --- MODIFIED/NEW PLANT/ALGAE/POTATO AREAS ---
initial_algae_area_m2 = 0
max_algae_area_m2 = 12000

initial_potato_area_m2 = 0
max_potato_area_m2 = 8000
# --- END MODIFIED/NEW ---

CO2_PER_O2_MASS_RATIO = 44.0095 / 31.9988

# --- NEW: Global store for the current colony and its size ---
current_colony_list = []
current_colony_actual_size = 0

def generate_new_colony(size):
    """Generates a new list of Person objects."""
    return [Person() for _ in range(size)]
# --- END NEW ---

# Create the figure and axis
fig, ax = plt.subplots(figsize=(12, 8))
plt.subplots_adjust(left=0.1, bottom=0.45, right=0.95)

# --- MODIFIED SIMULATE FUNCTION ---
# Now takes people_list instead of colony_size
def simulate_oxygen_over_time(people_list, days, total_algae_area_m2, total_potato_area_m2):
    # daily_consumption_o2 is now based on the passed people_list
    daily_consumption_o2 = sum(p.oxygen_consumption() for p in people_list)
    
    daily_production_o2 = oxygen_production(total_algae_area_m2, total_potato_area_m2)
    daily_consumption_co2 = daily_production_o2 * CO2_PER_O2_MASS_RATIO

    net_oxygen = daily_production_o2 - daily_consumption_o2
    # Ensure there's at least one person to base initial reserve on, or use a default
    initial_reserve_basis = daily_consumption_o2 if daily_consumption_o2 > 0 else 0.8 * len(people_list) # Fallback if consumption is zero
    initial_oxygen_reserve = initial_reserve_basis * 15
    
    oxygen_levels = [initial_oxygen_reserve]

    for day in range(1, days + 1):
        daily_variation = np.random.normal(1.0, 0.02) # This randomness still applies to daily net change
        day_change = net_oxygen * daily_variation
        next_level = max(0, oxygen_levels[-1] + day_change)
        oxygen_levels.append(next_level)

    return np.array(oxygen_levels[:days+1]), daily_consumption_o2, daily_production_o2, daily_consumption_co2
# --- END MODIFIED ---

# --- Initialize the colony at the start ---
current_colony_list = generate_new_colony(initial_colony_size)
current_colony_actual_size = initial_colony_size
# --- END NEW ---

time_points = np.linspace(0, initial_days, initial_days + 1)

# Initial plot using the globally stored colony
oxygen_levels, consumption_o2, production_o2, consumption_co2 = simulate_oxygen_over_time(
    current_colony_list, initial_days, initial_algae_area_m2, initial_potato_area_m2
)

# Create plots (lines and text initial setup - no change here needed for this modification)
line, = ax.plot(time_points, oxygen_levels, lw=2, label='Oxygen Level (Reserve)')
consumption_line = ax.axhline(y=consumption_o2 * 30, color='r', linestyle='--', label=f'O₂ Consumption Buffer (30d): {consumption_o2:.2f} kg/day')
production_line = ax.axhline(y=production_o2 * 30, color='g', linestyle='--', label=f'O₂ Production Buffer (30d): {production_o2:.2f} kg/day')
co2_consumption_line = ax.axhline(y=consumption_co2 * 30, color='c', linestyle=':', label=f'CO₂ Consumption Buffer (30d): {consumption_co2:.2f} kg/day')
balance_line = ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)

net_change_o2 = production_o2 - consumption_o2
y_pos_net_text_initial = oxygen_levels[-1] * 0.9 if len(oxygen_levels) > 0 and oxygen_levels[-1] > 0 else 10
net_text = ax.text(initial_days * 0.7, y_pos_net_text_initial,
                   f'Net O₂ change: {net_change_o2:.2f} kg/day',
                   bbox=dict(facecolor='white', alpha=0.7))

sustainability_threshold = 1.1
if consumption_o2 > 0 and net_change_o2 > 0 and production_o2 / consumption_o2 >= sustainability_threshold:
    status = "SUSTAINABLE (O₂)"
    color = "darkgreen"
elif net_change_o2 > 0:
    status = "MARGINALLY SUSTAINABLE (O₂)"
    color = "darkorange"
else:
    status = "UNSUSTAINABLE (O₂)"
    color = "darkred"

y_pos_status_text_initial = oxygen_levels[-1] * 1.1 if len(oxygen_levels) > 0 and oxygen_levels[-1] > 0 else 15
status_text = ax.text(initial_days * 0.8, y_pos_status_text_initial,
                      status, fontsize=14, fontweight='bold', color=color,
                      bbox=dict(facecolor='white', alpha=0.7))

ax.set_xlabel('Days')
ax.set_ylabel('Gas Level / Buffer (kg)')
ax.set_title(f'Oxygen & CO₂ Dynamics (Colony: {current_colony_actual_size}, Days: {initial_days}, Algae: {initial_algae_area_m2:.0f}m², Potatoes: {initial_potato_area_m2:.0f}m²)')
ax.legend(loc='upper left')
ax.grid(True)

slider_color = 'lightgoldenrodyellow'
colony_slider_ax = plt.axes([0.2, 0.30, 0.65, 0.03], facecolor=slider_color)
colony_slider = Slider(
    ax=colony_slider_ax, label='Colony Size', valmin=10, valmax=50,
    valinit=initial_colony_size, valstep=1
)
days_slider_ax = plt.axes([0.2, 0.25, 0.65, 0.03], facecolor=slider_color)
days_slider = Slider(
    ax=days_slider_ax, label='Simulation Days', valmin=30, valmax=max_days,
    valinit=initial_days, valstep=1
)
algae_area_slider_ax = plt.axes([0.2, 0.20, 0.65, 0.03], facecolor=slider_color)
algae_area_slider = Slider(
    ax=algae_area_slider_ax, label='Algae Area (m²)', valmin=0,
    valmax=max_algae_area_m2, valinit=initial_algae_area_m2, valstep=1
)
potato_area_slider_ax = plt.axes([0.2, 0.15, 0.65, 0.03], facecolor=slider_color)
potato_area_slider = Slider(
    ax=potato_area_slider_ax, label='Potato Area (m²)', valmin=0,
    valmax=max_potato_area_m2, valinit=initial_potato_area_m2, valstep=1
)
reset_ax = plt.axes([0.8, 0.08, 0.1, 0.04], facecolor=slider_color)
reset_button = Button(reset_ax, 'Reset', color=slider_color, hovercolor='0.975')


# Update function for the sliders
def update(val=None):
    # --- MODIFIED: Manage global colony list ---
    global current_colony_list, current_colony_actual_size
    # --- END MODIFIED ---

    new_colony_slider_val = int(colony_slider.val) # Value from slider
    days = int(days_slider.val)
    algae_area_m2 = float(algae_area_slider.val)
    potato_area_m2 = float(potato_area_slider.val)

    # --- MODIFIED: Regenerate colony only if size slider changed ---
    if new_colony_slider_val != current_colony_actual_size:
        current_colony_list = generate_new_colony(new_colony_slider_val)
        current_colony_actual_size = new_colony_slider_val
    # --- END MODIFIED ---

    current_time_points = np.linspace(0, days, days + 1 if days > 0 else 1)

    # MODIFIED: Pass the (potentially updated) current_colony_list
    oxygen_levels, consumption_o2, production_o2, consumption_co2 = simulate_oxygen_over_time(
        current_colony_list, days, algae_area_m2, potato_area_m2
    )

    line.set_xdata(current_time_points)
    line.set_ydata(oxygen_levels)

    consumption_line.set_ydata([consumption_o2 * 30, consumption_o2 * 30])
    production_line.set_ydata([production_o2 * 30, production_o2 * 30])
    co2_consumption_line.set_ydata([consumption_co2 * 30, consumption_co2 * 30])

    net_change_o2 = production_o2 - consumption_o2
    consumption_line.set_label(f'O₂ Consumption Buffer (30d): {consumption_o2:.2f} kg/day')
    production_line.set_label(f'O₂ Production Buffer (30d): {production_o2:.2f} kg/day')
    co2_consumption_line.set_label(f'CO₂ Consumption Buffer (30d): {consumption_co2:.2f} kg/day')
    
    current_y_max = ax.get_ylim()[1]
    if days > 0 and len(oxygen_levels) > 0:
        y_pos_net_text = oxygen_levels[-1] * 0.9
        x_pos_net_text = days * 0.7
        y_pos_status_text = oxygen_levels[-1] * 1.1
        x_pos_status_text = days * 0.9
    else:
        y_pos_net_text = current_y_max * 0.1 if current_y_max > 0 else 10
        x_pos_net_text = initial_days * 0.7
        y_pos_status_text = current_y_max * 0.15 if current_y_max > 0 else 15
        x_pos_status_text = initial_days * 0.8

    net_text.set_text(f'Net O₂ change: {net_change_o2:.2f} kg/day')
    net_text.set_position((x_pos_net_text, y_pos_net_text))

    sustainability_threshold = 1.1
    # Ensure consumption_o2 > 0 to avoid division by zero if colony size is 0 (though slider min is 10)
    if consumption_o2 > 0 and net_change_o2 > 0 and production_o2 / consumption_o2 >= sustainability_threshold:
        status = "SUSTAINABLE (O₂)"
        color = "darkgreen"
    elif net_change_o2 > 0:
        status = "MARGINALLY SUSTAINABLE (O₂)"
        color = "darkorange"
    else:
        status = "UNSUSTAINABLE (O₂)"
        color = "darkred"

    status_text.set_text(status)
    status_text.set_color(color)
    status_text.set_bbox(dict(facecolor='white', alpha=0.7))
    status_text.set_position((x_pos_status_text, y_pos_status_text))

    if net_change_o2 >= 0:
        net_text.set_bbox(dict(facecolor='lightgreen', alpha=0.7))
    else:
        net_text.set_bbox(dict(facecolor='lightcoral', alpha=0.7))

    # Use current_colony_actual_size for the title
    ax.set_title(f'Oxygen & CO₂ Dynamics (Colony: {current_colony_actual_size}, Days: {days}, Algae: {algae_area_m2:.0f}m², Potatoes: {potato_area_m2:.0f}m²)')
    ax.set_xlim([0, days if days > 0 else 1])
    
    min_y_val = 0
    all_buffer_values = [0, consumption_o2 * 30, production_o2 * 30, consumption_co2 * 30]
    
    if len(oxygen_levels) > 0:
      min_y_val_o2 = np.min(oxygen_levels)
      min_y_val = min(min(all_buffer_values), min_y_val_o2 if min_y_val_o2 < 0 else 0)
      current_max_o2 = np.max(oxygen_levels)
      max_y_val = max(max(all_buffer_values), current_max_o2 if current_max_o2 > 0 else 100)
    else:
        min_y_val = min(all_buffer_values)
        max_y_val = max(all_buffer_values) if max(all_buffer_values) > 0 else 100

    final_min_y = min_y_val * 1.1 if min_y_val < 0 else min_y_val * 0.9
    if min_y_val == 0: final_min_y = -max_y_val*0.05

    final_max_y = max_y_val * 1.1
    if final_min_y >= final_max_y :
        final_max_y = final_min_y + 100

    ax.set_ylim([final_min_y, final_max_y])
    
    ax.legend(loc='upper left')
    fig.canvas.draw_idle()

# Reset function
def reset(event):
    # --- MODIFIED: Reset global colony list ---
    global current_colony_list, current_colony_actual_size
    current_colony_list = generate_new_colony(initial_colony_size)
    current_colony_actual_size = initial_colony_size
    # --- END MODIFIED ---

    colony_slider.reset()
    days_slider.reset()
    algae_area_slider.reset()
    potato_area_slider.reset()
    # Update will now use the reset global colony
    update()

colony_slider.on_changed(update)
days_slider.on_changed(update)
algae_area_slider.on_changed(update)
potato_area_slider.on_changed(update)
reset_button.on_clicked(reset)

update()
plt.show()