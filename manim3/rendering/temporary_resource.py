#__all__ = [
#    "ColorFramebufferBatch",
#    "TransparentFramebufferBatch",
#    "OpaqueFramebufferBatch",
#    "TemporaryResource"
#]


#from abc import (
#    ABC,
#    abstractmethod
#)
#from typing import (
#    Generic,
#    ParamSpec
#)

#import moderngl
#import numpy as np
##import OpenGL.GL as gl

#from ..rendering.config import ConfigSingleton
#from ..rendering.context import Context


#_ResourceParameters = ParamSpec("_ResourceParameters")


#class TemporaryResource(ABC, Generic[_ResourceParameters]):
#    __slots__ = ()

#    _INSTANCE_TO_PARAMETERS_DICT: dict
#    _VACANT_INSTANCES: dict[tuple, list]

#    def __init_subclass__(cls) -> None:
#        super().__init_subclass__()
#        cls._INSTANCE_TO_PARAMETERS_DICT = {}
#        cls._VACANT_INSTANCES = {}

#    def __new__(
#        cls,
#        *args: _ResourceParameters.args,
#        **kwargs: _ResourceParameters.kwargs
#    ):
#        parameters = (*args, *kwargs.values())
#        if (vacant_instances := cls._VACANT_INSTANCES.get(parameters)) is not None and vacant_instances:
#            self = vacant_instances.pop()
#        else:
#            self = super().__new__(cls)
#            self._new_instance(*args, **kwargs)
#            cls._INSTANCE_TO_PARAMETERS_DICT[self] = parameters
#        return self

#    def __init__(
#        self,
#        *args: _ResourceParameters.args,
#        **kwargs: _ResourceParameters.kwargs
#    ) -> None:
#        super().__init__()
#        self._init_instance()

#    def __enter__(self):
#        return self

#    def __exit__(
#        self,
#        exc_type,
#        exc_value,
#        exc_traceback
#    ) -> None:
#        cls = self.__class__
#        parameters = cls._INSTANCE_TO_PARAMETERS_DICT[self]
#        cls._VACANT_INSTANCES.setdefault(parameters, []).append(self)

#    @abstractmethod
#    def _new_instance(
#        self,
#        *args: _ResourceParameters.args,
#        **kwargs: _ResourceParameters.kwargs
#    ) -> None:
#        pass

#    @abstractmethod
#    def _init_instance(self) -> None:
#        pass


##class TemporaryBuffer(TemporaryResource):
##    __slots__ = ("buffer",)

##    def _new_instance(
##        self,
##        *,
##        reserve: int
##    ) -> None:
##        self.buffer: moderngl.Buffer = Context.buffer(reserve=reserve, dynamic=False)

##    def _init_instance(self) -> None:
##        self.buffer.clear()


#class OpaqueFramebufferBatch(TemporaryResource):
#    __slots__ = (
#        "color_texture",
#        "depth_texture",
#        "framebuffer"
#    )

#    def _new_instance(
#        self,
#        size: tuple[int, int] | None = None
#    ) -> None:
#        if size is None:
#            size = ConfigSingleton().size.pixel_size
#        color_texture = Context.texture(
#            size=size,
#            components=4,
#            dtype="f1"
#        )
#        depth_texture = Context.depth_texture(
#            size=size
#        )
#        framebuffer = Context.framebuffer(
#            color_attachments=(color_texture,),
#            depth_attachment=depth_texture
#        )
#        self.color_texture: moderngl.Texture = color_texture
#        self.depth_texture: moderngl.Texture = depth_texture
#        self.framebuffer: moderngl.Framebuffer = framebuffer

#    def _init_instance(self) -> None:
#        self.framebuffer.clear()


#class ColorFramebufferBatch(TemporaryResource):
#    __slots__ = (
#        "color_texture",
#        "depth_texture",
#        "framebuffer"
#    )

#    def _new_instance(
#        self,
#        *,
#        depth_texture: moderngl.Texture
#    ) -> None:
#        #if size is None:
#        #    size = ConfigSingleton().size.pixel_size
#        size: tuple[int, int] = depth_texture.size
#        color_texture = Context.texture(
#            size=size,
#            components=4,
#            dtype="f1"
#        )
#        framebuffer = Context.framebuffer(
#            color_attachments=(color_texture,),
#            depth_attachment=depth_texture
#        )
#        self.color_texture: moderngl.Texture = color_texture
#        self.depth_texture: moderngl.Texture = depth_texture
#        self.framebuffer: moderngl.Framebuffer = framebuffer

#    def _init_instance(self) -> None:
#        self.framebuffer.depth_mask = False
#        self.framebuffer.clear()


#class TransparentFramebufferBatch(TemporaryResource):
#    __slots__ = (
#        #"opaque_texture",
#        "accum_texture",
#        "revealage_texture",
#        "depth_texture",
#        #"opaque_framebuffer",
#        "framebuffer"
#    )

#    def _new_instance(
#        self,
#        *,
#        depth_texture: moderngl.Texture
#        #size: tuple[int, int] | None = None
#    ) -> None:
#        #if size is None:
#        #    size = ConfigSingleton().size.pixel_size
#        #opaque_texture = Context.texture(
#        #    size=size,
#        #    components=4,
#        #    dtype="f1"
#        #)
#        size: tuple[int, int] = depth_texture.size
#        accum_texture = Context.texture(
#            size=size,
#            components=4,
#            dtype="f2"
#        )
#        revealage_texture = Context.texture(
#            size=size,
#            components=1,
#            dtype="f1"
#        )
#        #depth_texture = depth_texture
#        #opaque_framebuffer = Context.framebuffer(
#        #    color_attachments=(opaque_texture,),
#        #    depth_attachment=depth_texture
#        #)
#        framebuffer = Context.framebuffer(
#            color_attachments=(accum_texture, revealage_texture),
#            depth_attachment=depth_texture
#        )
#        #revealage_framebuffer = Context.framebuffer(
#        #    color_attachments=(revealage_texture,),
#        #    depth_attachment=depth_texture
#        #)
#        #self.opaque_texture: moderngl.Texture = opaque_texture
#        self.accum_texture: moderngl.Texture = accum_texture
#        self.revealage_texture: moderngl.Texture = revealage_texture
#        self.depth_texture: moderngl.Texture = depth_texture
#        #self.opaque_framebuffer: moderngl.Framebuffer = opaque_framebuffer
#        self.framebuffer: moderngl.Framebuffer = framebuffer
#        #self.revealage_framebuffer: moderngl.Framebuffer = revealage_framebuffer

#    def _init_instance(self) -> None:
#        #self.opaque_framebuffer.clear()
#        # Test against each fragment by the depth buffer, but never write to it.
#        self.framebuffer.depth_mask = False
#        self.framebuffer.clear()
#        # Initialize `revealage` with 1.0.
#        # TODO: There should be a more elegant way using `clear`.
#        self.revealage_texture.write(np.ones(self.revealage_texture.size, dtype="f2").tobytes())
#        #gl.glBindBuffer(gl.GL_DRAW_BUFFER1)
#        #gl.glClearBufferfv(gl.GL_COLOR, 1, 1.0)  # Initialize `revealage` with 1.0.
#        #self.accum_framebuffer.clear()
#        #self.revealage_framebuffer.clear(red=1.0)
#        #self.accum_framebuffer.depth_mask = False
#        #self.revealage_framebuffer.depth_mask = False