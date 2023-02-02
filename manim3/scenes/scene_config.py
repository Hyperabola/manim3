__all__ = ["SceneConfig"]


import numpy as np

from ..cameras.camera import Camera
from ..cameras.perspective_camera import PerspectiveCamera
from ..custom_typing import (
    ColorType,
    Real,
    Vec3T
)
from ..rendering.render_procedure import UniformBlockBuffer
from ..utils.color import ColorUtils
from ..utils.lazy import (
    LazyBase,
    lazy_property,
    lazy_property_updatable,
    lazy_property_writable
)


class PointLight(LazyBase):
    @lazy_property_writable
    @staticmethod
    def _position_() -> Vec3T:
        return np.zeros(3)

    @lazy_property_writable
    @staticmethod
    def _color_() -> Vec3T:
        return np.ones(3)

    @lazy_property_writable
    @staticmethod
    def _opacity_() -> Real:
        return 1.0

    def set_style(
        self,
        *,
        position: Vec3T | None = None,
        color: ColorType | None = None,
        opacity: Real | None = None
    ):
        if position is not None:
            self._position_ = position
        color_component, opacity_component = ColorUtils.normalize_color_input(color, opacity)
        if color_component is not None:
            self._color_ = color_component
        if opacity_component is not None:
            self._opacity_ = opacity_component
        return self


class SceneConfig(LazyBase):
    def __init__(self):
        self._camera: Camera = PerspectiveCamera()

    @lazy_property_writable
    @staticmethod
    def _background_color_() -> Vec3T:
        return np.zeros(3)

    @lazy_property_writable
    @staticmethod
    def _background_opacity_() -> Real:
        return 1.0

    @lazy_property_writable
    @staticmethod
    def _ambient_light_color_() -> Vec3T:
        return np.ones(3)

    @lazy_property_writable
    @staticmethod
    def _ambient_light_opacity_() -> Real:
        return 1.0

    @lazy_property_updatable
    @staticmethod
    def _point_lights_() -> list[PointLight]:
        return []

    @lazy_property
    @staticmethod
    def _ub_lights_o_() -> UniformBlockBuffer:
        return UniformBlockBuffer("ub_lights", [
            "vec4 u_ambient_light_color",
            "PointLight u_point_lights[NUM_U_POINT_LIGHTS]"
        ], {
            "PointLight": [
                "vec3 position",
                "vec4 color"
            ]
        })

    @lazy_property
    @staticmethod
    def _ub_lights_(
        ub_lights_o: UniformBlockBuffer,
        ambient_light_color: Vec3T,
        ambient_light_opacity: Real,
        point_lights: list[PointLight]
    ) -> UniformBlockBuffer:
        return ub_lights_o.write({
            "u_ambient_light_color": np.append(ambient_light_color, ambient_light_opacity),
            "u_point_lights": {
                "position": np.array([
                    point_light._position_
                    for point_light in point_lights
                ]),
                "color": np.array([
                    np.append(point_light._color_, point_light._opacity_)
                    for point_light in point_lights
                ])
            }
        })

    def set_view(
        self,
        *,
        eye: Vec3T | None = None,
        target: Vec3T | None = None,
        up: Vec3T | None = None
    ):
        self._camera.set_view(
            eye=eye,
            target=target,
            up=up
        )

    def set_background(
        self,
        *,
        color: ColorType | None = None,
        opacity: Real | None = None
    ):
        color_component, opacity_component = ColorUtils.normalize_color_input(color, opacity)
        if color_component is not None:
            self._background_color_ = color_component
        if opacity_component is not None:
            self._background_opacity_ = opacity_component
        return self

    def set_ambient_light(
        self,
        *,
        color: ColorType | None = None,
        opacity: Real | None = None
    ):
        color_component, opacity_component = ColorUtils.normalize_color_input(color, opacity)
        if color_component is not None:
            self._ambient_light_color_ = color_component
        if opacity_component is not None:
            self._ambient_light_opacity_ = opacity_component
        return self

    @_point_lights_.updater
    def add_point_light(
        self,
        *,
        position: Vec3T | None = None,
        color: ColorType | None = None,
        opacity: Real | None = None
    ):
        point_light = PointLight()
        point_light.set_style(
            position=position,
            color=color,
            opacity=opacity
        )
        self._point_lights_.append(point_light)

    @_point_lights_.updater
    def set_point_light(
        self,
        *,
        index: int | None = None,
        position: Vec3T | None = None,
        color: ColorType | None = None,
        opacity: Real | None = None
    ):
        if self._point_lights_:
            if index is None:
                index = 0
            self._point_lights_[index].set_style(
                position=position,
                color=color,
                opacity=opacity
            )
        else:
            if index is not None:
                raise IndexError
            if any(param is not None for param in (
                position,
                color,
                opacity
            )):
                self.add_point_light(
                    position=position,
                    color=color,
                    opacity=opacity
                )
        return self

    def set_style(
        self,
        *,
        background_color: ColorType | None = None,
        background_opacity: Real | None = None,
        ambient_light_color: ColorType | None = None,
        ambient_light_opacity: Real | None = None,
        point_light_position: Vec3T | None = None,
        point_light_color: ColorType | None = None,
        point_light_opacity: Real | None = None
    ):
        self.set_background(
            color=background_color,
            opacity=background_opacity
        )
        self.set_ambient_light(
            color=ambient_light_color,
            opacity=ambient_light_opacity
        )
        self.set_point_light(
            index=None,
            position=point_light_position,
            color=point_light_color,
            opacity=point_light_opacity
        )
        return self
