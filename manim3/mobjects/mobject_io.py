from __future__ import annotations


import hashlib
import json
import pathlib
from abc import (
    ABC,
    abstractmethod
)
from contextlib import contextmanager
from typing import (
    Iterator,
    Never,
    Self,
    TypedDict
)

import attrs

from ..utils.path_utils import PathUtils


@attrs.frozen(kw_only=True)
class MobjectInput:
    pass


@attrs.frozen(kw_only=True)
class MobjectOutput:
    pass


class MobjectJSON(TypedDict):
    pass


class MobjectIO[MobjectInputT: MobjectInput, MobjectOutputT: MobjectOutput, MobjectJSONT: MobjectJSON](ABC):
    __slots__ = ()

    def __new__(
        cls: type[Self]
    ) -> Never:
        raise TypeError

    @classmethod
    def get(
        cls: type[Self],
        input_data: MobjectInputT
    ) -> MobjectOutputT:
        # Notice that as we are using `str(input_data)` as key,
        # each item shall have an explicit string representation of data,
        # which shall not contain any information varying in each run, like addresses.
        hash_content = str(input_data)
        # Truncating at 16 bytes for cleanliness.
        hex_string = hashlib.sha256(hash_content.encode()).hexdigest()[:16]
        json_path = PathUtils.get_output_subdir(cls._dir_name).joinpath(f"{hex_string}.json")
        if not json_path.exists():
            with cls.display_during_execution():
                temp_path = PathUtils.get_output_subdir("_temp").joinpath(hex_string)
                output_data = cls.generate(input_data, temp_path)
                json_data = cls.dump_json(output_data)
                json_text = json.dumps(json_data, ensure_ascii=False)
                json_path.write_text(json_text, encoding="utf-8")
        json_text = json_path.read_text(encoding="utf-8")
        json_data = json.loads(json_text)
        return cls.load_json(json_data)

    @classmethod
    @property
    @abstractmethod
    def _dir_name(
        cls: type[Self]
    ) -> str:
        pass

    @classmethod
    @abstractmethod
    def generate(
        cls: type[Self],
        input_data: MobjectInputT,
        temp_path: pathlib.Path
    ) -> MobjectOutputT:
        pass

    @classmethod
    @abstractmethod
    def dump_json(
        cls: type[Self],
        output_data: MobjectOutputT
    ) -> MobjectJSONT:
        pass

    @classmethod
    @abstractmethod
    def load_json(
        cls: type[Self],
        json_data: MobjectJSONT
    ) -> MobjectOutputT:
        pass

    @classmethod
    @contextmanager
    def display_during_execution(
        cls: type[Self]
    ) -> Iterator[None]:  # TODO: needed?
        message = "Generating intermediate files..."
        try:
            print(message, end="\r")
            yield
        finally:
            print(" " * len(message), end="\r")