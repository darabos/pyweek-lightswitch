import ctypes
import zipfile

import pictures_3

all_the_words = pictures_3.words

OUTPUT = 'pictures_vbuf.zip'


def GenerateVertexBuffer(data):
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
    while stroke[-1].time == None:
      del stroke[-1]
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

  n = len(vertices)
  v_array = (ctypes.c_float * (n * 4))()
  for i, v in enumerate(vertices):
    v_array[i * 4 + 0] = v[0]
    v_array[i * 4 + 1] = v[1]
    v_array[i * 4 + 2] = v[2]
    v_array[i * 4 + 3] = v[3]
  return v_array



output = zipfile.ZipFile(OUTPUT, 'a', zipfile.ZIP_DEFLATED)

for word, data in all_the_words.iteritems():
  print word
  vbuf = GenerateVertexBuffer(data)
  output.writestr(word, vbuf)

output.close()
