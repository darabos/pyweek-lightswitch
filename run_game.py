import ctypes
import contextlib
import math
import os
import picture_render
import pygame
import random
import sys
from OpenGL.GL import *

WIDTH, HEIGHT = 800, 600


def Quad(width, height):
  glBegin(GL_TRIANGLE_STRIP)
  glTexCoord2d(0, 0)
  glVertex2d(-0.5 * width, -0.5 * height)
  glTexCoord2d(1, 0)
  glVertex2d(0.5 * width, -0.5 * height)
  glTexCoord2d(0, 1)
  glVertex2d(-0.5 * width, 0.5 * height)
  glTexCoord2d(1, 1)
  glVertex2d(0.5 * width, 0.5 * height)
  glEnd()


@contextlib.contextmanager
def Buffer(buf):
  glBindFramebuffer(GL_FRAMEBUFFER, buf)
  glViewport(0, 0, WIDTH * 2, HEIGHT * 2)
  yield
  glBindFramebuffer(GL_FRAMEBUFFER, 0)
  glViewport(0, 0, WWIDTH, WHEIGHT)


@contextlib.contextmanager
def Texture(tex):
  glEnable(GL_TEXTURE_2D)
  glBindTexture(GL_TEXTURE_2D, tex)
  yield
  glDisable(GL_TEXTURE_2D)


@contextlib.contextmanager
def Blending(src, dst):
  glEnable(GL_BLEND)
  glBlendFunc(src, dst)
  yield
  glDisable(GL_BLEND)


@contextlib.contextmanager
def Transform():
  glPushMatrix()
  yield
  glPopMatrix()


@contextlib.contextmanager
def Color(*rgba):
  glColor(*rgba)
  yield
  glColor(1, 1, 1, 1)


class Font(object):

  def __init__(self, size):
    self.font = pygame.font.Font('OpenSans-ExtraBold.ttf', size)
    self.cache = {}

  def Render(self, x, y, text):
    if text not in self.cache:
      surface = self.font.render(text, True, (255, 255, 255), (0, 0, 0))
      data = pygame.image.tostring(surface, 'RGBA', 1)
      tex = glGenTextures(1)
      width = surface.get_width()
      height = surface.get_height()
      glBindTexture(GL_TEXTURE_2D, tex)
      glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
      glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
      glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP)
      glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP)
      glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
      if len(self.cache) > 200:
        self.DropCache()
      self.cache[text] = width, height, tex
    width, height, tex = self.cache[text]
    glUseProgram(0)
    with Transform():
      glTranslate(x, y, 0)
      with Texture(tex):
        with Blending(GL_ZERO, GL_ONE_MINUS_SRC_COLOR):
          Quad(width, height)
        with Blending(GL_ONE, GL_ONE):
          with Color(1, 1, 1, 1):
            Quad(width, height)

  def DropCache(self):
    for w, h, tex in self.cache.values():
      glDeleteTextures(tex)
    self.cache = {}


class Game(object):

  def __init__(self):
    self.word = ''

  def Loop(self):
    pygame.init()
    pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
    pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 4)
    pygame.display.set_caption('Lightswitch')
    pygame.display.set_mode((WIDTH, HEIGHT), pygame.OPENGL | pygame.DOUBLEBUF | pygame.HWSURFACE)
    glViewport(0, 0, WIDTH, HEIGHT)
    glMatrixMode(GL_PROJECTION)
    glScale(2.0/WIDTH, 2.0/HEIGHT, 1.0)
    glMatrixMode(GL_MODELVIEW)
    clock = pygame.time.Clock()
    pygame.font.init()
    self.font = Font(40)
    picture_render.Shaders.Setup()
    self.time = 0
    self.pictures = []

    while True:
      dt = clock.tick(60)
      self.time += dt / 1000.0
      for e in pygame.event.get():
        if e.type == pygame.KEYDOWN:
          if ord('a') <= e.key <= ord('z'):
            self.word += chr(e.key).upper()
          elif e.key == pygame.K_BACKSPACE:
            self.word = self.word[:-1]
          elif e.key == pygame.K_RETURN:
            p = picture_render.WordPictureForWord(self.word.lower())
            p.start = self.time
            self.pictures.append(p)
            self.word = ''
        if e.type == pygame.QUIT or e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
          pygame.quit()
          sys.exit(0)
      glClear(GL_COLOR_BUFFER_BIT)
      glLoadIdentity()
      with Transform():
        glScale(300, 300, 1.0)
        glTranslate(-0.5, -0.2, 0)
        for p in self.pictures:
          p.RenderSetup()
          p.Render(self.time - p.start)
      self.font.Render(0, -200, self.word)
      pygame.display.flip()


if __name__ == '__main__':
  game = Game()
  game.Loop()
