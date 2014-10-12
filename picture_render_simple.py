import ctypes
import pictures_light as pictures
import random
from OpenGL.GL import *


class Shaders(object):
  @classmethod
  def Setup(self):
    pass

class WordPicture(object):
  def __init__(self, word):
    self.word = word

  @classmethod
  def RenderSetup(cls, main_color, tip_color, viewport_width, viewport_height):
    pass

  def Render(self, rtime):
    for strip in pictures.words[self.word]:
      if len(strip) < 2: continue
      oop = strip[0]
      op = strip[1]
      for p in strip[2:]:
        glLineWidth(op.pressure * 0.01)
        glBegin(GL_LINES)
        glVertex2d(oop.x / 500.0, 1 - oop.y / 500.0)
        glVertex2d(p.x / 500.0, 1 - p.y / 500.0)
        glEnd()
        oop = op
        op = p



class WordPictureLoader(object):
  def WordPictureForWord(self, word):
    if word not in pictures.words:
      word = random.choice(pictures.words.keys())
    return WordPicture(word)
