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
    WordPicture.main_color = main_color
    WordPicture.tip_color = tip_color

  def Render(self, rtime):
    picture = pictures.words[self.word]
    max_time = float(picture[-1][-1].time)
    glColor(*WordPicture.main_color)
    erasing = WordPicture.tip_color == (0, 0, 0, 0)
    for strip in picture:
      if len(strip) < 2: continue
      if erasing:
        strip = list(reversed(strip))
      oop = strip[0]
      op = strip[1]
      for p in strip[2:]:
        if erasing and (1 - rtime) > p.time / max_time:
          break
        if not erasing and rtime < p.time / max_time:
          break
        glLineWidth(op.pressure * 0.01)
        glBegin(GL_LINES)
        glVertex2d(oop.x / 500.0, 1 - oop.y / 500.0)
        glVertex2d(p.x / 500.0, 1 - p.y / 500.0)
        glEnd()
        oop = op
        op = p
    glColor(1, 1, 1, 1)


class WordPictureLoader(object):
  def WordPictureForWord(self, word):
    if word not in pictures.words:
      word = random.choice(pictures.words.keys())
    return WordPicture(word)
