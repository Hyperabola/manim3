import pathlib
from typing import (
    Callable,
    Iterator,
    overload
)

import numpy as np
import svgelements as se
from scipy.interpolate import BSpline

from ..constants.custom_typing import (
    NP_2f8,
    NP_x2f8,
    NP_xf8
)
from ..utils.space import SpaceUtils
from .shape_mobjects.shapes.shape import Shape
from .shape_mobjects.shape_mobject import ShapeMobject


class BezierCurve(BSpline):
    __slots__ = ("_degree",)

    def __init__(
        self,
        control_positions: NP_x2f8
    ) -> None:
        degree = len(control_positions) - 1
        assert degree >= 0
        super().__init__(
            t=np.append(np.zeros(degree + 1), np.ones(degree + 1)),
            c=control_positions,
            k=degree
        )
        self._degree: int = degree

    @overload
    def gamma(
        self,
        sample: float
    ) -> NP_2f8: ...

    @overload
    def gamma(
        self,
        sample: NP_xf8
    ) -> NP_x2f8: ...

    def gamma(
        self,
        sample: float | NP_xf8
    ) -> NP_2f8 | NP_x2f8:
        return self.__call__(sample)

    def get_sample_positions(self) -> NP_x2f8:
        # Approximate the bezier curve with a polyline.

        def smoothen_samples(
            gamma: Callable[[NP_xf8], NP_x2f8],
            samples: NP_xf8,
            bisect_depth: int
        ) -> NP_xf8:
            # Bisect a segment if one of its endpositions has a turning angle above the threshold.
            # Bisect for no more than 4 times, so each curve will be split into no more than 16 segments.
            if bisect_depth == 4:
                return samples
            positions = gamma(samples)
            directions = SpaceUtils.normalize(np.diff(positions, axis=0))
            angle_cosines = (directions[1:] * directions[:-1]).sum(axis=1)
            large_angle_indices = np.flatnonzero(angle_cosines < np.cos(np.pi / 16.0))
            if not len(large_angle_indices):
                return samples
            insertion_indices = np.unique(np.concatenate(
                (large_angle_indices, large_angle_indices + 1)
            ))
            new_samples = np.insert(
                samples,
                insertion_indices + 1,
                (samples[insertion_indices] + samples[insertion_indices + 1]) / 2.0
            )
            return smoothen_samples(gamma, new_samples, bisect_depth + 1)

        if self._degree <= 1:
            start_position = self.gamma(0.0)
            stop_position = self.gamma(1.0)
            if np.isclose(SpaceUtils.norm(stop_position - start_position), 0.0):
                return np.array((start_position,))
            return np.array((start_position, stop_position))
        samples = smoothen_samples(self.gamma, np.linspace(0.0, 1.0, 3), 1)
        return self.gamma(samples)


class SVGMobject(ShapeMobject):
    __slots__ = ()

    def __init__(
        self,
        file_path: str | pathlib.Path | None = None,
        *,
        width: float | None = None,
        height: float | None = None,
        frame_scale: float | None = None
    ) -> None:
        super().__init__()
        if file_path is None:
            return

        svg: se.SVG = se.SVG.parse(file_path)
        bbox: tuple[float, float, float, float] | None = svg.bbox()
        if bbox is None:
            return

        # Handle transform before constructing `ShapeMesh`
        # so that the center of the mesh falls on the origin.
        transform = self._get_transform(
            bbox=bbox,
            width=width,
            height=height,
            frame_scale=frame_scale
        )

        # TODO: handle strokes, etc.
        self.add(*(
            ShapeMobject(
                self._get_shape_from_se_shape(shape * transform)
            ).set_style(
                color=fill.hex if (fill := shape.fill) is not None else None
            )
            for shape in svg.elements()
            if isinstance(shape, se.Shape)
        ))

    @classmethod
    def _get_transform(
        cls,
        bbox: tuple[float, float, float, float],
        width: float | None,
        height: float | None,
        frame_scale: float | None
    ) -> se.Matrix:

        def perspective(
            origin_x: float,
            origin_y: float,
            radius_x: float,
            radius_y: float
        ) -> se.Matrix:
            # `(origin=(0.0, 0.0), radius=(1.0, 1.0))` ->
            # `(origin=(origin_x, origin_y), radius=(radius_x, radius_y))`
            return se.Matrix(
                radius_x,
                0.0,
                0.0,
                radius_y,
                origin_x,
                origin_y
            )

        min_x, min_y, max_x, max_y = bbox
        origin_x = (min_x + max_x) / 2.0
        origin_y = (min_y + max_y) / 2.0
        radius_x = (max_x - min_x) / 2.0
        radius_y = (max_y - min_y) / 2.0
        transform = ~perspective(
            origin_x=origin_x,
            origin_y=origin_y,
            radius_x=radius_x,
            radius_y=radius_y
        )
        scale_x, scale_y = SpaceUtils._get_frame_scale_vector(
            original_width=radius_x * 2.0,
            original_height=radius_y * 2.0,
            specified_width=width,
            specified_height=height,
            specified_frame_scale=frame_scale
        )
        transform *= perspective(
            origin_x=0.0,
            origin_y=0.0,
            radius_x=scale_x * radius_x,
            radius_y=-scale_y * radius_y  # Flip y.
        )
        return transform

    @classmethod
    def _get_shape_from_se_shape(
        cls,
        se_shape: se.Shape
    ) -> Shape:

        def iter_paths_from_se_shape(
            se_shape: se.Shape
        ) -> Iterator[tuple[NP_x2f8, bool]]:
            se_path = se.Path(se_shape.segments(transformed=True))
            se_path.approximate_arcs_with_cubics()
            positions_list: list[NP_2f8] = []
            is_ring: bool = False
            positions_dtype = np.dtype((np.float64, (2,)))
            for segment in se_path.segments(transformed=True):
                match segment:
                    case se.Move(end=end):
                        yield np.fromiter(positions_list, dtype=positions_dtype), is_ring
                        positions_list = [np.array(end)]
                        is_ring = False
                    case se.Close():
                        is_ring = True
                    case se.Line() | se.QuadraticBezier() | se.CubicBezier():
                        control_positions = np.array(segment)
                        positions_list.extend(BezierCurve(control_positions).get_sample_positions()[1:])
                    case _:
                        raise ValueError(f"Cannot handle path segment type: {type(segment)}")
            yield np.fromiter(positions_list, dtype=positions_dtype), is_ring

        return Shape.from_paths(iter_paths_from_se_shape(se_shape))
