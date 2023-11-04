import time
from napari.qt.threading import thread_worker
from PyQt5.QtCore import Qt
from qtpy.QtWidgets import (
    QWidget,
    QLabel,
    QComboBox,
    QPushButton,
    QDoubleSpinBox,
    QGridLayout,
    QSizePolicy,
)


class WoggleOpacityWidget(QWidget):
    def __init__(self, napari_viewer):
        super().__init__()

        self.viewer = napari_viewer
        self.viewer.bind_key("w", lambda k: self._start())

        self.step = 0.05
        self.is_woggling = False

        self.transitions = {
            "Smooth": self.smooth_transition,
            "Sharp": self.sharp_transition,
        }

        # Layout
        grid_layout = QGridLayout()
        grid_layout.setAlignment(Qt.AlignTop)
        self.setLayout(grid_layout)

        # Image
        self.cb_image = QComboBox()
        self.cb_image.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.cb_image.currentTextChanged.connect(
            self._on_selected_layer_changed
        )
        grid_layout.addWidget(QLabel("Image", self), 0, 0)
        grid_layout.addWidget(self.cb_image, 0, 1)

        # Speed
        self.speed_spinbox = QDoubleSpinBox()
        self.speed_spinbox.setMinimum(1)
        self.speed_spinbox.setMaximum(10)
        self.speed_spinbox.setSingleStep(1)
        self.speed_spinbox.setValue(self.speed)
        self.speed_spinbox.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )
        grid_layout.addWidget(QLabel("Speed", self), 1, 0)
        grid_layout.addWidget(self.speed_spinbox, 1, 1)

        # Transition
        self.cb_transition = QComboBox()
        self.cb_transition.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )
        self.cb_transition.addItems(list(self.transitions.keys()))
        grid_layout.addWidget(QLabel("Transition", self), 2, 0)
        grid_layout.addWidget(self.cb_transition, 2, 1)

        # Start button
        self.start_btn = QPushButton("Start", self)
        self.start_btn.clicked.connect(self._start)
        grid_layout.addWidget(self.start_btn, 3, 0, 1, 2)

        # Setup layer callbacks
        self.viewer.layers.events.inserted.connect(
            lambda e: e.value.events.name.connect(self._on_layer_change)
        )
        self.viewer.layers.events.inserted.connect(self._on_layer_change)
        self.viewer.layers.events.removed.connect(self._on_layer_change)
        self._on_layer_change(None)

    def _on_layer_change(self, e):
        self.cb_image.clear()
        for x in self.viewer.layers:
            self.cb_image.addItem(x.name, x.data)

    def _on_selected_layer_changed(self, *args):
        self.is_woggling = False
        self.start_btn.setText("Start")

    @property
    def speed(self):
        return 0.1 - self.speed_spinbox.value() / 100 + 0.01

    def smooth_transition(self):
        time.sleep(self.speed)

        if (self.layer.opacity - 2 * self.step <= 0.0) | (
            self.layer.opacity - 2 * self.step >= 1.0
        ):
            self.step = -self.step

        opacity = self.layer.opacity - self.step

        return opacity

    def sharp_transition(self):
        wait_time = 1.0 / abs(self.step) * self.speed
        time.sleep(wait_time)

        opacity = self.layer.opacity

        if opacity == 1.0:
            opacity = 0.0
        elif opacity == 0.0:
            opacity = 1.0
        else:
            opacity = round(opacity, 0)

        return opacity

    @thread_worker()
    def _threaded_woggling(self):
        while self.is_woggling:
            opacity = self.transitions.get(
                self.cb_transition.currentText()
            ).__call__()

            yield opacity

        return 0

    def _start(self):
        self.is_woggling = not self.is_woggling

        self.start_btn.setText("Stop" if self.is_woggling else "Start")
        if self.is_woggling is False:
            return

        self.layer = self.viewer.layers[self.cb_image.currentText()]

        worker = self._threaded_woggling()
        worker.yielded.connect(self._set_opacity)
        worker.start()

    def _set_opacity(self, opacity):
        self.layer.opacity = opacity
