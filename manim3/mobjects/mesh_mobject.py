__all__ = ["MeshMobject"]


import moderngl
import numpy as np

from ..custom_typing import (
    ColorType,
    Real,
    Vec3T,
    Vec3sT
)
from ..geometries.empty_geometry import EmptyGeometry
from ..geometries.geometry import Geometry
from ..mobjects.mobject import Mobject
from ..rendering.render_procedure import (
    RenderProcedure,
    TextureStorage,
    UniformBlockBuffer
)
from ..scenes.scene_config import SceneConfig
from ..utils.color import ColorUtils
from ..utils.lazy import (
    lazy_property,
    lazy_property_writable
)


class MeshMobject(Mobject):
    @lazy_property_writable
    @staticmethod
    def _color_map_texture_() -> moderngl.Texture | None:
        return None

    @lazy_property_writable
    @staticmethod
    def _geometry_() -> Geometry:
        return EmptyGeometry()

    @lazy_property_writable
    @staticmethod
    def _color_() -> Vec3T:
        return np.ones(3)

    @lazy_property_writable
    @staticmethod
    def _opacity_() -> Real:
        return 1.0

    @lazy_property_writable
    @staticmethod
    def _ambient_strength_() -> Real:
        return 1.0

    @lazy_property_writable
    @staticmethod
    def _specular_strength_() -> Real:
        return 0.5

    @lazy_property_writable
    @staticmethod
    def _shininess_() -> Real:
        return 32.0

    @lazy_property_writable
    @staticmethod
    def _apply_phong_lighting_() -> bool:
        return True

    @lazy_property
    @staticmethod
    def _u_color_maps_o_() -> TextureStorage:
        return TextureStorage("sampler2D u_color_maps[NUM_U_COLOR_MAPS]")

    @lazy_property
    @staticmethod
    def _u_color_maps_(
        u_color_maps_o: TextureStorage,
        color_map_texture: moderngl.Texture | None
    ) -> TextureStorage:
        textures = [color_map_texture] if color_map_texture is not None else []
        return u_color_maps_o.write(np.array(textures))

    @lazy_property
    @staticmethod
    def _ub_material_o_() -> UniformBlockBuffer:
        return UniformBlockBuffer("ub_material", [
            "vec4 u_color",
            "float u_ambient_strength",
            "float u_specular_strength",
            "float u_shininess"
        ])

    @lazy_property
    @staticmethod
    def _ub_material_(
        ub_material_o: UniformBlockBuffer,
        color: Vec3T,
        opacity: Real,
        ambient_strength: Real,
        specular_strength: Real,
        shininess: Real
    ) -> UniformBlockBuffer:
        return ub_material_o.write({
            "u_color": np.append(color, opacity),
            "u_ambient_strength": np.array(ambient_strength),
            "u_specular_strength": np.array(specular_strength),
            "u_shininess": np.array(shininess)
        })

    @lazy_property_writable
    @staticmethod
    def _render_samples_() -> int:
        return 4

    def _render(self, scene_config: SceneConfig, target_framebuffer: moderngl.Framebuffer) -> None:
        custom_macros = []
        if self._apply_phong_lighting_:
            custom_macros.append("#define APPLY_PHONG_LIGHTING")
        RenderProcedure.render_step(
            shader_str=RenderProcedure.read_shader("mesh"),
            custom_macros=custom_macros,
            texture_storages=[
                self._u_color_maps_
            ],
            uniform_blocks=[
                scene_config._camera._ub_camera_,
                self._ub_model_,
                scene_config._ub_lights_,
                self._ub_material_
            ],
            attributes=self._geometry_._attributes_,
            index_buffer=self._geometry_._index_buffer_,
            framebuffer=target_framebuffer,
            context_state=RenderProcedure.context_state(
                enable_only=moderngl.BLEND | moderngl.DEPTH_TEST
            ),
            mode=moderngl.TRIANGLES
        )

    #@_color_.updater
    def _set_style_locally(
        self,
        *,
        color: ColorType | None = None,
        opacity: Real | None = None,
        apply_oit: bool | None = None,
        ambient_strength: Real | None = None,
        specular_strength: Real | None = None,
        shininess: Real | None = None,
        apply_phong_lighting: bool | None = None
    ):
        color_component, opacity_component = ColorUtils.normalize_color_input(color, opacity)
        if color_component is not None:
            self._color_ = color_component
        if opacity_component is not None:
            self._opacity_ = opacity_component
        if apply_oit is not None:
            self._apply_oit_ = apply_oit
        else:
            if opacity_component is not None:
                self._apply_oit_ = True
        if ambient_strength is not None:
            self._ambient_strength_ = ambient_strength
        if specular_strength is not None:
            self._specular_strength_ = specular_strength
        if shininess is not None:
            self._shininess_ = shininess
        if apply_phong_lighting is not None:
            self._apply_phong_lighting_ = apply_phong_lighting
        else:
            if any(param is not None for param in (
                ambient_strength,
                specular_strength,
                shininess
            )):
                self._apply_phong_lighting_ = True
        return self

    def set_style(
        self,
        *,
        color: ColorType | None = None,
        opacity: Real | None = None,
        apply_oit: bool | None = None,
        ambient_strength: Real | None = None,
        specular_strength: Real | None = None,
        shininess: Real | None = None,
        apply_phong_lighting: bool | None = None,
        broadcast: bool = True
    ):
        for mobject in self.iter_descendants(broadcast=broadcast):
            if not isinstance(mobject, MeshMobject):
                continue
            mobject._set_style_locally(
                color=color,
                opacity=opacity,
                apply_oit=apply_oit,
                ambient_strength=ambient_strength,
                specular_strength=specular_strength,
                shininess=shininess,
                apply_phong_lighting=apply_phong_lighting
            )
        return self

    def _get_local_sample_points(self) -> Vec3sT:
        return self._geometry_._position_
