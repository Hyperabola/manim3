import numpy as np

from ...custom_typing import NP_3f8
from ...lazy.lazy import Lazy
from ...utils.space import SpaceUtils
from ..mobject import (
    Mobject,
    MobjectStyleMeta
)


class AmbientLight(Mobject):
    __slots__ = ()

    @MobjectStyleMeta.register(
        interpolate_method=SpaceUtils.lerp_3f8
    )
    @Lazy.variable_array
    @classmethod
    def _color_(cls) -> NP_3f8:
        return np.ones((3,))
