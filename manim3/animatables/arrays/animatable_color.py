from __future__ import annotations


from typing import Self

from ...constants.custom_typing import (
    ColorT,
    NP_3f8
)
from ...lazy.lazy import Lazy
from ...toplevel.toplevel import Toplevel
from ...utils.color_utils import ColorUtils
from .animatable_array import AnimatableArray


class AnimatableColor(AnimatableArray[NP_3f8]):
    __slots__ = ()

    @Lazy.variable(hasher=Lazy.array_hasher)
    @staticmethod
    def _array_() -> NP_3f8:
        return ColorUtils.standardize_color(Toplevel.config.default_color)

    @classmethod
    def _convert_input(
        cls: type[Self],
        color_input: ColorT
    ) -> Self:
        return AnimatableColor(ColorUtils.standardize_color(color_input))
