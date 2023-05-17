import napari

from napari_woggle import WoggleWidget

viewer = napari.Viewer()

woggle = WoggleWidget(viewer)

viewer.window.add_dock_widget(woggle, name="Woggle")

import skimage.data
viewer.add_image(skimage.data.coins())

if __name__ == '__main__':
    napari.run()