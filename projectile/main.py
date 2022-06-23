"""
Main file for projectile motion

Imports:
- Path from pathlib
- numpy (as np)
- pymunk
- pygame
- Label from root includes
- Projectile and Boundary from project's includes
- Camera from project's includes
- Constants from project's includes

Warnings:
- Zoom function is not working correctly. Press <Space> to reset zoom and camera position

Controls:
- W/A/S/D                    : Camera movement. Works like most game out there.
- Space                      : Reset camera position and zoom.
- Backspace                  : Delete a projectile
- C                          : Create a new projectile at mouse position
- Click & Drag on projectile : Select, aim and shoot projectile
- Click on empty space       : Deselect selected projectile

Feature roadmap:
###### Goal to achieve by showcase day
• Fix zoom feature
• Add widgets allowing users to:
    - Create static obstacle of fixed shape and various size at specified locations
      (Square, Rectangle, Triangle (isosceles), Diamond, Trapezoid, Circle, Rhombus)
    - A field to name new obstacle
    ### Maybe
    - In-game setting UI, allowing users to modify:
        + Camera's panning speed
        + Camera's zoom speed
        + Camera's zoom limit
        + Invert x/y axis
        + Change keyboard control
        + Change boundary size (Or remove boundary completely)
        + Change gravity value
        + Invert gravity
        + Change impulse force modifier
    ###
    - Delete obstacles (by name)
    - Move obstacle (by name)
    - Reset game window
    - Hiding widgets
"""
from pathlib import Path
from collections import deque

import numpy as np
import pymunk
from pymunk.pygame_util import *
from pymunk.vec2d import Vec2d
import pygame
from pygame.locals import *
from pyrsistent import s

from includes.label import Label
from includes.button import Button
from includes.entry import Entry
from projectile.includes.sprites import Projectile, Boundary, StaticObstacle
from projectile.includes.camera import Camera
from projectile.includes.selector import ObjectSelector
try:
    from projectile.includes.constants import SIZE, GRAY, RED, FPS, \
        G_HORIZONTAL, G_VERTICAL
except ImportError:
    SIZE = (600, 600)
    WIDTH = SIZE[0]
    HEIGHT = SIZE[1]
    FPS = 60
    G_HORIZONTAL, G_VERTICAL = 0, 900
    GRAY = "#dcdcdc"
    RED = "#ff0000"

#!: This file is a modified version of App from this tutorial
#!: https://pymunk-tutorial.readthedocs.io/en/latest/mouse/mouse.html

class ProjectileMain:
    """Projectile Motion main class. Entry point for menu
    """
    def __init__(self):
        """Initiate the simulation
        """
        pygame.init()
        self.__space = pymunk.Space()
        self.__screen = pygame.display.set_mode(SIZE)
        self.__clock = pygame.time.Clock()
        self.__draw_options = DrawOptions(self.__screen)
        self.__boundary = Boundary(self.__space.static_body, (0, 0), (300, 300))
        self.__projectile = Projectile((100, 100), 25)
        self.__label_font = pygame.font.Font(rf"{Path(__file__).parent}\assets\fonts\times.ttf", 20)
        self.__desc_font = pygame.font.Font(rf"{Path(__file__).parent}\assets\fonts\times.ttf", 20)
        self.__button_font = pygame.font.Font(rf"{Path(__file__).parent}\assets\fonts\times.ttf", 15)
        self.__entry_font = pygame.font.Font(rf"{Path(__file__).parent}\assets\fonts\times.ttf", 20)
        self.__camera = Camera(5, 0.01, 0.01)
        self.__ignore_zone = pygame.Rect(0, 0, 0, 0)
        self.__selected_object = ObjectSelector.Circle.name
        self.__object_queue = deque(ObjectSelector)
        self.__is_menu_visible = True
        self.__is_description_visible = False
        self.__ready_to_step = False
        self.__during_query = False
        self.__show_info = False
        self.__impulse = -1000
        self.__info_frame = 0
        self.__objects = []

        self.__space.gravity = G_HORIZONTAL, G_VERTICAL
        self.__active_shape = None
        self.__pulling = False
        self.__running = True

        for segment in self.__boundary.segments:
            self.__space.add(segment)
        self.__space.add(self.__projectile.body, self.__projectile.shape)

    def init_widgets(self):
        """Initiate widgets
        """
        self.__label_info = Label(self.__screen, self.__label_font, "", "#000000", "#E0E0E0",
                                  'center')
        self.__label_object_name = Label(self.__screen, self.__label_font, f"{self.__selected_object}",
                                         "#FFFFFF", "#393939")
        self.__label_name = Label(self.__screen, self.__desc_font, "Name",
                                  "#FFFFFF", "#393939")
        self.__label_multiplier = Label(self.__screen, self.__desc_font, "Multiplier (Radius)",
                                        "#FFFFFF", "#393939")
        self.__label_position = Label(self.__screen, self.__desc_font, "Position (x, y)",
                                      "#FFFFFF", "#393939")
        self.__btn_up = Button(self.__screen, self.__button_font, "/\\", self.__previous_object)
        self.__btn_down = Button(self.__screen, self.__button_font, "\/", self.__next_object)
        self.__btn_create_object = Button(self.__screen, self.__button_font,
                                          f"Create {self.__selected_object}",
                                          command=self.__create, args=(self.__selected_object,))
        self.__btn_remove_object = Button(self.__screen, self.__button_font,
                                          "Remove Object By Name",
                                          command=self.__remove)
        self.__btn_menu_visibility = Button(self.__screen, self.__button_font,
                                      "Collapse Menu", command=self.__toggle_menu_visibility,
                                      use_thread=False)
        self.__btn_description_visibility = Button(self.__screen, self.__button_font,
                                                   "Show Descriptions",
                                                   command=self.__toggle_desc_visibility,
                                                   use_thread=False)
        self.__entry_name = Entry(self.__screen, self.__entry_font, "",
                                  border_width=3, clear_on_focus=True)
        self.__entry_multiplier = Entry(self.__screen, self.__entry_font, "",
                                  border_width=3, clear_on_focus=True, regex_filter=r"([0-9])+")
        self.__entry_pos_x = Entry(self.__screen, self.__entry_font, "", bg=GRAY + "00",
                                   border_width=3, regex_filter=r"([0-9])+", clear_on_focus=True)
        self.__entry_pos_y = Entry(self.__screen, self.__entry_font, "", bg=GRAY + "00",
                                   border_width=3, regex_filter=r"([0-9])+", clear_on_focus=True)
        self.__entries = [self.__entry_name, self.__entry_multiplier,
                          self.__entry_pos_x, self.__entry_pos_y]

    def __draw_widgets(self):
        """Draw widgets on screen
        """
        if self.__show_info:
            self.__info_frame += 1
            self.__label_info.place(0, 0, SIZE[0], 75)
            if self.__info_frame >= FPS * 3:
                self.__show_info = False
        if self.__is_menu_visible:
            self.__btn_up.place(400, 60, 200, 25)
            self.__label_object_name.place(400, 85, 200, 50)
            self.__btn_down.place(400, 135, 200, 25)
            self.__btn_create_object.place(400, 305, 200, 50)
            self.__btn_remove_object.place(400, 360, 200, 50)
            self.__btn_description_visibility.place(400, 415, 200, 50)
            self.__entry_name.place(400, 175, 200, 35)
            self.__entry_multiplier.place(400, 215, 200, 35)
            self.__entry_pos_x.place(400, 255, 95, 35)
            self.__entry_pos_y.place(505, 255, 95, 35)
        if self.__is_description_visible:
            self.__label_name.place(200, 175, 200, 35)
            self.__label_position.place(200, 255, 200, 35)
            self.__label_multiplier.place(200, 215, 200, 35)
        self.__btn_menu_visibility.place(400, 470, 200, 50)

    def __update_create_button(self):
        self.__label_object_name.config(text=f"{self.__selected_object}")
        self.__btn_create_object.config(text=f"Create {self.__selected_object}",
                                        command=self.__create, args=(self.__selected_object,))

    def __previous_object(self):
        self.__object_queue.rotate(1)
        self.__selected_object = self.__object_queue[0].name
        self.__update_create_button()

    def __create(self, shape):
        if self.__ready_to_step or self.__during_query:
            self.__show_info = True
            self.__label_info.config(text="Can not create object during space step or query")
        elif not self.__ready_to_step and not self.__during_query:
            if any([not bool(entry.get(False)) for entry in self.__entries]):
                self.__show_info = True
                self.__label_info.config("Please fill all the fields")
                return
            if self.__selected_object == "Circle":
                tmp_object = StaticObstacle(self.__entry_name.get(),
                                            (self.__entry_pos_x.get(as_type=int),
                                            self.__entry_pos_y.get(as_type=int)), shape,
                                            radius=self.__entry_multiplier.get(as_type=int))
            else:
                tmp_object = StaticObstacle(self.__entry_name.get(),
                                            (self.__entry_pos_x.get(as_type=int),
                                            self.__entry_pos_y.get(as_type=int)), shape,
                                            multiplier=self.__entry_multiplier.get(as_type=int))
            self.__objects.append(tmp_object)
            self.__show_info = False
            self.__label_info.config(text="")
            self.__space.add(tmp_object.body, tmp_object.shape)

    def __remove(self):
        if self.__ready_to_step or self.__during_query:
            self.__show_info = True
            self.__label_info.config(text="Can not remove object during space step or query")
        elif not self.__ready_to_step and not self.__during_query:
            if not bool(self.__entry_name.get(False)):
                self.__show_info = True
                self.__label_info.config("Please fill \"name\" field")
                return
            self.__show_info = False
            self.__label_info.config(text="")
            remove_name = self.__entry_name.get()
            for object in self.__objects:
                if object.name == remove_name:
                    self.__space.remove(object.shape, object.body)
                    self.__objects.remove(object)

    def __next_object(self):
        self.__object_queue.rotate(-1)
        self.__selected_object = self.__object_queue[0].name
        self.__update_create_button()
        
    def __toggle_menu_visibility(self):
        if self.__is_menu_visible:
            self.__is_menu_visible = False
            self.__btn_menu_visibility.config("Expand")
        else:
            self.__is_menu_visible = True
            self.__btn_menu_visibility.config("Collapse")
        
    def __toggle_desc_visibility(self):
        if self.__is_description_visible:
            self.__is_description_visible = False
            self.__btn_description_visibility.config("Show Description")
        else:
            self.__is_description_visible = True
            self.__btn_description_visibility.config("Hide Description")

    def __handle_camera_movement(self):
        if any([entry.get_status() for entry in self.__entries]):
            return
        keys = pygame.key.get_pressed()
        self.__camera_transform = self.__camera.compute_translation_and_scaling(keys)
        self.__draw_options.transform = (
            pymunk.Transform.translation(int(SIZE[0] / 2), int(SIZE[1] / 2))
            @ pymunk.Transform.scaling(self.__camera_transform[1])
            @ self.__camera_transform[0]
            @ pymunk.Transform.rotation(self.__camera_transform[2])
            @ pymunk.Transform.translation(-int(SIZE[0] / 2), -int(SIZE[1] / 2))
        )
        
    def __create_projectile(self):
        if any([entry.get_status() for entry in self.__entries]):
            return
        pg_position = from_pygame(
            tuple(np.subtract(
                pygame.mouse.get_pos(),
                (self.__camera.x_offset, self.__camera.y_offset)
            )),
            self.__screen
        )
        self.__projectile = Projectile(pg_position, radius=20)
        self.__space.add(self.__projectile.body, self.__projectile.shape)

    def mainloop(self):
        """Mainloop
        """
        pygame.display.set_caption("Projectile Motion Simulation (PMS)")

        while self.__running:
            if pygame.event.peek(pygame.QUIT):
                pygame.quit()
                self.__running = False
                return 0
            for event in pygame.event.get():
                for entry in self.__entries:
                    entry.handle_entry_events(event)
                if event.type == KEYDOWN:
                    if event.key in (K_ESCAPE,):
                        self.__running = False
                        pygame.quit()
                        return 0
                    elif event.key == K_c:
                        self.__create_projectile()
                    elif event.key == K_BACKSPACE and self.__active_shape != None:
                        self.__space.remove(self.__active_shape, self.__active_shape.body)
                        self.__active_shape = None
                elif event.type == MOUSEBUTTONDOWN:
                    pg_position = from_pygame(
                        tuple(np.subtract(
                            pygame.mouse.get_pos(),
                            (self.__camera.x_offset, self.__camera.y_offset)
                        )),
                        self.__screen
                    )
                    self.__active_shape = None
                    for body in self.__space.bodies:
                        if body.body_type == pymunk.Body.DYNAMIC:
                            shape = list(body.shapes)[0]
                            self.__during_query = True
                            q_info = shape.point_query(pg_position)
                            self.__during_query = False
                            distance = q_info.distance
                            if distance < 0:
                                self.__active_shape = shape
                                self.__pulling = True
                                shape.body.angle = (pg_position - shape.body.position).angle
                elif event.type == MOUSEMOTION:
                    self.__m_position = event.pos
                elif event.type == MOUSEBUTTONUP:
                    if self.__pulling:
                        new_event_pos = from_pygame(
                            tuple(np.subtract(
                                event.pos,
                                (self.__camera.x_offset, self.__camera.y_offset)
                            )),
                            self.__screen
                        )
                        self.__pulling = False
                        active_body = self.__active_shape.body
                        point1 = Vec2d(active_body.position[0], active_body.position[1])
                        point2 = from_pygame(new_event_pos, self.__screen)
                        impulse = self.__impulse * Vec2d((point1 - point2)[0],
                                                (point1 - point2)[1]).rotated(-active_body.angle)
                        active_body.apply_impulse_at_local_point(impulse)

            self.__ready_to_step = True
            self.__screen.fill(GRAY)
            self.__handle_camera_movement()
            self.__space.debug_draw(self.__draw_options)
            self.__draw_widgets()

            if self.__active_shape != None:
                shape = self.__active_shape
                radius = int(shape.radius)
                pg_position = to_pygame(
                    tuple(np.add(
                        shape.body.position,
                        (self.__camera.x_offset, self.__camera.y_offset)
                    )),
                    self.__screen
                )
                pygame.draw.circle(self.__screen, RED, pg_position, radius, 3)
                if self.__pulling:
                    pygame.draw.line(self.__screen, RED, pg_position, self.__m_position, 3)
                    pygame.draw.circle(self.__screen, RED, self.__m_position, radius, 3)

            self.__space.step(0.01)
            self.__ready_to_step = False
            pygame.display.flip()
            self.__clock.tick(FPS)