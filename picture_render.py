import ctypes
from OpenGL.GL import *

import pictures_light


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
  def __init__(self, data):
    self.data = data

    min_x = max_x = data[0][0].x
    min_y = max_y = data[0][0].y
    t_adjust = 0
    last_t = 0
    vertices = []
    for stroke in data:
      if not stroke:
        continue
      t_adjust += stroke[0].time - last_t
      vertices.append([stroke[0].x, stroke[0].y, stroke[0].time - t_adjust, 0])
      for time, x, y, pressure in stroke:
        min_x = min(min_x, x)
        max_x = max(max_x, x)
        min_y = min(min_y, y)
        max_y = max(max_y, y)
        vertices.append([x, y, time - t_adjust, min(1, pressure / 500.)])
      vertices.append([x, y, time - t_adjust, 0])
      last_t = time
    max_t = vertices[-1][2]

    x_scale = 1 / float(max_x - min_x)
    y_scale = 1 / float(max_y - min_y)
    scale = scale = min(x_scale, y_scale)
    if x_scale > y_scale:
      x_offs = (1 - y_scale / x_scale) / 2.
      y_offs = 0
    else:
      x_offs = 0
      y_offs = (1 - x_scale / y_scale) / 2.
    t_scale = 1 / float(max_t)
    for v in vertices:
      v[0] = 0.05 + 0.9 * ((v[0] - min_x) * scale + x_offs)
      v[1] = 0.95 - 0.9 * ((v[1] - min_y) * scale + y_offs)
      v[2] = v[2] * t_scale

    self.n = len(vertices)
    self.v_array = (ctypes.c_float * (self.n * 4))()
    for i, v in enumerate(vertices):
      self.v_array[i * 4 + 0] = v[0]
      self.v_array[i * 4 + 1] = v[1]
      self.v_array[i * 4 + 2] = v[2]
      self.v_array[i * 4 + 3] = v[3]


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


def WordPictureForWord(word):
  data = pictures_light.words.get(word)
  if data is None:
    fallback = random.choice(pictures_light.words.keys())
    data = pictures_light.words[fallback]

  return WordPicture(data)



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

  print pictures_light.words.keys()
  w = random.sample(pictures_light.words.keys(), 1)[0]
  #w = 'accountant'
  word = WordPictureForWord(w)
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
    word.Render(t, t - 1.2)
    pygame.display.flip()

if __name__ == '__main__':
  main_hack()
