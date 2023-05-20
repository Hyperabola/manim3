from abc import (
    ABC,
    abstractmethod
)
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
import hashlib
import itertools as it
import pathlib
import re
from typing import (
    Any,
    Callable,
    ClassVar,
    Iterable,
    Iterator
)
import warnings

from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist

from ..config import ConfigSingleton
from ..custom_typing import SelectorT
from ..mobjects.mobject import AlignMobject
from ..mobjects.shape_mobject import ShapeMobject
from ..mobjects.svg_mobject import SVGMobject
from ..utils.color import ColorUtils


class CommandFlag(Enum):
    OPEN = 1
    CLOSE = -1
    OTHER = 0


class EdgeFlag(Enum):
    START = 1
    STOP = -1

    def __neg__(self) -> "EdgeFlag":
        return EdgeFlag(-self.get_value())

    def get_value(self) -> int:
        return self.value


class Span:
    __slots__ = (
        "start",
        "stop"
    )

    def __init__(
        self,
        start: int,
        stop: int
    ) -> None:
        assert start <= stop, f"Invalid span: ({start}, {stop})"
        self.start: int = start
        self.stop: int = stop

    def __contains__(
        self,
        span: "Span"
    ) -> bool:
        return self.start <= span.start and self.stop >= span.stop

    def as_slice(self) -> slice:
        return slice(self.start, self.stop)

    def get_edge_index(
        self,
        edge_flag: EdgeFlag
    ) -> int:
        return self.start if edge_flag == EdgeFlag.START else self.stop


@dataclass(
    frozen=True,
    kw_only=True,
    slots=True
)
class ConfiguredItem:
    span: Span
    attrs: dict[str, str]


@dataclass(
    frozen=True,
    kw_only=True,
    slots=True
)
class IsolatedItem:
    span: Span


@dataclass(
    frozen=True,
    kw_only=True,
    slots=True
)
class ProtectedItem:
    span: Span


@dataclass(
    frozen=True,
    kw_only=True,
    slots=True
)
class CommandItem:
    match_obj: re.Match[str]

    @property
    def span(self) -> Span:
        return Span(*self.match_obj.span())


@dataclass(
    frozen=True,
    kw_only=True,
    slots=True
)
class LabelledItem:
    label: int
    span: Span
    attrs: dict[str, str]


@dataclass(
    frozen=True,
    kw_only=True,
    slots=True
)
class LabelledInsertionItem:
    labelled_item: LabelledItem
    edge_flag: EdgeFlag

    @property
    def span(self) -> Span:
        index = self.labelled_item.span.get_edge_index(self.edge_flag)
        return Span(index, index)


@dataclass(
    frozen=True,
    kw_only=True,
    slots=True
)
class LabelledShapeItem:
    label: int
    shape_mobject: ShapeMobject


@dataclass(
    frozen=True,
    kw_only=True,
    slots=True
)
class ShapeItem:
    span: Span
    shape_mobject: ShapeMobject


@dataclass(
    frozen=True,
    kw_only=True,
    slots=True
)
class ParsingResult:
    shape_items: list[ShapeItem]
    specified_part_items: list[tuple[str, list[ShapeMobject]]]
    group_part_items: list[tuple[str, list[ShapeMobject]]]


class StringFileWriter(ABC):
    __slots__ = (
        "_parameters",
    )

    _dir_name: ClassVar[str]

    def __init__(
        self,
        **parameters: Any
    ) -> None:
        super().__init__()
        self._parameters: dict[str, Any] = parameters

    def get_svg_file(
        self,
        content: str
    ) -> pathlib.Path:
        parameters = self._parameters
        cls = type(self)
        hash_content = str((content, *parameters.values()))
        svg_path = cls.get_svg_path(hash_content)
        if not svg_path.exists():
            with cls.display_during_execution(content):
                cls.create_svg_file(content, svg_path, **parameters)
        return svg_path

    @classmethod
    @abstractmethod
    def create_svg_file(
        cls,
        content: str,
        svg_path: pathlib.Path,
        **parameters: Any
    ) -> None:
        pass

    @classmethod
    def get_svg_path(
        cls,
        hash_content: str
    ) -> pathlib.Path:
        # Truncating at 16 bytes for cleanliness.
        hex_string = hashlib.sha256(hash_content.encode()).hexdigest()[:16]
        svg_dir = ConfigSingleton().path.get_output_subdir(cls._dir_name)
        return svg_dir.joinpath(f"{hex_string}.svg")

    @classmethod
    @contextmanager
    def display_during_execution(
        cls,
        string: str
    ) -> Iterator[None]:
        max_characters = 60
        summary = string.replace("\n", "")
        if len(summary) > max_characters:
            summary = f"{summary[:max_characters - 3]}..."
        message = f"Writing \"{summary}\""
        try:
            print(message, end="\r")
            yield
        finally:
            print(" " * len(message), end="\r")


class StringParser(ABC):
    __slots__ = ("_parsing_result",)

    def __init__(
        self,
        string: str,
        isolate: Iterable[SelectorT],
        protect: Iterable[SelectorT],
        local_attrs: dict[SelectorT, dict[str, str]],
        global_attrs: dict[str, str],
        file_writer: StringFileWriter,
        frame_scale: float
    ) -> None:
        super().__init__()
        self._parsing_result: ParsingResult = self.parse(
            string=string,
            isolate=isolate,
            protect=protect,
            local_attrs=local_attrs,
            global_attrs=global_attrs,
            file_writer=file_writer,
            frame_scale=frame_scale
        )

    @classmethod
    def parse(
        cls,
        string: str,
        isolate: Iterable[SelectorT],
        protect: Iterable[SelectorT],
        local_attrs: dict[SelectorT, dict[str, str]],
        global_attrs: dict[str, str],
        file_writer: StringFileWriter,
        frame_scale: float
    ) -> ParsingResult:
        labelled_items, replaced_items = cls.get_labelled_items_and_replaced_items(
            string=string,
            isolate=isolate,
            protect=protect,
            local_attrs=local_attrs
        )
        replaced_spans = [replaced_item.span for replaced_item in replaced_items]
        original_pieces = [
            string[start:stop]
            for start, stop in zip(
                [interval_span.stop for interval_span in replaced_spans[:-1]],
                [interval_span.start for interval_span in replaced_spans[1:]],
                strict=True
            )
        ]

        labelled_shape_items = cls.get_labelled_shape_items(
            original_pieces=original_pieces,
            replaced_items=replaced_items,
            labels_count=len(labelled_items),
            global_attrs=global_attrs,
            file_writer=file_writer,
            frame_scale=frame_scale
        )

        label_to_span_dict = {
            labelled_item.label: labelled_item.span
            for labelled_item in labelled_items
        }
        shape_items = cls.get_shape_items(
            labelled_shape_items=labelled_shape_items,
            label_to_span_dict=label_to_span_dict
        )
        specified_part_items = cls.get_specified_part_items(
            shape_items=shape_items,
            string=string,
            labelled_items=labelled_items
        )
        group_part_items = cls.get_group_part_items(
            original_pieces=original_pieces,
            replaced_items=replaced_items,
            labelled_shape_items=labelled_shape_items,
            label_to_span_dict=label_to_span_dict
        )
        return ParsingResult(
            shape_items=shape_items,
            specified_part_items=specified_part_items,
            group_part_items=group_part_items
        )

    @classmethod
    def get_labelled_items_and_replaced_items(
        cls,
        string: str,
        isolate: Iterable[SelectorT],
        protect: Iterable[SelectorT],
        local_attrs: dict[SelectorT, dict[str, str]]
    ) -> tuple[list[LabelledItem], list[CommandItem | LabelledInsertionItem]]:

        def get_key(
            index_item: tuple[ConfiguredItem | IsolatedItem | ProtectedItem | CommandItem, EdgeFlag, int, int]
        ) -> tuple[int, int, int, int, int]:
            span_item, edge_flag, priority, i = index_item
            flag_value = edge_flag.get_value()
            index = span_item.span.get_edge_index(edge_flag)
            paired_index = span_item.span.get_edge_index(-edge_flag)
            return (
                index,
                flag_value * (2 if index != paired_index else -1),
                -paired_index,
                flag_value * priority,
                flag_value * i
            )

        index_items: list[tuple[ConfiguredItem | IsolatedItem | ProtectedItem | CommandItem, EdgeFlag, int, int]] = sorted((
            (span_item, edge_flag, priority, i)
            for priority, span_item_iter in enumerate((
                (
                    ConfiguredItem(span=span, attrs=attrs)
                    for selector, attrs in local_attrs.items()
                    for span in cls.iter_spans_by_selector(selector, string)
                ),
                (
                    IsolatedItem(span=span)
                    for selector in isolate
                    for span in cls.iter_spans_by_selector(selector, string)
                ),
                (
                    ProtectedItem(span=span)
                    for selector in protect
                    for span in cls.iter_spans_by_selector(selector, string)
                ),
                (
                    CommandItem(match_obj=match_obj)
                    for match_obj in cls.iter_command_matches(string)
                )
            ), start=1)
            for i, span_item in enumerate(span_item_iter)
            for edge_flag in EdgeFlag
        ), key=get_key)

        labelled_items: list[LabelledItem] = []
        replaced_items: list[CommandItem | LabelledInsertionItem] = []
        overlapping_spans: list[Span] = []
        level_mismatched_spans: list[Span] = []
        label_counter: it.count[int] = it.count(start=1)
        protect_level: int = 0
        bracket_count: int = 0
        bracket_stack: list[int] = [0]
        open_command_stack: list[tuple[int, CommandItem]] = []
        open_stack: list[tuple[int, ConfiguredItem | IsolatedItem, int, list[int]]] = []

        def add_labelled_item(
            labelled_item: LabelledItem,
            pos: int
        ) -> None:
            labelled_items.append(labelled_item)
            replaced_items.insert(pos, LabelledInsertionItem(
                labelled_item=labelled_item,
                edge_flag=EdgeFlag.START
            ))
            replaced_items.append(LabelledInsertionItem(
                labelled_item=labelled_item,
                edge_flag=EdgeFlag.STOP
            ))

        for span_item, edge_flag, _, _ in index_items:
            if isinstance(span_item, ProtectedItem | CommandItem):
                protect_level += edge_flag.get_value()
                if isinstance(span_item, ProtectedItem):
                    continue
                if edge_flag == EdgeFlag.START:
                    continue
                command_item = span_item
                command_flag = cls.get_command_flag(command_item.match_obj)
                if command_flag == CommandFlag.OPEN:
                    bracket_count += 1
                    bracket_stack.append(bracket_count)
                    replaced_items.append(command_item)
                    open_command_stack.append((len(replaced_items), command_item))
                elif command_flag == CommandFlag.OTHER:
                    replaced_items.append(command_item)
                else:
                    pos, open_command_item = open_command_stack.pop()
                    bracket_stack.pop()
                    attrs = cls.get_attrs_from_command_pair(
                        open_command_item.match_obj, command_item.match_obj
                    )
                    if attrs is not None:
                        add_labelled_item(LabelledItem(
                            label=next(label_counter),
                            span=Span(open_command_item.span.stop, command_item.span.start),
                            attrs=attrs
                        ), pos)
                    replaced_items.append(command_item)
                continue
            if edge_flag == EdgeFlag.START:
                open_stack.append((
                    len(replaced_items), span_item, protect_level, bracket_stack.copy()
                ))
                continue
            span = span_item.span
            pos, open_span_item, open_protect_level, open_bracket_stack = open_stack.pop()
            if open_span_item is not span_item:
                overlapping_spans.append(span)
                continue
            if open_protect_level or protect_level:
                continue
            if open_bracket_stack != bracket_stack:
                level_mismatched_spans.append(span)
                continue
            add_labelled_item(LabelledItem(
                label=next(label_counter),
                span=span,
                attrs=span_item.attrs if isinstance(span_item, ConfiguredItem) else {}
            ), pos)
        add_labelled_item(LabelledItem(
            label=0,
            span=Span(0, len(string)),
            attrs={}
        ), 0)

        if overlapping_spans:
            warnings.warn(
                "Partly overlapping substrings detected: {0}".format(
                    ", ".join(
                        f"'{string[span.as_slice()]}'"
                        for span in overlapping_spans
                    )
                )
            )
        if level_mismatched_spans:
            warnings.warn(
                "Cannot handle substrings: {0}".format(
                    ", ".join(
                        f"'{string[span.as_slice()]}'"
                        for span in level_mismatched_spans
                    )
                )
            )
        return labelled_items, replaced_items

    @classmethod
    def get_replaced_pieces(
        cls,
        replaced_items: list[CommandItem | LabelledInsertionItem],
        command_replace_func: Callable[[re.Match[str]], str],
        command_insert_func: Callable[[int, EdgeFlag, dict[str, str]], str]
    ) -> list[str]:
        return [
            command_replace_func(replaced_item.match_obj)
            if isinstance(replaced_item, CommandItem)
            else command_insert_func(
                replaced_item.labelled_item.label,
                replaced_item.edge_flag,
                replaced_item.labelled_item.attrs
            )
            for replaced_item in replaced_items
        ]

    @classmethod
    def replace_string(
        cls,
        original_pieces: list[str],
        replaced_pieces: list[str],
        start_index: int,
        stop_index: int
    ) -> str:
        return "".join(it.chain.from_iterable(zip(
            original_pieces[start_index:stop_index],
            (*replaced_pieces[start_index + 1:stop_index], ""),
            strict=True
        )))

    @classmethod
    def get_labelled_shape_items(
        cls,
        original_pieces: list[str],
        replaced_items: list[CommandItem | LabelledInsertionItem],
        labels_count: int,
        global_attrs: dict[str, str],
        file_writer: StringFileWriter,
        frame_scale: float
    ) -> list[LabelledShapeItem]:

        def get_shape_mobjects(
            is_labelled: bool
        ) -> list[ShapeMobject]:
            content_replaced_pieces = cls.get_replaced_pieces(
                replaced_items=replaced_items,
                command_replace_func=cls.replace_for_content,
                command_insert_func=lambda label, edge_flag, attrs: cls.get_command_string(
                    attrs,
                    edge_flag=edge_flag,
                    label=label if is_labelled else None
                )
            )
            body = cls.replace_string(
                original_pieces=original_pieces,
                replaced_pieces=content_replaced_pieces,
                start_index=0,
                stop_index=len(original_pieces)
            )
            prefix, suffix = tuple(
                cls.get_command_string(
                    global_attrs,
                    edge_flag=edge_flag,
                    label=0 if is_labelled else None
                )
                for edge_flag in (EdgeFlag.START, EdgeFlag.STOP)
            )
            content = "".join((prefix, body, suffix))
            svg_path = file_writer.get_svg_file(content)
            return list(SVGMobject(
                file_path=svg_path,
                frame_scale=frame_scale
            ).iter_children_by_type(mobject_type=ShapeMobject))

        plain_shapes = get_shape_mobjects(is_labelled=False)
        if labels_count == 1:
            return [
                LabelledShapeItem(
                    label=0,
                    shape_mobject=plain_shape
                )
                for plain_shape in plain_shapes
            ]

        labelled_shapes = get_shape_mobjects(is_labelled=True)
        if len(plain_shapes) != len(labelled_shapes):
            warnings.warn(
                "Cannot align children of the labelled svg to the original svg. Skip the labelling process."
            )
            return [
                LabelledShapeItem(
                    label=0,
                    shape_mobject=plain_shape
                )
                for plain_shape in plain_shapes
            ]

        rearranged_labelled_shapes = cls.rearrange_labelled_shapes_by_positions(plain_shapes, labelled_shapes)
        unrecognizable_colors: list[str] = []
        labelled_shape_items: list[LabelledShapeItem] = []
        for plain_shape, labelled_shape in zip(plain_shapes, rearranged_labelled_shapes, strict=True):
            color_hex = ColorUtils.color_to_hex(labelled_shape._color_.value)
            label = int(color_hex[1:], 16)
            if label >= labels_count:
                unrecognizable_colors.append(color_hex)
                label = 0
            labelled_shape_items.append(LabelledShapeItem(
                label=label,
                shape_mobject=plain_shape
            ))

        if unrecognizable_colors:
            warnings.warn(
                "Unrecognizable color labels detected ({0}). The result could be unexpected.".format(
                    ", ".join(dict.fromkeys(unrecognizable_colors))
                )
            )
        return labelled_shape_items

    @classmethod
    def rearrange_labelled_shapes_by_positions(
        cls,
        plain_shapes: list[ShapeMobject],
        labelled_shapes: list[ShapeMobject]
    ) -> list[ShapeMobject]:
        # Rearrange children of `labelled_svg` so that
        # each child is labelled by the nearest one of `labelled_svg`.
        # The correctness cannot be ensured, since the svg may
        # change significantly after inserting color commands.
        if not labelled_shapes:
            return []

        plain_svg = SVGMobject().add(*plain_shapes)
        labelled_svg = SVGMobject().add(*labelled_shapes)
        labelled_svg.move_to(AlignMobject(plain_svg)).scale_to(
            plain_svg.get_bounding_box_size()
        )

        distance_matrix = cdist(
            [shape.get_center() for shape in plain_shapes],
            [shape.get_center() for shape in labelled_shapes]
        )
        _, indices = linear_sum_assignment(distance_matrix)
        return [
            labelled_shapes[index]
            for index in indices
        ]

    @classmethod
    def get_shape_items(
        cls,
        labelled_shape_items: list[LabelledShapeItem],
        label_to_span_dict: dict[int, Span]
    ) -> list[ShapeItem]:
        return [
            ShapeItem(
                span=label_to_span_dict[labelled_shape_item.label],
                shape_mobject=labelled_shape_item.shape_mobject
            )
            for labelled_shape_item in labelled_shape_items
        ]

    @classmethod
    def get_specified_part_items(
        cls,
        shape_items: list[ShapeItem],
        string: str,
        labelled_items: list[LabelledItem]
    ) -> list[tuple[str, list[ShapeMobject]]]:
        return [
            (
                string[labelled_item.span.as_slice()],
                cls.get_shape_mobject_list_by_span(labelled_item.span, shape_items)
            )
            for labelled_item in labelled_items
        ]

    @classmethod
    def get_group_part_items(
        cls,
        original_pieces: list[str],
        replaced_items: list[CommandItem | LabelledInsertionItem],
        labelled_shape_items: list[LabelledShapeItem],
        label_to_span_dict: dict[int, Span]
    ) -> list[tuple[str, list[ShapeMobject]]]:
        if not labelled_shape_items:
            return []

        range_lens, group_labels = zip(*(
            (len(list(grouper)), val)
            for val, grouper in it.groupby(labelled_shape_item.label for labelled_shape_item in labelled_shape_items)
        ), strict=True)
        labelled_insertion_item_to_index_dict = {
            (replaced_item.labelled_item.label, replaced_item.edge_flag): index
            for index, replaced_item in enumerate(replaced_items)
            if isinstance(replaced_item, LabelledInsertionItem)
        }
        start_items = [
            (group_labels[0], EdgeFlag.START),
            *(
                (curr_label, EdgeFlag.START)
                if label_to_span_dict[curr_label] in label_to_span_dict[prev_label]
                else (prev_label, EdgeFlag.STOP)
                for prev_label, curr_label in it.pairwise(group_labels)
            )
        ]
        stop_items = [
            *(
                (curr_label, EdgeFlag.STOP)
                if label_to_span_dict[curr_label] in label_to_span_dict[next_label]
                else (next_label, EdgeFlag.START)
                for curr_label, next_label in it.pairwise(group_labels)
            ),
            (group_labels[-1], EdgeFlag.STOP)
        ]
        matching_replaced_pieces = cls.get_replaced_pieces(
            replaced_items=replaced_items,
            command_replace_func=cls.replace_for_matching,
            command_insert_func=lambda label, flag, attrs: ""
        )
        group_substrs = [
            re.sub(r"\s+", "", cls.replace_string(
                original_pieces=original_pieces,
                replaced_pieces=matching_replaced_pieces,
                start_index=labelled_insertion_item_to_index_dict[start_item],
                stop_index=labelled_insertion_item_to_index_dict[stop_item]
            ))
            for start_item, stop_item in zip(start_items, stop_items, strict=True)
        ]
        return list(zip(group_substrs, [
            [
                labelled_shape_item.shape_mobject
                for labelled_shape_item in labelled_shape_items[slice(*part_range)]
            ]
            for part_range in it.pairwise((0, *it.accumulate(range_lens)))
        ], strict=True))

    @classmethod
    def iter_spans_by_selector(
        cls,
        selector: SelectorT,
        string: str
    ) -> Iterator[Span]:
        match selector:
            case str():
                pattern = re.compile(re.escape(selector))
            case re.Pattern():
                pattern = selector
        for match_obj in pattern.finditer(string):
            yield Span(*match_obj.span())

    @classmethod
    def get_shape_mobject_list_by_span(
        cls,
        arbitrary_span: Span,
        shape_items: list[ShapeItem]
    ) -> list[ShapeMobject]:
        return [
            shape_item.shape_mobject
            for shape_item in shape_items
            if shape_item.span in arbitrary_span
        ]

    # Implemented in subclasses.

    @classmethod
    @abstractmethod
    def iter_command_matches(
        cls,
        string: str
    ) -> Iterator[re.Match[str]]:
        pass

    @classmethod
    @abstractmethod
    def get_command_flag(
        cls,
        match_obj: re.Match[str]
    ) -> CommandFlag:
        pass

    @classmethod
    @abstractmethod
    def replace_for_content(
        cls,
        match_obj: re.Match[str]
    ) -> str:
        pass

    @classmethod
    @abstractmethod
    def replace_for_matching(
        cls,
        match_obj: re.Match[str]
    ) -> str:
        pass

    @classmethod
    @abstractmethod
    def get_attrs_from_command_pair(
        cls,
        open_command: re.Match[str],
        close_command: re.Match[str]
    ) -> dict[str, str] | None:
        pass

    @classmethod
    @abstractmethod
    def get_command_string(
        cls,
        attrs: dict[str, str],
        edge_flag: EdgeFlag,
        label: int | None
    ) -> str:
        pass


class StringMobject(SVGMobject):
    """
    An abstract base class for `Tex` and `MarkupText`.

    This class aims to optimize the logic of "slicing children
    via substrings". This could be much clearer and more user-friendly
    than slicing through numerical indices explicitly.

    Users are expected to specify substrings in `isolate` parameter
    if they want to do anything with their corresponding children.
    `isolate` parameter can be either a string, a `re.Pattern` object,
    or a 2-tuple containing integers or None, or a collection of the above.
    Note, substrings specified cannot *partly* overlap with each other.

    Each instance of `StringMobject` generates 2 svg files.
    The additional one is generated with some color commands inserted,
    so that each child of the original `SVGMobject` will be labelled
    by the color of its paired child from the additional `SVGMobject`.
    """
    __slots__ = (
        "_string",
        "_parser"
    )

    def __init__(
        self,
        *,
        string: str,
        parser: StringParser
    ) -> None:
        super().__init__()
        self._string: str = string
        self._parser: StringParser = parser
        self.add(*(
            shape_item.shape_mobject
            for shape_item in parser._parsing_result.shape_items
        ))

    def _iter_shape_mobject_lists_by_selector(
        self,
        selector: SelectorT
    ) -> Iterator[list[ShapeMobject]]:
        parser = self._parser
        for span in parser.iter_spans_by_selector(selector, self._string):
            if (shape_mobject_list := parser.get_shape_mobject_list_by_span(span, parser._parsing_result.shape_items)):
                yield shape_mobject_list

    def select_parts(
        self,
        selector: SelectorT
    ) -> ShapeMobject:
        return ShapeMobject().add(*(
            ShapeMobject().add(*shape_mobject_list)
            for shape_mobject_list in self._iter_shape_mobject_lists_by_selector(selector)
        ))

    def select_part(
        self,
        selector: SelectorT,
        index: int = 0
    ) -> ShapeMobject:
        return ShapeMobject().add(*(
            list(self._iter_shape_mobject_lists_by_selector(selector))[index]
        ))
