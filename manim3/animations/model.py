from typing import Callable

from scipy.spatial.transform import Rotation

from ..animations.animation import Animation
from ..custom_typing import (
    Mat4T,
    Vec3T
)
from ..mobjects.mobject import (
    AboutABC,
    Mobject
)
from ..utils.rate import RateUtils


class ModelFiniteAnimationABC(Animation):
    __slots__ = ()

    def __init__(
        self,
        mobject: Mobject,
        alpha_to_matrix: Callable[[float], Mat4T],
        *,
        arrive: bool = False,
        run_time: float = 1.0,
        rate_func: Callable[[float], float] = RateUtils.linear
    ) -> None:
        initial_model_matrix = mobject._model_matrix_.value

        def updater(
            alpha: float
        ) -> None:
            if arrive:
                alpha -= 1.0
            mobject._model_matrix_ = alpha_to_matrix(alpha) @ initial_model_matrix

        super().__init__(
            updater=updater,
            run_time=run_time,
            relative_rate=RateUtils.adjust(rate_func, run_time_scale=run_time)
        )

    async def timeline(self) -> None:
        await self.wait()


class Shift(ModelFiniteAnimationABC):
    __slots__ = ()

    def __init__(
        self,
        mobject: Mobject,
        vector: Vec3T,
        *,
        arrive: bool = False,
        run_time: float = 1.0,
        rate_func: Callable[[float], float] = RateUtils.linear
    ) -> None:
        super().__init__(
            mobject=mobject,
            alpha_to_matrix=mobject._shift_callback(vector),
            arrive=arrive,
            run_time=run_time,
            rate_func=rate_func
        )


class Scale(ModelFiniteAnimationABC):
    __slots__ = ()

    def __init__(
        self,
        mobject: Mobject,
        scale: float | Vec3T,
        about: AboutABC | None = None,
        *,
        arrive: bool = False,
        run_time: float = 1.0,
        rate_func: Callable[[float], float] = RateUtils.linear
    ) -> None:
        super().__init__(
            mobject=mobject,
            alpha_to_matrix=mobject._scale_callback(scale, about),
            arrive=arrive,
            run_time=run_time,
            rate_func=rate_func
        )


class Rotate(ModelFiniteAnimationABC):
    __slots__ = ()

    def __init__(
        self,
        mobject: Mobject,
        rotation: Rotation,
        about: AboutABC | None = None,
        *,
        arrive: bool = False,
        run_time: float = 1.0,
        rate_func: Callable[[float], float] = RateUtils.linear
    ) -> None:
        super().__init__(
            mobject=mobject,
            alpha_to_matrix=mobject._rotate_callback(rotation, about),
            arrive=arrive,
            run_time=run_time,
            rate_func=rate_func
        )


class ModelRunningAnimationABC(Animation):
    __slots__ = ()

    def __init__(
        self,
        mobject: Mobject,
        alpha_to_matrix: Callable[[float], Mat4T],
        *,
        run_time: float | None = None,
        speed: float = 1.0
    ) -> None:
        initial_model_matrix = mobject._model_matrix_.value

        def updater(
            alpha: float
        ) -> None:
            mobject._model_matrix_ = alpha_to_matrix(alpha) @ initial_model_matrix

        super().__init__(
            updater=updater,
            run_time=run_time,
            relative_rate=RateUtils.adjust(RateUtils.linear, run_alpha_scale=speed)
        )


class Shifting(ModelRunningAnimationABC):
    __slots__ = ()

    def __init__(
        self,
        mobject: Mobject,
        vector: Vec3T,
        *,
        run_time: float | None = None,
        speed: float = 1.0
    ) -> None:
        super().__init__(
            mobject=mobject,
            alpha_to_matrix=mobject._shift_callback(vector),
            run_time=run_time,
            speed=speed
        )


class Scaling(ModelRunningAnimationABC):
    __slots__ = ()

    def __init__(
        self,
        mobject: Mobject,
        factor: float | Vec3T,
        about: AboutABC | None = None,
        *,
        run_time: float | None = None,
        speed: float = 1.0
    ) -> None:
        super().__init__(
            mobject=mobject,
            alpha_to_matrix=mobject._scale_callback(factor, about),
            run_time=run_time,
            speed=speed
        )


class Rotating(ModelRunningAnimationABC):
    __slots__ = ()

    def __init__(
        self,
        mobject: Mobject,
        rotation: Rotation,
        about: AboutABC | None = None,
        *,
        run_time: float | None = None,
        speed: float = 1.0
    ) -> None:
        super().__init__(
            mobject=mobject,
            alpha_to_matrix=mobject._rotate_callback(rotation, about),
            run_time=run_time,
            speed=speed
        )