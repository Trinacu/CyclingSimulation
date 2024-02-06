import pygame as pg
from ..GUI import button
from .. import tools, data
import os
import random
import json

from ..cyclist import Course, Rider, RiderGroup, PaceLine

import faulthandler

class Game(tools.States):
    def __init__(self, screen_rect):
        faulthandler.enable()
        tools.States.__init__(self)
        self.screen_rect = screen_rect

        # TODO - adjust rider surf size in regard to renderwindow width - make it always be 2m long
        # reserve top and bottom 20% of screen
        self.vert_margins = 0.4*self.screen_rect[3]

        self.course = Course([0, 12, 6, -6, -6, -6, -10, -10, -10, -10, -10, -10, 0, 0, 0, 6, 6, 6, 0, 0, 10, 10])


        riders = Rider.load_riders(data.riders)
        self.course.init_riders(riders)

        self.course_window_margins = (10, 10)
        self.course_window_y_pos = self.screen_rect[3]/2

        w = self.screen_rect[2] - 2*self.course_window_margins[0]
        h = self.screen_rect[3] - self.course_window_y_pos - 2*self.course_window_margins[1]
        self.window_screen_size = (w, h)
        
        self.window_length = 200
        self.render_window = tools.RenderWindow(0, self.window_screen_size, self.window_length)

        colors = [(200,20,20), (20,200,20), (20,20,200), (200,200,20), (200, 20, 200), (200,200,200)]
        color_names = ['red', 'green', 'blue', 'yellow', 'purple', 'grey']

        # scale rider image size according to render_window.length
        for idx, rider in enumerate(self.course.riders):
            rider.surf = pg.Surface((2 * self.render_window.screen_size[0] / self.render_window.length, 5), pg.SRCALPHA)
            rider.surf.fill(colors[idx])
            print(f"{rider.name} {color_names[idx]}")
            rider.display = Rider.RiderDisplay(rider)
            rider.speed = 5

            rider.pulling = rider.name != 'Aleks'
            rider.pulling = idx != len(self.course.riders)-1

        self.timestep = 0.1
        for rider in self.course.riders:
            rider.timestep = self.timestep
        self.frame_count = 0
        self.elapsed_seconds = 0

        self.stopwatch_surf = pg.Surface((10,10))



    def draw_course(self):
        surf = pg.Surface(self.render_window.screen_size)
        surf.fill((255,255,255))
        pt_x = []
        pt_y = []
        y = 0
        # 1 step for every meter of window width
        for i in range(self.render_window.physical_size[0]):
            g = self.course.gradients[int(self.render_window.pos) + i]
            x = i * self.render_window.screen_size[0] / self.render_window.physical_size[0]
            y = y - g * self.render_window.screen_size[1] / self.render_window.physical_size[1] / 100
            pt_x.append(x)
            pt_y.append(y)

        y_offset = - pt_y[int(self.render_window.physical_size[0]/2)] + self.render_window.screen_size[1] / 2
        for i in range(len(pt_y)):
            pt_y[i] += y_offset

        self.course_points = list(zip(pt_x, pt_y))

        pg.draw.lines(surf, (0,0,0), False, self.course_points, 2)
        return surf

        # align so that the course is in the middle (vertically) at the middle of the display

    def get_event(self, event, keys):
        if event.type == pg.QUIT:
            self.quit = True
            
        elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            print('click!')


        elif event.type == pg.KEYDOWN:
            if event.key == self.keybinding['back']:
                self.done = True
                self.next = 'MENU'

        #for item in self.gui_elements:
        #    item.check_event(event)
                

    def update(self, now, keys):
        rotate_period = 20
        update_per_ticks = 2
        # TODO - how do I trigger an event every N seconds (to call rider.update() or ridergroup.update())
        self.frame_count += 1
        if (self.frame_count % update_per_ticks) == 0:
            for group in self.course.rider_groups:
                group.update()
            self.elapsed_seconds += self.timestep
            self.stopwatch_surf = tools.make_text_surf(tools.seconds_to_time(self.elapsed_seconds), (0,0,0), 30, (255,255,255))

            # keep the pulling rider in the middle of the display
            self.render_window.pos = int(self.course.rider_groups[0].riders[0].pos) - self.render_window.physical_size[0]/2


        if (self.frame_count % (rotate_period * update_per_ticks / self.timestep)) == 0:
            if len(self.course.rider_groups[0].paceline.pulling) > 1:
                self.course.rider_groups[0].paceline.rotate()
            print(", ".join([rider.name for rider in self.course.rider_groups[0].paceline.riders]))
            print(", ".join([rider.name for rider in self.course.rider_groups[0].followers.riders]))
            

    def render(self, screen):
        screen.fill(self.bg_color)
        #screen.blit(self.bg, self.bg_rect)
        #for item in self.gui_elements:
        #    item.render(screen)

        screen.blit(self.stopwatch_surf, (0,0))

        screen.blit(self.draw_course(), (self.course_window_margins[0], self.course_window_y_pos + self.course_window_margins[1]))

        # TODO - need to somehow sort the course.rider_groups so that we are displaying this correctly
        # and so splits are working right
        disp_x = self.render_window.screen_size[0] - self.course.riders[0].display.size[0]
        disp_idx = 0
        for group in self.course.rider_groups:
            for idx, rider in enumerate(group.sorted_riders()):
                g = self.course.gradients[int(rider.pos)]
                x = (rider.pos - self.render_window.pos) * self.render_window.screen_size[0] / self.render_window.physical_size[0]
                if (x < 0) or (x > self.render_window.screen_size[0]):
                    continue
                y = self.course_points[int(rider.pos - self.render_window.pos)][1] -  12
                y -= rider.row*4
                screen.blit(pg.transform.rotate(rider.surf, g*45/100), (self.course_window_margins[0] + x, self.course_window_y_pos + self.course_window_margins[1] + y))

                rider.display.update()
                #screen.blit(rider.display.surf, (1.1*rider.display.size[0]*(len(self.course.group.riders)-disp_idx), 0))
                screen.blit(rider.display.surf, (disp_x, 0))
                disp_x -= rider.display.size[0] * 1.1
                disp_idx += 1

                if rider.name == 'Aleks':
                    screen.blit(rider.display.surf, (100, 0))
            disp_x -= 20
            disp_idx += 1

            s = pg.Surface((5,5))
            s.fill((255,0,0))
            screen.blit(s, (self.course_window_margins[0] + self.render_window.screen_size[0]/2, 
                            self.course_window_y_pos + self.course_window_margins[1] + self.render_window.screen_size[1]/2))
            

    def cleanup(self):
        pass#pg.mixer.music.unpause()
        #pg.mixer.music.stop()
        #self.background_music.setup(self.background_music_volume)
        
    def entry(self):
        pass

        #pg.mixer.music.pause()
        #pg.mixer.music.play()
