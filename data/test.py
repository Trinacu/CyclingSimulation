import os
import json
import math

import matplotlib.pyplot as plt

from copy import copy

import pygame as pg

from cyclist import Course, Rider, RiderGroup, PaceLine


script_path = os.path.dirname(__file__)
json_path = os.path.join(script_path, 'json')
cyclists_path = os.path.join(json_path, 'cyclists')

course = Course([0, 12, 6, -6, -6, -6, -10, -10, -10, -10, -10, -10, 0, 0, 0, 6, 6, 6, 0, 0, 10, 10])

riders = []
for root, dirs, files in os.walk(cyclists_path, topdown=False):
    for filename in files:
        if 'ignore' in filename:
            continue
        #print('loaded ' + filename)
        f = open(os.path.join(root, filename))
        d = json.load(f)
        riders.append(Rider(d, course))

course.init_riders(riders)

for idx, rider in enumerate(riders):
    rider.A = 0.34
    rider.pos = 20 - idx*2.1
    if rider.name == 'Anton':
        anton = riders[idx]
    elif rider.name == 'Pedro':
        pedro = riders[idx]
    elif rider.name == 'Joe':
        joe = riders[idx]
    elif rider.name == 'Mario':
        mario = riders[idx]
    elif rider.name == 'Giovanni':
        giovanni = riders[idx]

g = RiderGroup(course, riders)


# START OF SIM LOOP
timestep = 2
for rider in g.riders:
    rider.pos = 0
    rider.speed = 0
    rider.gradient = 0
    rider.course = course
    rider.timestep = timestep

for i in range(int(500/timestep)):
    interval = 60

    # check if a rider crossed the line, save his time and stop updating? or somehow solve idx out of range
    # maybe extend course past finish line and then take time at defined finish line and 'delete'' riders at end of course?
    for group in course.rider_groups:
        group.update()

    if i % interval == 0:
        print('\n-- update at {:.1f} min --'.format(i*timestep/60))
        for group in course.rider_groups:
            print('group')
            for rider in group.riders:
                print('{} {:.0f}% {:.0f}W ({:.0f}%) {:.1f}km/h\nCdAfactor:{:.1f} mode:{}'.format(rider.name, rider.gradient, rider.effort*rider.ftp, rider.effort*100, rider.speed*3.6, rider.CdAfactor, rider.mode))
                print(rider.visual_res(20))
                print(rider.visual_spr(20))
                print(rider.visual_pos(20))



