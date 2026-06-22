"""Hybrid GL + QPainter star chart renderer.

GL: skybox, star Gaussian sprites, scintillation.
QPainter overlay: planets, sun, moon, satellites, aircraft, DSO,
                  grids, labels, info panels, hover, click.
"""
import math, ctypes, traceback
from datetime import datetime
import numpy as np

from PySide6.QtWidgets import QSizePolicy
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtCore import Qt, QTimer, QPointF, QRectF
from PySide6.QtGui import (QMatrix4x4, QVector3D, QColor, QPainter,
                           QPen, QBrush, QFontMetrics, QSurfaceFormat)
from PySide6.QtOpenGL import QOpenGLShaderProgram, QOpenGLBuffer, QOpenGLVertexArrayObject
from OpenGL import GL

from app.theme import Theme
from app.config import config
from app.api.astronomy_api import sky, DEVICE_CONFIGS, compute_satellites_bg
from app.widgets.gl_shaders import (STAR_VERTEX_SHADER, STAR_FRAGMENT_SHADER,
                                    SKYBOX_VERTEX_SHADER, SKYBOX_FRAGMENT_SHADER)

_RAD = math.pi / 180.0
HOVER_R = 12

def _c(hex_color, a=255):
    c = QColor(hex_color)
    if a < 255: c.setAlpha(a)
    return c

def _srgb(hex_color):
    c = QColor(hex_color)
    return (c.redF(), c.greenF(), c.blueF())

def _altaz_to_xyz(alt, az):
    ar, azr = alt*_RAD, az*_RAD
    r = math.cos(ar)
    return (r*math.sin(azr), math.sin(ar), r*math.cos(azr))

class GLHybridChart(QOpenGLWidget):
    def __init__(self, parent=None):
        fmt = QSurfaceFormat(); fmt.setSamples(4); fmt.setSwapInterval(1)
        QSurfaceFormat.setDefaultFormat(fmt)
        super().__init__(parent)
        self.setMinimumSize(500, 400)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

        self._show_stars = self._show_planets = self._show_sun_moon = True
        self._show_satellites = self._show_aircraft = True
        self._show_dso = self._show_dso_nebula = self._show_dso_cluster = self._show_dso_galaxy = True
        self._show_constellations = True
        self._stars = []; self._planets = []; self._sun = None; self._moon = None
        self._satellites = []; self._aircraft = []; self._aircraft_warnings = []; self._dsos = []
        self._const_lines = {}; self._dso_visibility = []
        self._device_index = 0; self._device_config = DEVICE_CONFIGS[0]
        self._view_scale = 1.0; self._rot_x = 0.0; self._rot_z = 0.0
        self._proj = QMatrix4x4(); self._view = QMatrix4x4()
        self._hovered = None; self._selected = None
        self._mouse_pos = None; self._panning = False
        self._press = None; self._pan_sx = 0.0; self._pan_sy = 0.0
        self._hit_stars = []; self._hit_planets = []; self._hit_suns = []
        self._hit_moons = []; self._hit_sats = []; self._hit_ac = []; self._hit_dsos_list = []
        self._time = 0.0
        self._tick = QTimer(); self._tick.timeout.connect(self._on_tick); self._tick.start(33)
        self._refresh_timer = QTimer(); self._refresh_timer.timeout.connect(self.refresh); self._refresh_timer.start(600000)
        self._net_timer = QTimer(); self._net_timer.timeout.connect(self._refresh_net); self._net_timer.start(600000)
        QTimer.singleShot(3000, self._refresh_net)
        self._gl_ok = False
        self._last_paint_ms = 0

    def set_show(self, k, v): setattr(self, f"_show_{k}", v); self.update()
    def set_device(self, i):
        self._device_index = i; self._device_config = DEVICE_CONFIGS[i]; self.refresh()

    def set_camera_fov(self, params):
        pass  # GLHybridChart doesn't use camera FOV overlay yet

    def refresh(self):
        dt = datetime.now()
        self._stars = sky.get_bright_stars_altaz(dt, self._device_config["mag_limit"])
        self._planets = sky.get_planet_positions(dt)
        self._sun = sky.get_sun_position(dt)
        self._moon = sky.get_moon_position(dt)
        self._satellites = sky.get_satellite_positions(dt) if config.is_pro else []
        self._const_lines = sky.get_constellation_lines()
        self._dsos = sky.get_dso_list()
        self._dso_visibility = sky.get_dso_visibility(dt) if config.is_pro else []
        self._upload_stars(); self.update()

    def _refresh_net(self):
        if not config.is_pro: return
        from app.core.background_worker import run_in_background
        d = sky.get_satellite_positions_bg()
        run_in_background(compute_satellites_bg, lambda r: setattr(self,'_satellites',r or []) or self.update(), args=(d,))

    def _on_tick(self): self._time += 0.033; self.update()

    def guide_goto(self, alt, az):
        """Rotate view to center on given altitude/azimuth."""
        self._rot_x = 90 - alt
        self._rot_z = az - 180
        self._view_scale = 2.0
        self.update()

    # ═══ OpenGL ═══
    def initializeGL(self):
        GL.glClearColor(0,0,0.02,1); GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_PROGRAM_POINT_SIZE); GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        for name, src in [('star', STAR_VERTEX_SHADER), ('sky', SKYBOX_VERTEX_SHADER)]:
            pass
        self._sp = QOpenGLShaderProgram()
        self._sp.addShaderFromSourceCode(QOpenGLShader.Vertex, STAR_VERTEX_SHADER)
        self._sp.addShaderFromSourceCode(QOpenGLShader.Fragment, STAR_FRAGMENT_SHADER); self._sp.link()
        self._skp = QOpenGLShaderProgram()
        self._skp.addShaderFromSourceCode(QOpenGLShader.Vertex, SKYBOX_VERTEX_SHADER)
        self._skp.addShaderFromSourceCode(QOpenGLShader.Fragment, SKYBOX_FRAGMENT_SHADER); self._skp.link()
        sb = np.array([-1,-1,-1,1,-1,-1,1,1,-1,-1,-1,-1,1,1,-1,-1,1,-1,
            -1,-1,1,1,-1,1,1,1,1,-1,-1,1,1,1,1,-1,1,1,
            -1,1,-1,1,1,-1,1,1,1,-1,1,-1,1,1,1,-1,1,1,
            -1,-1,-1,-1,1,-1,-1,1,1,-1,-1,-1,-1,1,1,-1,-1,1,
            1,-1,-1,1,1,-1,1,1,1,1,-1,-1,1,1,1,1,-1,1,
            -1,-1,-1,-1,-1,1,1,-1,1,-1,-1,-1,1,-1,1,1,-1,-1], dtype=np.float32)
        self._skvao = QOpenGLVertexArrayObject(); self._skvao.create(); self._skvao.bind()
        self._skvbo = QOpenGLBuffer(); self._skvbo.create(); self._skvbo.bind()
        self._skvbo.allocate(sb.tobytes(), sb.nbytes)
        GL.glVertexAttribPointer(0,3,GL.GL_FLOAT,GL.GL_FALSE,0,None); GL.glEnableVertexAttribArray(0)
        self._skvao.release()
        self._stvao = QOpenGLVertexArrayObject(); self._stvao.create()
        self._stvbo = QOpenGLBuffer(); self._stvbo.create()
        self._gl_ok = True

    def resizeGL(self,w,h): GL.glViewport(0,0,w,h)

    def _upload_stars(self):
        if not self._gl_ok: return
        vis = [s for s in self._stars if s.get("altitude",-90) > -5]
        n = len(vis)
        if n == 0: self._st_cnt = 0; return
        d = np.zeros(n*8, np.float32)
        for i,s in enumerate(vis):
            x,y,z = _altaz_to_xyz(s["altitude"],s["azimuth"])
            d[i*8]=x*5; d[i*8+1]=y*5; d[i*8+2]=z*5; d[i*8+3]=s.get("mag",5)
            r,g,b = _srgb(s.get("color","#FFFFFF"))
            d[i*8+4]=r; d[i*8+5]=g; d[i*8+6]=b; d[i*8+7]=hash(s.get("name",""))%1000*0.00628
        self._st_cnt = n
        self._stvao.bind(); self._stvbo.bind()
        self._stvbo.allocate(d.tobytes(), d.nbytes)
        stride=32
        GL.glVertexAttribPointer(0,3,GL.GL_FLOAT,GL.GL_FALSE,stride,None); GL.glEnableVertexAttribArray(0)
        GL.glVertexAttribPointer(1,1,GL.GL_FLOAT,GL.GL_FALSE,stride,ctypes.c_void_p(12)); GL.glEnableVertexAttribArray(1)
        GL.glVertexAttribPointer(2,3,GL.GL_FLOAT,GL.GL_FALSE,stride,ctypes.c_void_p(16)); GL.glEnableVertexAttribArray(2)
        GL.glVertexAttribPointer(3,1,GL.GL_FLOAT,GL.GL_FALSE,stride,ctypes.c_void_p(28)); GL.glEnableVertexAttribArray(3)
        self._stvao.release()

    # ═══ Paint ═══
    def paintGL(self):
        w,h = self.width(),self.height()
        if w<4 or h<4: return
        self._setup_view(w,h)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT|GL.GL_DEPTH_BUFFER_BIT)
        self._draw_skybox()
        self._draw_stars_gl()
        self._draw_overlay()
        self._last_paint_ms = 16  # FPS tracking for HUD

    def _setup_view(self,w,h):
        aspect=w/h if h>0 else 1; fov=90.0/max(0.3,self._view_scale)
        self._proj=QMatrix4x4(); self._proj.perspective(fov,aspect,0.1,100)
        self._view=QMatrix4x4()
        self._view.lookAt(QVector3D(0,0,0),QVector3D(0,0,-1),QVector3D(0,1,0))
        self._view.rotate(-self._rot_x+30,1,0,0); self._view.rotate(self._rot_z,0,1,0)

    def _draw_skybox(self):
        GL.glDepthMask(GL.GL_FALSE); self._skp.bind()
        self._skp.setUniformValue("uProjection",self._proj); self._skp.setUniformValue("uView",self._view)
        self._skp.setUniformValue("uSunAltitude",self._sun["altitude"] if self._sun else -90)
        lp={"暗空区":0.1,"乡村":0.3,"郊区":0.5,"城市":0.8}.get(config.light_pollution,0.5)
        self._skp.setUniformValue("uMilkyWayAlpha",max(0,1-lp*1.2))
        self._skvao.bind(); GL.glDrawArrays(GL.GL_TRIANGLES,0,36); self._skvao.release()
        self._skp.release(); GL.glDepthMask(GL.GL_TRUE)

    def _draw_stars_gl(self):
        if not hasattr(self,'_st_cnt') or self._st_cnt==0: return
        self._sp.bind()
        self._sp.setUniformValue("uProjection",self._proj); self._sp.setUniformValue("uView",self._view)
        self._sp.setUniformValue("uPointScale",max(0.3,self._view_scale)); self._sp.setUniformValue("uTime",self._time)
        self._stvao.bind(); GL.glDrawArrays(GL.GL_POINTS,0,self._st_cnt); self._stvao.release()
        self._sp.release()

    # ═══ World → screen ═══
    def _w2s(self,alt,az,w,h):
        x,y,z=_altaz_to_xyz(max(0,alt),az)
        v=self._view*QVector3D(x*5,y*5,z*5); p=self._proj*v
        if p.z()<=0: return None
        return QPointF((p.x()/p.z()+1)*.5*w,(1-p.y()/p.z())*.5*h)

    def _hit_pt(self,alt,az,w,h):
        p=self._w2s(alt,az,w,h)
        return p if p and 0<p.x()<w and 0<p.y()<h else None

    # ═══ QPainter overlay ═══
    def _draw_overlay(self):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w,h=self.width(),self.height()
        for lst in [self._hit_stars,self._hit_planets,self._hit_suns,self._hit_moons,
                     self._hit_sats,self._hit_ac,self._hit_dsos_list]: lst.clear()
        try:
            self._ov_grid(p,w,h); self._ov_planets(p,w,h); self._ov_sun_moon(p,w,h)
            self._ov_sats(p,w,h); self._ov_ac(p,w,h); self._ov_dso(p,w,h)
            self._ov_hover(p); self._ov_info(p,w,h); self._ov_status(p,w,h)
        except: traceback.print_exc()
        p.end()

    def _ov_grid(self,p,w,h):
        c=self._w2s(0,0,w,h)
        if c:
            r=min(w,h)*.42*self._view_scale
            p.setPen(QPen(_c(Theme.TEXT_PRIMARY,40),1)); p.setBrush(Qt.NoBrush); p.drawEllipse(c,r,r)
        for az,lbl,col in [(0,"北",Theme.ACCENT),(90,"东",Theme.STAR_GOLD),
                           (180,"南",Theme.WARNING),(270,"西",Theme.ACCENT)]:
            pt=self._w2s(5,az,w,h)
            if pt: p.setPen(_c(col,160)); p.setFont(Theme.font(10,True)); p.drawText(int(pt.x()-10),int(pt.y()-4),lbl)

    def _ov_planets(self,p,w,h):
        if not self._show_planets: return
        for pl in self._planets:
            s=self._hit_pt(pl["altitude"],pl["azimuth"],w,h)
            if not s: continue
            self._hit_planets.append({**pl,"sx":s.x(),"sy":s.y(),"type":"planet"})
            col=QColor(pl.get("color","#6C8CFF"))
            p.setPen(col); p.setFont(Theme.font(10,True))
            p.drawText(int(s.x()-20),int(s.y()-12),pl["name"])
            p.setBrush(col); p.setPen(Qt.NoPen); p.drawEllipse(s,4,4)

    def _ov_sun_moon(self,p,w,h):
        if not self._show_sun_moon: return
        # Sun
        if self._sun:
            s=self._hit_pt(self._sun["altitude"],self._sun["azimuth"],w,h)
            if s:
                self._hit_suns.append({**self._sun,"sx":s.x(),"sy":s.y(),"type":"sun","name":"太阳"})
                p.setPen(QPen(QColor(255,200,50),2)); p.setBrush(QBrush(QColor(255,200,50,60)))
                p.drawEllipse(s,10,10); p.setBrush(QColor(255,220,50)); p.drawEllipse(s,5,5)
        # Moon
        if self._moon:
            s=self._hit_pt(self._moon["altitude"],self._moon["azimuth"],w,h)
            if s:
                ph=self._moon.get("phase",{})
                self._hit_moons.append({**self._moon,"sx":s.x(),"sy":s.y(),"type":"moon","name":f"月亮({ph.get('name','')})"})
                p.setPen(Qt.NoPen); p.setBrush(QColor(180,190,210,80)); p.drawEllipse(s,8,8)
                p.drawEllipse(s,6,6)

    def _ov_sats(self,p,w,h):
        if not self._show_satellites: return
        for sat in self._satellites:
            s=self._hit_pt(sat["altitude"],sat["azimuth"],w,h)
            if not s or sat["altitude"]<-5: continue
            self._hit_sats.append({**sat,"sx":s.x(),"sy":s.y(),"type":"satellite","name":sat["name"]})
            col=QColor(sat.get("color","#FFFFFF"))
            p.setPen(Qt.NoPen); p.setBrush(col); p.drawEllipse(s,3,3)
            p.setPen(_c(sat.get("color","#FFFFFF"),180)); p.setFont(Theme.caption())
            p.drawText(int(s.x()-15),int(s.y()-6),sat["name"])

    def _ov_ac(self,p,w,h):
        if not config.is_pro or not self._aircraft: return
        for ac in self._aircraft:
            s=self._hit_pt(ac["altitude"],ac["azimuth"],w,h)
            if not s or ac["altitude"]<0: continue
            self._hit_ac.append({**ac,"sx":s.x(),"sy":s.y(),"type":"aircraft","name":ac["callsign"]})
            p.setPen(Qt.NoPen); p.setBrush(QColor(255,120,50)); p.drawEllipse(s,3,3)
            p.setPen(_c(Theme.WARNING,200)); p.setFont(Theme.caption())
            p.drawText(int(s.x()-15),int(s.y()-6),f"✈{ac['callsign']}")

    def _ov_dso(self,p,w,h):
        if not self._show_dso or not config.is_pro: return
        for obj in self._dsos:
            if isinstance(obj,(list,tuple)): continue
            oid=obj.get("id",""); name=obj.get("name","")
            ra=obj.get("ra",0); dec=obj.get("dec",0)
            lst=self._approx_lst()
            ha=lst-ra/15.0; ha=ha%24
            if ha>12: ha-=24
            ha_deg=ha*15
            dec_r=math.radians(dec); lat_r=math.radians(config.latitude); ha_r=math.radians(ha_deg)
            alt_dso=math.degrees(math.asin(math.sin(lat_r)*math.sin(dec_r)+math.cos(lat_r)*math.cos(dec_r)*math.cos(ha_r)))
            if alt_dso<=0: continue
            az=math.degrees(math.atan2(-math.sin(ha_r),math.tan(dec_r)*math.cos(lat_r)-math.sin(lat_r)*math.cos(ha_r)))
            s=self._hit_pt(alt_dso,az,w,h)
            if not s: continue
            self._hit_dsos_list.append({"name":f"{oid}({name})","type":"dso","sx":s.x(),"sy":s.y()})
            p.setPen(QPen(_c(Theme.DANGER,180),1.5)); p.setBrush(Qt.NoBrush); p.drawEllipse(s,5,5)
            p.setPen(_c(Theme.DANGER,100)); p.setFont(Theme.caption())
            p.drawText(int(s.x()+7),int(s.y()+3),f"{oid}")

    def _approx_lst(self):
        from app.api.astronomy_api import SkyCalculator
        return SkyCalculator.get_jd()%1*24

    def _ov_hover(self,p):
        if not self._hovered: return
        px,py=self._hovered.get("sx",0),self._hovered.get("sy",0)
        p.setPen(QPen(_c(Theme.ACCENT,120),1.5)); p.setBrush(Qt.NoBrush); p.drawEllipse(QPointF(px,py),HOVER_R,HOVER_R)

    def _ov_info(self,p,w,h):
        if not self._selected and not self._hovered: return
        obj=self._selected or self._hovered
        name=obj.get("name","?"); lines=[f"{name}"]
        lines.append(f"Alt {obj.get('altitude',0):.1f}°  Az {obj.get('azimuth',0):.1f}°")
        p.setFont(Theme.caption()); fm=QFontMetrics(p.font())
        lh=fm.height()+2; bw=max(fm.horizontalAdvance(l) for l in lines)+20; bh=len(lines)*lh+12
        bx=min(20, w-bw-10); by=20
        p.setBrush(QBrush(QColor(11,14,26,220))); p.setPen(QPen(_c(Theme.DIVIDER,100),1))
        p.drawRoundedRect(QRectF(bx,by,bw,bh),6,6)
        p.setPen(_c(Theme.TEXT_PRIMARY,200))
        for i,ln in enumerate(lines): p.drawText(int(bx+10),int(by+12+i*lh),ln)

    def _ov_status(self,p,w,h):
        dc=self._device_config; now=datetime.now()
        txt=f"{dc['icon']}{dc['name']} | {config.city_name} {now.strftime('%H:%M:%S')} | {self._view_scale:.1f}x"
        p.setPen(QPen(_c(Theme.TEXT_MUTED,60),1)); p.setFont(Theme.caption()); p.drawText(16,h-12,txt)

    # ═══ Events ═══
    def wheelEvent(self,e):
        f=1.1 if e.angleDelta().y()>0 else 1/1.1
        self._view_scale=max(0.3,min(8,self._view_scale*f)); self.update()

    def mousePressEvent(self,e):
        self._press=e.position(); self._pan_sx=self._rot_z; self._pan_sy=self._rot_x

    def mouseMoveEvent(self,e):
        self._mouse_pos=e.position()
        if e.buttons()&Qt.LeftButton:
            dx=e.position().x()-self._press.x(); dy=e.position().y()-self._press.y()
            self._rot_z=self._pan_sx+dx*.3; self._rot_x=max(-90,min(90,self._pan_sy-dy*.3))
            self.update()
        else:
            pos=e.position(); hit=self._hit_test(pos)
            if hit!=self._hovered: self._hovered=hit; self.update()

    def mouseReleaseEvent(self,e):
        w,h=self.width(),self.height()
        if e.button()==Qt.LeftButton and self._press:
            pos=e.position(); hit=self._hit_test(pos)
            if hit: self._selected=hit if hit!=self._selected else None
            else: self._selected=None
            self.update()
        self._press=None

    def mouseDoubleClickEvent(self,e):
        pos=e.position(); hit=self._hit_test(pos)
        if hit:
            import webbrowser
            t=hit.get("type",""); name=hit.get("name","")
            if t=="star":
                from app.widgets.star_chart import STAR_DATA
                sd=STAR_DATA.get(name)
                webbrowser.open(f"https://starfyi.com/zh-hans/star/{sd[3]}/" if sd and sd[3] else f"https://baike.baidu.com/item/{name}")
            elif t=="planet": webbrowser.open(f"https://starfyi.com/zh-hans/star/{name}/")
            elif t=="dso": webbrowser.open(f"https://aladin.cds.unistra.fr/AladinLite/?target={hit.get('id','')}&fov=0.5")
        self._view_scale=1; self._rot_x=self._rot_z=0; self.refresh()

    def _hit_test(self,pos):
        best=None; best_d=HOVER_R*2
        for item in self._hit_suns+self._hit_moons+self._hit_sats+self._hit_ac+self._hit_planets+self._hit_stars+self._hit_dsos_list:
            d=(QPointF(item["sx"],item["sy"])-pos).manhattanLength()
            if d<best_d: best_d=d; best=item
        return best
