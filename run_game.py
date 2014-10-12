import ctypes
import contextlib
import math
import os
import picture_render
#import picture_render_simple as picture_render
import pygame
import random
import string
import sys
from OpenGL.GL import *

WIDTH, HEIGHT = 800, 600

SOUNDS = {
  'accepted': 'sounds/cor.ogg',
  'rejected': 'sounds/wrong.ogg',
}

MUSIC = ['sounds/lightswitch.ogg']


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


class ContainsRule(object):
  def __init__(self, letter):
    self.letter = letter
  def accepts(self, word):
    return self.letter in word
  def hint(self):
    return 'Hint: Guess my favorite letter!'


class EndsWithRule(object):
  def __init__(self, letters):
    self.letters = letters
  def accepts(self, word):
    return word[-1] in self.letters
  def hint(self):
    return 'Hint: The word ends with you!'


class StartsWithRule(object):
  def __init__(self, letters):
    self.letters = letters
  def accepts(self, word):
    return word[0] in self.letters
  def hint(self):
    return 'Hint: It all starts with the word itself...'


class LengthRule(object):
  def __init__(self, length):
    self.length = length
  def accepts(self, word):
    return len(word) == self.length
  def hint(self):
    return 'Hint: Not too long, not too short...'


class MusicalRule(object):
  def accepts(self, word):
    for x in 'do re mi fa sol la ti'.split():
      if x in word:
        return True
    return False
  def hint(self):
    return 'Hint: You hear sounds of music from the room...'


class DoubleLetterRule(object):
  def accepts(self, word):
    last = None
    for c in word:
      if c == last:
        return True
      last = c
    return False
  def hint(self):
    return 'Hint: Double, Double, Toil and Trouble...'


letters = string.lowercase.replace('x', '')
vowels = 'aeiou'
consonants = [l for l in letters if l not in vowels]
next_rules = []
def RandomRule():
  if not next_rules:
    next_rules.append(MusicalRule())
    next_rules.append(DoubleLetterRule())
    next_rules.append(EndsWithRule(consonants))
    next_rules.append(EndsWithRule(vowels))
    for i in range(3):
      next_rules.append(StartsWithRule(random.choice(letters)))
    for i in range(6):
      next_rules.append(ContainsRule(random.choice(letters)))
    for i in range(2):
      next_rules.append(LengthRule(random.randint(3, 6)))
    random.shuffle(next_rules)
  rule = next_rules.pop()
  print rule.hint()
  return rule


class Game(object):

  def __init__(self):
    self.word = ''
    self.reset()

  def reset(self):
    self.rule = RandomRule()
    self.words = []
    self.successes = 0
    self.victory = False
    self.victory_pictures = {}

  def Loop(self):
    pygame.init()
    pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
    pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 4)
    pygame.display.set_caption('Lightswitch')
    pygame.display.set_mode((WIDTH, HEIGHT), pygame.OPENGL | pygame.DOUBLEBUF | pygame.HWSURFACE)
    glViewport(0, 0, WIDTH, HEIGHT)
    glMatrixMode(GL_PROJECTION)
    glScale(2.0 / WIDTH, 2.0 / HEIGHT, 1.0)
    glMatrixMode(GL_MODELVIEW)
    clock = pygame.time.Clock()
    pygame.font.init()
    self.font = Font(40)
    picture_render.Shaders.Setup()
    self.time = 0
    self.pictures = []
    self.background = 0
    self.wpl = picture_render.WordPictureLoader()
    for k, v in SOUNDS.items():
      SOUNDS[k] = pygame.mixer.Sound(v)

    while True:
      dt = clock.tick(60)
      self.time += dt / 1000.0
      if not pygame.mixer.music.get_busy():
        m = MUSIC.pop()
        pygame.mixer.music.load(m)
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play()
        MUSIC.insert(0, m)
      for e in pygame.event.get():
        if e.type == pygame.KEYDOWN:
          self.HandleKey(e.key)
        if e.type == pygame.QUIT or e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
          pygame.quit()
          sys.exit(0)

      if self.victory:
        self.background += 0.05
        if self.background > 1:
          self.background = 1
      else:
        self.background -= 0.05
        if self.background < 0:
          self.background = 0
      glClearColor(self.background, self.background, self.background, 1)
      glClear(GL_COLOR_BUFFER_BIT)
      glLoadIdentity()

      with Transform():
        glTranslate(0, 100, 0)
        glScale(300, 300, 1.0)
        for p in self.pictures[:]:
          with Transform():
            t = self.time - p.start
            s = 1.0 + t * 0.1
            glScale(s, s, 1.0)
            glTranslate(-0.5, -0.5, 0)
            if t < 3.5:
              p.RenderSetup(p.primary, p.secondary, WIDTH, HEIGHT)
              if p.accepted:
                p.Render(t, t - 2.5)
              else:
                p.Render(t, t - 1.2)
            else:
              self.pictures.remove(p)

        if self.victory:
          for p in self.victory_pictures.values():
            with Transform():
              glTranslate(-0.5 + p.x, -0.5 + p.y, 0)
              glScale(p.scale, p.scale, 1.0)
              p.RenderSetup((0, 0, 0, 1), (0, 0, 0, 1), WIDTH, HEIGHT)
              p.Render(2)

      self.font.Render(0, -200, self.word.upper())
      pygame.display.flip()

  def HandleKey(self, key):
    if self.victory:
      self.reset()
      return
    if ord('a') <= key <= ord('z'):
      self.word += chr(key)
    elif key == pygame.K_BACKSPACE:
      self.word = self.word[:-1]
    elif key == pygame.K_RETURN and self.word:
      p = self.wpl.WordPictureForWord(self.word)
      p.start = self.time
      if self.rule.accepts(self.word):
        SOUNDS['accepted'].play()
        p.accepted = True
        p.primary = 0.3, 2, 0.3, 1
        p.secondary = 1, 1, 1, 1
        if self.word not in self.victory_pictures:
          self.successes += 1
          self.victory_pictures[self.word] = p
      else:
        SOUNDS['rejected'].play()
        p.accepted = False
        p.primary = 2, 0.3, 0.3, 1
        p.secondary = 1, 1, 1, 1
        self.successes = 0
      self.pictures.append(p)

      if self.successes == 5:
        self.victory = True
        for p in self.victory_pictures.values():
          p.scale = random.uniform(0.3, 0.5)
          p.x = random.uniform(-0.8, 0.8)
          p.y = random.uniform(-0.5, 0.5)

      self.words.append(self.word)
      self.word = ''


if __name__ == '__main__':
  game = Game()
  game.Loop()
