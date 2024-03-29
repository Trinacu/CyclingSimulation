
import os
import pygame as pg
from .states import game

class Control():
    def __init__(self, size):
        pg.mixer.pre_init(44100, -16, 1, 512)
        pg.init()
        self.monitor = (pg.display.Info().current_w, pg.display.Info().current_h)
        pg.display.set_caption("Boom")
        self.screensize = (int(size[0]), int(size[1]))

        os.environ["SDL_VIDEO_CENTERED"] = "True"
        self.screen = pg.display.set_mode(self.screensize)

        self.screen_rect = self.screen.get_rect()
        self.clock = pg.time.Clock()
        self.fps = 60
        self.keys = pg.key.get_pressed()
        self.done = False
        self.state_dict = {
            'GAME'     : game.Game(self.screen_rect)
            #'OVERLAY' : overlay.Overlay(self.screen_rect),
        }

        self.state_name = "GAME"
        self.state = self.state_dict[self.state_name]


    def event_loop(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.quit = True
            elif event.type in (pg.KEYDOWN,pg.KEYUP):
                self.keys = pg.key.get_pressed()
            self.state.get_event(event, self.keys)

    def change_state(self):
        if self.state.done:
            self.state.cleanup()
            self.state_name = self.state.next
            self.state.done = False
            self.state = self.state_dict[self.state_name]
            self.state.entry()


    def run(self):
        while not self.done:
            if self.state.quit:
                self.done = True
            now = pg.time.get_ticks()
            self.event_loop()
            self.change_state()
            self.state.update(now, self.keys)
            self.state.render(self.screen)
            pg.display.update()
            self.clock.tick(self.fps)


