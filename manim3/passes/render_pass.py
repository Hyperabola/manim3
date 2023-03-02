__all__ = ["RenderPass"]


from abc import abstractmethod

import moderngl
import numpy as np

from ..lazy.core import LazyObject
from ..lazy.interfaces import lazy_property
from ..rendering.glsl_buffers import (
    AttributesBuffer,
    IndexBuffer
)
from ..rendering.vertex_array import IndexedAttributesBuffer


class RenderPass(LazyObject):
    __slots__ = ()

    @lazy_property
    @classmethod
    def _indexed_attributes_buffer_(cls) -> IndexedAttributesBuffer:
        return IndexedAttributesBuffer(
            attributes=AttributesBuffer(
                fields=[
                    "vec3 in_position",
                    "vec2 in_uv"
                ],
                num_vertex=4,
                data={
                    "in_position": np.array((
                        [-1.0, -1.0, 0.0],
                        [1.0, -1.0, 0.0],
                        [1.0, 1.0, 0.0],
                        [-1.0, 1.0, 0.0],
                    )),
                    "in_uv": np.array((
                        [0.0, 0.0],
                        [1.0, 0.0],
                        [1.0, 1.0],
                        [0.0, 1.0],
                    ))
                }
            ),
            index_buffer=IndexBuffer(
                data=np.array((
                    0, 1, 2, 3
                ))
            ),
            mode=moderngl.TRIANGLE_FAN
        )

    @abstractmethod
    def _render(
        self,
        texture: moderngl.Texture,
        target_framebuffer: moderngl.Framebuffer
    ) -> moderngl.Texture:
        pass
