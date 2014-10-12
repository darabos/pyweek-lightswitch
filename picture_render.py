import ctypes
import math
import zipfile
from OpenGL.GL import *


def CompileShader(src, kind, kind_name, name):
  shader = glCreateShader(kind)
  glShaderSource(shader, [src])
  glCompileShader(shader)
  result = glGetShaderiv(shader, GL_COMPILE_STATUS)
  if not result:
    # Super-ugly hack. Remove 'flat' and try again since it isn't
    # really a v120 feature.
    src = src.replace('flat ', '')
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

varying float line_dist;
varying vec2 line_normal;

varying vec2 v1;
varying vec2 v2;

varying float d1;
varying float d2;

void main() {
  gl_Position = gl_ModelViewProjectionMatrix * vec4(gl_Vertex.xy, 0, 1);
  time = gl_Vertex.z;
  pressure = gl_Vertex.w;

  v1 = (gl_ModelViewProjectionMatrix * vec4(gl_Color.xy, 0, 1)).xy;
  v2 = (gl_ModelViewProjectionMatrix * vec4(gl_Color.zw, 0, 1)).xy;
  vec2 p = vec2(v2.x - v1.x, v2.y - v1.y);
  p = normalize(p);
  vec2 normal = vec2(p.y, -p.x);
  normal = normalize(normal);
  line_normal = normal;
  line_dist = dot(normal, v2);
  d1 = dot(p, v1);
  d2 = dot(p, v2);
}""", """
#version 120

varying float time;
varying float pressure;

varying float line_dist;
varying vec2 line_normal;

varying vec2 v1;
varying vec2 v2;

varying float d1;
varying float d2;

uniform float render_time;
uniform float unrender_time;

uniform float render_pre_time;
uniform float render_post_time;
uniform float unrender_pre_time;
uniform vec4 main_color;
uniform vec4 tip_color;

uniform int viewport_width;
uniform int viewport_height;

void main() {
  if (pressure <= 0) {
    discard;
  }

  vec3 c;
  float a_mult = 1.0;
  if (time > render_time + render_pre_time) {
    c = vec3(0, 0, 0);
    discard;
  } else if (time > render_time) {
    float a = (time - render_time) / render_pre_time;
    c = tip_color.rgb;
    a_mult = 1 - a;
  } else if (time > render_time - render_post_time) {
    float a = (render_time - time) / render_post_time;
    c = mix(tip_color.rgb, main_color.rgb, a);
  } else if (time > unrender_time + unrender_pre_time) {
    c = main_color.rgb;
  } else if (time > unrender_time) {
    float a = (time - unrender_time) / unrender_pre_time;
    c = mix(vec3(0, 0, 0), main_color.rgb, a);
  } else {
    c = vec3(0, 0, 0);
    discard;
  }

  gl_FragColor.rgb = c;
  float width = pressure * 0.005;
  vec2 coord = vec2(gl_FragCoord.x / viewport_width - 1,
                    gl_FragCoord.y / viewport_height - 1);

  vec2 p = vec2(-line_normal.y, line_normal.x);
  float pd = dot(p, coord);
  float nd = abs(dot(line_normal, coord) - line_dist);

  if (pd < d1) {
    nd = length(vec2(nd, d1 - pd));
    gl_FragColor.a = 0;
  } else if (pd > d2) {
    nd = length(vec2(nd, pd - d2));
  }

  gl_FragColor.a = a_mult * clamp(1 - (nd - width) * 350, 0, 1);
}
""")
    self.line_drawing_time = glGetUniformLocation(self.line_drawing_program,
                                                  b'render_time')
    self.line_drawing_untime = glGetUniformLocation(self.line_drawing_program,
                                                    b'unrender_time')

class WordPicture(object):
  def __init__(self, vbuf):
    n = len(vbuf) / 16
    #n = 150
    self.lines = lines = n - 1
    points = (ctypes.c_float * (4 * n)).from_buffer_copy(vbuf)

    self.vbuf = vbuf = (ctypes.c_float * (4 * 2 * lines))()
    self.cbuf = cbuf = (ctypes.c_float * (4 * 2 * lines))()

    for i in xrange(lines):
      v1_x = points[4 * i + 0]
      v1_y = points[4 * i + 1]
      v1_time = points[4 * i + 2]
      v1_pressure = points[4 * i + 3]
      v2_x = points[4 * i + 4]
      v2_y = points[4 * i + 5]
      v2_time = points[4 * i + 6]
      v2_pressure = points[4 * i + 7]

      n_x = v2_x - v1_x
      n_y = v2_y - v1_y
      d = math.hypot(n_x, n_y)
      if d <= 0:
        d = 0.005
      else:
        d = 0.005 / d

      vbuf[8 * i + 0] = v1_x - d * n_x
      vbuf[8 * i + 1] = v1_y - d * n_y
      vbuf[8 * i + 2] = v1_time
      vbuf[8 * i + 3] = v1_pressure
      vbuf[8 * i + 4] = v2_x + d * n_x
      vbuf[8 * i + 5] = v2_y + d * n_y
      vbuf[8 * i + 6] = v2_time
      vbuf[8 * i + 7] = v2_pressure

      # Width in view space: pressure * 0.01 / 300. -ish

      cbuf[8 * i + 0] = cbuf[8 * i + 4] = v1_x
      cbuf[8 * i + 1] = cbuf[8 * i + 5] = v1_y
      cbuf[8 * i + 2] = cbuf[8 * i + 6] = v2_x
      cbuf[8 * i + 3] = cbuf[8 * i + 7] = v2_y

      #print 'v%i: %r' % (i, ['%6.4f' % x for x in vbuf[8 * i + 0 : 8 * i + 8]])
      #print 'c%i: %r' % (i, ['%6.4f' % x for x in cbuf[8 * i + 0 : 8 * i + 8]])

  # Sets up misc. render state for drawing word pictures. Can be
  # called once followed by many Render calls.
  @classmethod
  def RenderSetup(cls, main_color, tip_color, viewport_width, viewport_height):
    #glEnable(GL_LINE_SMOOTH)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glLineWidth(6)

    prg = Shaders.line_drawing_program
    glUseProgram(prg)
    l = glGetUniformLocation(prg, b'render_pre_time')
    glUniform1f(l, 0.1)
    l = glGetUniformLocation(prg, b'render_post_time')
    glUniform1f(l, 0.2)
    l = glGetUniformLocation(prg, b'unrender_pre_time')
    glUniform1f(l, 0.8)
    l = glGetUniformLocation(prg, b'main_color')
    glUniform4f(l, *main_color)
    l = glGetUniformLocation(prg, b'tip_color')
    glUniform4f(l, *tip_color)
    l = glGetUniformLocation(prg, b'viewport_width')
    glUniform1i(l, viewport_width / 2)
    l = glGetUniformLocation(prg, b'viewport_height')
    glUniform1i(l, viewport_height / 2)

  # Draws into a square (0, 0) to (1, 1), positive x going right on
  # the screen, positive y going up.
  def Render(self, rtime, unrender_time=-10):
    glUniform1f(Shaders.line_drawing_time, rtime)
    glUniform1f(Shaders.line_drawing_untime, unrender_time)
    if 1:
      glEnableClientState(GL_VERTEX_ARRAY)
      glEnableClientState(GL_COLOR_ARRAY)
      glVertexPointer(4, GL_FLOAT, 16, self.vbuf)
      glColorPointer(4, GL_FLOAT, 16, self.cbuf)
      glDrawArrays(GL_LINES, 0, 2 * self.lines)
      glDisableClientState(GL_VERTEX_ARRAY)
      glDisableClientState(GL_COLOR_ARRAY)
    else:
      glBegin(GL_LINES)

      glColor(0, 0, 0, 0.5)
      # d = (0, 1) -> (0, 0.005)
      #glVertex(0, 0, 0, 0.01)
      #glVertex(0, 0.5, 0.5, 1)
      glVertex(0, -0.005, 0, 0.01)
      glVertex(0,  0.505, 0.5, 1)

      glColor(0, 0.5, 1.0, 0.5)
      # d = (1, 0) -> (0.005, 0)
      #glVertex(0, 0.5, 0.5, 1)
      #glVertex(1.0, 0.5, 1.0, 0.01)
      glVertex(-0.005, 0.5, 0.5, 1)
      glVertex( 1.005, 0.5, 1.0, 0.01)

      glEnd()


class WordPictureLoader(object):
  def __init__(self):
    self.source = zipfile.ZipFile('pictures_vbuf.zip', 'r')
    self.all_words = self.source.namelist()

  def WordPictureForWord(self, word):
    if word not in self.all_words:
      word = random.choice(self.all_words)
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
  w = 'ox'
  word = wpl.WordPictureForWord(w)
  print w

  glViewport(0, 0, 600, 600)

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
    word.RenderSetup((1, 1, 1, 1), (2.0, 0.3, 0.3, 1.0), 600, 600)
    word.Render(t, -5) # t - 5.0)
    pygame.display.flip()

if __name__ == '__main__':
  main_hack()
