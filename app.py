import sys
import math
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                QHBoxLayout, QGraphicsView, QGraphicsScene, 
                                QGraphicsEllipseItem, QGraphicsPolygonItem, QLabel, QSlider, QPushButton, 
                                QGroupBox, QTextEdit, QCheckBox)
from PySide6.QtCore import Qt, QPointF, QRectF, Signal, QPolygonF
from PySide6.QtGui import QBrush, QColor, QPen, QPainter, QRadialGradient, QLinearGradient, QPainterPath, QGraphicsBlurEffect

class LightItem(QGraphicsEllipseItem):
    positionChanged = Signal()

    def __init__(self, name, color, x, y):
        super().__init__(-12, -12, 24, 24)
        self.name = name
        self.base_color = color
        self.setBrush(QBrush(color))
        self.setPen(QPen(Qt.white, 2))
        self.setPos(x, y)
        self.setFlag(QGraphicsEllipseItem.ItemIsMovable, True)
        self.setFlag(QGraphicsEllipseItem.ItemSendsGeometryChanges, True)
        self.setZValue(10)

    def itemChange(self, change, value):
        if change == QGraphicsEllipseItem.ItemPositionHasChanged:
            self.positionChanged.emit()
        return super().itemChange(change, value)

class PreviewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(350, 400)
        self.lights = {}
        self.haze_on = False
        self.bg_color = QColor(15, 15, 15)

    def update_lights(self, lights, haze_on):
        self.lights = lights
        self.haze_on = haze_on
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), self.bg_color)

        center_x = self.width() / 2
        center_y = self.height() / 2
        radius = min(self.width(), self.height()) * 0.25

        # 1. Background Spill
        for name, data in self.lights.items():
            light_pos = data['pos']
            color = QColor(data['color'])
            intensity = data['effective_intensity']
            
            spill_x = center_x - (light_pos.x() / 2.0)
            spill_y = center_y - (light_pos.y() / 2.0)
            
            spill_grad = QRadialGradient(QPointF(spill_x, spill_y), self.width() * 0.8)
            spill_color = QColor(color)
            spill_color.setAlpha(int(100 * intensity))
            spill_grad.setColorAt(0, spill_color)
            transparent = QColor(spill_color)
            transparent.setAlpha(0)
            spill_grad.setColorAt(1, transparent)
            
            painter.setBrush(QBrush(spill_grad))
            painter.setPen(Qt.NoPen)
            painter.drawRect(self.rect())

        # 2. Volumetric Fog (God Rays)
        if self.haze_on:
            for name, data in self.lights.items():
                light_pos = data['pos']
                color = QColor(data['color'])
                intensity = data['effective_intensity']
                
                # Project light screen position
                light_screen_x = center_x - (light_pos.x() / 2.5)
                light_screen_y = center_y - (light_pos.y() / 2.5)
                
                # Draw cone of light
                angle = math.atan2(center_y - light_screen_y, center_x - light_screen_x)
                cone_width = math.radians(15)
                
                p1 = QPointF(light_screen_x, light_screen_y)
                p2 = QPointF(center_x + math.cos(angle + cone_width) * radius, center_y + math.sin(angle + cone_width) * radius)
                p3 = QPointF(center_x + math.cos(angle - cone_width) * radius, center_y + math.sin(angle - cone_width) * radius)
                
                cone_poly = QPolygonF([p1, p2, p3])
                cone_grad = QRadialGradient(p1, math.hypot(center_x - light_screen_x, center_y - light_screen_y))
                cone_color = QColor(color)
                cone_color.setAlpha(int(60 * intensity))
                cone_grad.setColorAt(0, cone_color)
                cone_grad.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 0))
                
                painter.setBrush(QBrush(cone_grad))
                painter.drawPolygon(cone_poly)

        # 3. Subject Base (Sphere & Eyes)
        shadow_grad = QRadialGradient(QPointF(center_x, center_y + radius * 0.8), radius * 1.2)
        shadow_grad.setColorAt(0, QColor(0, 0, 0, 150))
        shadow_grad.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(shadow_grad))
        painter.drawEllipse(QPointF(center_x, center_y + radius * 0.9), radius * 1.2, radius * 0.4)

        base_color = QColor(100, 100, 100)
        painter.setBrush(QBrush(base_color))
        painter.drawEllipse(QPointF(center_x, center_y), radius, radius)

        # 4. Diffuse Lighting & Lens Flares
        for name, data in self.lights.items():
            light_pos = data['pos']
            color = QColor(data['color'])
            intensity = data['effective_intensity']
            is_soft = data['is_soft']
            
            offset_x = light_pos.x() / 2.5
            offset_y = light_pos.y() / 2.5
            
            # Lens flare for backlights
            if light_pos.y() < -50 and name == "Backlight":
                flare_x = center_x - offset_x
                flare_y = center_y - offset_y
                
                # Bloom
                bloom_grad = QRadialGradient(QPointF(flare_x, flare_y), radius * 1.5)
                bloom_color = QColor(color)
                bloom_color.setAlpha(int(150 * intensity))
                bloom_grad.setColorAt(0, bloom_color)
                bloom_grad.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 0))
                painter.setBrush(QBrush(bloom_grad))
                painter.drawEllipse(QPointF(flare_x, flare_y), radius * 1.5, radius * 1.5)
                
                # Anamorphic Flare Line
                painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), int(200 * intensity)), 3))
                painter.drawLine(QPointF(flare_x - radius * 2, flare_y), QPointF(flare_x + radius * 2, flare_y))
                continue

            # Diffuse Light Gradient (Wider wrap if soft)
            hx = center_x - offset_x
            hy = center_y - offset_y
            
            grad = QRadialGradient(QPointF(hx, hy), radius * (2.5 if is_soft else 1.8))
            c = QColor(color)
            c.setAlpha(int(255 * intensity))
            grad.setColorAt(0, c)
            transparent = QColor(c)
            transparent.setAlpha(0)
            grad.setColorAt(1, transparent)
            
            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(center_x, center_y), radius, radius)

        # 5. Catchlights (Reflections in Eyes)
        eye_y = center_y - radius * 0.3
        eye_offset = radius * 0.35
        eye_radius_x = radius * 0.15
        eye_radius_y = radius * 0.1
        
        # Draw Eye Whites
        painter.setBrush(QBrush(QColor(240, 240, 240)))
        painter.drawEllipse(QPointF(center_x - eye_offset, eye_y), eye_radius_x, eye_radius_y)
        painter.drawEllipse(QPointF(center_x + eye_offset, eye_y), eye_radius_x, eye_radius_y)
        # Draw Pupils
        painter.setBrush(QBrush(QColor(20, 20, 20)))
        painter.drawEllipse(QPointF(center_x - eye_offset, eye_y), eye_radius_x * 0.6, eye_radius_y * 0.6)
        painter.drawEllipse(QPointF(center_x + eye_offset, eye_y), eye_radius_x * 0.6, eye_radius_y * 0.6)

        # Draw Catchlights in Pupils
        for name, data in self.lights.items():
            light_pos = data['pos']
            intensity = data['effective_intensity']
            is_soft = data['is_soft']
            
            # Only front lights create catchlights
            if light_pos.y() < -50: continue 
            
            # Calculate position mapped to the tiny pupil
            spec_offset_x = -(light_pos.x() / 200.0) * eye_radius_x
            spec_offset_y = -(light_pos.y() / 200.0) * eye_radius_y
            
            for eye_x in [center_x - eye_offset, center_x + eye_offset]:
                if is_soft:
                    # Softbox catchlight (rounded rectangle)
                    rect = QRectF(eye_x + spec_offset_x - 3, eye_y + spec_offset_y - 2, 6, 4)
                    painter.setBrush(QBrush(QColor(255, 255, 255, int(200 * intensity))))
                    painter.drawRoundedRect(rect, 2, 2)
                else:
                    # Bare bulb catchlight (sharp circle)
                    painter.setBrush(QBrush(QColor(255, 255, 255, int(255 * intensity))))
                    painter.drawEllipse(QPointF(eye_x + spec_offset_x, eye_y + spec_offset_y), 2, 2)


class LightingStudioApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cinematic Lighting Studio: Catchlights, Fog & Flares")
        self.resize(1300, 850)
        self.setStyleSheet("background-color: #1e1e1e; color: #e0e0e0; font-size: 11pt;")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- LEFT PANEL ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setFixedWidth(340)

        self.aspect_group = QGroupBox("Video Format & Environment")
        aspect_layout = QVBoxLayout()
        
        ratio_layout = QHBoxLayout()
        self.btn_horizontal = QPushButton("YouTube (16:9)")
        self.btn_vertical = QPushButton("Shorts (9:16)")
        self.btn_horizontal.clicked.connect(lambda: self.change_aspect_ratio("16:9"))
        self.btn_vertical.clicked.connect(lambda: self.change_aspect_ratio("9:16"))
        ratio_layout.addWidget(self.btn_horizontal)
        ratio_layout.addWidget(self.btn_vertical)
        aspect_layout.addLayout(ratio_layout)

        env_layout = QHBoxLayout()
        self.btn_guides = QPushButton("Guides")
        self.btn_guides.setCheckable(True)
        self.btn_guides.clicked.connect(self.toggle_guides)
        
        self.btn_haze = QPushButton("Atmospheric Haze")
        self.btn_haze.setCheckable(True)
        self.btn_haze.clicked.connect(self.update_all_visuals)
        
        env_layout.addWidget(self.btn_guides)
        env_layout.addWidget(self.btn_haze)
        aspect_layout.addLayout(env_layout)
        self.aspect_group.setLayout(aspect_layout)
        left_layout.addWidget(self.aspect_group)

        self.light_sliders = {}
        self.blur_effects = {}
        
        for light_name in ["Key", "Fill", "Backlight"]:
            group = QGroupBox(f"{light_name} Light")
            v_layout = QVBoxLayout()
            
            controls_layout = QHBoxLayout()
            int_slider = QSlider(Qt.Horizontal)
            int_slider.setValue(80 if light_name == "Key" else 60 if light_name == "Fill" else 70)
            int_slider.valueChanged.connect(self.update_all_visuals)
            
            soft_check = QCheckBox("Softbox")
            soft_check.setChecked(light_name != "Key")
            soft_check.toggled.connect(self.update_all_visuals)
            
            controls_layout.addWidget(QLabel("Intensity"))
            controls_layout.addWidget(int_slider)
            controls_layout.addWidget(soft_check)
            v_layout.addLayout(controls_layout)
            
            temp_slider = QSlider(Qt.Horizontal)
            temp_slider.setValue(30 if light_name == "Key" else 70 if light_name == "Fill" else 50)
            temp_slider.valueChanged.connect(self.update_all_visuals)
            v_layout.addWidget(QLabel("Temperature (Warm <-> Cool)"))
            v_layout.addWidget(temp_slider)
            
            group.setLayout(v_layout)
            left_layout.addWidget(group)
            self.light_sliders[light_name] = {"intensity": int_slider, "temp": temp_slider, "soft": soft_check}

        self.edu_text = QTextEdit()
        self.edu_text.setReadOnly(True)
        self.edu_text.setStyleSheet("background-color: #2b2b2b; border: none; padding: 10px;")
        self.update_education_text("16:9")
        left_layout.addWidget(self.edu_text)

        main_layout.addWidget(left_panel)

        # --- CENTER PANEL ---
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(-250, -250, 500, 500)
        self.view = QGraphicsView(self.scene)
        self.view.setStyleSheet("background-color: #121212; border: 1px solid #333;")
        self.view.setRenderHint(QPainter.Antialiasing)
        
        pen_grid = QPen(QColor(255, 255, 255, 20), 1, Qt.DashLine)
        for i in range(-250, 251, 50):
            self.scene.addLine(i, -250, i, 250, pen_grid)
            self.scene.addLine(-250, i, 250, i, pen_grid)
            
        self.camera_frame = self.scene.addRect(QRectF(-160, -90, 320, 180), QPen(Qt.red, 2), QBrush(Qt.NoBrush))
        self.subject = self.scene.addEllipse(-20, -20, 40, 40, QPen(Qt.white, 2), QBrush(QColor(80, 80, 80)))
        self.subject.setPos(0, 0)
        self.camera = self.scene.addRect(-15, -10, 30, 20, QPen(Qt.yellow, 2), QBrush(QColor(200, 200, 0)))
        self.camera.setPos(0, 130)
        
        self.guide_lines = []
        pen_guide = QPen(QColor(0, 255, 0, 100), 2, Qt.DashLine)
        self.guide_lines.append(self.scene.addLine(-250, -250, 250, 250, pen_guide))
        self.guide_lines.append(self.scene.addLine(250, -250, -250, 250, pen_guide))
        for line in self.guide_lines:
            line.setVisible(False)
            
        self.beams = {}
        self.shadows = {}
        self.halos = {}
        
        self.lights = {
            "Key": LightItem("Key", QColor(255, 180, 120), -120, -60),
            "Fill": LightItem("Fill", QColor(120, 180, 255), 120, -60),
            "Backlight": LightItem("Backlight", QColor(255, 255, 255), 0, -160)
        }
        
        for name, light in self.lights.items():
            self.scene.addItem(light)
            light.positionChanged.connect(self.update_all_visuals)
            
            self.halos[name] = self.scene.addEllipse(QRectF(-150, -150, 300, 300), QPen(Qt.NoPen), QBrush(Qt.NoBrush))
            self.beams[name] = self.scene.addPolygon(QPolygonF(), QBrush(QColor(light.base_color.red(), light.base_color.green(), light.base_color.blue(), 40)), QPen(Qt.NoPen))
            self.shadows[name] = self.scene.addPolygon(QPolygonF(), QBrush(QColor(0, 0, 0, 150)), QPen(Qt.NoPen))
            
            self.shadows[name].setZValue(1)
            self.beams[name].setZValue(2)
            self.halos[name].setZValue(0)
            
            blur = QGraphicsBlurEffect()
            blur.setBlurRadius(0)
            self.shadows[name].setGraphicsEffect(blur)
            self.blur_effects[name] = blur

        center_layout.addWidget(QLabel("Top-Down Studio View (Watch beams, shadows & fall-off)"))
        center_layout.addWidget(self.view)
        
        # --- RIGHT PANEL ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        self.preview = PreviewWidget()
        right_layout.addWidget(QLabel("Live 3D Preview (Check eyes for catchlights & air for fog)"))
        right_layout.addWidget(self.preview)

        main_layout.addWidget(center_panel, stretch=2)
        main_layout.addWidget(right_panel, stretch=1)

        self.update_all_visuals()

    def toggle_guides(self):
        for line in self.guide_lines:
            line.setVisible(self.btn_guides.isChecked())

    def change_aspect_ratio(self, ratio):
        if ratio == "16:9":
            self.camera_frame.setRect(-160, -90, 320, 180)
            self.update_education_text("16:9")
        else:
            self.camera_frame.setRect(-56, -100, 112, 200)
            self.update_education_text("9:16")
        self.update_all_visuals()

    def update_education_text(self, ratio):
        if ratio == "16:9":
            text = """
            <h3>Cinematic Lighting Concepts</h3>
            <p><b>1. Catchlights (Eye Reflections):</b><br>
            Look closely at the subject's eyes in the 3D Preview. You will see the reflection of your lights! Bare bulbs create sharp dots; Softboxes create rounded squares. Catchlights give "life" to a subject on camera.</p>
            <p><b>2. Atmospheric Haze (God Rays):</b><br>
            Toggle "Atmospheric Haze" on. You will see visible cones of light shining through the air. Haze adds depth and reveals the beams of light, highly used in cinematic YouTube documentaries.</p>
            <p><b>3. Lens Flares:</b><br>
            Drag the Backlight so it points directly at the camera (move it to the top center). Watch the 3D Preview simulate a bloom and an anamorphic lens flare. Use this for dramatic effect!</p>
            <p><b>4. Soft Light Wrap:</b><br>
            Toggle the Softbox on the Key light. Notice how the light wraps around the sphere, softening the transition from light to shadow.</p>
            """
        else:
            text = """
            <h3>YouTube Shorts (9:16)</h3>
            <p><b>Advanced Vertical Lighting:</b></p>
            <ul>
            <li><b>Catchlights:</b> Since phone screens are small, catchlights are CRITICAL to make the subject look alive. Ensure your Key light creates a reflection in the upper part of the eye.</li>
            <li><b>Haze & Depth:</b> Because vertical video has deep backgrounds, using Atmospheric Haze creates a sense of 3D depth that keeps viewers engaged.</li>
            <li><b>Lens Flares:</b> A backlight flare in a vertical video draws the eye directly to the center of the screen where the subject is. Very popular in Shorts/TikToks.</li>
            </ul>
            """
        self.edu_text.setHtml(text)

    def calculate_shadow(self, light_pos, subject_pos=QPointF(0,0), subject_radius=20, proj_dist=400):
        Lx, Ly = light_pos.x(), light_pos.y()
        Sx, Sy = subject_pos.x(), subject_pos.y()
        dx, dy = Sx - Lx, Sy - Ly
        dist = math.hypot(dx, dy)
        if dist <= subject_radius: return QPolygonF()
        
        angle_to_center = math.atan2(dy, dx)
        tangent_angle = math.asin(subject_radius / dist)
        
        ang1 = angle_to_center + tangent_angle
        ang2 = angle_to_center - tangent_angle
        
        p1 = QPointF(Sx + subject_radius * math.cos(ang1), Sy + subject_radius * math.sin(ang1))
        p2 = QPointF(Sx + subject_radius * math.cos(ang2), Sy + subject_radius * math.sin(ang2))
        
        pp1 = QPointF(p1.x() + math.cos(ang1) * proj_dist, p1.y() + math.sin(ang1) * proj_dist)
        pp2 = QPointF(p2.x() + math.cos(ang2) * proj_dist, p2.y() + math.sin(ang2) * proj_dist)
        
        return QPolygonF([p1, pp1, pp2, p2])

    def calculate_beam(self, light_pos, subject_pos=QPointF(0,0), subject_radius=20, width_factor=1.5):
        Lx, Ly = light_pos.x(), light_pos.y()
        Sx, Sy = subject_pos.x(), subject_pos.y()
        dx, dy = Sx - Lx, Sy - Ly
        dist = math.hypot(dx, dy)
        if dist == 0: return QPolygonF()
        
        angle = math.atan2(dy, dx)
        beam_angle = math.atan(subject_radius / dist) * width_factor
        
        ang1 = angle + beam_angle
        ang2 = angle - beam_angle
        
        beam_len = dist + 100
        p1 = QPointF(Lx + beam_len * math.cos(ang1), Ly + beam_len * math.sin(ang1))
        p2 = QPointF(Lx + beam_len * math.cos(ang2), Ly + beam_len * math.sin(ang2))
        
        return QPolygonF([QPointF(Lx, Ly), p1, p2])

    def update_all_visuals(self):
        def get_color(temp_val):
            r = 255 - int((temp_val / 100.0) * 155)
            g = 200 - int((temp_val / 100.0) * 50)
            b = 150 + int((temp_val / 100.0) * 105)
            return QColor(r, g, b)

        light_data = {}
        haze_on = self.btn_haze.isChecked()
        
        for name, light in self.lights.items():
            sliders = self.light_sliders[name]
            color = get_color(sliders['temp'].value())
            intensity = sliders['intensity'].value()
            is_soft = sliders['soft'].isChecked()
            
            light.setBrush(QBrush(color))
            self.blur_effects[name].setBlurRadius(20 if is_soft else 0)
            
            # Top-Down Beam (make denser if haze is on)
            beam_poly = self.calculate_beam(light.pos())
            self.beams[name].setPolygon(beam_poly)
            beam_color = QColor(color)
            beam_alpha = int(100 * (intensity / 100.0)) if haze_on else int(60 * (intensity / 100.0))
            beam_color.setAlpha(beam_alpha)
            self.beams[name].setBrush(QBrush(beam_color))
            
            # Top-Down Shadow
            if name != "Backlight" or light.pos().y() > -50:
                shadow_poly = self.calculate_shadow(light.pos())
                self.shadows[name].setPolygon(shadow_poly)
                shadow_alpha = int(180 if not is_soft else 120 * (intensity / 100.0))
                self.shadows[name].setBrush(QBrush(QColor(0, 0, 0, shadow_alpha)))
            else:
                self.shadows[name].setPolygon(QPolygonF())

            # Halo
            self.halos[name].setPos(light.pos())
            halo_grad = QRadialGradient(QPointF(0,0), 150)
            halo_color = QColor(color)
            halo_color.setAlpha(60)
            halo_grad.setColorAt(0, halo_color)
            halo_grad.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 0))
            self.halos[name].setBrush(QBrush(halo_grad))

            # Inverse Square Law
            distance = math.hypot(light.pos().x(), light.pos().y())
            if distance < 1: distance = 1
            effective_intensity = (intensity / 100.0) / (1.0 + (distance / 100.0)**2)
            
            light_data[name] = {
                'pos': light.pos(),
                'color': color,
                'effective_intensity': effective_intensity,
                'is_soft': is_soft
            }
        
        self.preview.update_lights(light_data, haze_on)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LightingStudioApp()
    window.show()
    sys.exit(app.exec())