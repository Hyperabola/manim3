import itertools as it

import numpy as np

from ..custom_typing import (
    Vec2T,
    Vec2sT,
    Vec3T,
    Vec3sT,
    VertexIndexT
)
from ..geometries.geometry import GeometryData
from ..geometries.shape_geometry import ShapeGeometry
from ..lazy.lazy import Lazy
from ..utils.iterables import IterUtils
from ..utils.space import SpaceUtils


class PrismoidGeometry(ShapeGeometry):
    __slots__ = ()

    @Lazy.property_external
    @classmethod
    def _geometry_data_(
        cls,
        shape__multi_line_string__line_strings__points: list[Vec3sT],
        shape__triangulation: tuple[VertexIndexT, Vec2sT]
    ) -> GeometryData:
        position_list: list[Vec3T] = []
        normal_list: list[Vec3T] = []
        uv_list: list[Vec2T] = []
        index_list: list[int] = []
        index_offset = 0
        for line_string_points in shape__multi_line_string__line_strings__points:
            points = SpaceUtils.decrease_dimension(line_string_points)
            # Remove redundant adjacent points to ensure
            # all segments have non-zero lengths.
            # TODO: Shall we normalize winding?
            points_list: list[Vec2T] = [points[0]]
            current_point = points[0]
            for point in points:
                if np.isclose(SpaceUtils.norm(point - current_point), 0.0):
                    continue
                current_point = point
                points_list.append(point)
            if np.isclose(SpaceUtils.norm(current_point - points[0]), 0.0):
                points_list.pop()
            if len(points_list) <= 1:
                continue

            # Assemble side faces.
            triplets: list[tuple[int, Vec2T, Vec2T]] = []
            rotation_mat = np.array(((0.0, 1.0), (-1.0, 0.0)))
            for ip, (p_prev, p, p_next) in enumerate(zip(
                np.roll(points_list, 1, axis=0),
                points_list,
                np.roll(points_list, -1, axis=0),
                strict=True
            )):
                n0 = rotation_mat @ SpaceUtils.normalize(p - p_prev)
                n1 = rotation_mat @ SpaceUtils.normalize(p_next - p)

                angle = abs(np.arccos(np.clip(np.dot(n0, n1), -1.0, 1.0)))
                if angle <= np.pi / 16.0:
                    n_avg = SpaceUtils.normalize(n0 + n1)
                    triplets.append((ip, p, n_avg))
                else:
                    # Vertices shall be duplicated if its connected faces have significantly different normal vectors.
                    triplets.append((ip, p, n0))
                    triplets.append((ip, p, n1))

            ip_iterator, p_iterator, normal_iterator = IterUtils.unzip_triplets(triplets)
            duplicated_points = np.array(list(p_iterator))
            normals = np.array(list(normal_iterator))
            position_list.extend(SpaceUtils.increase_dimension(duplicated_points, z_value=1.0))
            position_list.extend(SpaceUtils.increase_dimension(duplicated_points, z_value=-1.0))
            normal_list.extend(SpaceUtils.increase_dimension(normals))
            normal_list.extend(SpaceUtils.increase_dimension(normals))
            uv_list.extend(duplicated_points)
            uv_list.extend(duplicated_points)

            ips = list(ip_iterator)
            l = len(ips)
            for (i0, ip0), (i1, ip1) in it.islice(it.pairwise(it.cycle(enumerate(ips))), l):
                if ip0 == ip1:
                    continue
                index_list.extend(
                    index_offset + i
                    for i in (i0, i0 + l, i1, i1 + l, i1, i0 + l)
                )
            index_offset += 2 * l

        # Assemble top and bottom faces.
        shape_index, shape_points = shape__triangulation
        for sign in (1.0, -1.0):
            position_list.extend(SpaceUtils.increase_dimension(shape_points, z_value=sign))
            normal_list.extend(SpaceUtils.increase_dimension(np.zeros_like(shape_points), z_value=sign))
            uv_list.extend(shape_points)
            index_list.extend(index_offset + shape_index)
            index_offset += len(shape_points)

        return GeometryData(
            index=np.array(index_list),
            position=np.array(position_list),
            normal=np.array(normal_list),
            uv=np.array(uv_list)
        )
