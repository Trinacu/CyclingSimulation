import os
import sys
import json
import math
import matplotlib.pyplot as plt
import numpy as np

from . import tools

from copy import copy

import pygame as pg

glb_GROUP_SPLIT_DIST = 25
glb_GRADIENT_TRANSITION_LEN = 20

# distance behind rider in front's wheel where cdA factor is lowest (before it starts to rise)
glb_FOLLOW_MARGIN = 0.15
glb_FOLLOW_CDA_DROP = 0.43

glb_UPSTREAM_CDA_DROP = 0.03


        
class Course:
    def __init__(self, gradients):
        global glb_GRADIENT_TRANSITION_LEN
        tran_len=glb_GRADIENT_TRANSITION_LEN
        self.riders = []
        self.rider_groups = []
        self.gradients = [g for g in gradients for i in range(1000)]
        # make transitions smooth
        for i in range(1, len(self.gradients)-100):
            if self.gradients[i-1] != self.gradients[i]:
                diff = int(self.gradients[i] - self.gradients[i-1])
                if abs(diff) > 1:
                    for j in range(abs(diff)):
                        for k in range(tran_len):
                            self.gradients[i+tran_len*j+k] = self.gradients[i-1] + j * np.sign(diff)
                    i += tran_len*diff


        self.surf = pg.Surface((10,10))
        
    def init_riders(self, riders):
        for rider in riders:
            rider.course = self
            self.riders.append(rider)
        self.add_rider_group(riders)
        
    def add_rider_group(self, riders):
        grp = RiderGroup(self, riders)
        self.rider_groups.append(grp)

    def update(self):
        # TODO - sort groups and split/join them
        for group in self.rider_groups:
            group.update_pos()
            
            # this updates the riders in the groups, first moves pulling ones into paceline and other way around,
            # then updates CdA, then changes pos according to speed
            group.update()

        
class RiderGroup:
    def __init__(self, course, riders):
        self.pos = (0, 0)
        self.riders = riders
        self.paceline = PaceLine(self)
        self.followers = Followers(self)
        self.course = course
        
        for rider in riders:
            rider.group = self
            # TODO - which riders actually want in the paceline?
            if rider.pulling:
                self.paceline.add_rider(rider)
            else:
                self.followers.add_rider(rider)
    
    # update pos and split if needed (what about join?)
            
    def sorted_riders(self):
        return sorted(self.riders, key=lambda rider: rider.pos, reverse=True)
    
    def sort_riders(self):
        self.riders = sorted(self.riders, key=lambda rider: rider.pos, reverse=True)
    
    def update_pos(self):
        self.pos = (self.riders[0].pos, self.riders[-1].pos)
        #print(f"new group pos = {self.pos}")
            
    # TODO - also check for joins?
    def check_for_splits(self):
        global glb_GROUP_SPLIT_DIST
        for i in range(1, len(self.riders)):
            if self.riders[i-1].pos - self.riders[i].pos > glb_GROUP_SPLIT_DIST:
                print(f"split between {self.riders[i-1].name} ({self.riders[i-1].pos} and {self.riders[i].name} ({self.riders[i].pos}")
                riders = []
                for j in range(i, len(self.riders)):
                    riders.append(self.riders[j])
                for rider in riders:
                    self.riders.remove(rider)
                self.course.add_rider_group(riders)
                break
                
    def update(self):
        for rider in self.riders:
            if (rider.pulling) and (rider not in self.paceline.riders):
                self.paceline.add_rider(rider)
                self.followers.remove_rider(rider)
            if (not rider.pulling) and (rider in self.paceline.riders):
                self.paceline.remove_rider(rider)
                self.followers.add_rider(rider)

        self.paceline.update()
        self.followers.update()
        [r.update() for r in self.riders]

        self.check_for_splits()
        #self.check_for_splits()

class Followers():
    def __init__(self, rider_group):
        self.rider_group = rider_group
        self.riders = []

    def sort_riders(self):
        self.riders = sorted(self.riders, key=lambda rider: rider.pos, reverse=True)
            
    def sorted_riders(self):
        return sorted(self.riders, key=lambda rider: rider.pos, reverse=True)
    
    def add_rider(self, rider):
        self.riders.append(rider)
        
    def remove_rider(self, rider):
        self.riders.remove(rider)

    def update(self):
        # TODO - cycling the rotation?
        self.sort_riders()
        self.update_cda()
        for idx in range(len(self.riders)):
            if idx == 0:
                if len(self.rider_group.paceline.riders) > 0:
                    self.riders[idx].follow(self.rider_group.paceline.riders[-1])
                else:
                    self.riders[idx].effort = 0.7
            else:
                self.riders[idx].follow(self.riders[idx-1])



    def update_cda(self):
        # pulling row
        for idx, rider in enumerate(self.riders):
            if len(self.rider_group.paceline.riders) > 0:
                rider.CdAfactor = self.rider_group.paceline.pulling[-1].CdAfactor
            else:
                if idx == 0:
                    rider.lowest_CdAfactor = 1
                    rider.aero_gain = 0
                    rider.CdAfactor = 1
                elif idx < 6:
                    rider.lowest_CdAfactor = (1 - glb_FOLLOW_CDA_DROP) - self.riders[idx-1].aero_gain * PaceLine.additional_cda_gain[min(idx, len(PaceLine.additional_cda_gain)-1)]
                    rider.aero_gain = rider.aero_gain_dist(self.riders[idx-1])
                    rider.CdAfactor = 1 - (1-rider.lowest_CdAfactor) * rider.aero_gain
                else:
                    rider.lowest_CdAfactor = (1 - glb_FOLLOW_CDA_DROP) - self.riders[idx-1].aero_gain * PaceLine.additional_cda_gain[-1]
                    rider.aero_gain = rider.aero_gain_dist(self.riders[idx-1])
                    rider.CdAfactor = 1 - (1-rider.lowest_CdAfactor) * rider.aero_gain
        
class PaceLine():
    # list of relative (%) extra aero gains for rider after the 2nd (drafting more than 1 rider)
    additional_cda_gain = [0, 0, 0.14, 0.21, 0.24, 0.25]
    def __init__(self, rider_group):
        self.rider_group = rider_group
        self.riders = []

        # 2 rows, one is pulling, the other contains riders going to the back of the pulling row
        self.pulling = []
        self.rotating = []

        
    def sort_riders(self):
        self.riders = sorted(self.riders, key=lambda rider: rider.pos, reverse=True)
            
    def sorted_riders(self):
        return sorted(self.riders, key=lambda rider: rider.pos, reverse=True)
    
    def add_rider(self, rider):
        self.riders.append(rider)
        self.pulling.append(rider)
        
    def remove_rider(self, rider):
        if rider in self.pulling:
            self.pulling.remove(rider)
        else:
            self.rotating.remove(rider)
        self.riders.remove(rider)

    def rotate(self):
        rider = self.pulling.pop(0)
        self.rotating.append(rider)
        rider.row = 2

    def update(self):
        self.update_cda()
        being_dropped = []
        for idx in range(len(self.pulling)):
            if ((self.pulling[idx].resistance < 5) or (self.pulling[idx].sprint < 5)) and self.pulling[idx].pos_err_hist[-1] > 5:
                # append and remove outside loop, otherwise we get idx out of range
                being_dropped.append(self.pulling[idx])
            if idx == 0:
                if self.pulling[idx].gradient < 0:
                    self.pulling[idx].effort = 0.8
                    self.pulling[idx].CdAfactor = 0.7
                else:
                    self.pulling[idx].effort = 1.2
            else:
                self.pulling[idx].follow(self.pulling[idx-1])

        finished_rotating = []
        for idx in range(len(self.rotating)):
            # !! TODO !! - stuff like this needs to have checks for whether there's even riders (for example self.pulling[-1])!
            #if self.rotating[idx].pos > self.pulling[-1].pos - self.pulling[-1].bikelength - glb_FOLLOW_MARGIN:
            if self.rotating[idx].pos > self.pulling[-1].pos:
                self.rotating[idx].follow(self.pulling[-1])
            else:
                # append and remove outside loop, otherwise we get idx out of range
                finished_rotating.append(self.rotating[idx])
                self.sort_riders()

        for rider in being_dropped:
            print(f"{rider.name} is being dropped into followers group")
            self.remove_rider(rider)
            self.rider_group.followers.add_rider(rider)
            rider.pulling = False
            if rider in finished_rotating:
                finished_rotating.remove(rider)

        for rider in finished_rotating:
            self.rotating.remove(rider)
            self.pulling.append(rider)
            rider.row = 0

        
    def update_cda(self):
        # pulling row
        for idx, rider in enumerate(self.pulling):
            #if rider == self.riders[0]:
            if idx == 0:
                rider.lowest_CdAfactor = 1
                rider.aero_gain = 0
                rider.CdAfactor = 1
            else:
                rider.lowest_CdAfactor = (1 - glb_FOLLOW_CDA_DROP) - self.pulling[idx-1].aero_gain * PaceLine.additional_cda_gain[min(idx, len(PaceLine.additional_cda_gain)-1)]
                rider.aero_gain = rider.aero_gain_dist(self.pulling[idx-1])
                rider.CdAfactor = 1 - (1-rider.lowest_CdAfactor) * rider.aero_gain

            if idx < len(self.pulling)-1:
                rider.CdAfactor -= rider.upstream_aero_gain_dist(self.pulling[idx+1]) * glb_UPSTREAM_CDA_DROP

        for idx, rider in enumerate(self.rotating):
            # TODO - do something fancier?
            rider.CdAfactor = 0.6


class Rider:
    def __init__(self, d):
        self.name = d['name']
        self.lastname = d['lastname']
        self.fullname = self.name + ' ' + self.lastname
        self.mass = d['mass']
        self.ftp = d['ftp']
        self.Cd = d['Cd']
        self.A = d['A']
        self.Crr = d['Crr']
        
        self.poserr_old = 0
        self.poserr_sum = 0
        
        self.speed_hist = np.array([])
        self.pos_hist = np.array([])
        self.effort_hist = np.array([])
        self.gradient_hist = np.array([])
        self.pos_err_hist = np.array([])
        self.poserr_sum_hist = np.array([])
        self.CdAfactor_hist = np.array([])
        
        self.timestep = 1
        #follow pid param
        # these work quite well
        if False:
            self.kp = 10
            self.ti = 60
            self.td = 1
        else:
            self.kp = 12
            self.ti = 35
            self.td = 0.5
        
        self.CdAfactor = 1
        self.lowest_CdAfactor = 1
        # value [0, 1] which is multiplied by max CdA saving to get actual CdA
        self.aero_gain = 0
        # margin behind rider in front where CdAfactor = lowest
        self.followmargin = glb_FOLLOW_MARGIN
        
        self.gradient = 0
        self.Vhw = 0
        self.rho = 1.22
        
        # this is used when displaying, even rows are the standard, odds are for offsetting riders that would collide/overlap?
        self.row = 0
        
        self.follow_target = None
        self.following = []
        self.in_paceline = False
        
        self.bikemass = 8
        self.bikelength = 2 - glb_FOLLOW_MARGIN
        
        self.hr = 60
        self.resistance = 100
        self.stamina = 100
        self.sprint = 100
        self.pos = 0
        self.speed = 0
        self.effort = 0.7
        
        # 0: maintain pos / follow
        # 1: pull
        # 2: manual/attack
        self.mode = 0

        self.pulling = False

        self.surf = pg.Surface((10,3))
        self.surf.fill((100,100,100))


    @staticmethod
    def load_riders(d):
        riders = []
        for ridername in d:
            riders.append(Rider(d[ridername]))
        return riders
        
    def stats_str(self):
        return "{}:\nFTP:{:.0f}W, mass:{:.1f}kg, Cd*A:{:.2f}".format(self.name, self.ftp, self.mass, self.CdAfactor * self.Cd * self.A)

    # not used
    def p_spd(self, spd):
        a = 0.5 * self.CdAfactor * self.Cd * self.A * self.rho
        b = self.Vhw * self.CdAfactor * self.Cd * self.A * self.rho
        c = 9.8 * (self.mass+self.bikemass) * \
         (self.gradient/100 + self.Crr * math.cos(self.gradient/100)) + \
         0.5 * self.CdAfactor * self.Cd * self.A * self.rho * self.Vhw**2
        return (a * spd**3) + (b * spd**2) + (c * spd)

    # also takes into account stored kinetic energy - meaning it cares about acceleration (starting speed)
    def p_spd2(self, spd):
        a = 0.5 * self.CdAfactor * self.Cd * self.A * self.rho
        b = self.Vhw * self.CdAfactor * self.Cd * self.A * self.rho +\
        	self.mass / (2*self.timestep)
        c = 9.8 * (self.mass+self.bikemass) *\
         (self.gradient/100 + self.Crr * math.cos(self.gradient/100)) +\
        		0.5 * self.CdAfactor * self.Cd * self.A * self.rho * self.Vhw**2
        d = - (self.mass * self.speed**2 / (2*self.timestep))
        return (a * spd**3) + (b * spd**2) + (c * spd) + d


    def spd_p(self, power, margin=0.01):
        return illinois_algorithm(self.p_spd, 0, 30, power, margin)

    def spd_p2(self, power, margin=0.1):
        try:
            return illinois_algorithm(self.p_spd2, 0, 40, power, margin)
        except AssertionError:
            self.effort = 0
            print('oops')
            self.power = self.effort * self.ftp
            return self.spd_p2(self.power)

    # returns a value [0, 1] which is then multiplied by max CdA factor gain to get actual CdA factor
    def aero_gain_dist(self, target):
        dist = target.pos - self.pos
        bikelen = target.bikelength
        margin = glb_FOLLOW_MARGIN
        benefit_start = 0.3
        grad1 = 0.06
        grad2 = 0.15
        if dist <= bikelen-benefit_start:
            return 0
        elif dist <= bikelen:
            return 1 - bikelen/(benefit_start) + dist * 1/(benefit_start)
        elif dist <= bikelen + margin:
            return 1
        elif dist <= bikelen + margin + 5:
            return 1 + grad1 * (bikelen+margin) - dist * grad1
        elif dist <= 12:
            return max(0, 1 - grad1*5 + grad2*(bikelen+margin+5) - dist * grad2)
        elif dist <= 30:
            return 0
        # we really shouldn't be following hre anymore
        else:
            print(f"why is {self.name} following {target.name} at 30m distance?")
            return 1

    def upstream_aero_gain_dist(self, follower):
        dist = self.pos - follower.pos
        bikelen = self.bikelength
        benefit_start = 0.1
        margin = 0.05
        grad1 = 0.7
        if dist <= bikelen-benefit_start:
            return 0
        elif dist <= bikelen:
            return 1 - bikelen/(benefit_start) + dist * 1/(benefit_start)
        elif dist <= bikelen + margin:
            return 1
        elif dist <= 3.7:
            return max(0, 1 + grad1 * (bikelen+margin) - dist * grad1)
        elif dist <= 30:
            return 0
        else:
            print(f"why are we checking upstream gains of {self.name} followed by {follower.name} at 30m distance?")
            return 1



            
    def follow(self, target):
        # aim to stay at follow.margin behind the rider because CdAfactor rises more shallowly behind thr rider as opposed to coming up to their side
        err = target.pos - self.pos - target.bikelength - target.followmargin

        # when error is large, go up to this much faster/slow untill error is small, then we use PID
        manage_high_error = True
        if manage_high_error:
            absolute_spd_diff = 0.5     # m/s
            if np.abs(err) > 0.2:
                if np.abs(err) > 1:
                    self.effort = self.p_spd2(target.speed + np.sign(err) * absolute_spd_diff) / self.ftp
                else:
                    self.effort = self.p_spd2(target.speed + err * absolute_spd_diff) / self.ftp

        
        if np.abs(err) < 0.2 or (not manage_high_error):
            self.follow_target = target
            self.poserr_sum += err
                    
            if self.ti > 0:
                self.effort = self.kp * (err + (1/self.ti) * self.poserr_sum + self.td * ((err - self.poserr_old)/self.timestep))
            else:
                self.effort = self.kp * (err + self.td * ((err - self.poserr_old)/self.timestep))

            # don't go backwards?
            if self.speed < 0.5:
                self.effort = max(0, self.effort)
                
        self.poserr_old = err


    def drop_back_to(self, target):
        if self.pos > target.pos - target.bikelength:
            self.effort = self.p_spd2(0.95*target.speed) / self.ftp
        elif self.pos > target.pos - target.bikelength - glb_FOLLOW_MARGIN:
            self.effort = self.p_spd2(0.98*target.speed) / self.ftp
        else:
            print("THIS SHOULD NOT HAPPEN (Rider.drop_back_to())")
            sys.exit()
                
            
    def strategy(self):
        # follow mode
        if self.mode == 0:
            if self in self.group.paceline.riders:
                self.group.paceline.remove_rider(self)
            
            # TODO - write logic for how many follow spots are available depeneding on nr of pulling riders (up to 5 maybe 1 spot, then up to 10 2 spots etc)
            pulling_nr = len(self.group.pulling)
            
            if self.follow_target != None:
                # if current target is not in my group, remove it
                if self.follow_target not in self.group.riders:
                    self.follow_target = None
                else:
                    self.follow(self.follow_target)

            # list riders from last guy in pulling group to last in follow grp and find some1 to follow
            if self.follow_target == None:
                for i in range(pulling_nr-1, len(self.group.riders)):
                    #print(group.riders[i].name + ' being followed by')
                    #print('[' + ' '.join([rider.name for rider in group.riders[i].following]) + ']')
                    if (not group.riders[i] == self) and (not group.riders[i] in self.following) and (len(group.riders[i].following) == 0) and ((group.riders[i] in group.pulling) or (group.riders[i].follow_target != None)):
                        self.follow_target = group.riders[i]
                        group.riders[i].following.append(self)
                        # todo - when do we remove some1 frm this list?
                        print(f"{self.name} decided to follow {group.riders[i].name}")
                        break
                # if noone to follow, go pull (todo - except if tired?)
                    if i == len(self.group.riders):
                        self.mode = 1
                
            '''
            else:
                print(f"ERROR: {self.name} mode follow but without a target!")
                self.effort = 0.4
            '''
        
        # pull mode
        if self.mode == 1:
            if self not in self.group.paceline.riders:
                self.group.paceline.add_rider(self)
                
            if self == self.group.paceline.riders[0]:
                # TODO - logic (timer) for swapping rider at the front
                if len(self.group.paceline.riders) > 1:
                    self.effort = 1.05
                else:
                    self.effort = 0.9
            else:
                # TODO - fix to follow rider in front
                #print(self.group.pulling)
                self.follow(self.group.pulling[0])
                #self.effort = 0.7


    def update(self):
        self.gradient = self.course.gradients[int(self.pos)]
        
        #limit effort
        self.effort = max(-2, min(4, self.effort))
        
        if self.sprint <= 0.1:
            self.sprint = 0
        if self.sprint <= 5:
            #print(f"{self.name} {self.mode} {self.sprint} attempted {self.effort} effort capped to 1")
            self.effort = min(self.effort, 1)
            
        if self.resistance <= 0.1:
            self.resistance = 0
        if self.resistance <= 5:   
            self.effort = min(self.effort, 0.4)
        
        # to prevent unwanted regeneration due to braking (when effort < 0)
        drain_effort = max(0,self.effort)
        resistance_drain = self.timestep * (0.035 - 0.095 * math.exp(-2*drain_effort))
        self.resistance -= resistance_drain
        self.resistance = min(self.resistance, 100)
        self.resistance = max(self.resistance, 0)
        
        sprint_drain = self.timestep * (-1.2 + 0.45 * self.effort + 0.75 * drain_effort**2)
        # this is unnecessary since we check for resistance <= 5 above and then limit the effort
        if self.resistance <= 0 and resistance_drain > 0:
            sprint_drain = resistance_drain * 100
        self.sprint -= sprint_drain
        self.sprint = min(self.sprint, 100)
        self.sprint = max(self.sprint, 0)
        
        #print(self.effort, self.resistance)
        #print('{}: res={:f}'.format(rider.fullname, rider.resistance))

        #print(self.resistance, self.sprint, self.effort)

        self.power = self.effort * self.ftp
        self.speed = self.spd_p2(self.power)
        
        dist = self.speed * self.timestep
        self.pos += dist
        
        # save values to hist arrays for plotting    
        self.speed_hist = np.append(self.speed_hist, self.speed)
        self.pos_hist = np.append(self.pos_hist, self.pos)
        self.effort_hist = np.append(self.effort_hist, self.effort)
        self.gradient_hist = np.append(self.gradient_hist, self.gradient)
        self.CdAfactor_hist = np.append(self.CdAfactor_hist, self.CdAfactor)
        self.pos_err_hist = np.append(self.pos_err_hist, self.poserr_old)
        self.poserr_sum_hist = np.append(self.poserr_sum_hist, self.poserr_sum)
            
    # maybe this could be done for a whole group at the same time as strategy() call?"
    def update_cda(self):
        if self == self.group.riders[0]:
        	if self.gradient < -5:
        	    self.CdAfactor = 0.99
        	else:
        	    self.CdAfactor = 1
        	return
        # todo - maybe check if in big group and just say CdAfactor = 0.2
        # if following target, just check distance to them - makes CdA and thus speed more stable
        if self.follow_target != None:
            #self.CdAfactor = self.CdAfactor_dist(self.follow_target)
            self.lowest_CdAfactor = 1 - glb_FOLLOW_CDA_DROP
            self.aero_gain = self.aero_gain_dist(self.follow_target)

        else:
            idx = [x for x in range(len(self.group.riders)) if self.group.riders[x] == self][0]
            factors = []
            # get up to 5 riders in front and find lowest CdAfactor
            for i in range(max(0, idx-5), idx):
                factors.append(self.CdAfactor_dist(self.group.riders[i]))
            self.CdAfactor = factors[-1]#min(factors)
        # if going downhill, assume we can get more aero?
        if self.gradient < -5:
            self.CdAfactor = min(self.CdAfactor, 0.85)


    class RiderDisplay():
        def __init__(self, rider):
            self.rider = rider

            self.size = (120,80)
            self.h_margin = 10

            self.surf = pg.Surface(self.size)
            self.surf.fill((255,255,255))
            text = tools.make_text_surf(rider.name, (0,0,0), 30)
            self.surf.blit(text, (10,4))
            self.surf_clean = self.surf.copy()

            # TODO - how do I pass self.rider.resistance as reference, so we can read its value in update function of ProgressBar?
            # that way, update() of ProgressBar doesn't need any parameters, because it just reads the value that it is linked to
            self.resistance_bar = tools.ProgressBar((self.size[0] - 2*self.h_margin, 6), (50, 200, 50), (255,255,255), self.rider.resistance)
            self.sprint_bar = tools.ProgressBar((self.size[0] - 2*self.h_margin, 6), (200, 50, 50), (255,255,255), self.rider.sprint)

            # TODO - add bars (yellow stamina, red sprint) and pos, power etc values

        def update(self):
            self.surf = self.surf_clean.copy()
            if self.rider.follow_target:
                text = tools.make_text_surf(f"{self.rider.follow_target.name}", (0,0,0), 20)
                self.surf.blit(text, (70, 4))

            text = tools.make_text_surf(f"{self.rider.effort*self.rider.ftp:.0f} W  ({self.rider.effort*100:.0f} %)", (0,0,0), 20)
            self.surf.blit(text, (10, 25))
            text = tools.make_text_surf(f"{self.rider.speed*3.6:.2f} km/h", (0,0,0), 20)
            self.surf.blit(text, (10, 40))
            text = tools.make_text_surf(f"{self.rider.CdAfactor:.2f} cda", (0,0,0), 20)
            self.surf.blit(text, (80, 40))

            self.resistance_bar.update(self.rider.resistance/100)
            self.surf.blit(self.resistance_bar.surf, (self.h_margin, 60))
            self.sprint_bar.update(self.rider.sprint/100)
            self.surf.blit(self.sprint_bar.surf, (self.h_margin, 70))
    
def illinois_algorithm(f, a, b, y, margin=.00_001):
    '''
    Bracketed approach of Root-finding
    with illinois method
    Parameters ----------
    f: callable, continuous function
    a: float, lower bound to be searched
    b: float, upper bound to be searched
    y: float, target value
    margin: float, margin of error in absolute term
    Returns -------
    A float c, where f(c) is within the margin of y
    '''
    
    lower = f(a)
    upper = f(b)
    
    
    assert y >= lower, f"y is smaller than the lower bound. {y} < {lower}"
    assert y <= upper, f"y is larger than the upper bound. {y} > {upper}"

    stagnant = 0
    while 1:
        c = ((a * (upper - y)) - (b * (lower - y))) / (upper - lower)
        y_c = f(c)
        #print(y_c)
        if abs(y_c - y) < margin:
            # found!
            return c
        elif y < y_c:
            b, upper = c, y_c
            
        if stagnant == -1:
            # Lower bound is stagnant!
            lower += (y - lower) / 2
            stagnant = -1
        else:
            a, lower = c, y_c
            
        if stagnant == 1:
            # Upper bound is stagnant!
            upper -= (upper - y) / 2
            stagnant = 1




if __name__ == '__main__':

    riders = Rider.load_riders(data.riders)



    # END OF SIM LOOP
            
            
            
    for grp in course.rider_groups:
        print(f"grp: [{','.join([r.name for r in grp.riders])}]")
        


    # riders pos (relative) and speed

    fig, ax_subplot= plt.subplots(2, 1)
    ax_pos = ax_subplot[0]

    ax_pos.set_xlabel(f"time ({riders[0].timestep}*s)")
    ax_pos.set_ylabel('position diff (m)', color='k')
    ax_pos.tick_params(axis='y', labelcolor='k')
    ax_pos.grid(color='k', linestyle='--', linewidth=1)

    ax_spd = ax_pos.twinx()
    ax_spd.spines.right.set_position(("axes", 1))
    ax_spd.set_ylabel('speed (km/h)')
    colors = ['k', 'r', 'c', 'm', 'b']
    riders = sorted(riders, key=lambda rider: rider.pos, reverse=True)
        
    i = 0
    plot_relative_follow_pos = False
    for rider in riders:
        if plot_relative_follow_pos:
            if rider.follow_target != None:
                ax_pos.plot(rider.follow_target.pos_hist - rider.pos_hist - rider.follow_target.bikelength - 0.8 * rider.follow_target.followmargin, color=colors[i%len(colors)])
        else:
                ax_pos.plot(anton.pos_hist - rider.pos_hist, color=colors[i%len(colors)], linestyle=':')
        ax_spd.plot(3.6*rider.speed_hist, color=colors[i%len(colors)], label=rider.name+' bhnd '+rider.follow_target.name if rider.follow_target!=None else rider.name, linewidth=(2 if rider.name=='Anton' else 1))
        i+=1

        
    ax_spd.legend()
        

    # plot rider that has most trouble following
    worst = 0
    val = 0
    for rider in riders:
        if rider.follow_target != None:
            val = max(np.abs(rider.pos_err_hist))
            print(f"{rider.name} worst pos_err {val}")
            if val > worst:
                worst = val
                worst_rider = rider

    rider = joe

    err_sum = sum([abs(val) for val in rider.pos_err_hist])

    data2 = 100*np.array(rider.effort_hist)
    #data3 = np.array(rider.follow_target.speed_hist) - np.array(rider.speed_hist)
    """
    fig, ax = plt.subplots()
    ax.plot([pedro.CdAfactor_dist(t/99, 2, 0.3) for t in range(900)])
    """
    ax_poserr = ax_subplot[1]

    color = 'tab:red'
    ax_poserr.set_xlabel(f"{rider.name}  time ({riders[0].timestep}*s)  err_sum={err_sum:.0f}")
    ax_poserr.set_ylabel('position error (m)', color=color)
    ax_poserr.plot(rider.pos_err_hist, color=color, linewidth=2)
    ax_poserr.tick_params(axis='y', labelcolor=color)
    ax_poserr.grid(color='r', linestyle='--', linewidth=1)



    ax_grad= ax_poserr.twinx()
    ax_grad.spines.right.set_position(("axes", -0.1))
    ax_grad.plot(rider.gradient_hist, color='k')
    ax_grad.set_ylabel('gradient (%)', color='k')

    color ='tab:blue'
    ax_effort= ax_poserr.twinx()
    ax_effort.spines.right.set_position(("axes", -0.2))
    ax_effort.plot(100*np.array(rider.effort_hist), color=color)
    ax_effort.set_ylabel('effort and CdAfactor (%)', color=color)
    ax_effort.plot(100*np.array(rider.CdAfactor_hist), color='c')
    ax_effort.tick_params(axis='y', labelcolor='c')

    ax2 = ax_poserr.twinx()  # instantiate a second axes that shares the same x-axis
    ax2.set_ylabel('pos err sum)', color='m')  # we already handled the x-label with ax1
    ax2.tick_params(axis='y', labelcolor='m')
    ax2.plot(rider.poserr_sum_hist, color='m')


    fig.tight_layout()  # otherwise the right y-label is slightly clipped

    plt.show()
    plt.savefig('cycleplot.png')


