import ctypes
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

flat varying float line_dist;
flat varying vec2 line_normal;

void main() {
  gl_Position = gl_ModelViewProjectionMatrix * vec4(gl_Vertex.xy, 0, 1);
  time = gl_Vertex.z;
  pressure = gl_Vertex.w;

  vec2 next_vert = (gl_ModelViewProjectionMatrix * vec4(gl_Color.xy, 0, 1)).xy;
  vec2 normal = vec2(next_vert.y - gl_Position.y, gl_Position.x - next_vert.x);
  normal = normalize(normal);
  line_normal = normal;
  line_dist = dot(normal, next_vert);
}""", """
#version 120

varying float time;
varying float pressure;

flat varying float line_dist;
flat varying vec2 line_normal;

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
  vec3 c;
  float actual_pressure = 0;
  if (time > render_time + render_pre_time) {
    c = vec3(0, 0, 0);
  } else if (time > render_time) {
    float a = (time - render_time) / render_pre_time;
    c = mix(vec3(0, 0, 0), tip_color.rgb, a);
  } else if (time > render_time - render_post_time) {
    float a = (render_time - time) / render_post_time;
    c = mix(tip_color.rgb, main_color.rgb, a);
    actual_pressure = pressure * 2 * a;
  } else if (time > unrender_time + unrender_pre_time) {
    c = main_color.rgb;
    actual_pressure = pressure;
  } else if (time > unrender_time) {
    float a = (time - unrender_time) / unrender_pre_time;
    c = mix(vec3(0, 0, 0), main_color.rgb, a);
    actual_pressure = pressure * a;
  } else {
    c = vec3(0, 0, 0);
  }

  gl_FragColor.rgb = c;
  if (actual_pressure < 0.01) {
    gl_FragColor.a = 0;
  } else {
    vec2 coord = vec2(gl_FragCoord.x / viewport_width,
                      gl_FragCoord.y / viewport_height);
    coord.x -= 1;
    coord.y -= 1;
    float dist = abs(dot(coord, line_normal) - line_dist);

    dist = 1 - clamp(dist * 100 - actual_pressure / 10., 0, 1);

    gl_FragColor.a = dist;
  }
}
""")
    self.line_drawing_time = glGetUniformLocation(self.line_drawing_program,
                                                  b'render_time')
    self.line_drawing_untime = glGetUniformLocation(self.line_drawing_program,
                                                    b'unrender_time')

class WordPicture(object):
  def __init__(self, vbuf):
    self.v_array = vbuf
    self.shifted_v_array = vbuf[16:] + ('0' * 16)
    self.n = len(vbuf) / 16

  # Sets up misc. render state for drawing word pictures. Can be
  # called once followed by many Render calls.
  @classmethod
  def RenderSetup(cls, main_color, tip_color, viewport_width, viewport_height):
    glEnable(GL_LINE_SMOOTH)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glLineWidth(10)

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
    l = glGetUniformLocation(prg, b'viewport_width')
    glUniform1i(l, viewport_width / 2)
    l = glGetUniformLocation(prg, b'viewport_height')
    glUniform1i(l, viewport_height / 2)
    glProvokingVertex(GL_FIRST_VERTEX_CONVENTION)

  # Draws into a square (0, 0) to (1, 1), positive x going right on
  # the screen, positive y going up.
  def Render(self, rtime, unrender_time=-10):
    glUniform1f(Shaders.line_drawing_time, rtime)
    glUniform1f(Shaders.line_drawing_untime, unrender_time)
    glEnableClientState(GL_VERTEX_ARRAY)
    glEnableClientState(GL_COLOR_ARRAY)
    glVertexPointer(4, GL_FLOAT, 16, self.v_array)
    glColorPointer(4, GL_FLOAT, 16, self.shifted_v_array)
    glDrawArrays(GL_LINE_STRIP, 0, self.n)
    glDisableClientState(GL_VERTEX_ARRAY)
    glDisableClientState(GL_COLOR_ARRAY)


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
  #w = 'accountant'
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
    word.Render(t, t - 5.0)
    pygame.display.flip()

if __name__ == '__main__':
  main_hack()
