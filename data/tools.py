import pygame as pg
import os
import shutil
import random

def clean_files():
    '''remove all pyc files and __pycache__ direcetories in subdirectory'''
    for root, dirs, files in os.walk('.'):
        for dir in dirs:
            if dir == '__pycache__':
                path = os.path.join(root, dir)
                print('removing {}'.format(os.path.abspath(path)))
                shutil.rmtree(path)
        for name in files:
            if name.endswith('.pyc'):
                path = os.path.join(root, name)
                print('removing {}'.format(os.path.abspath(path)))
                os.remove(path)
                
def get_category(path):
    '''get category from image fullpath of card'''
    return os.path.split(os.path.split(path)[0])[1]
    
def get_filename(path):
    return os.path.split(os.path.splitext(path)[0])[1]



class TextRectException:
    def __init__(self, message = None):
        self.message = message
    def __str__(self):
        return self.message

def render_textrect(string, font, rect, text_color, background_color, justification=0):
    """Returns a surface containing the passed text string, reformatted
    to fit within the given rect, word-wrapping as necessary. The text
    will be anti-aliased.

    Takes the following arguments:

    string - the text you wish to render. \n begins a new line.
    font - a Font object
    rect - a rectstyle giving the size of the surface requested.
    text_color - a three-byte tuple of the rgb value of the
                 text color. ex (0, 0, 0) = BLACK
    background_color - a three-byte tuple of the rgb value of the surface.
    justification - 0 (default) left-justified
                    1 horizontally centered
                    2 right-justified

    Returns the following values:

    Success - a surface object with the text rendered onto it.
    Failure - raises a TextRectException if the text won't fit onto the surface.
    """
    
    final_lines = []

    requested_lines = string.splitlines()

    # Create a series of lines that will fit on the provided
    # rectangle.

    for requested_line in requested_lines:
        if font.size(requested_line)[0] > rect.width:
            words = requested_line.split(' ')
            # if any of our words are too long to fit, return.
            for word in words:
                if font.size(word)[0] >= rect.width:
                    raise TextRectException("The word " + word + " is too long to fit in the rect passed.")
            # Start a new line
            accumulated_line = ""
            for word in words:
                test_line = accumulated_line + word + " "
                # Build the line while the words fit.    
                if font.size(test_line)[0] < rect.width:
                    accumulated_line = test_line
                else:
                    final_lines.append(accumulated_line)
                    accumulated_line = word + " "
            final_lines.append(accumulated_line)
        else:
            final_lines.append(requested_line)

    # Let's try to write the text out on the surface.

    surface = pg.Surface(rect.size).convert()
    #surface.fill(0)
    #surface.set_alpha(0)
    surface.fill(background_color)

    accumulated_height = 0
    for line in final_lines:
        if accumulated_height + font.size(line)[1] >= rect.height:
            raise TextRectException("Once word-wrapped, the text string was too tall to fit in the rect.")
        if line != "":
            tempsurface = font.render(line, 1, text_color)
            if justification == 0:
                surface.blit(tempsurface, (0, accumulated_height))
            elif justification == 1:
                surface.blit(tempsurface, ((rect.width - tempsurface.get_width()) / 2, accumulated_height))
            elif justification == 2:
                surface.blit(tempsurface, (rect.width - tempsurface.get_width(), accumulated_height))
            else:
                raise TextRectException("Invalid justification argument: " + str(justification))
        accumulated_height += font.size(line)[1]

    return surface
    

def make_text_surf(message, color, size, bgcolor=None):
    font = pg.font.SysFont(None, size)
    text = font.render(message, True, color)
    rect = text.get_rect()
    if bgcolor:
        surf = pg.Surface((rect[2], rect[3]))
        surf.fill(bgcolor)
        surf.blit(text, (0,0))
        text = surf

    return text    
                    
def make_text(message,color,center,size, fonttype='impact.ttf'):
    font = Font.load(fonttype, size)
    text = font.render(message,True,color)
    rect = text.get_rect(center=center)
    return text,rect
    
                    
class Image:
    path = 'resources/graphics'
    @staticmethod
    def load(filename):
        p = os.path.join(Image.path, filename)
        return pg.image.load(os.path.abspath(p))

class Font:
    path = 'resources/fonts'
    @staticmethod
    def load(filename, size):
        p = os.path.join(Font.path, filename)
        return pg.font.Font(os.path.abspath(p), size)

class Sound:
    def __init__(self, filename):
        self.path = os.path.join('resources', 'sound')
        self.fullpath = os.path.join(self.path, filename)
        pg.mixer.init(frequency=22050, size=-16, channels=2, buffer=128)
        self.sound = pg.mixer.Sound(self.fullpath)
        
class Music:
    def __init__(self, volume):
        self.path = os.path.join('resources', 'music')
        self.setup(volume)

        
    def setup(self, volume):
        self.track_end = pg.USEREVENT+1
        self.tracks = []
        self.track = 0
        for track in os.listdir(self.path):
            self.tracks.append(os.path.join(self.path, track))
        random.shuffle(self.tracks)
        pg.mixer.music.set_volume(volume)
        pg.mixer.music.set_endevent(self.track_end)
        pg.mixer.music.load(self.tracks[0])

class States:
    def __init__(self):        
        self.bogus_rect = pg.Surface([0,0]).get_rect()
        self.screen_rect = self.bogus_rect
        self.bg_color = (25,25,25)
        self.timer = 0.0
        self.quit = False
        self.done = False
        self.rendered = None
        self.next_list = None
        self.last_option = None
        self.gametitle = 'cycling'
        
        self.menu_option_deselect = (50,50,50)
        self.menu_option_select = (255,255,255)
        self.title_color = (50,50,50)
        self.text_basic_color = (255,255,255)
        self.text_hover_color = (100,100,100)
        self.text_color = self.text_basic_color 
        
        
        self.selected_index = 0
        
        self.action = None
        self.keybinding = {
            'up'    : [pg.K_UP, pg.K_w],
            'down'  : [pg.K_DOWN, pg.K_s],
            'right' : [pg.K_RIGHT, pg.K_d],
            'left'  : [pg.K_LEFT, pg.K_a],
            'select': pg.K_RETURN, 
            'pause' : pg.K_p,
            'back'  : pg.K_ESCAPE
        }
        
    def update_controller_dict(self, keyname, event):
        self.controller_dict[keyname] = event.key
        
    def mouse_hover_sound(self):
        for i,opt in enumerate(self.rendered["des"]):
            if opt[1].collidepoint(pg.mouse.get_pos()):
                if self.last_option != opt:
                    self.button_hover.sound.play()
                    self.last_option = opt
                    
    def mouse_menu_click(self, event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            for i,opt in enumerate(self.rendered["des"]):
                if opt[1].collidepoint(pg.mouse.get_pos()):
                    self.selected_index = i
                    self.select_option(i)
                    break
        
    def pre_render_options(self):
        font_deselect = Font.load('impact.ttf', 25)
        font_selected = Font.load('impact.ttf', 40)

        rendered_msg = {"des":[],"sel":[]}
        for option in self.options:
            d_rend = font_deselect.render(option, 1, self.menu_option_deselect)
            d_rect = d_rend.get_rect()
            s_rend = font_selected.render(option, 1, self.menu_option_select)
            s_rect = s_rend.get_rect()
            rendered_msg["des"].append((d_rend,d_rect))
            rendered_msg["sel"].append((s_rend,s_rect))
        self.rendered = rendered_msg
        
    def select_option(self, i):
        '''select menu option via keys or mouse'''
        if i == len(self.next_list):
            self.quit = True
        else:
            self.button_sound.sound.play()
            self.next = self.next_list[i]
            self.done = True
            self.selected_index = 0

    def change_selected_option(self, op=0):
        '''change highlighted menu option'''
        for i,opt in enumerate(self.rendered["des"]):
            if opt[1].collidepoint(pg.mouse.get_pos()):
                self.selected_index = i

        if op:
            self.selected_index += op
            max_ind = len(self.rendered['des'])-1
            if self.selected_index < 0:
                self.selected_index = max_ind
            elif self.selected_index > max_ind:
                self.selected_index = 0
            self.button_hover.sound.play()

class ProgressBar():
    def __init__(self, size, color, bgcolor, value):
        self.size = size
        self.color = color
        self.value = value

        self.surf = pg.Surface(size)
        self.surf.fill(bgcolor)
        pg.draw.rect(self.surf, (0,0,0), (0, 0, size[0], size[1]), 1)
        self.surf_clean = self.surf.copy()

    def update(self, value):
        self.surf = self.surf_clean.copy()
        pg.draw.rect(self.surf, self.color, (1, 1, value * self.size[0]-2, self.size[1]-2), 0)


class RenderWindow():
    def __init__(self, pos, screen_size, length):
        self.pos = pos
        self.screen_size = screen_size
        self.length = length
        self.physical_size = (length, length * screen_size[1]/screen_size[0])

def seconds_to_time(s):
    h = int(s / 3600)
    s = s % 3600
    m = int(s / 60)
    s = s % 60
    s = f"{s:.1f}"

    if len(str(h)) < 2:
        h = '0' + str(h)
    if len(str(m)) < 2:
        m = '0' + str(m)
    if len(str(s)) < 2:
        s = '0' + s
    return f"{h}:{m}:{s}"