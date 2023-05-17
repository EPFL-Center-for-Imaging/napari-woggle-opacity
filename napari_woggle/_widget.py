import time
from napari.qt.threading import thread_worker
from PyQt5.QtCore import Qt
from qtpy.QtWidgets import (
    QVBoxLayout, 
    QWidget, 
    QHBoxLayout, 
    QLabel, 
    QComboBox, 
    QPushButton, 
    QSlider,
    QRadioButton,
)   

class WoggleWidget(QWidget):
    def __init__(self, napari_viewer):
        super().__init__()

        self.viewer = napari_viewer
        self.viewer.bind_key('w', lambda k: self._toggle_start_process())
        
        self.step = 0.05
        self.woggle_speed = 0.05
        self.flag = False
        self.woggle_transition_fnct = self.smooth_transition
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)
        layout.addWidget(self)
        self.setLayout(layout)

        qw00 = QWidget(self)
        self.layout().addWidget(qw00)
        sub00 = QHBoxLayout()
        qw00.setLayout(sub00)
        sub00.addWidget(QLabel("Image", self))
        self.cb_image = QComboBox()
        sub00.addWidget(self.cb_image)

        # Woggle speed
        qw01 = QWidget(self)
        self.layout().addWidget(qw01)
        sub01 = QHBoxLayout()
        qw01.setLayout(sub01)
        sub01.addWidget(QLabel("Speed", self))
        self.woggle_speed_slider = QSlider(Qt.Horizontal)
        self.woggle_speed_slider.valueChanged.connect(self.update_woggle_speed)
        sub01.addWidget(self.woggle_speed_slider)

        # Woggle shape
        qw02 = QWidget(self)
        self.layout().addWidget(qw02)
        sub02 = QHBoxLayout()
        qw02.setLayout(sub02)
        sub02.addWidget(QLabel("Transition", self))
        self.b1 = QRadioButton("Smooth")
        self.b1.setChecked(True)
        self.b1.toggled.connect(lambda:self.update_woggle_transition_type(self.b1))
        sub02.addWidget(self.b1)
        self.b2 = QRadioButton("Sharp")
        self.b2.toggled.connect(lambda:self.update_woggle_transition_type(self.b2))
        sub02.addWidget(self.b2)

        # Start button        
        self.start_btn = QPushButton('Start woggling', self)
        self.start_btn.clicked.connect(self._toggle_start_process)
        self.layout().addWidget(self.start_btn)

        self.viewer.layers.events.inserted.connect(self._add_rename_event)
        self.viewer.layers.events.inserted.connect(self._on_layer_change)
        self.viewer.layers.events.removed.connect(self._on_layer_change)
        self._on_layer_change(None)

    def update_woggle_speed(self):
        speed = self.woggle_speed_slider.value()  # Values are in [0-100]
        self.woggle_speed = (100 - speed) / 100 * 0.10 + 0.001

    def smooth_transition(self):
        time.sleep(self.woggle_speed)
        
        if (self.layer.opacity - 2*self.step <= 0.0) | (self.layer.opacity - 2*self.step >= 1.0):
            self.step = -self.step
        
        opacity = self.layer.opacity - self.step

        return opacity

    def sharp_transition(self):
        wait_time = 1.0 / abs(self.step) * self.woggle_speed
        time.sleep(wait_time)

        opacity = self.layer.opacity
        
        if opacity == 1.0:
            opacity = 0.0
        elif opacity == 0.0:
            opacity = 1.0
        else:
            opacity = round(opacity, 0)
        
        return opacity

    def update_woggle_transition_type(self, b):
        print('Selected transition type: ', b.text())
        if b.text() == 'Smooth':
            self.woggle_transition_fnct = self.smooth_transition
        elif b.text() == 'Sharp':
            self.woggle_transition_fnct = self.sharp_transition
        
    @thread_worker()
    def _threaded_process(self):
        while self.flag:
            opacity = self.woggle_transition_fnct()
            yield opacity
        
        return 0

    def _toggle_start_process(self):
        self.flag = not self.flag
        self.start_btn.setText('Stop woggling' if self.flag else 'Start woggling')
        if self.flag:
            self._trigger_threaded_process()
    
    def _trigger_threaded_process(self):
        self.layer = self.viewer.layers[self.cb_image.currentText()]
        self.layer.opacity = 0.5

        worker = self._threaded_process()
        worker.yielded.connect(self._update_opacity)
        worker.returned.connect(self._set_opacity_max)
        worker.start()

    def _set_opacity_max(self, return_value):
        self.layer.opacity = 1.0
        self.layer.refresh()

    def _update_opacity(self, opacity):
        self.layer.opacity = opacity
    
    def _add_rename_event(self, e):
        source_layer = e.value
        source_layer.events.name.connect(self._proxy_on_layer_change)

    def _proxy_on_layer_change(self, e):
        self._on_layer_change(None)

    def _on_layer_change(self, e):
        self.cb_image.clear()
        for x in self.viewer.layers:
            self.cb_image.addItem(x.name, x.data)
