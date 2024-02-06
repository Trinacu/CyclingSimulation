import os
import json
import math
import matplotlib.plt as plt

class PowerProfile:
    def __init__(self, d):
        self.ftp = d['ftp']
        self._20min = d['20min']

class Stats:
    def __init__(self, d):
        self.flat = d['flat']
        self.mountain = d['mountain']
        self.hill = d['hill']
        self.downhill = d['downhill']
        self.resistance = d['resistance']
        self.stamina = d['stamina']
        self.recovery = d['recovery']
        
        
class RiderGroup:
    def __init__(self, course, riders):
        self.dist = 0
        self.riders = riders
        self.pulling = []
        
        for rider in riders:
            rider.group = self

class Rider:
    def __init__(self, d, course):
        self.name = d['name']
        self.lastname = d['lastname']
        self.fullname = self.name + ' ' + self.lastname
        self.stats = Stats(d['stats'])
        self.mass = d['mass']
        self.ftp = d['ftp']
        self.Cd = d['Cd']
        self.A = d['A']
        self.Crr = d['Crr']
        
        #follow pid param
        self.kp = 0.5
        self.ti = 0
        self.td = 0
        
        self.CdAfactor = 1
        
        self.gradient = 0
        self.Vhw = 0
        self.rho = 1.22
        
        self.timestep = 5
        
        self.follow_target = None
        self.following = []
        
        self.bikemass = 8
        self.bikelength = 2
        
        self.course = course
        
        self.hr = 60
        self.resistance = 100
        self.stamina = 100
        self.sprint = 100
        self.dist = 0
        self.speed = 0
        self.effort = 0.7
        
        # 0: maintain pos / follow
        # 1: pull
        # 2: manual/attack
        self.mode = 0
        
    def stats_str(self):
        return "{}:\nFTP:{:.0f}W, mass:{:.1f}kg, Cd*A:{:.2f}".format(self.name, self.ftp, self.mass, self.CdAfactor * self.Cd * self.A)

    def p_spd(self, spd):
        a = 0.5 * self.CdAfactor * self.Cd * self.A * self.rho
        b = self.Vhw * self.CdAfactor * self.Cd * self.A * self.rho
        c = 9.8 * (self.mass+self.bikemass) * \
         (self.gradient/100 + self.Crr * math.cos(self.gradient/100)) + \
         0.5 * self.CdAfactor * self.Cd * self.A * self.rho * self.Vhw**2
        return (a * spd**3) + (b * spd**2) + (c * spd)

    # also takes into account stored kinetic energy
    def p_spd2(self, spd):
        a = 0.5 * self.CdAfactor * self.Cd * self.A * self.rho
        b = self.Vhw * self.CdAfactor * self.Cd * self.A * self.rho +\
        	self.mass / (2*self.timestep)
        c = 9.8 * (self.mass+self.bikemass) *\
         (self.gradient/100 + self.Crr * math.cos(self.gradient/100)) +\
        		0.5 * self.CdAfactor * self.Cd * self.A * self.rho * self.Vhw**2
        d = - (self.mass * self.speed**2 / (2*self.timestep))
        #print(spd**2 * self.mass / (2*self.timestep))
        #print(d)
        return (a * spd**3) + (b * spd**2) + (c * spd) + d


    def spd_p(self, power, margin=0.01):
        return illinois_algorithm(self.p_spd, 0, 30, power, margin)

    def spd_p2(self, power, margin=0.1):
        return illinois_algorithm(self.p_spd2, 0, 30, power, margin)

    def strategy(self):
        """
        if self.name == 'Pedro' and (len(self.course.gradients) - self.dist) < 5:
            # manual (attack?) mode
            self.mode = 2
            self.effort = 1.02
        """
        # follow mode
        if self.mode == 0:
            if self in self.group.pulling:
                self.group.pulling.remove(self)
            # TODO - write logic for how many follow spots are available depeneding on nr of pulling riders (up to 5 maybe 1 spot, then up to 10 2 spots etc)
            pulling_nr = len(self.group.pulling)
            # list riders from last guy in pulling group to last in follow grp and find some1 to follow
            #print(self.name)
            for i in range(pulling_nr-1, len(self.group.riders)):
                #print(group.riders[i].name + ' being followed by')
                #print('[' + ' '.join([rider.name for rider in group.riders[i].following]) + ']')
                if (not group.riders[i] == self) and (not group.riders[i] in self.following) and (len(group.riders[i].following) == 0):
                    self.follow_target = group.riders[i]
                    # todo - when do we remove some1 frm this list?
                    group.riders[i].following.append(self)
                    break
                # if noone to follow, go pull (todo - except if tired?)
                if i == len(self.group.riders):
                    self.mode = 1
                
            # todo - maybe do a PID sort of method here?
            if len(self.group.pulling) > 0:
                err = self.follow_target.dist - self.dist - self.follow_target.bikelength
                
                if self.ti > 0:
                    self.out = self.kp * (err + (1/self.ti) * self.poserr_sum + self.td * ((err - self.poserr_old)/self.timestep))
                else:
                    self.out = self.kp * (err + self.td * ((err - self.poserr_old)/self.timestep))
                # aim to cut distance in half?
                dDist = err / 2# = (self.speed - self.follow_target.sped) * self.timestep
                self.poserr_old = err
                targetSpd = dDist / self.timestep + self.follow_target.speed
                self.effort = self.p_spd2(targetSpd) / self.ftp
                """
                if follow_dist > 2: 
                    self.effort = 2.5
                elif follow_dist > 0.5:
                    self.effort = 1.5
                else:
                    self.effort = max(0, 1.005 * self.p_spd(self.follow_target.speed) / self.ftp)
                """
                #print(self.effort)
            else:
                self.effort = 0.2
                
        
        # pull mode
        elif self.mode == 1:
            if self not in self.group.pulling:
                self.group.pulling.append(self)
                
            if self == self.group.pulling[0]:
                # TODO - logic (timer) for swapping rider at the front
                if len(self.group.pulling) > 1:
                    self.effort = 1.1
                else:
                    self.effort = 0.8
            else:
                self.effort = 1.01 * self.p_spd(self.group.pulling[0].speed) / self.ftp
                #self.effort = 0.7
        '''
        if self.name == "Pedro":
            if self.gradient < -2:
                self.effort = 0.2
            elif self.gradient > 9:
                if self.sprint > 10:
                    self.effort = 2
                else:
                    self.effort = 1
            else:
                self.effort = 0.9
        else:
            self.effort = 1
        '''

    def update(self):
        self.gradient = self.course.gradients[int(self.dist)]
        
        #limit effort
        self.effort = max(0, min(5, self.effort))
        
        if self.sprint <= 0.1:
            self.sprint = 0
        if self.sprint <= 5:
            self.effort = min(self.effort, 1)
            
        if self.resistance <= 0.1:
            self.resistance = 0
        if self.resistance <= 5:   
            self.effort = min(self.effort, 0.4)
        
                
        #resistance_drain = self.timestep * (-0.1 + 0.128 * self.effort)
        resistance_drain = self.timestep * (0.035 - 0.095 * math.exp(-2*max(0,self.effort)))
        self.resistance -= resistance_drain
        self.resistance = min(self.resistance, 100)
        self.resistance = max(self.resistance, 0)
        
        sprint_drain = self.timestep * (-1.2 + 0.45 * self.effort + 0.75 * self.effort**2)
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
        
        if len(self.group.pulling) > 0:
            olddist = self.group.pulling[-1].dist - self.dist
        
        dist = self.speed * self.timestep
        #todo - how to solve this? glue followers to backwheel? or regulate power better
        if self.mode == 3:
            self.dist = min(self.dist + dist, self.follow_target.dist - self.follow_target.bikelength)
        else:
            self.dist += dist
            
        if False and self.name == 'Pedro' and len(self.group.pulling) > 0:
            print(olddist)
            print(self.group.pulling[-1].dist - self.dist)

    def update_cda(self):
        if self.group.riders[0] == self:
            if self.gradient < -8:
                self.CdAfactor = 0.9
            else:
                self.CdAfactor = 1
            return
            
        idx = [x for x in range(len(self.group.riders)) if self.group.riders[x] == self][0]
        #print(idx)
        riderinfront = self.group.riders[idx-1]
        followdist = riderinfront.dist - self.dist
        #print(dist)
        #followdist = self.follow_target.dist - self.dist
        if followdist < riderinfront.bikelength:
           self.CdAfactor = 0.5
        elif followdist < 8:
            self.CdAfactor = 1 - (1 / (followdist))
        else:
            self.CdAfactor = 1
        #print(self.follow_target.dist, self.dist)
        #print(self.CdAfactor)
            


    def visual_res(self, segments):
        val = max(0, int(self.resistance * segments / 100))
        return 'res: [' + val*'=' + (segments-val)*'-' + '] ' + str(round(self.resistance,1)) + '%'
    
    def visual_spr(self, segments):
        val = max(0, int(self.sprint * segments / 100))
        return 'spr: [' + val*'x' + (segments-val)*'-' + '] ' + str(round(self.sprint,1)) + '%'

    def visual_pos(self, segments):
        val = int(self.dist * segments / len(self.course.gradients))
        return 'pos: [' + (val)*'-' + '|' + (segments-val-1)*'-' + '] ' + str(round(self.dist/1000,3)) + '/' + str(int(len(self.course.gradients)/1000)) + 'km'
        
class Course:
    def __init__(self, gradients):
        self.gradients = [g for g in gradients for i in range(1000)]
        for i in range(1, len(self.gradients)-100):
            if self.gradients[i-1] != self.gradients[i]:
                diff = int(self.gradients[i] - self.gradients[i-1])
                if abs(diff) > 1:
                    for j in range(abs(diff)):
                        for k in range(10):
                            self.gradients[i+10*j+k] = int(self.gradients[i-1] + j * diff / abs(diff))
                    i += 10*diff
            
def p_spd(Cd, A, rho, Vhw, mass, Crr, gradient, power, spd):
    a = 0.5 * Cd * A * rho
    b = Vhw * Cd * A * rho
    c = 9.8 * mass * (gradient/100 + Crr * math.cos(gradient/100)) + 0.5 * Cd * A * rho * Vhw**2
    return (a * spd**3) + (b * spd**2) + (c * spd) - power


    
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
    #assert y >= (lower := f(a)), f"y is smaller than the lower bound. {y} < {lower}"
    #assert y <= (upper := f(b)), f"y is larger than the upper bound. {y} > {upper}"
    lower = f(a)
    upper = f(b)
    
    
    assert y >= lower, f"y is smaller than the lower bound. {y} < {lower}"
    assert y <= upper, f"y is larger than the upper bound. {y} > {upper}"

    stagnant = 0
    #print('new')
    while 1:
        #print('{:.2f} {:.2f}'.format(upper, lower))
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

'''
def f1(x):
    return x**2 - 2   
print(illinois_algorithm(f1, 0, 2, -2, margin=0.01))
'''

script_path = os.path.dirname(__file__)
json_path = os.path.join(script_path, 'json')
cyclists_path = os.path.join(json_path, 'cyclists')

fpath = os.path.join(cyclists_path, 'test.json')
print(fpath + '\n')

course = Course([0,0,0,0,2,0,-1,0,1,1,0,0,12,12,-6,-6,-6,-6,0,0,0,0,0,0,0,7,7,7,8,8,10,8,8,9,9,12,9,9,10,14])
course = Course([12,-6, -6, 0, 0, 10])
riders = []
for root, dirs, files in os.walk(cyclists_path, topdown=False):
    for filename in files:
        #print('loaded ' + filename)
        f = open(os.path.join(root, filename))
        d = json.load(f)
        riders.append(Rider(d, course))

riders[0].mode == 1

group = RiderGroup(course, riders)

#riders[0].A = 0.5
print('-----\nSpeed at FTP\n-----')
print('flat:')
crs = Course([0,0,0,0,0])
for rider in riders:
    rider.course = crs
    rider.mode = 1
    # to reach steady state, because we take accel into account
    for i in range(50):
        rider.update()
    print(rider.stats_str())
    rider.gradident = 0
    print('{:.1f} km/h'.format(3.6*rider.spd_p(rider.ftp)))
    print('{:.1f} km/h'.format(3.6*rider.spd_p2(rider.ftp)))

print('\n8% gradient')
crs = Course([8,8,8,8,8])
for rider in riders:
    rider.course = crs
    # to reach steady state, because we take accel into account
    for i in range(50):
        rider.update()
    print(rider.stats_str())
    rider.gradient = 8
    print('{:.1f} km/h'.format(3.6*rider.spd_p(rider.ftp)))
    print('{:.1f} km/h'.format(3.6*rider.spd_p2(rider.ftp)))



print('')



timestep = 5
for rider in riders:
    rider.dist = 0
    rider.course = course
    rider.timestep = timestep
    if rider.name == 'Anton':
        rider.mode = 1
    else:
        rider.mode = 0

for i in range(100):
    interval = 1
    if i % interval == 0:
        print('\n-- update at {:.1f} min --'.format(i*timestep/60))
    [rider.strategy() for rider in group.riders]
    for rider in group.riders:
        #print(rider.fullname)
        rider.update()
        if i % interval == 0:
            print('{} {:.0f}% {:.0f}W ({:.0f}%) {:.1f}km/h {:.1f}'.format(rider.name, rider.gradient, rider.power, rider.effort*100, rider.speed*3.6, rider.CdAfactor))
            print(rider.visual_res(20))
            print(rider.visual_spr(20))
            print(rider.visual_pos(20))
            
    for rider in group.riders:
        rider.update_cda()
    
    # sort riders by distance
    group.riders = sorted(group.riders, key=lambda rider: rider.dist, reverse=True)
    #print(round(riders[0].dist - riders[1].dist, 2))
    #print(''.join([rider.name for rider in riders]))
    
riders[0].resistance = 50
riders[0].sprint = 100
riders[0].dist = 0
riders[0].timestep = 1
print('')
for i in range(20):
    riders[0].update()
    print(riders[0].effort)
    print(riders[0].visual_res(20))
    print(riders[0].visual_spr(20))
     
'''
riders[0].gradient = 0
riders[0].speed = 0

print(riders[0].stats_str())
print(riders[0].p_spd2(10))
riders[0].speed = 5
print(riders[0].p_spd2(10))
riders[0].speed = 10
print(riders[0].p_spd2(10))
        
print(riders[0].p_spd(10))
'''