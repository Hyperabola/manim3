import numpy as np

from ..geometries.plane_geometry import PlaneGeometry
from ..mobjects.mesh_mobject import MeshMobject
from ..rendering.framebuffer import (
    OpaqueFramebuffer,
    TransparentFramebuffer
)
from ..rendering.texture import TextureFactory
from ..scene.scene import Scene


class ChildSceneMobject(MeshMobject):
    __slots__ = ("_scene",)

    def __init__(
        self,
        scene: Scene
    ) -> None:
        super().__init__()
        self._scene: Scene = scene
        self._geometry_ = PlaneGeometry()
        self._enable_phong_lighting_ = False
        self.scale(np.array((
            scene.camera._width_.value,
            scene.camera._height_.value,
            1.0
        )))

    def _render(
        self,
        target_framebuffer: OpaqueFramebuffer | TransparentFramebuffer
    ) -> None:
        scene = self._scene
        with TextureFactory.texture() as color_texture:
            scene._render_to_texture(color_texture)
            self._color_map_ = color_texture
            super()._render(target_framebuffer)