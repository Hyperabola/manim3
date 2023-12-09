from __future__ import annotations


import asyncio
from abc import (
    ABC,
    abstractmethod
)
from typing import (
    TYPE_CHECKING,
    Callable,
    Coroutine,
    Self
)

import attrs

from ..constants.custom_typing import (
    ConditionType,
    RateType
)
from ..constants.rates import Rates
from ..toplevel.toplevel import Toplevel

if TYPE_CHECKING:
    from ..toplevel.scene import Scene


@attrs.frozen(kw_only=True)
class TimelineState:
    pass


@attrs.frozen(kw_only=True)
class AfterScheduled(TimelineState):
    parent_absolute_rate: Callable[[], float]
    rate: RateType
    run_time_scale: float
    run_alpha_scale: float


@attrs.frozen(kw_only=True)
class AfterLaunched(TimelineState):
    construct_coroutine: Coroutine[None, None, None]
    absolute_rate: Callable[[], float]
    children: list[Timeline]


@attrs.frozen(kw_only=True)
class AfterTerminated(TimelineState):
    pass


class Timeline(ABC):
    __slots__ = (
        "__weakref__",
        "_run_alpha",
        "_timeline_state",
        "_launch_condition",
        "_terminate_condition",
        "_progress_condition"
    )

    def __init__(
        self: Self,
        # The accumulated alpha value of `construct`.
        # Left as `inf` if infinite or indefinite.
        # This parameter is required mostly for the program to know
        # how long the timeline is before running the timeline.
        run_alpha: float = float("inf")
    ) -> None:
        super().__init__()
        self._run_alpha: float = run_alpha
        self._timeline_state: TimelineState | None = None
        self._launch_condition: ConditionType | None = None  # default: lambda: True
        self._terminate_condition: ConditionType | None = None  # default: lambda: False
        self._progress_condition: ConditionType | None = None  # default: lambda: True

    def _get_after_scheduled_state(
        self: Self
    ) -> AfterScheduled | None:
        if isinstance(timeline_state := self._timeline_state, AfterScheduled):
            return timeline_state
        return None

    def _get_after_launched_state(
        self: Self
    ) -> AfterLaunched | None:
        if isinstance(timeline_state := self._timeline_state, AfterLaunched):
            return timeline_state
        return None

    def _get_after_terminated_state(
        self: Self
    ) -> AfterTerminated | None:
        if isinstance(timeline_state := self._timeline_state, AfterTerminated):
            return timeline_state
        return None

    def _progress(
        self: Self
    ) -> None:
        if self._get_after_scheduled_state() is not None:
            if self._launch_condition is not None and not self._launch_condition():
                return
            self.launch()
        if (timeline_state := self._get_after_launched_state()) is not None:
            self._animation_update(timeline_state.absolute_rate())
            while self._terminate_condition is None or not self._terminate_condition():
                for child in timeline_state.children[:]:
                    child._progress()
                    if child._get_after_terminated_state() is not None:
                        timeline_state.children.remove(child)
                if self._progress_condition is not None and not self._progress_condition():
                    return
                try:
                    timeline_state.construct_coroutine.send(None)
                except StopIteration:
                    break
            self.terminate()
        if self._get_after_terminated_state() is not None:
            return

    def _animation_update(
        self: Self,
        time: float
    ) -> None:
        pass

    @abstractmethod
    async def construct(
        self: Self
    ) -> None:
        pass

    def schedule(
        self: Self,
        parent_absolute_rate: Callable[[], float],
        rate: RateType = Rates.linear(),
        run_time_scale: float = 1.0,
        run_alpha_scale: float = 1.0,
        launch_condition: ConditionType | None = None,
        terminate_condition: ConditionType | None = None
    ) -> None:
        assert self._timeline_state is None
        self._timeline_state = AfterScheduled(
            parent_absolute_rate=parent_absolute_rate,
            rate=rate,
            run_time_scale=run_time_scale,
            run_alpha_scale=run_alpha_scale
        )
        if launch_condition is not None:
            self._launch_condition = launch_condition
        if terminate_condition is not None:
            self._terminate_condition = terminate_condition

    def launch(
        self: Self,
        initial_progress_condition: ConditionType | None = None
    ) -> None:
        assert (timeline_state := self._get_after_scheduled_state()) is not None
        parent_absolute_rate = timeline_state.parent_absolute_rate
        rate = timeline_state.rate
        run_time_scale = timeline_state.run_time_scale
        run_alpha_scale = timeline_state.run_alpha_scale
        initial_alpha = parent_absolute_rate()
        self._timeline_state = AfterLaunched(
            construct_coroutine=self.construct(),
            absolute_rate=lambda: rate((parent_absolute_rate() - initial_alpha) / run_time_scale) * run_alpha_scale,
            children=[]
        )
        if initial_progress_condition is not None:
            self._progress_condition = initial_progress_condition

    def terminate(
        self: Self
    ) -> None:
        assert self._get_after_launched_state() is not None
        self._timeline_state = AfterTerminated()
        self._launch_condition = None
        self._terminate_condition = None
        self._progress_condition = None

    def prepare(
        self: Self,
        timeline: Timeline,
        *,
        # `[0.0, +infty) -> [0.0, +infty), time |-> alpha`
        # Must be an increasing function.
        # Must be `None` if `_run_alpha` is infinity.
        rate: RateType | None = None,
        # Intepreted as "the inverse of run speed" if `_run_alpha` is infinity.
        run_time: float | None = None,
        launch_condition: ConditionType | None = None,
        terminate_condition: ConditionType | None = None
    ) -> None:
        assert (timeline_state := self._get_after_launched_state()) is not None
        if (run_alpha := timeline._run_alpha) == float("inf"):
            assert rate is None
            run_alpha_scale = 1.0
        else:
            run_alpha_scale = run_alpha
        if run_time is None:
            run_time_scale = run_alpha_scale
        else:
            run_time_scale = run_time
        if rate is None:
            rate = Rates.linear()
        timeline.schedule(
            parent_absolute_rate=timeline_state.absolute_rate,
            rate=rate,
            run_time_scale=run_time_scale,
            run_alpha_scale=run_alpha_scale,
            launch_condition=launch_condition,
            terminate_condition=terminate_condition
        )
        timeline_state.children.append(timeline)

    async def wait_until(
        self: Self,
        progress_condition: ConditionType
    ) -> None:
        self._progress_condition = progress_condition
        await asyncio.sleep(0.0)

    # shortcuts

    @property
    def scene(
        self: Self
    ) -> Scene:
        return Toplevel._get_scene()

    async def play(
        self: Self,
        timeline: Timeline,
        rate: RateType | None = None,
        run_time: float | None = None,
        launch_condition: ConditionType | None = None,
        terminate_condition: ConditionType | None = None
    ) -> None:
        self.prepare(
            timeline,
            rate=rate,
            run_time=run_time,
            launch_condition=launch_condition,
            terminate_condition=terminate_condition
        )
        await self.wait_until(timeline.terminated)

    async def wait(
        self: Self,
        delta_alpha: float = 1.0
    ) -> None:
        assert (timeline_state := self._get_after_launched_state()) is not None
        target_alpha = timeline_state.absolute_rate() + delta_alpha
        await self.wait_until(
            lambda: (timeline_state := self._get_after_launched_state()) is None or timeline_state.absolute_rate() >= target_alpha
        )

    def scheduled(
        self: Self
    ) -> bool:
        return bool(self._get_after_scheduled_state() or self._get_after_launched_state() or self._get_after_terminated_state())

    def launched(
        self: Self
    ) -> bool:
        return bool(self._get_after_launched_state() or self._get_after_terminated_state())

    def terminated(
        self: Self
    ) -> bool:
        return bool(self._get_after_terminated_state())
