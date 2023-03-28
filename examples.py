from scipy.spatial.transform import Rotation

from manim3 import *


class TextExample(Scene):
    def construct(self) -> None:
        text = Text("Example Text")
        target = text.copy().shift(RIGHT * 3).set_fill(color="#00ff00")
        for shape, target_shape in zip(text.iter_children(), target.iter_children()):
            self.add(shape)
            if isinstance(shape, ShapeMobject) and isinstance(target_shape, ShapeMobject):
                self.prepare(Transform(shape, target_shape))


class ShapeTransformExample(Scene):
    def construct(self) -> None:
        circle = Circle()
        circle.set_fill(color=BLUE, opacity=0.5)
        circle.set_stroke(color=BLUE_E, width=4)
        square = Square()

        #self.play(ShowCreation(square))
        self.add(square)
        self.wait()
        self.play(Transform(square, circle))
        self.wait(5)


class TexTransformExample(Scene):
    def construct(self) -> None:
        #text = RegularPolygon(3)
        #tex = RegularPolygon(4).set_stroke(width=0.3)
        #self.add(text)
        #self.wait()
        #self.play(Transform(text, tex))
        #self.wait()
        text = Text("Text").scale(3).add_stroke(width=0.2, color=BLUE).add_stroke(width=0.4, color=GREEN).concatenate()
        tex = Tex("Tex").scale(3).set_fill(color=BLUE).set_stroke(width=0.3, color=PINK).concatenate()
        self.add(text)
        #self.wait()
        self.play(Transform(text, tex.shift(RIGHT * 2), replace=True))
        self.wait()
        self.play(Transform(tex, tex.copy().shift(LEFT * 2)))
        self.wait()


class Rotating(Animation):
    def __init__(
        self,
        mobject: Mobject
    ) -> None:

        def alpha_animate_func(
            alpha_0: float,
            alpha: float
        ) -> None:
            mobject.rotate(Rotation.from_rotvec(DOWN * (alpha - alpha_0) * 0.5))

        super().__init__(
            alpha_animate_func=alpha_animate_func,
            alpha_regroup_items=[],
            start_time=0.0,
            stop_time=None
        )


class ThreeDTextExample(Scene):
    def construct(self) -> None:
        self.add_point_light(position=4 * RIGHT + 4 * UP + 2 * OUT)
        text = Text("Text").concatenate()
        text_3d = MeshMobject()
        text_3d._geometry_ = PrismoidGeometry(text._shape_)
        text_3d._model_matrix_ = text._model_matrix_
        text_3d.scale(5.0).stretch_to_fit_depth(0.5)
        text_3d.set_style(color="#00FFAA99")
        self.add(text_3d)
        self.prepare(Rotating(text_3d))
        self.wait(10)


class SceneMobjectExample(Scene):
    def construct(self) -> None:
        scene_0 = SceneMobject(TexTransformExample).scale(0.5).shift(3 * LEFT)
        #scene_1 = SceneMobject(ThreeDTextExample).scale(0.5).shift(3 * RIGHT)
        self.add(scene_0)
        self.play(PlayScene(scene_0))
        self.wait(5)


if __name__ == "__main__":
    config = Config()
    config.tex.use_mathjax = True
    #config.rendering.time_span = (2.0, 3.0)
    #config.rendering.fps = 3
    #config.rendering.preview = False
    #config.rendering.write_video = True
    #config.size.pixel_size = (960, 540)
    #config.rendering.write_last_frame = True
    TexTransformExample.render(config)
