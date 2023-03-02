__all__ = ["ImageMobject"]


import moderngl
import numpy as np
from PIL import Image

from ..custom_typing import Real
from ..geometries.geometry import Geometry
from ..geometries.plane_geometry import PlaneGeometry
from ..lazy.interfaces import lazy_object
from ..mobjects.mesh_mobject import MeshMobject
from ..rendering.config import ConfigSingleton
from ..rendering.framebuffer_batches import ColorFramebufferBatch
from ..utils.scene_config import SceneConfig


class ImageMobject(MeshMobject):
    __slots__ = ("_image",)

    def __init__(
        self,
        image_path: str,
        *,
        width: Real | None = None,
        height: Real | None = 4.0,
        frame_scale: Real | None = None
    ) -> None:
        super().__init__()
        image = Image.open(image_path)
        self._image: Image.Image = image

        x_scale, y_scale = self._get_frame_scale_vector(
            image.width / ConfigSingleton().pixel_per_unit,
            image.height / ConfigSingleton().pixel_per_unit,
            width,
            height,
            frame_scale
        )
        self.scale(np.array((x_scale, -y_scale, 1.0)))  # flip y

    @lazy_object
    @classmethod
    def _geometry_(cls) -> Geometry:
        return PlaneGeometry()

    def _render(
        self,
        scene_config: SceneConfig,
        target_framebuffer: moderngl.Framebuffer
    ) -> None:
        image = self._image
        with ColorFramebufferBatch() as batch:
            batch.color_texture.write(image.tobytes())
            self._color_map_ = batch.color_texture
            super()._render(scene_config, target_framebuffer)
