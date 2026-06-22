import math
import ctypes
from datetime import datetime

import numpy as np

from PySide6.QtWidgets import QSizePolicy
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtCore import Qt, QTimer, QPointF, QElapsedTimer
from PySide6.QtGui import QSurfaceFormat, QMatrix4x4, QVector3D, QColor

from PySide6.QtOpenGL import QOpenGLShaderProgram, QOpenGLBuffer, QOpenGLVertexArrayObject
from OpenGL import GL

from app.theme import Theme
from app.config import config
from app.api.astronomy_api import sky, DEVICE_CONFIGS
from app.widgets.gl_shaders import (
    STAR_VERTEX_SHADER, STAR_FRAGMENT_SHADER,
    SKYBOX_VERTEX_SHADER, SKYBOX_FRAGMENT_SHADER,
    BLOOM_VERTEX_SHADER, BLOOM_FRAGMENT_SHADER,
)

_RAD = math.pi / 180.0


def radec_to_cartesian(ra_hours, dec_deg):
    ra_rad = ra_hours * 15 * _RAD
    dec_rad = dec_deg * _RAD
    x = math.cos(dec_rad) * math.cos(ra_rad)
    y = math.sin(dec_rad)
    z = math.cos(dec_rad) * math.sin(ra_rad)
    return (x, y, z)


def altaz_to_cartesian(alt_deg, az_deg):
    alt_r = alt_deg * _RAD
    az_r = az_deg * _RAD
    r = math.cos(alt_r)
    x = r * math.sin(az_r)
    y = math.sin(alt_r)
    z = r * math.cos(az_r)
    return (x, y, z)


def _star_color_to_rgb(color_hex):
    c = QColor(color_hex)
    return (c.redF(), c.greenF(), c.blueF())


class GLStarChart(QOpenGLWidget):
    def __init__(self, parent=None):
        fmt = QSurfaceFormat()
        fmt.setSamples(4)
        fmt.setSwapInterval(1)
        QSurfaceFormat.setDefaultFormat(fmt)
        super().__init__(parent)

        self.setMinimumSize(500, 400)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)

        self._view_scale = 1.0
        self._view_offset = QPointF(0, 0)
        self._rotation_x = 0.0
        self._rotation_z = 0.0

        self._star_data = []
        self._planet_data = []
        self._sun_pos = None
        self._moon_pos = None
        self._milky_way_alpha = 0.3
        self._light_pollution = 0.5

        self._program = None
        self._skybox_program = None
        self._bloom_program = None
        self._vbo = None
        self._vao = None
        self._skybox_vbo = None
        self._skybox_vao = None
        self._fbo = None
        self._fbo_texture = None
        self._time = 0.0

        self._elapsed = QElapsedTimer()
        self._tick_timer = QTimer()
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start(33)

    def _tick(self):
        self._time += 0.033
        self.update()

    def initializeGL(self):
        GL.glClearColor(0.01, 0.01, 0.03, 1.0)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_PROGRAM_POINT_SIZE)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

        self._program = QOpenGLShaderProgram()
        self._program.addShaderFromSourceCode(QOpenGLShader.Vertex, STAR_VERTEX_SHADER)
        self._program.addShaderFromSourceCode(QOpenGLShader.Fragment, STAR_FRAGMENT_SHADER)
        self._program.link()

        self._skybox_program = QOpenGLShaderProgram()
        self._skybox_program.addShaderFromSourceCode(QOpenGLShader.Vertex, SKYBOX_VERTEX_SHADER)
        self._skybox_program.addShaderFromSourceCode(QOpenGLShader.Fragment, SKYBOX_FRAGMENT_SHADER)
        self._skybox_program.link()

        self._bloom_program = QOpenGLShaderProgram()
        self._bloom_program.addShaderFromSourceCode(QOpenGLShader.Vertex, BLOOM_VERTEX_SHADER)
        self._bloom_program.addShaderFromSourceCode(QOpenGLShader.Fragment, BLOOM_FRAGMENT_SHADER)
        self._bloom_program.link()

        # Skybox cube
        skybox_verts = np.array([
            -1, -1, -1, 1, -1, -1, 1, 1, -1, -1, -1, -1, 1, 1, -1, -1, 1, -1,
            -1, -1, 1, 1, -1, 1, 1, 1, 1, -1, -1, 1, 1, 1, 1, -1, 1, 1,
            -1, 1, -1, 1, 1, -1, 1, 1, 1, -1, 1, -1, 1, 1, 1, -1, 1, 1,
            -1, -1, -1, -1, 1, -1, -1, 1, 1, -1, -1, -1, -1, 1, 1, -1, -1, 1,
            1, -1, -1, 1, 1, -1, 1, 1, 1, 1, -1, -1, 1, 1, 1, 1, -1, 1,
            -1, -1, -1, -1, -1, 1, 1, -1, 1, -1, -1, -1, 1, -1, 1, 1, -1, -1,
        ], dtype=np.float32)

        self._skybox_vao = QOpenGLVertexArrayObject()
        self._skybox_vao.create()
        self._skybox_vao.bind()

        self._skybox_vbo = QOpenGLBuffer()
        self._skybox_vbo.create()
        self._skybox_vbo.bind()
        self._skybox_vbo.allocate(skybox_verts.tobytes(), skybox_verts.nbytes)

        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
        GL.glEnableVertexAttribArray(0)
        self._skybox_vao.release()

        # Fullscreen quad for bloom
        quad_verts = np.array([-1, -1, 1, -1, -1, 1, 1, 1], dtype=np.float32)
        self._quad_vao = QOpenGLVertexArrayObject()
        self._quad_vao.create()
        self._quad_vao.bind()
        self._quad_vbo = QOpenGLBuffer()
        self._quad_vbo.create()
        self._quad_vbo.bind()
        self._quad_vbo.allocate(quad_verts.tobytes(), quad_verts.nbytes)
        GL.glVertexAttribPointer(0, 2, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
        GL.glEnableVertexAttribArray(0)
        self._quad_vao.release()

    def resizeGL(self, w, h):
        GL.glViewport(0, 0, w, h)
        self._create_fbo(w, h)

    def _create_fbo(self, w, h):
        if w < 4 or h < 4:
            return
        if self._fbo:
            GL.glDeleteFramebuffers(1, [self._fbo])
            GL.glDeleteTextures(1, [self._fbo_texture])
        self._fbo = GL.glGenFramebuffers(1)
        self._fbo_texture = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self._fbo_texture)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, w, h, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, None)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self._fbo)
        GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0, GL.GL_TEXTURE_2D, self._fbo_texture, 0)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)

    def refresh(self):
        dt = datetime.now()
        self._star_data = sky.get_bright_stars_altaz(dt, DEVICE_CONFIGS[0]["mag_limit"])
        planets = sky.get_planet_positions(dt)
        self._sun_pos = sky.get_sun_position(dt)
        self._moon_pos = sky.get_moon_position(dt)
        self._planet_data = planets[:5]
        p = config.light_pollution
        lp_map = {"暗空区": 0.1, "乡村": 0.3, "郊区": 0.5, "城市": 0.8}
        self._light_pollution = lp_map.get(p, 0.5)
        self._milky_way_alpha = max(0.0, 1.0 - self._light_pollution * 1.2)
        self.update()

    def paintGL(self):
        w, h = self.width(), self.height()
        if w < 4 or h < 4:
            return

        self._setup_view_matrix(w, h)

        # 1. Render skybox to FBO
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self._fbo)
        GL.glViewport(0, 0, w, h)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        self._render_skybox()

        # 2. Render stars
        self._render_stars()

        # 3. Post-process: bloom
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        self._render_bloom(w, h)

    def _setup_view_matrix(self, w, h):
        aspect = w / h if h > 0 else 1.0
        fov = 90.0 / self._view_scale
        self._proj = QMatrix4x4()
        self._proj.perspective(fov, aspect, 0.1, 100.0)

        self._view = QMatrix4x4()
        self._view.lookAt(
            QVector3D(0, 0, 0),
            QVector3D(0, 0, -1),
            QVector3D(0, 1, 0)
        )
        self._view.rotate(-self._rotation_x + 30, 1, 0, 0)
        self._view.rotate(self._rotation_z, 0, 1, 0)

        ox = -self._view_offset.x() * 0.001
        oy = -self._view_offset.y() * 0.001
        self._view.translate(ox, oy, 0)

    def _render_skybox(self):
        GL.glDepthMask(GL.GL_FALSE)
        self._skybox_program.bind()
        self._skybox_program.setUniformValue("uProjection", self._proj)
        self._skybox_program.setUniformValue("uView", self._view)
        self._skybox_program.setUniformValue("uMilkyWayAlpha", self._milky_way_alpha)

        sun_alt = self._sun_pos["altitude"] if self._sun_pos else -90.0
        self._skybox_program.setUniformValue("uSunAltitude", sun_alt)

        sky_color = QVector3D(0.01, 0.01, 0.03)
        horizon_color = QVector3D(0.08, 0.04, 0.12)
        self._skybox_program.setUniformValue("uSkyColor", sky_color)
        self._skybox_program.setUniformValue("uHorizonColor", horizon_color)

        self._skybox_vao.bind()
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, 36)
        self._skybox_vao.release()
        self._skybox_program.release()
        GL.glDepthMask(GL.GL_TRUE)

    def _render_stars(self):
        if not self._star_data:
            return
        self._program.bind()
        self._program.setUniformValue("uProjection", self._proj)
        self._program.setUniformValue("uView", self._view)
        self._program.setUniformValue("uPointScale", self._view_scale)
        self._program.setUniformValue("uTime", self._time)

        star_positions = []
        star_mags = []
        star_colors = []
        scint_phases = []

        for s in self._star_data:
            if s.get("altitude", -90) < -5:
                continue
            x, y, z = altaz_to_cartesian(s["altitude"], s["azimuth"])
            star_positions.extend([x * 5, y * 5, z * 5])
            star_mags.append(s.get("mag", 5))
            r, g, b = _star_color_to_rgb(s.get("color", "#FFFFFF"))
            star_colors.extend([r, g, b])
            scint_phases.append(hash(s["name"]) % 100 * 0.1)

        verts = np.array(star_positions, dtype=np.float32)
        mags = np.array(star_mags, dtype=np.float32)
        colors = np.array(star_colors, dtype=np.float32)
        phases = np.array(scint_phases, dtype=np.float32)

        n = len(star_mags)
        interleaved = np.zeros(n * 8, dtype=np.float32)
        interleaved[0::8] = verts[0::3]
        interleaved[1::8] = verts[1::3]
        interleaved[2::8] = verts[2::3]
        interleaved[3::8] = mags
        interleaved[4::8] = colors[0::3]
        interleaved[5::8] = colors[1::3]
        interleaved[6::8] = colors[2::3]
        interleaved[7::8] = phases

        vao = QOpenGLVertexArrayObject()
        vao.create()
        vao.bind()
        vbo = QOpenGLBuffer()
        vbo.create()
        vbo.bind()
        vbo.allocate(interleaved.tobytes(), interleaved.nbytes)

        stride = 8 * 4
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, stride, None)
        GL.glEnableVertexAttribArray(0)
        GL.glVertexAttribPointer(1, 1, GL.GL_FLOAT, GL.GL_FALSE, stride, ctypes.c_void_p(12))
        GL.glEnableVertexAttribArray(1)
        GL.glVertexAttribPointer(2, 3, GL.GL_FLOAT, GL.GL_FALSE, stride, ctypes.c_void_p(16))
        GL.glEnableVertexAttribArray(2)
        GL.glVertexAttribPointer(3, 1, GL.GL_FLOAT, GL.GL_FALSE, stride, ctypes.c_void_p(28))
        GL.glEnableVertexAttribArray(3)

        GL.glDrawArrays(GL.GL_POINTS, 0, n)

        vao.release()
        vbo.release()
        self._program.release()

    def _render_bloom(self, w, h):
        GL.glDisable(GL.GL_DEPTH_TEST)
        self._bloom_program.bind()
        self._bloom_program.setUniformValue("uSceneTex", 0)
        self._bloom_program.setUniformValue("uTexelSize", 1.0 / w, 1.0 / h)

        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self._fbo_texture)

        self._quad_vao.bind()
        GL.glDrawArrays(GL.GL_TRIANGLE_STRIP, 0, 4)
        self._quad_vao.release()
        self._bloom_program.release()
        GL.glEnable(GL.GL_DEPTH_TEST)

    def wheelEvent(self, event):
        from PySide6.QtGui import QWheelEvent
        factor = 1.1 if event.angleDelta().y() > 0 else 1 / 1.1
        self._view_scale = max(0.3, min(8.0, self._view_scale * factor))
        self.update()

    def mousePressEvent(self, event):
        self._press_pos = event.position()
        self._pan_start_x = self._rotation_z
        self._pan_start_y = self._rotation_x

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            dx = event.position().x() - self._press_pos.x()
            dy = event.position().y() - self._press_pos.y()
            self._rotation_z = self._pan_start_x + dx * 0.3
            self._rotation_x = self._pan_start_y - dy * 0.3
            self._rotation_x = max(-90, min(90, self._rotation_x))
            self.update()

    def mouseReleaseEvent(self, event):
        pass

    def mouseDoubleClickEvent(self, event):
        self._view_scale = 1.0
        self._rotation_x = 0.0
        self._rotation_z = 0.0
        self._view_offset = QPointF(0, 0)
        self.update()
