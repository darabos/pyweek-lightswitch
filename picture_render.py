import ctypes
import zipfile
from OpenGL.GL import *


def CompileShader(src, kind, kind_name, name):
  shader = glCreateShader(kind)
  glShaderSource(shader, [src])
  glCompileShader(shader)
  result = glGetShaderiv(shader, GL_COMPILE_STATUS)
  if not result:
    print ('Shader compilation failed (%s, %s): %s'
           % (name, kind_name, glGetShaderInfoLog(shader)))
    sys.exit(1)
  return shader


def BuildShader(name, vertex_shader_src, fragment_shader_src):
  program = glCreateProgram()
  for kind, src, kind_name in (
    (GL_VERTEX_SHADER, vertex_shader_src, 'vertex'),
    (GL_FRAGMENT_SHADER, fragment_shader_src, 'fragment')):
    if not src:
      continue
    shader = CompileShader(src, kind, kind_name, name)
    glAttachShader(program, shader)
    glDeleteShader(shader)
  glLinkProgram(program)
  return program


class Shaders(object):
  @classmethod
  def Setup(self):
    self.line_drawing_program = BuildShader('line drawing', """
#version 120

varying float time;
varying float pressure;

void main() {
  gl_Position = gl_ModelViewProjectionMatrix * vec4(gl_Vertex.xy, 0, 1);
  time = gl_Vertex.z;
  pressure = gl_Vertex.w;
}""", """
#version 120

varying float time;
varying float pressure;

uniform float render_time;
uniform float unrender_time;

uniform float render_pre_time;
uniform float render_post_time;
uniform float unrender_pre_time;
uniform vec4 main_color;
uniform vec4 tip_color;

void main() {
  vec4 c;
  if (time > render_time + render_pre_time) {
    c = vec4(0, 0, 0, 0);
  } else if (time > render_time) {
    float a = (time - render_time) / render_pre_time;
    c = mix(vec4(0, 0, 0, 0), tip_color, a);
  } else if (time > render_time - render_post_time) {
    float a = (render_time - time) / render_post_time;
    c = mix(tip_color, vec4(main_color.xyz, pressure), a);
  } else if (time > unrender_time + unrender_pre_time) {
    c = vec4(main_color.xyz, pressure);
  } else if (time > unrender_time) {
    float a = (time - unrender_time) / unrender_pre_time;
    c = mix(vec4(0, 0, 0, 0), vec4(main_color.xyz, pressure), a);
  } else {
    c = vec4(0, 0, 0, 0);
  }

  gl_FragColor = c;
}
""")
    self.line_drawing_time = glGetUniformLocation(self.line_drawing_program,
                                                  b'render_time')
    self.line_drawing_untime = glGetUniformLocation(self.line_drawing_program,
                                                    b'unrender_time')

class WordPicture(object):
  def __init__(self, vbuf):
    self.v_array = vbuf
    self.n = len(vbuf) / 16

  # Sets up misc. render state for drawing word pictures. Can be
  # called once followed by many Render calls.
  @classmethod
  def RenderSetup(cls, main_color, tip_color):
    glEnable(GL_LINE_SMOOTH)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glLineWidth(4)

    prg = Shaders.line_drawing_program
    glUseProgram(prg)
    l = glGetUniformLocation(prg, b'render_pre_time')
    glUniform1f(l, 0.1)
    l = glGetUniformLocation(prg, b'render_post_time')
    glUniform1f(l, 0.2)
    l = glGetUniformLocation(prg, b'unrender_pre_time')
    glUniform1f(l, 0.4)
    l = glGetUniformLocation(prg, b'main_color')
    glUniform4f(l, *main_color)
    l = glGetUniformLocation(prg, b'tip_color')
    glUniform4f(l, *tip_color)

  # Draws into a square (0, 0) to (1, 1), positive x going right on
  # the screen, positive y going up.
  def Render(self, rtime, unrender_time=-10):
    glUniform1f(Shaders.line_drawing_time, rtime)
    glUniform1f(Shaders.line_drawing_untime, unrender_time)
    glEnableClientState(GL_VERTEX_ARRAY)
    glVertexPointer(4, GL_FLOAT, 16, self.v_array)
    glDrawArrays(GL_LINE_STRIP, 0, self.n)
    glDisableClientState(GL_VERTEX_ARRAY)


class WordPictureLoader(object):
  def __init__(self):
    self.source = zipfile.ZipFile('pictures_vbuf.zip', 'r')
    self.all_words = self.source.namelist()

  def WordPictureForWord(self, word):
    if word not in self.all_words:
      word = random.choice()
    raw_data = self.source.read(word)
    return WordPicture(raw_data)



# === cut here ===

import pygame
import random
import sys
import time

import OpenGL
#OpenGL.ERROR_CHECKING = False
#OpenGL.ERROR_LOGGING = False
from OpenGL import GL

def main_hack():
  pygame.init()
  flags = pygame.OPENGL | pygame.DOUBLEBUF | pygame.HWSURFACE
  screen = pygame.display.set_mode((600, 600), flags)

  Shaders.Setup()

  wpl = WordPictureLoader()
  w = random.choice(wpl.all_words)
  #w = 'accountant'
  word = wpl.WordPictureForWord(w)
  print w

  clock = pygame.time.Clock()
  t = 0
  while True:
    dt = clock.tick()
    #print clock
    for e in pygame.event.get():
      if e.type == pygame.QUIT:
        return
      if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
        return

    t += dt / 1000.
    GL.glClear(GL.GL_COLOR_BUFFER_BIT)
    word.RenderSetup((1, 1, 1, 1), (2.0, 0.3, 0.3, 1.0))
    word.Render(t, t - 5.0)
    pygame.display.flip()

if __name__ == '__main__':
  main_hack()
