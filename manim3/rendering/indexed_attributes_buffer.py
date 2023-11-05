from __future__ import annotations


from typing import Self

from ..lazy.lazy import Lazy
from ..lazy.lazy_object import LazyObject
from .buffers.attributes_buffer import AttributesBuffer
from .buffers.index_buffer import IndexBuffer
from .mgl_enums import PrimitiveMode


class IndexedAttributesBuffer(LazyObject):
    __slots__ = ()

    def __init__(
        self: Self,
        *,
        attributes_buffer: AttributesBuffer,
        index_buffer: IndexBuffer | None = None,
        mode: PrimitiveMode
    ) -> None:
        super().__init__()
        self._attributes_buffer_ = attributes_buffer
        if index_buffer is not None:
            self._index_buffer_ = index_buffer
        self._mode_ = mode

    @Lazy.variable()
    @staticmethod
    def _attributes_buffer_() -> AttributesBuffer:
        return AttributesBuffer(
            fields=[],
            num_vertex=0,
            data={}
        )

    @Lazy.variable()
    @staticmethod
    def _index_buffer_() -> IndexBuffer:
        return IndexBuffer()

    @Lazy.variable()
    @staticmethod
    def _mode_() -> PrimitiveMode:
        return PrimitiveMode.TRIANGLES