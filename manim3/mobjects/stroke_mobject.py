__all__ = ["StrokeMobject"]


import itertools as it
from typing import (
    Callable,
    Generator,
    Iterable
)

import moderngl
import numpy as np

from ..cameras.camera import Camera
from ..custom_typing import (
    ColorType,
    Mat4T,
    Vec3T,
    Vec3sT,
    VertexIndexType
)
from ..lazy.core import LazyCollection
from ..lazy.interface import (
    Lazy,
    LazyMode
)
from ..mobjects.mobject import Mobject
from ..rendering.glsl_buffers import (
    AttributesBuffer,
    IndexBuffer,
    UniformBlockBuffer
)
from ..rendering.vertex_array import (
    ContextState,
    IndexedAttributesBuffer,
    VertexArray
)
from ..utils.color import ColorUtils
from ..utils.scene_config import SceneConfig
from ..utils.shape import (
    LineStringKind,
    MultiLineString3D
)
from ..utils.space import SpaceUtils


class StrokeMobject(Mobject):
    __slots__ = ()

    def __init__(
        self,
        multi_line_string_3d: MultiLineString3D | None = None
    ) -> None:
        super().__init__()
        if multi_line_string_3d is not None:
            self._multi_line_string_3d_ = multi_line_string_3d

    #@staticmethod
    #def __winding_sign_key(
    #    winding_sign: bool
    #) -> bool:
    #    return winding_sign

    @Lazy.variable(LazyMode.OBJECT)
    @classmethod
    def _multi_line_string_3d_(cls) -> MultiLineString3D:
        return MultiLineString3D()

    @Lazy.variable(LazyMode.UNWRAPPED)
    @classmethod
    def _width_(cls) -> float:
        # TODO: The unit mismatches by a factor of 5
        return 0.2

    @Lazy.variable(LazyMode.UNWRAPPED)
    @classmethod
    def _single_sided_(cls) -> bool:
        return False

    @Lazy.variable(LazyMode.UNWRAPPED)
    @classmethod
    def _has_linecap_(cls) -> bool:
        return True

    @Lazy.variable(LazyMode.UNWRAPPED)
    @classmethod
    def _color_(cls) -> Vec3T:
        return np.ones(3)

    @Lazy.variable(LazyMode.UNWRAPPED)
    @classmethod
    def _opacity_(cls) -> float:
        return 1.0

    @Lazy.variable(LazyMode.UNWRAPPED)
    @classmethod
    def _dilate_(cls) -> float:
        return 0.0

    @Lazy.variable(LazyMode.SHARED)
    @classmethod
    def _winding_sign_(cls) -> bool:
        return NotImplemented

    #@Lazy.property(LazyMode.UNWRAPPED)
    #@classmethod
    #def _winding_sign_(
    #    cls,
    #    scene_config__camera__projection_matrix: Mat4T,
    #    scene_config__camera__view_matrix: Mat4T,
    #    model_matrix: Mat4T,
    #    multi_line_string_3d__children__coords: list[Vec3sT],
    #    width: float
    #) -> bool:
    #    # TODO: The calculation here is somehow redundant with what shader does...
    #    transform = scene_config__camera__projection_matrix @ scene_config__camera__view_matrix @ model_matrix
    #    area = 0.0
    #    for coords in multi_line_string_3d__children__coords:
    #        coords_2d = SpaceUtils.apply_affine(transform, coords)[:, :2]
    #        area += np.cross(coords_2d, np.roll(coords_2d, -1, axis=0)).sum()
    #    return area * width >= 0.0

    @Lazy.property(LazyMode.UNWRAPPED)
    @classmethod
    def _local_sample_points_(
        cls,
        _multi_line_string_3d_: MultiLineString3D
    ) -> Vec3sT:
        line_strings = _multi_line_string_3d_._children_
        if not line_strings:
            return np.zeros((0, 3))
        return np.concatenate([
            line_string._coords_.value
            for line_string in line_strings
        ])

    @Lazy.property(LazyMode.OBJECT)
    @classmethod
    def _ub_stroke_(
        cls,
        width: float,
        color: Vec3T,
        opacity: float,
        dilate: float
    ) -> UniformBlockBuffer:
        return UniformBlockBuffer(
            name="ub_stroke",
            fields=[
                "float u_width",
                "vec4 u_color",
                "float u_dilate"
            ],
            data={
                "u_width": np.array(abs(width)),
                "u_color": np.append(color, opacity),
                "u_dilate": np.array(dilate)
            }
        )

    @Lazy.property(LazyMode.OBJECT)
    @classmethod
    def _ub_winding_sign_(
        cls,
        winding_sign: bool
    ) -> UniformBlockBuffer:
        return UniformBlockBuffer(
            name="ub_winding_sign",
            fields=[
                "float u_winding_sign"
            ],
            data={
                "u_winding_sign": np.array(1.0 if winding_sign else -1.0)
            }
        )

    @Lazy.property(LazyMode.OBJECT)
    @classmethod
    def _attributes_(
        cls,
        _multi_line_string_3d_: MultiLineString3D
    ) -> AttributesBuffer:
        if not _multi_line_string_3d_._children_:
            position = np.zeros((0, 3))
        else:
            position = np.concatenate([
                line_string._coords_.value
                for line_string in _multi_line_string_3d_._children_
            ])
        return AttributesBuffer(
            fields=[
                "vec3 in_position"
            ],
            num_vertex=len(position),
            data={
                "in_position": position
            }
        )

    @Lazy.variable(LazyMode.OBJECT)
    @classmethod
    def _line_vertex_array_(cls) -> VertexArray:
        return VertexArray()

    @Lazy.variable(LazyMode.OBJECT)
    @classmethod
    def _join_vertex_array_(cls) -> VertexArray:
        return VertexArray()

    @Lazy.variable(LazyMode.OBJECT)
    @classmethod
    def _cap_vertex_array_(cls) -> VertexArray:
        return VertexArray()

    @Lazy.variable(LazyMode.OBJECT)
    @classmethod
    def _point_vertex_array_(cls) -> VertexArray:
        return VertexArray()

    #@Lazy.variable(LazyMode.COLLECTION)
    #@classmethod
    #def _vertex_arrays_(cls) -> LazyCollection[VertexArray]:
    #    return LazyCollection(VertexArray(), VertexArray(), VertexArray(), VertexArray())

    #@Lazy.property(LazyMode.COLLECTION)
    #@classmethod
    #def _vertex_arrays_(
    #    cls,
    #    _scene_config__camera__ub_camera_: UniformBlockBuffer,
    #    _ub_model_: UniformBlockBuffer,
    #    _ub_stroke_: UniformBlockBuffer,
    #    _ub_winding_sign_: UniformBlockBuffer,
    #    _multi_line_string_3d_: MultiLineString3D,
    #    single_sided: bool,
    #    has_linecap: bool,
    #    _attributes_: AttributesBuffer
    #) -> LazyCollection[VertexArray]:
    #    
    #    return result

    #@_vertex_arrays_.restocker
    #@staticmethod
    #def _vertex_arrays_restocker(
    #    vertex_array_items: list[VertexArray]
    #) -> None:
    #    for vertex_array in vertex_array_items:
    #        vertex_array._restock()

    #@lazy_slot
    #@staticmethod
    #def _render_samples() -> int:
    #    return 4

    @classmethod
    def _lump_index_from_getter(
        cls,
        index_getter: Callable[[int, LineStringKind], list[int]],
        multi_line_string_3d: MultiLineString3D
    ) -> VertexIndexType:
        offset = 0
        index_arrays: list[VertexIndexType] = []
        for line_string in multi_line_string_3d._children_:
            coords_len = len(line_string._coords_.value)
            kind = line_string._kind_.value
            index_arrays.append(np.array(index_getter(coords_len, kind), dtype=np.uint32) + offset)
            offset += coords_len
        if not index_arrays:
            return np.zeros(0, dtype=np.uint32)
        return np.concatenate(index_arrays, dtype=np.uint32)

    @classmethod
    def _line_index_getter(
        cls,
        coords_len: int,
        kind: LineStringKind
    ) -> list[int]:
        if kind == LineStringKind.POINT:
            return []
        #n_points = len(line_string._coords_.value)
        if kind == LineStringKind.LINE_STRING:
            # (0, 1, 1, 2, ..., n-2, n-1)
            return list(it.chain(*zip(*(
                range(i, coords_len - 1 + i)
                for i in range(2)
            ))))
        if kind == LineStringKind.LINEAR_RING:
            return list(it.chain(*zip(*(
                np.roll(range(coords_len - 1), -i)
                for i in range(2)
            ))))
        raise ValueError  # never

    @classmethod
    def _join_index_getter(
        cls,
        coords_len: int,
        kind: LineStringKind
    ) -> list[int]:
        if kind == LineStringKind.POINT:
            return []
        #n_points = len(line_string._coords_.value)
        if kind == LineStringKind.LINE_STRING:
            # (0, 1, 2, 1, 2, 3, ..., n-3, n-2, n-1)
            return list(it.chain(*zip(*(
                range(i, coords_len - 2 + i)
                for i in range(3)
            ))))
        if kind == LineStringKind.LINEAR_RING:
            return list(it.chain(*zip(*(
                np.roll(range(coords_len - 1), -i)
                for i in range(3)
            ))))
        raise ValueError  # never

    @classmethod
    def _cap_index_getter(
        cls,
        coords_len: int,
        kind: LineStringKind
    ) -> list[int]:
        if kind == LineStringKind.POINT:
            return []
        #n_points = len(line_string._coords_.value)
        if kind == LineStringKind.LINE_STRING:
            return [0, 1, coords_len - 1, coords_len - 2]
        if kind == LineStringKind.LINEAR_RING:
            return []
        raise ValueError  # never

    @classmethod
    def _point_index_getter(
        cls,
        coords_len: int,
        kind: LineStringKind
    ) -> list[int]:
        if kind == LineStringKind.POINT:
            return [0]
        if kind == LineStringKind.LINE_STRING:
            return []
        if kind == LineStringKind.LINEAR_RING:
            return []
        raise ValueError  # never

    #@Lazy.variable(LazyMode.OBJECT)
    #@classmethod
    #def _scene_config_(cls) -> SceneConfig:
    #    return NotImplemented

    def _render(
        self,
        scene_config: SceneConfig,
        target_framebuffer: moderngl.Framebuffer
    ) -> None:
        self._winding_sign_ = self._calculate_winding_sign(scene_config._camera_)
        uniform_blocks = [
            scene_config._camera_._ub_camera_,
            self._ub_model_,
            self._ub_stroke_,
            self._ub_winding_sign_
        ]

        def get_vertex_array(
            vertex_array: VertexArray,
            index_getter: Callable[[int, LineStringKind], list[int]],
            mode: int,
            custom_macros: list[str]
        ) -> VertexArray:
            return vertex_array.write(
                shader_filename="stroke",
                custom_macros=custom_macros,
                texture_storages=[],
                uniform_blocks=uniform_blocks,
                indexed_attributes=IndexedAttributesBuffer(
                    attributes=self._attributes_,
                    index_buffer=IndexBuffer(
                        data=self._lump_index_from_getter(index_getter, self._multi_line_string_3d_)
                    ),
                    mode=mode
                )
            )

        subroutine_name = "single_sided" if self._single_sided_.value else "both_sided"
        vertex_arrays = [
            get_vertex_array(self._line_vertex_array_, self._line_index_getter, moderngl.LINES, [
                "#define STROKE_LINE",
                f"#define line_subroutine {subroutine_name}"
            ]),
            get_vertex_array(self._join_vertex_array_, self._join_index_getter, moderngl.TRIANGLES, [
                "#define STROKE_JOIN",
                f"#define join_subroutine {subroutine_name}"
            ])
        ]
        if self._has_linecap_.value and not self._single_sided_.value:
            vertex_arrays.extend([
                get_vertex_array(self._cap_vertex_array_, self._cap_index_getter, moderngl.LINES, [
                    "#define STROKE_CAP"
                ]),
                get_vertex_array(self._point_vertex_array_, self._point_index_getter, moderngl.POINTS, [
                    "#define STROKE_POINT"
                ])
            ])

        # TODO: Is this already the best practice?
        # Render color
        target_framebuffer.depth_mask = False
        for vertex_array in vertex_arrays:
            vertex_array.render(
                #shader_filename="stroke",
                #custom_macros=custom_macros,
                #texture_storages=[],
                #texture_array_dict={},
                #uniform_blocks=uniform_blocks,
                framebuffer=target_framebuffer,
                context_state=ContextState(
                    enable_only=moderngl.BLEND,
                    blend_func=moderngl.ADDITIVE_BLENDING,
                    blend_equation=moderngl.MAX
                )
            )
        target_framebuffer.depth_mask = True
        # Render depth
        target_framebuffer.color_mask = (False, False, False, False)
        for vertex_array in vertex_arrays:
            vertex_array.render(
                #shader_filename="stroke",
                #custom_macros=custom_macros,
                #texture_storages=[],
                #texture_array_dict={},
                #uniform_blocks=uniform_blocks,
                framebuffer=target_framebuffer,
                context_state=ContextState(
                    enable_only=moderngl.DEPTH_TEST
                )
            )
        target_framebuffer.color_mask = (True, True, True, True)

    def _calculate_winding_sign(
        self,
        camera: Camera
    ) -> bool:
        # TODO: The calculation here is somehow redundant with what shader does...
        area = 0.0
        transform = camera._projection_matrix_.value @ camera._view_matrix_.value @ self._model_matrix_.value
        for line_string in self._multi_line_string_3d_._children_:
            coords_2d = SpaceUtils.apply_affine(transform, line_string._coords_.value)[:, :2]
            area += np.cross(coords_2d, np.roll(coords_2d, -1, axis=0)).sum()
        return area * self._width_.value >= 0.0

    def iter_stroke_descendants(
        self,
        broadcast: bool = True
    ) -> "Generator[StrokeMobject, None, None]":
        for mobject in self.iter_descendants(broadcast=broadcast):
            if isinstance(mobject, StrokeMobject):
                yield mobject

    @classmethod
    def class_set_style(
        cls,
        mobjects: "Iterable[StrokeMobject]",
        *,
        width: float | None = None,
        single_sided: bool | None = None,
        has_linecap: bool | None = None,
        color: ColorType | None = None,
        opacity: float | None = None,
        dilate: float | None = None,
        apply_oit: bool | None = None
    ) -> None:
        width_value = width if width is not None else None
        single_sided_value = single_sided if single_sided is not None else None
        has_linecap_value = has_linecap if has_linecap is not None else None
        color_component, opacity_component = ColorUtils.normalize_color_input(color, opacity)
        color_value = color_component if color_component is not None else None
        opacity_value = opacity_component if opacity_component is not None else None
        dilate_value = dilate if dilate is not None else None
        apply_oit_value = apply_oit if apply_oit is not None else \
            True if any(param is not None for param in (
                opacity_component,
                dilate
            )) else None
        for mobject in mobjects:
            if width_value is not None:
                mobject._width_ = width_value
            if single_sided_value is not None:
                mobject._single_sided_ = single_sided_value
            if has_linecap_value is not None:
                mobject._has_linecap_ = has_linecap_value
            if color_value is not None:
                mobject._color_ = color_value
            if opacity_value is not None:
                mobject._opacity_ = opacity_value
            if dilate_value is not None:
                mobject._dilate_ = dilate_value
            if apply_oit_value is not None:
                mobject._apply_oit_ = apply_oit_value

    def set_style(
        self,
        *,
        width: float | None = None,
        single_sided: bool | None = None,
        has_linecap: bool | None = None,
        color: ColorType | None = None,
        opacity: float | None = None,
        dilate: float | None = None,
        apply_oit: bool | None = None,
        broadcast: bool = True
    ):
        self.class_set_style(
            mobjects=self.iter_stroke_descendants(broadcast=broadcast),
            width=width,
            single_sided=single_sided,
            has_linecap=has_linecap,
            color=color,
            opacity=opacity,
            dilate=dilate,
            apply_oit=apply_oit
        )
        return self
