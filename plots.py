import os
from copy import copy
import json

import matplotlib.pyplot as plt

from data.cyclist import Rider, PaceLine, Course

import data.data



course = Course([0, 12, 6, -6, -6, -6, -10, -10, -10, -10, -10, -10, 0, 0, 0, 6, 6, 6, 0, 0, 10, 10])
course = Course([0, 10, -5, 10, 0, 10, 10, 10])
course2 = Course([0, 10, -5, 10, 0, 10, 10, 10])



riders_orig = Rider.load_riders(data.data.riders)
riders = riders_orig
course.init_riders(riders)

riders_orig = Rider.load_riders(data.data.riders)
riders2 = riders_orig
course2.init_riders(riders2)

# SIM AND PLOT FOR PID ADJUSTING
timestep = 0.1
timestep2 = timestep

kp = 15
ti = 60
td = 0.3
kp2 = 12
ti2 = 35
td2 = 0.5
for i in range(len(riders)):
    riders[i].kp = kp
    riders[i].ti = ti
    riders[i].td = td
    riders2[i].kp = kp2
    riders2[i].ti = ti2
    riders2[i].td = td2
    
    riders[i].pos = 10 - i * 2.1
    riders[i].pos = 0
    riders[i].speed = 0
    riders[i].gradient = 0
    riders[i].course = course
    riders[i].timestep = timestep
    #riders[i].pulling = i != len(riders)-1
    riders[i].pulling = True

    riders2[i].pos = 10 - i * 2.1
    riders2[i].pos = 0
    riders2[i].speed = 0
    riders2[i].gradient = 0
    riders2[i].course = course2
    riders2[i].timestep = timestep2
    riders2[i].pulling = i != len(riders2)-1
    #riders2[i].pulling = True
    print(f"{riders[i].name}")
    print(f"{riders2[i].name}")
    if i == len(riders) - 1:
        print(f"{riders2[i].name} is the one in followers grp")
        print(f"{riders[i].name} is the one in followers grp")
    


sim_duration = 100
# START OF SIM LOOP
for i in range(int(sim_duration/timestep)):
    if i == 2000 or i == 500:
        #course.rider_groups[0].riders[0].pos += 1
        #course.rider_groups[0].paceline.rotate()
        pass
    course.update()

for i in range(int(sim_duration/timestep2)):
    if i == 2000 or i == 500:
        #course2.rider_groups[0].riders[0].pos += 1
        #course2.rider_groups[0].paceline.rotate()
        pass
    course2.update()
# END OF SIM LOOP

print(", ".join([rider.name for rider in course2.rider_groups[0].paceline.riders]))
print(", ".join([rider.name for rider in course2.rider_groups[0].followers.riders]))


plot_dist_err = True
if plot_dist_err:
    riders = course.rider_groups[0].sorted_riders()

    fig, ax_subplot = plt.subplots(2, 1)
    ax_pos = ax_subplot[0]
    colors = ['k', 'r', 'c', 'm', 'b']

    ax_pos.set_xlabel(f"time ({riders[0].timestep}*s)")
    ax_pos.set_ylabel('position diff (m)', color='k')
    ax_pos.tick_params(axis='y', labelcolor='k')
    ax_pos.grid(color='k', linestyle='--', linewidth=1)

    #ax_spd = ax_pos.twinx()
    #ax_spd.spines.right.set_position(("axes", 1))
    #ax_spd.set_ylabel('speed (km/h)')

    ax_effort = ax_pos.twinx()
    ax_effort.set_xlabel(f"time ({riders[0].timestep}*s)")
    ax_effort.set_ylabel('effort %', color='r')
    ax_effort.tick_params(axis='y', labelcolor='r')
    #ax_effort.grid(color='r', linestyle='--', linewidth=1)


    plot_relative_follow_pos = True
    for idx, rider in enumerate(riders):
        if plot_relative_follow_pos:
            if rider.follow_target != None:
                ax_pos.plot(rider.pos_err_hist, color=colors[idx%len(colors)], label=rider.name+' bhnd '+rider.follow_target.name, linewidth=(2 if rider == riders[0] else 1))
        else:
            ax_pos.plot(riders[0].pos_hist - rider.pos_hist, color=colors[idx%len(colors)], label=rider.name+' bhnd '+riders[0].name if rider.follow_target!=None else rider.name, linewidth=(2 if rider == riders[0] else 1))
        #ax_spd.plot(3.6*rider.speed_hist, color=colors[idx%len(colors)], label=rider.name+' bhnd '+rider.follow_target.name if rider.follow_target!=None else rider.name, linewidth=(2 if rider == riders[0] else 1))
        ax_effort.plot(rider.effort_hist, color=colors[idx%len(colors)], linestyle=':', label=f"{rider.name} effort")
    ax_pos.legend()
    ax_effort.legend()

    
    riders = course2.rider_groups[0].sorted_riders()
    ax_pos2 = ax_subplot[1]
    ax_pos2.set_xlabel(f"time ({riders[0].timestep}*s)")
    ax_pos2.set_ylabel('position diff (m)', color='k')
    ax_pos2.tick_params(axis='y', labelcolor='k')
    ax_pos2.grid(color='k', linestyle='--', linewidth=1)

    ax_effort2 = ax_pos2.twinx()
    ax_effort2.set_xlabel(f"time ({riders[0].timestep}*s)")
    ax_effort2.set_ylabel('effort %', color='r')
    ax_effort2.tick_params(axis='y', labelcolor='r')
    #ax_effort2.grid(color='r', linestyle='--', linewidth=1)

    plot_relative_follow_pos = True
    for idx, rider in enumerate(riders):
        if plot_relative_follow_pos:
            if rider.follow_target != None:
                #ax_pos2.plot(rider.follow_target.pos_hist - rider.pos_hist - rider.follow_target.bikelength - rider.follow_target.followmargin, color=colors[idx%len(colors)], label=rider.name+' bhnd '+rider.follow_target.name, linewidth=(2 if rider == riders[0] else 1))
                ax_pos2.plot(rider.pos_err_hist, color=colors[idx%len(colors)], label=rider.name+' bhnd '+rider.follow_target.name, linewidth=(2 if rider == riders[0] else 1))
        else:
            ax_pos2.plot(riders[0].pos_hist - rider.pos_hist, color=colors[idx%len(colors)], label=rider.name+' bhnd '+riders[0].name if rider.follow_target!=None else rider.name, linewidth=(2 if rider == riders[0] else 1))
        #ax_spd.plot(3.6*rider.speed_hist, color=colors[idx%len(colors)], label=rider.name+' bhnd '+rider.follow_target.name if rider.follow_target!=None else 'None', linewidth=(2 if rider == riders[0] else 1))
        ax_effort2.plot(rider.effort_hist, color=colors[idx%len(colors)], linestyle=':', label=f"{rider.name} effort")
    ax_pos2.legend()
    ax_effort2.legend()
    

for rider in course.rider_groups[0].riders:
    print(f"{max(rider.effort_hist[874:880]) - min(rider.effort_hist[874:880]):.3f}")
print('')
for rider in course2.rider_groups[0].riders:
    print(f"{max(rider.effort_hist[874:880]) - min(rider.effort_hist[874:880]):.3f}")
print('=')
for rider in course.rider_groups[0].riders:
    print(f"{rider.sprint:.1f}")
print('')
for rider in course2.rider_groups[0].riders:
    print(f"{rider.sprint:.1f}")

'''
for rider in course.rider_groups[0].riders:
    print(sum(rider.pos_err_hist))
print('')
for rider in course2.rider_groups[0].riders:
    print(sum(rider.pos_err_hist))
'''
plt.show()

show_savings_in_paceline = False
if show_savings_in_paceline:
    riders2 = []
    dist = 0.5
    for i in range(9):
        riders2.append(copy(riders[0]))
    for idx, rider in enumerate(riders2):
        rider.A = 0.34
        rider.Cd = 0.5
        rider.pos = 20 - idx*(2+dist)
        rider.speed = 15
    baseline = riders2[0].p_spd2(riders2[0].speed)
    paceline = PaceLine(riders2)
    paceline.sort_riders()
    paceline.riders[0].CdAfactor = 1
    paceline.sort_riders()
    paceline.update_cda()
    savings = []
    print(f"Distance between riders {dist} m")
    for idx, rider in enumerate(paceline.riders):
        pwr = rider.p_spd2(rider.speed)
        print(f"{idx}) {pwr:.0f} W   {pwr/baseline*100:.1f} %  {rider.CdAfactor:.3f} cda")
        savings.append(f"{pwr/baseline*100:.1f}")
    print(savings)


plot_aero_gains = False
if plot_aero_gains:
    rider1 = riders[2]
    rider2 = copy(riders[2])
    rider3 = copy(riders[2])
    fig, ax = plt.subplots()
    ax2 = ax.twinx()
    rider1.pos = 10
    t = []
    u = []
    u2 = []
    for i in range(130):
        t.append(0.1*i)
        rider2.pos = 10 - 0.1*i
        rider3.pos = 10 - 0.2*i
        x = rider2.upstream_aero_gain_dist(rider3)
        y = rider2.aero_gain_dist(rider1)
        u.append(x)
        u2.append(y)
    ax.plot(t, u, label='upstream')
    ax.plot(t, u2, label='drafting')
    ax.set_xlabel(f'distance [m]')
    ax.set_ylabel('CdA reduction (factor)')
    ax.legend()
    plt.show()
