from __future__ import annotations


import itertools
from abc import (
    ABC,
    abstractmethod
)
from typing import (
    Callable,
    ClassVar,
    Self
)
#from typing import TYPE_CHECKING

import numpy as np

from ...constants.constants import (
    ORIGIN,
    PI
)
from ...constants.custom_typing import (
    BoundaryT,
    NP_3f8,
    NP_44f8,
    NP_x3f8
)
from ...lazy.lazy import Lazy
from ...lazy.lazy_object import LazyObject
from ...rendering.buffers.uniform_block_buffer import UniformBlockBuffer
from ...timelines.timeline.timeline import Timeline
from ...utils.space_utils import SpaceUtils
from ..arrays.model_matrix import (
    AffineApplier,
    ModelMatrix
)
from ..animatable.animatable import (
    Animatable,
    Animation
)
from ..animatable.piecewiser import Piecewiser

#if TYPE_CHECKING:
#    from ...models.model.model import model


class Box(LazyObject):
    __slots__ = ()

    def __init__(
        self: Self,
        maximum: NP_3f8,
        minimum: NP_3f8
    ) -> None:
        super().__init__()
        self._maximum_ = maximum
        self._minimum_ = minimum

    @Lazy.variable(hasher=Lazy.array_hasher)
    @staticmethod
    def _maximum_() -> NP_3f8:
        return NotImplemented

    @Lazy.variable(hasher=Lazy.array_hasher)
    @staticmethod
    def _minimum_() -> NP_3f8:
        return NotImplemented

    @Lazy.property(hasher=Lazy.array_hasher)
    @staticmethod
    def _centroid_(
        maximum: NP_3f8,
        minimum: NP_3f8
    ) -> NP_3f8:
        return (maximum + minimum) / 2.0

    @Lazy.property(hasher=Lazy.array_hasher)
    @staticmethod
    def _radii_(
        maximum: NP_3f8,
        minimum: NP_3f8
    ) -> NP_3f8:
        return (maximum - minimum) / 2.0

    def get(
        self: Self,
        direction: NP_3f8 = ORIGIN,
        buff: float | NP_3f8 = 0.0
    ) -> NP_3f8:
        return self._centroid_ + self._radii_ * direction + buff * direction

    def get_radii(
        self: Self
    ) -> NP_3f8:
        return self._radii_

    #def get_centroid(
    #    self: Self
    #) -> NP_3f8:
    #    return self._centroid_

    #@property
    #def center(self) -> NP_3f8:
    #    return (self.maximum + self.minimum) / 2.0

    #@property
    #def radii(self) -> NP_3f8:
    #    radii = (self.maximum - self.minimum) / 2.0
    #    # For zero-width dimensions of radii, thicken a little bit to avoid zero division.
    #    radii[np.isclose(radii, 0.0)] = 1e-8
    #    return radii


class Model(Animatable):
    __slots__ = ("_model_actions",)

    _special_slot_copiers: ClassVar[dict[str, Callable]] = {
        "_model_actions": lambda o: []
    }

    def __init__(
        self: Self
    ) -> None:
        super().__init__()
        self._model_actions: list[ModelAction] = []
        #self._reset_animations()

    @Lazy.variable(freeze=False)
    @staticmethod
    def _model_matrix_() -> ModelMatrix:
        return ModelMatrix()

    @Lazy.variable_collection()
    @staticmethod
    def _associated_models_() -> tuple[Model, ...]:
        return ()

    @Lazy.property()
    @staticmethod
    def _model_uniform_block_buffer_(
        model_matrix__array: NP_44f8
    ) -> UniformBlockBuffer:
        return UniformBlockBuffer(
            name="ub_model",
            fields=[
                "mat4 u_model_matrix"
            ],
            data={
                "u_model_matrix": model_matrix__array.T
            }
        )

    @Lazy.property(hasher=Lazy.array_hasher)
    @staticmethod
    def _local_sample_positions_() -> NP_x3f8:
        return np.zeros((0, 3))

    @Lazy.property(hasher=Lazy.array_hasher)
    @staticmethod
    def _world_sample_positions_(
        model_matrix__applier: AffineApplier,
        local_sample_positions: NP_x3f8,
    ) -> NP_x3f8:
        return model_matrix__applier.apply_multiple(local_sample_positions)

    #@Lazy.property(hasher=Lazy.array_hasher)
    #@staticmethod
    #def _box_reference_points_(
    #    world_sample_positions: NP_x3f8,
    #) -> NP_x3f8:
    #    return world_sample_positions

    #@Lazy.variable(hasher=Lazy.array_hasher)
    #@staticmethod
    #def _centroid_() -> NP_3f8:
    #    return np.zeros((3,))

    #@Lazy.variable(hasher=Lazy.array_hasher)
    #@staticmethod
    #def _radii_() -> NP_3f8:
    #    return np.zeros((3,))

    @Lazy.property()
    @staticmethod
    def _box_(
        world_sample_positions: NP_x3f8,
        associated_models__world_sample_positions: tuple[NP_x3f8, ...]
    ) -> Box:
        sample_positions = np.concatenate((
            world_sample_positions,
            *associated_models__world_sample_positions
        ))
        if not len(sample_positions):
            return Box(
                maximum=np.zeros((3,)),
                minimum=np.zeros((3,))
            )
        return Box(
            maximum=sample_positions.max(axis=0),
            minimum=sample_positions.min(axis=0)
        )

    #@Lazy.property(hasher=Lazy.array_hasher)
    #@staticmethod
    #def _centroid_(
    #    box: Box
    #) -> NP_3f8:
    #    return (box.maximum + box.minimum) / 2.0

    #@Lazy.property(hasher=Lazy.array_hasher)
    #@staticmethod
    #def _radii_(
    #    box: Box
    #) -> NP_3f8:
    #    return (box.maximum - box.minimum) / 2.0
    #    # For zero-width dimensions of radii, thicken a little bit to avoid zero division.
    #    #radii[np.isclose(radii, 0.0)] = 1e-8
    #    #return radii

    #def get_box_position(
    #    self,
    #    direction: NP_3f8,
    #    buff: NP_3f8 = ORIGIN
    #) -> NP_3f8:
    #    return self._box_.get(direction, buff)

    #def get_centroid(self) -> NP_3f8:
    #    return self._box_._centroid_

    def copy(
        self: Self
    ) -> Self:
        result = super().copy()
        associated_models = self._associated_models_
        associated_models_copy = tuple(
            super(Model, associated_model).copy()
            for associated_model in associated_models
        )
        result._associated_models_ = associated_models_copy
        for associated_model_copy in associated_models_copy:
            associated_model_copy._associated_models_ = tuple(
                associated_models_copy[associated_models.index(associated_model)]
                for associated_model in associated_model_copy._associated_models_
            )
        return result

    @property
    def box(
        self: Self
    ) -> Box:
        return self._box_

    #@classmethod
    #def _split(
    #    cls: type[_ModelT],
    #    dst_tuple: tuple[_ModelT, ...],
    #    src: _ModelT,
    #    alphas: NP_xf8
    #) -> None:
    #    super()._split(dst_tuple, src, alphas)
    #    for dst_tuple_associated, src_assiciated in zip(
    #        tuple(dst._associated_models_ for dst in dst_tuple), src._associated_models_, strict=True
    #    ):
    #        super()._split(dst_tuple_associated, src_assiciated, alphas)

    #@classmethod
    #def _concatenate(
    #    cls: type[_ModelT],
    #    dst: _ModelT,
    #    src_tuple: tuple[_ModelT, ...]
    #) -> None:
    #    super()._concatenate(dst, src_tuple)
    #    for dst_associated, src_tuple_assiciated in zip(
    #        dst._associated_models_, tuple(src._associated_models_ for src in src_tuple), strict=True
    #    ):
    #        super()._concatenate(dst_associated, src_tuple_assiciated)

    #def _apply_directly(
    #    self,
    #    matrix: NP_44f8
    #):
    #    self._model_matrix_._apply(matrix)
    #    for associated_model in self._associated_models_:
    #        associated_model._model_matrix_._apply(matrix)
    #    return self

    def _reset_animations(
        self: Self
    ) -> None:
        super()._reset_animations()
        self._model_actions.clear()
        #model_animation = ModelAnimation(model_matrices={
        #    model_assiciated._model_matrix_: model_assiciated._model_matrix_._array_
        #    for model_assiciated in (self, *self._associated_models_)
        #})
        #self._model_animation = model_animation
        #self._animations.append(model_animation)

    def _submit_timeline(
        self: Self
    ) -> Timeline:
        self._animations.append(ModelAnimation(tuple(self._model_actions)))
        return super()._submit_timeline()

    def _get_interpolate_animations(
        self: Self,
        src_0: Self,
        src_1: Self
    ) -> list[Animation]:
        animations = super()._get_interpolate_animations(src_0, src_1)
        animations.extend(itertools.chain.from_iterable(
            super(Model, dst_associated)._get_interpolate_animations(src_0_assiciated, src_1_assiciated)
            for dst_associated, src_0_assiciated, src_1_assiciated in zip(
                self._associated_models_, src_0._associated_models_, src_1._associated_models_, strict=True
            )
        ))
        return animations

    def _get_piecewise_animations(
        self: Self,
        src: Self,
        piecewiser: Piecewiser
    ) -> list[Animation]:
        animations = super()._get_piecewise_animations(src, piecewiser)
        animations.extend(itertools.chain.from_iterable(
            super(Model, dst_associated)._get_piecewise_animations(src_assiciated, piecewiser)
            for dst_associated, src_assiciated in zip(
                self._associated_models_, src._associated_models_, strict=True
            )
        ))
        return animations

    def _stack_model_action(
        self: Self,
        model_action: ModelAction
    ) -> None:
        #for animation in animations:
        #    animation.update_boundary(1)
        ##if self._saved_state is not None:
        #self._animations.extend(animations)
        model_action._act(1.0)
        self._model_actions.append(model_action)

    def shift(
        self: Self,
        vector: NP_3f8,
        mask: float | NP_3f8 = 1.0
    ) -> Self:
        self._stack_model_action(ModelShiftAction(
            model=self,
            vector=vector,
            mask=mask * np.ones((3,))
        ))
        return self

    def move_to(
        self: Self,
        target: Model,
        direction: NP_3f8 = ORIGIN,
        buff: float | NP_3f8 = 0.0,
        mask: float | NP_3f8 = 1.0,
        direction_sign: float = 1.0
    ) -> Self:
        self.shift(
            vector=target.box.get(direction) - self.box.get(direction_sign * direction, buff),
            mask=mask
        )
        #signed_direction = direction_sign * direction
        #self._stack_model_action(ModelShiftToAction(
        #    model=self,
        #    target=target,
        #    direction=direction,
        #    buff=buff * np.ones((3,)),
        #    mask=mask * np.ones((3,)),
        #    direction_sign=direction_sign
        #    #buff_vector=self.get_box_position(signed_direction) + buff * signed_direction,
        #    #initial_model=self
        #))
        return self

    #def move_to(
    #    self: Self,
    #    target: Model,
    #    direction: NP_3f8 = ORIGIN,
    #    buff: float | NP_3f8 = 0.0,
    #    mask: float | NP_3f8 = 1.0
    #) -> Self:
    #    self.shift_to(
    #        target=target,
    #        direction=direction,
    #        buff=buff,
    #        mask=mask,
    #        direction_sign=1.0
    #    )
    #    return self

    def next_to(
        self: Self,
        target: Model,
        direction: NP_3f8 = ORIGIN,
        buff: float | NP_3f8 = 0.0,
        mask: float | NP_3f8 = 1.0,
        direction_sign: float = -1.0
    ) -> Self:
        self.move_to(
            target=target,
            direction=direction,
            buff=buff,
            mask=mask,
            direction_sign=direction_sign
        )
        return self

    def scale(
        self: Self,
        factor: float | NP_3f8,
        about: Model | None = None,
        direction: NP_3f8 = ORIGIN,
        mask: float | NP_3f8 = 1.0
    ) -> Self:
        if about is None:
            about = self
        self._stack_model_action(ModelScaleAction(
            model=self,
            factor=factor * np.ones((3,)),
            about=about,
            direction=direction,
            mask=mask * np.ones((3,))
        ))
        return self

    def scale_about_origin(
        self: Self,
        factor: float | NP_3f8,
        mask: float | NP_3f8 = 1.0
    ) -> Self:
        self.scale(
            factor=factor,
            about=Model(),
            mask=mask
        )
        return self

    def scale_to(
        self: Self,
        target: Model,
        about: Model | None = None,
        direction: NP_3f8 = ORIGIN,
        mask: float | NP_3f8 = 1.0
    ) -> Self:
        self.scale(
            factor=target.box.get_radii() / np.maximum(self.box.get_radii(), 1e-8),
            about=about,
            direction=direction,
            mask=mask
        )
        #if about is None:
        #    about = self
        
        #self._stack_model_action(ModelScaleToAction(
        #    model=self,
        #    target=target,
        #    #radii=self._radii_,
        #    about=about,
        #    direction=direction,
        #    mask=mask * np.ones((3,))
        #    #initial_model=self
        #))
        #factor = target / self.get_box_size()
        #self.scale(
        #    vector=target_size / (2.0 * self_copy._radii_),
        #    about=about,
        #    direction=direction,
        #    mask=mask
        #)
        return self

    def match_box(
        self: Self,
        model: Model,
        mask: float | NP_3f8 = 1.0
    ) -> Self:
        self.scale_to(model, mask=mask).move_to(model, mask=mask)
        #self.shift(-self.get_center()).scale_to(model.get_box_size()).shift(model.get_center())
        return self

    def rotate(
        self: Self,
        rotvec: NP_3f8,
        about: Model | None = None,
        direction: NP_3f8 = ORIGIN,
        mask: float | NP_3f8 = 1.0
    ) -> Self:
        if about is None:
            about = self
        self._stack_model_action(ModelRotateAction(
            model=self,
            rotvec=rotvec,
            about=about,
            direction=direction,
            mask=mask * np.ones((3,))
        ))
        return self

    def rotate_about_origin(
        self: Self,
        rotvec: NP_3f8,
        mask: float | NP_3f8 = 1.0
    ) -> Self:
        self.rotate(
            rotvec=rotvec,
            about=Model(),
            mask=mask
        )
        return self

    def flip(
        self: Self,
        axis: NP_3f8,
        about: Model | None = None,
        direction: NP_3f8 = ORIGIN,
        mask: float | NP_3f8 = 1.0
    ) -> Self:
        self.rotate(
            rotvec=SpaceUtils.normalize(axis) * PI,
            about=about,
            direction=direction,
            mask=mask
        )
        return self

    def apply(
        self: Self,
        matrix: NP_44f8,
        about: Model | None = None,
        direction: NP_3f8 = ORIGIN
    ) -> Self:
        if about is None:
            about = self
        self._stack_model_action(ModelApplyAction(
            model=self,
            matrix=matrix,
            about=about,
            direction=direction
        ))
        return self

    #def pose(
    #    self: Self,
    #    target: Model
    #    #about: "Model | None" = None,
    #    #direction: NP_3f8 = ORIGIN
    #) -> Self:
    #    #if about is None:
    #    #    about = self
    #    self._stack_model_action(ModelPoseAction(
    #        model=self,
    #        target=target,
    #        #matrix=self._matrix_,
    #        #about=about,
    #        #direction=direction
    #        #initial_model=self
    #    ))
    #    return self


class ModelAnimation(Animation):
    __slots__ = ("_model_actions",)

    def __init__(
        self: Self,
        model_actions: tuple[ModelAction, ...]
    ) -> None:
        super().__init__()
        self._model_actions: tuple[ModelAction, ...] = model_actions
        #self._model: Model = model
        #self._model_matrices: dict[ModelMatrix, NP_44f8] = model_matrices

    def update(
        self: Self,
        alpha: float
    ) -> None:
        super().update(alpha)
        for model_action in reversed(self._model_actions):
            model_action._restore()
        for model_action in self._model_actions:
            model_action._act(alpha)

    def update_boundary(
        self: Self,
        boundary: BoundaryT
    ) -> None:
        super().update_boundary(boundary)
        self.update(float(boundary))


class ModelAction(ABC):
    __slots__ = (
        "_pre_shift_matrix",
        "_post_shift_matrix",
        "_model_matrices"
    )

    def __init__(
        self: Self,
        model: Model,
        #factor: float | NP_3f8,
        about: Model,
        direction: NP_3f8
    ) -> None:
        #if not isinstance(factor, np.ndarray):
        #    factor *= np.ones((3,))
        #assert (factor >= 0.0).all(), "Scale factor must be positive"
        #factor = np.maximum(factor, 1e-8)
        #super().__init__()
        #self._factor: NP_3f8 = factor
        super().__init__()
        #self._model: Model = model
        about_point = about.box.get(direction)
        self._pre_shift_matrix: NP_44f8 = SpaceUtils.matrix_from_shift(-about_point)
        self._post_shift_matrix: NP_44f8 = SpaceUtils.matrix_from_shift(about_point)
        self._model_matrices: dict[ModelMatrix, NP_44f8] = {
            model_assiciated._model_matrix_: model_assiciated._model_matrix_._array_
            for model_assiciated in (model, *model._associated_models_)
        }
        #self._about_ = about
        #self._direction_ = direction

    #@Lazy.variable(freeze=False)
    #@staticmethod
    #def _about_() -> Model:
    #    return NotImplemented

    #@Lazy.variable(hasher=Lazy.array_hasher)
    #@staticmethod
    #def _direction_() -> NP_3f8:
    #    return NotImplemented

    #@Lazy.property(hasher=Lazy.array_hasher)
    #@staticmethod
    #def _about_point_(
    #    about__box: Box,
    #    direction: NP_3f8
    #) -> NP_3f8:
    #    return about__box.get(direction)

    #@Lazy.property(hasher=Lazy.array_hasher)
    #@staticmethod
    #def _pre_shift_matrix_(
    #    about_point: NP_3f8
    #) -> NP_44f8:
    #    return SpaceUtils.matrix_from_shift(-about_point)

    #@Lazy.property(hasher=Lazy.array_hasher)
    #@staticmethod
    #def _post_shift_matrix_(
    #    about_point: NP_3f8
    #) -> NP_44f8:
    #    return SpaceUtils.matrix_from_shift(about_point)

    @abstractmethod
    def _get_matrix(
        self: Self,
        alpha: float
    ) -> NP_44f8:
        pass

    def _restore(
        self: Self
    ) -> None:
        for model_matrix, initial_model_matrix_array in self._model_matrices.items():
            model_matrix._array_ = initial_model_matrix_array

    def _act(
        self: Self,
        alpha: float
    ) -> None:
        matrix = self._post_shift_matrix @ self._get_matrix(alpha) @ self._pre_shift_matrix
        for model_matrix in self._model_matrices:
            model_matrix._array_ = matrix @ model_matrix._array_

    #def restore(
    #    self: Self
    #) -> None:
    #    for model_matrix, initial_matrix in self._model_matrices.items():
    #        model_matrix._array_ = initial_matrix
    #    super().restore()  # TODO: order

    #def initial_update(self) -> None:
    #    self.update(0.0)

    #def final_update(self) -> None:
    #    self.update(1.0)


#class ModelAbstractShiftAnimation(ModelAnimation):
#    __slots__ = ("_mask",)

#    def __init__(
#        self,
#        mask: NP_3f8
#    ) -> None:
#        super().__init__(
#            about=Model(),
#            direction=ORIGIN
#        )
#        #self._vector: NP_3f8 = vector
#        self._mask: NP_3f8 = mask

#    @Lazy.property(hasher=Lazy.array_hasher)
#    @staticmethod
#    def _vector_() -> NP_3f8:
#        return NotImplemented

#    def _get_matrix(
#        self,
#        alpha: float
#    ) -> NP_44f8:
#        return SpaceUtils.matrix_from_shift(self._vector_ * (self._mask * alpha))


#class ModelAbstractScaleAnimation(ModelAnimation):
#    __slots__ = ("_mask",)

#    def __init__(
#        self,
#        #factor: float | NP_3f8,
#        about: Model,
#        direction: NP_3f8,
#        mask: NP_3f8
#    ) -> None:
#        #if not isinstance(factor, np.ndarray):
#        #    factor *= np.ones((3,))
#        #assert (factor >= 0.0).all(), "Scale factor must be positive"
#        #factor = np.maximum(factor, 1e-8)
#        #super().__init__()
#        #self._factor: NP_3f8 = factor
#        #self._about_ = about
#        #self._direction_ = direction
#        super().__init__(
#            about=about,
#            direction=direction
#        )
#        self._mask: NP_3f8 = mask

#    #@Lazy.variable(hasher=Lazy.array_hasher)
#    #@staticmethod
#    #def _mask_() -> NP_3f8:
#    #    return NotImplemented

#    @Lazy.property(hasher=Lazy.array_hasher)
#    @staticmethod
#    def _factor_() -> NP_3f8:
#        return NotImplemented

#    def _get_matrix(
#        self,
#        alpha: float
#    ) -> NP_44f8:
#        return SpaceUtils.matrix_from_scale(self._factor_ ** (self._mask * alpha))


#class ModelAbstractRotateAnimation(ModelAnimation):
#    __slots__ = ("_mask",)

#    def __init__(
#        self,
#        #vector: NP_3f8,
#        about: Model,
#        direction: NP_3f8,
#        mask: NP_3f8
#    ) -> None:
#        #super().__init__()
#        #self._vector: NP_3f8 = vector
#        super().__init__(
#            about=about,
#            direction=direction
#        )
#        self._mask: NP_3f8 = mask
#        #self._mask_ = mask

#    #@Lazy.variable(hasher=Lazy.array_hasher)
#    #@staticmethod
#    #def _mask_() -> NP_3f8:
#    #    return NotImplemented

#    @Lazy.property(hasher=Lazy.array_hasher)
#    @staticmethod
#    def _rotvec_() -> NP_3f8:
#        return NotImplemented

#    def _get_matrix(
#        self,
#        alpha: float
#    ) -> NP_44f8:
#        return SpaceUtils.matrix_from_rotate(self._rotvec_ * (self._mask * alpha))


#class ModelAbstractTransformationAnimation(ModelAnimation):
#    __slots__ = ()

#    def __init__(
#        self,
#        #vector: NP_3f8,
#        about: Model,
#        direction: NP_3f8
#    ) -> None:
#        #super().__init__()
#        #self._vector: NP_3f8 = vector
#        super().__init__(
#            about=about,
#            direction=direction
#        )
#        #self._mask: NP_3f8 = mask
#        #self._mask_ = mask

#    #@Lazy.variable(hasher=Lazy.array_hasher)
#    #@staticmethod
#    #def _mask_() -> NP_3f8:
#    #    return NotImplemented

#    @Lazy.property(hasher=Lazy.array_hasher)
#    @staticmethod
#    def _matrix_() -> NP_44f8:
#        return NotImplemented

#    def _get_matrix(
#        self,
#        alpha: float
#    ) -> NP_44f8:
#        return self._matrix_ * alpha


class ModelShiftAction(ModelAction):
    __slots__ = (
        "_vector",
        "_mask"
    )

    def __init__(
        self: Self,
        model: Model,
        vector: NP_3f8,
        mask: NP_3f8
    ) -> None:
        super().__init__(
            model=model,
            about=Model(),
            direction=ORIGIN
        )
        self._vector: NP_3f8 = vector
        self._mask: NP_3f8 = mask

    def _get_matrix(
        self: Self,
        alpha: float
    ) -> NP_44f8:
        return SpaceUtils.matrix_from_shift(self._vector * (self._mask * alpha))

    #@Lazy.variable(hasher=Lazy.array_hasher)
    #@staticmethod
    #def _mask_() -> NP_3f8:
    #    return NotImplemented

    #@Lazy.property(hasher=Lazy.array_hasher)
    #@staticmethod
    #def _shift_vector_(
    #    vector: NP_3f8,
    #    mask: NP_3f8
    #) -> NP_3f8:
    #    return vector * mask


#class ModelShiftToAction(ModelAction):
#    __slots__ = ("_mask",)

#    def __init__(
#        self: Self,
#        model: Model,
#        target: Model,
#        direction: NP_3f8,
#        buff: NP_3f8,
#        #buff_vector: NP_3f8,
#        mask: NP_3f8,
#        direction_sign: float
#        #initial_model: Model
#    ) -> None:
#        super().__init__(
#            model=model,
#            about=Model(),
#            direction=ORIGIN
#        )
#        self._target_ = target
#        self._direction_ = direction
#        self._buff_vector_ = (
#            model.box.get(direction_sign * direction, buff)
#        )
#        self._mask: NP_3f8 = mask

#    @Lazy.variable(freeze=False)
#    @staticmethod
#    def _target_() -> Model:
#        return NotImplemented

#    @Lazy.variable(hasher=Lazy.array_hasher)
#    @staticmethod
#    def _direction_() -> NP_3f8:
#        return NotImplemented

#    @Lazy.variable(hasher=Lazy.array_hasher)
#    @staticmethod
#    def _buff_vector_() -> NP_3f8:
#        return NotImplemented

#    #@Lazy.variable(hasher=Lazy.array_hasher)
#    #@staticmethod
#    #def _mask_() -> NP_3f8:
#    #    return NotImplemented

#    @Lazy.property(hasher=Lazy.array_hasher)
#    @staticmethod
#    def _vector_(
#        target__box: Box,
#        direction: NP_3f8,
#        buff_vector: NP_3f8
#    ) -> NP_3f8:
#        return target__box.get(direction) - buff_vector

#    def _get_matrix(
#        self: Self,
#        alpha: float
#    ) -> NP_44f8:
#        return SpaceUtils.matrix_from_shift(self._vector_ * (self._mask * alpha))


class ModelScaleAction(ModelAction):
    __slots__ = (
        "_factor",
        "_mask"
    )

    def __init__(
        self: Self,
        model: Model,
        factor: NP_3f8,
        about: Model,
        direction: NP_3f8,
        mask: NP_3f8
    ) -> None:
        assert (factor >= 0.0).all(), "Scale vector must be positive"
        factor = np.maximum(factor, 1e-8)
        super().__init__(
            model=model,
            about=about,
            direction=direction
        )
        self._factor: NP_3f8 = factor
        self._mask: NP_3f8 = mask

    def _get_matrix(
        self: Self,
        alpha: float
    ) -> NP_44f8:
        return SpaceUtils.matrix_from_scale(self._factor ** (self._mask * alpha))

    #@Lazy.variable(hasher=Lazy.array_hasher)
    #@staticmethod
    #def _mask_() -> NP_3f8:
    #    return NotImplemented

    #@Lazy.property(hasher=Lazy.array_hasher)
    #@staticmethod
    #def _scale_vector_(
    #    vector: NP_3f8,
    #    mask: NP_3f8
    #) -> NP_3f8:
    #    return np.maximum(vector * mask, 1e-8)


#class ModelScaleToAction(ModelAction):
#    __slots__ = ("_mask",)

#    def __init__(
#        self: Self,
#        model: Model,
#        target: Model,
#        #radii: NP_3f8,
#        about: Model,
#        direction: NP_3f8,
#        mask: NP_3f8
#        #initial_model: Model
#    ) -> None:
#        #assert (target_size >= 0.0).all(), "Scale vector must be positive"
#        #target_size = np.maximum(target_size, 1e-8)
#        super().__init__(
#            model=model,
#            about=about,
#            direction=direction
#        )
#        self._target_ = target
#        self._initial_radii_ = model.box._radii_
#        #self._target: Model = target
#        self._mask: NP_3f8 = mask
#        #self._target_size_ = target_size
#        #self._mask_ = mask

#    @Lazy.variable(freeze=False)
#    @staticmethod
#    def _target_() -> Model:
#        return NotImplemented

#    @Lazy.variable(hasher=Lazy.array_hasher)
#    @staticmethod
#    def _initial_radii_() -> NP_3f8:
#        return NotImplemented

#    @Lazy.property(hasher=Lazy.array_hasher)
#    @staticmethod
#    def _factor_(
#        target__box__radii: NP_3f8,
#        initial_radii: NP_3f8
#    ) -> NP_3f8:
#        return target__box__radii / np.maximum(initial_radii, 1e-8)

#    def _get_matrix(
#        self: Self,
#        alpha: float
#    ) -> NP_44f8:
#        #self._targeted_box_ = self._target.box
#        return SpaceUtils.matrix_from_scale(self._factor_ ** (self._mask * alpha))


class ModelRotateAction(ModelAction):
    __slots__ = (
        "_rotvec",
        "_mask"
    )

    def __init__(
        self: Self,
        model: Model,
        rotvec: NP_3f8,
        about: Model,
        direction: NP_3f8,
        mask: NP_3f8
    ) -> None:
        super().__init__(
            model=model,
            about=about,
            direction=direction
        )
        self._rotvec: NP_3f8 = rotvec
        self._mask: NP_3f8 = mask
        #self._mask_ = mask

    def _get_matrix(
        self: Self,
        alpha: float
    ) -> NP_44f8:
        return SpaceUtils.matrix_from_rotate(self._rotvec * (self._mask * alpha))

    #@Lazy.variable(hasher=Lazy.array_hasher)
    #@staticmethod
    #def _mask_() -> NP_3f8:
    #    return NotImplemented

    #@Lazy.property(hasher=Lazy.array_hasher)
    #@staticmethod
    #def _rotate_vector_(
    #    vector: NP_3f8,
    #    mask: NP_3f8
    #) -> NP_3f8:
    #    return vector * mask


class ModelApplyAction(ModelAction):
    __slots__ = ("_matrix",)

    def __init__(
        self: Self,
        model: Model,
        matrix: NP_44f8,
        about: Model,
        direction: NP_3f8
    ) -> None:
        super().__init__(
            model=model,
            about=about,
            direction=direction
        )
        self._matrix: NP_44f8 = matrix

    def _get_matrix(
        self: Self,
        alpha: float
    ) -> NP_44f8:
        return SpaceUtils.lerp(np.identity(4), self._matrix, alpha)


#class ModelPoseAction(ModelAction):
#    __slots__ = ()

#    def __init__(
#        self: Self,
#        model: Model,
#        target: Model
#        #matrix: NP_44f8,
#        #about: Model,
#        #direction: NP_3f8
#        #initial_model: Model
#    ) -> None:
#        super().__init__(
#            model=model,
#            about=Model(),
#            direction=ORIGIN
#        )
#        self._target_ = target
#        self._initial_model_matrix_inverse_ = np.linalg.inv(model._model_matrix_._array_)

#    @Lazy.variable(freeze=False)
#    @staticmethod
#    def _target_() -> Model:
#        return NotImplemented

#    @Lazy.property(hasher=Lazy.array_hasher)
#    @staticmethod
#    def _initial_model_matrix_inverse_() -> NP_44f8:
#        return NotImplemented

#    @Lazy.property(hasher=Lazy.array_hasher)
#    @staticmethod
#    def _matrix_(
#        target__model_matrix__array: NP_44f8,
#        initial_model_matrix_inverse: NP_44f8
#    ) -> NP_44f8:
#        return target__model_matrix__array @ initial_model_matrix_inverse

#    def _get_matrix(
#        self: Self,
#        alpha: float
#    ) -> NP_44f8:
#        return self._matrix_ * alpha
