#!/usr/bin/env python3
# filepath: /Users/owensun/Downloads/Tektite-R_EV_Template/o2-life-support/oxygen_vis.py

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from oxygen import Person, oxygen_consumption, oxygen_production, simulate_colony

# Time and colony settings
initial_days = 100  # Simulate for 100 days by default
max_days = 365  # Maximum simulation length of 1 year
initial_colony_size = 50

# Create the figure and axis
fig, ax = plt.subplots(figsize=(12, 8))
plt.subplots_adjust(left=0.1, bottom=0.35, right=0.95)  # Make room for the sliders and text

# Function to simulate oxygen over time for a given colony size
def simulate_oxygen_over_time(colony_size, days):
    # Create the colony
    people = [Person() for _ in range(colony_size)]
    
    # Calculate daily oxygen consumption (assume it's constant per day)
    daily_consumption = sum(p.oxygen_consumption() for p in people)
    
    # Calculate daily oxygen production from plants
    plant_area = colony_size * 61  # 61 m² per person
    daily_production = oxygen_production(plant_area)
    
    # Net oxygen change per day
    net_oxygen = daily_production - daily_consumption
    
    # Calculate cumulative oxygen levels over time
    # Start with a reasonable reserve (equal to 30 days of consumption)
    initial_oxygen = daily_consumption * 30
    oxygen_levels = [initial_oxygen]
    
    for day in range(1, days+1):
        # Add slight random variation to make it more realistic
        daily_variation = np.random.normal(1.0, 0.02)  # 2% standard deviation
        day_change = net_oxygen * daily_variation
        next_level = max(0, oxygen_levels[-1] + day_change)  # Ensure oxygen doesn't go negative
        oxygen_levels.append(next_level)
    
    return np.array(oxygen_levels[:-1]), daily_consumption, daily_production

# Create time points for initial plot
time_points = np.linspace(0, initial_days, initial_days)

# Initial plot
oxygen_levels, consumption, production = simulate_oxygen_over_time(initial_colony_size, initial_days)

# Create plots
line, = ax.plot(time_points, oxygen_levels, lw=2, label='Oxygen Level')
consumption_line = ax.axhline(y=consumption * 30, color='r', linestyle='--', label=f'Consumption: {consumption:.2f} kg/day')
production_line = ax.axhline(y=production * 30, color='g', linestyle='--', label=f'Production: {production:.2f} kg/day')
balance_line = ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)

# Add a line showing the net daily change
net_change = production - consumption
net_text = ax.text(initial_days*0.7, oxygen_levels[-1]*0.9, 
                f'Net O₂ change: {net_change:.2f} kg/day', 
                bbox=dict(facecolor='white', alpha=0.7))

# Add a sustainability indicator
sustainability_threshold = 1.1  # 10% safety margin
if net_change > 0 and production/consumption >= sustainability_threshold:
    status = "SUSTAINABLE"
    color = "darkgreen"
elif net_change > 0:
    status = "MARGINALLY SUSTAINABLE"
    color = "darkorange"
else:
    status = "UNSUSTAINABLE"
    color = "darkred"
    
status_text = ax.text(initial_days*0.5, oxygen_levels[-1]*1.1, 
                     status, fontsize=14, fontweight='bold', color=color,
                     bbox=dict(facecolor='white', alpha=0.7))

# Add labels and title
ax.set_xlabel('Days')
ax.set_ylabel('Oxygen Level (kg)')
ax.set_title(f'Oxygen Level Over Time (Colony Size: {initial_colony_size}, Days: {initial_days})')
ax.legend(loc='upper left')
ax.grid(True)

# Create sliders
slider_color = 'lightgoldenrodyellow'
# Colony size slider
colony_slider_ax = plt.axes([0.2, 0.2, 0.65, 0.03], facecolor=slider_color)
colony_slider = Slider(
    ax=colony_slider_ax,
    label='Colony Size',
    valmin=10,
    valmax=200,
    valinit=initial_colony_size,
    valstep=1
)

# Days slider
days_slider_ax = plt.axes([0.2, 0.15, 0.65, 0.03], facecolor=slider_color)
days_slider = Slider(
    ax=days_slider_ax,
    label='Simulation Days',
    valmin=30,
    valmax=max_days,
    valinit=initial_days,
    valstep=1
)

# Reset button
reset_ax = plt.axes([0.8, 0.025, 0.1, 0.04])
reset_button = Button(reset_ax, 'Reset', color=slider_color, hovercolor='0.975')

# Update function for the sliders
def update(val=None):
    colony_size = int(colony_slider.val)
    days = int(days_slider.val)
    
    # Update time points if days changed
    time_points = np.linspace(0, days, days)
    
    # Recalculate oxygen levels
    oxygen_levels, consumption, production = simulate_oxygen_over_time(colony_size, days)
    
    # Update plot data
    line.set_xdata(time_points)
    line.set_ydata(oxygen_levels)
    
    # Update horizontal lines for consumption and production
    consumption_line.set_ydata([consumption * 30, consumption * 30])
    production_line.set_ydata([production * 30, production * 30])
    
    # Update the legend and text elements
    net_change = production - consumption
    consumption_line.set_label(f'Consumption: {consumption:.2f} kg/day')
    production_line.set_label(f'Production: {production:.2f} kg/day')
    net_text.set_text(f'Net O₂ change: {net_change:.2f} kg/day')
    net_text.set_position((days*0.7, oxygen_levels[-1]*0.9))
    
    # Update sustainability status
    sustainability_threshold = 1.1  # 10% safety margin
    if net_change > 0 and production/consumption >= sustainability_threshold:
        status = "SUSTAINABLE"
        color = "darkgreen"
    elif net_change > 0:
        status = "MARGINALLY SUSTAINABLE"
        color = "darkorange"
    else:
        status = "UNSUSTAINABLE"
        color = "darkred"
    
    status_text.set_text(status)
    status_text.set_color(color)
    # set poisiton to top-right corner
    status_text.set_bbox(dict(facecolor='white', alpha=0.7))
    status_text.set_position((days*0.5, oxygen_levels[-1]*1.1))
    
    # Set color based on sustainability
    if net_change >= 0:
        net_text.set_bbox(dict(facecolor='lightgreen', alpha=0.7))
    else:
        net_text.set_bbox(dict(facecolor='lightcoral', alpha=0.7))
    
    # Update plot title
    ax.set_title(f'Oxygen Level Over Time (Colony Size: {colony_size}, Days: {days})')
    
    # Update x-axis and y-axis limits
    ax.set_xlim([0, days])
    ax.set_ylim([min(0, min(oxygen_levels)) * 1.1, max(oxygen_levels) * 1.1])
    
    # Update legend
    ax.legend(loc='upper left')
    
    fig.canvas.draw_idle()

# Reset function
def reset(event):
    colony_slider.reset()
    days_slider.reset()
    update()

# Register the update functions with sliders and button
colony_slider.on_changed(update)
days_slider.on_changed(update)
reset_button.on_clicked(reset)

# Show the plot
plt.tight_layout(rect=[0, 0.3, 1, 1])  # Adjust layout but leave space at bottom for text
plt.show()