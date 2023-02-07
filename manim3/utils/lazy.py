__all__ = [
    "LazyData",
    "LazyBase",
    "lazy_basedata",
    "lazy_property",
    "lazy_slot"
]


from abc import ABC
import inspect
from types import (
    GenericAlias,
    UnionType
)
from typing import (
    Any,
    Callable,
    ClassVar,
    Generator,
    Generic,
    TypeVar,
    overload
)


_T = TypeVar("_T")
_LazyBaseT = TypeVar("_LazyBaseT", bound="LazyBase")
_Annotation = Any


class LazyData(Generic[_T]):
    def __init__(self, data: _T):
        self._data: _T = data

    def __repr__(self) -> str:
        return f"<LazyData: {self._data}>"

    @property
    def data(self) -> _T:
        return self._data


class _lazy_descriptor(Generic[_LazyBaseT, _T]):
    def __init__(self, method: Callable[..., _T]):
        self.name: str = method.__name__
        self.method: Callable[..., _T] = method
        #self.default_basedata: LazyData[_T] = LazyData(method())
        self.signature: inspect.Signature = inspect.signature(method)
        #self.annotation: _Annotation = inspect.signature(method).return_annotation
        self.restock_method: Callable[[_T], None] | None = None

    @property
    def parameters(self) -> dict[str, _Annotation]:
        return {
            f"_{parameter.name}_": parameter.annotation
            for parameter in list(self.signature.parameters.values())
        }

    @property
    def return_annotation(self) -> _Annotation:
        return self.signature.return_annotation

    def _restock(self, data: _T) -> None:
        if self.restock_method is not None:
            self.restock_method(data)
        elif isinstance(data, LazyBase):
            data._restock()

    def restocker(self, restock_method: Callable[[_T], None]) -> Callable[[_T], None]:
        self.restock_method = restock_method
        return restock_method


class lazy_basedata(_lazy_descriptor[_LazyBaseT, _T]):
    def __init__(self, method: Callable[[], _T]):
        super().__init__(method)
        assert not self.parameters
        #self.name: str = method.__name__
        #self.method: Callable[..., _T] = method
        #self.default_basedata: LazyData[_T] = LazyData(method())
        #self.annotation: _Annotation = inspect.signature(method).return_annotation
        #self.restock_method: Callable[[_T], None] | None = None
        #self.property_descrs: tuple[lazy_property[_LazyBaseT, Any], ...] = ()
        self.instance_to_basedata_dict: dict[_LazyBaseT, LazyData[_T]] = {}
        self.basedata_to_instances_dict: dict[LazyData[_T], list[_LazyBaseT]] = {}
        #self.basedata_refcnt_dict: dict[LazyData[_T], int] = {}
        self._default_basedata: LazyData[_T] | None = None

    @overload
    def __get__(self, instance: None, owner: type[_LazyBaseT] | None = None) -> "lazy_basedata[_LazyBaseT, _T]": ...

    @overload
    def __get__(self, instance: _LazyBaseT, owner: type[_LazyBaseT] | None = None) -> _T: ...

    def __get__(self, instance: _LazyBaseT | None, owner: type[_LazyBaseT] | None = None) -> "lazy_basedata[_LazyBaseT, _T] | _T":
        if instance is None:
            return self
        return self._get_data(instance).data

    def __set__(self, instance: _LazyBaseT, basedata: LazyData[_T]) -> None:
        assert isinstance(basedata, LazyData)
        self._set_data(instance, basedata)

    @property
    def default_basedata(self) -> LazyData[_T]:
        if self._default_basedata is None:
            self._default_basedata = LazyData(self.method())
        return self._default_basedata

    def _get_data(self, instance: _LazyBaseT) -> LazyData[_T]:
        return self.instance_to_basedata_dict.get(instance, self.default_basedata)

    def _set_data(self, instance: _LazyBaseT, basedata: LazyData[_T] | None) -> None:
        self._clear_instance_basedata(instance)
        for property_descr in instance.__class__._BASEDATA_DESCR_TO_PROPERTY_DESCRS[self]:
            property_descr._clear_instance_basedata_tuple(instance)
        if basedata is None:
            return
        #if self.name == "_field_info_":
        #    print(f"Set {self.name} {instance} {basedata}")
        self.instance_to_basedata_dict[instance] = basedata
        self.basedata_to_instances_dict.setdefault(basedata, []).append(instance)

    def _clear_instance_basedata(self, instance: _LazyBaseT) -> None:
        #if self.name == "_field_info_":
        #    print(f"Pop {self.name} {instance}")
        if (basedata := self.instance_to_basedata_dict.pop(instance, None)) is None:
            return
        self.basedata_to_instances_dict[basedata].remove(instance)
        if self.basedata_to_instances_dict[basedata]:
            return
        self.basedata_to_instances_dict.pop(basedata)
        self._restock(basedata.data)


class lazy_property(_lazy_descriptor[_LazyBaseT, _T]):
    def __init__(self, method: Callable[..., _T]):
        super().__init__(method)
        assert self.parameters
        #signature = inspect.signature(method)
        #self.name: str = method.__name__
        #self.method: Callable[..., _T] = method
        #self.annotation: _Annotation = signature.return_annotation
        #self.parameters: dict[str, _Annotation] = {
        #    f"_{parameter.name}_": parameter.annotation
        #    for parameter in list(signature.parameters.values())
        #}
        #self.basedata_descrs: tuple[lazy_basedata[_LazyBaseT, Any], ...] = ()
        self.instance_to_basedata_tuple_dict: dict[_LazyBaseT, tuple[LazyData[Any], ...]] = {}
        self.basedata_tuple_to_instances_dict: dict[tuple[LazyData[Any], ...], list[_LazyBaseT]] = {}
        self.basedata_tuple_to_property_dict: dict[tuple[LazyData[Any], ...], _T] = {}
        #self.instance_to_property_dict: dict[_LazyBaseT, _T] = {}

    @overload
    def __get__(self, instance: None, owner: type[_LazyBaseT] | None = None) -> "lazy_property[_LazyBaseT, _T]": ...

    @overload
    def __get__(self, instance: _LazyBaseT, owner: type[_LazyBaseT] | None = None) -> _T: ...

    def __get__(self, instance: _LazyBaseT | None, owner: type[_LazyBaseT] | None = None) -> "lazy_property[_LazyBaseT, _T] | _T":
        if instance is None:
            return self
        if (basedata_tuple := self.instance_to_basedata_tuple_dict.get(instance)) is None:
            basedata_tuple = tuple(
                basedata_descr._get_data(instance)
                for basedata_descr in instance.__class__._PROPERTY_DESCR_TO_BASEDATA_DESCRS[self]
            )
            self.instance_to_basedata_tuple_dict[instance] = basedata_tuple
            self.basedata_tuple_to_instances_dict.setdefault(basedata_tuple, []).append(instance)
        return self.basedata_tuple_to_property_dict.setdefault(
            basedata_tuple,
            self.method(*(
                param_descr.__get__(instance)
                for param_descr in instance.__class__._PROPERTY_DESCR_TO_PARAMETER_DESCRS[self]
            ))
        )

    def __set__(self, instance: _LazyBaseT, value: Any) -> None:
        raise RuntimeError("Attempting to set a readonly lazy property")

    def _clear_instance_basedata_tuple(self, instance: _LazyBaseT) -> None:
        #import pprint
        #if self.name == "_attributes_":
        #    print(instance)
        #    pprint.pprint(self.basedata_tuple_to_instances_dict)
        #    pprint.pprint(self.instance_to_basedata_tuple_dict)
        if (basedata_tuple := self.instance_to_basedata_tuple_dict.pop(instance, None)) is None:
            #if self.name == "_attributes_":
            #    print(1)
            return
        self.basedata_tuple_to_instances_dict[basedata_tuple].remove(instance)
        if self.basedata_tuple_to_instances_dict[basedata_tuple]:
            #if self.name == "_attributes_":
            #    print(2)
            return
        self.basedata_tuple_to_instances_dict.pop(basedata_tuple)
        if (property_data := self.basedata_tuple_to_property_dict.pop(basedata_tuple, None)) is None:
            #if self.name == "_attributes_":
            #    print(3)
            return
        self._restock(property_data)


class lazy_slot(_lazy_descriptor[_LazyBaseT, _T]):
    def __init__(self, method: Callable[[], _T]):
        super().__init__(method)
        assert not self.parameters
        #self.name: str = method.__name__
        #self.method: Callable[..., _T] = method
        self.instance_to_value_dict: dict[_LazyBaseT, _T] = {}
        #self.copy_method: Callable[[_T], _T] | None = None
        #self._default_value: _T | None = None

    @overload
    def __get__(self, instance: None, owner: type[_LazyBaseT] | None = None) -> "lazy_slot[_LazyBaseT, _T]": ...

    @overload
    def __get__(self, instance: _LazyBaseT, owner: type[_LazyBaseT] | None = None) -> _T: ...

    def __get__(self, instance: _LazyBaseT | None, owner: type[_LazyBaseT] | None = None) -> "lazy_slot[_LazyBaseT, _T] | _T":
        if instance is None:
            return self
        if (value := self.instance_to_value_dict.get(instance)) is None:
            value = self.method()
            self.instance_to_value_dict[instance] = value
        return value

    def __set__(self, instance: _LazyBaseT, value: _T) -> None:
        self.instance_to_value_dict[instance] = value

    #def copier(self, copy_method: Callable[[_T], _T]) -> Callable[[_T], _T]:
    #    self.copy_method = copy_method
    #    return copy_method

    def _copy_value(self, instance_src: _LazyBaseT, instance_dst: _LazyBaseT) -> None:
        if (value := self.instance_to_value_dict.get(instance_src)) is None:
            self.instance_to_value_dict.pop(instance_dst, None)
            return
        #if self.copy_method is not None:
        #    value = self.copy_method(value)
        self.instance_to_value_dict[instance_dst] = value

    #@property
    #def default_value(self) -> _T:
    #    if self._default_value is None:
    #        self._default_value = self.method()
    #    return self._default_value


class LazyBase(ABC):
    __slots__ = ()

    _VACANT_INSTANCES: "ClassVar[list[LazyBase]]"
    _BASEDATA_DESCR_TO_PROPERTY_DESCRS: ClassVar[dict[lazy_basedata, tuple[lazy_property, ...]]]
    _PROPERTY_DESCR_TO_BASEDATA_DESCRS: ClassVar[dict[lazy_property, tuple[lazy_basedata, ...]]]
    _PROPERTY_DESCR_TO_PARAMETER_DESCRS: ClassVar[dict[lazy_property, tuple[lazy_basedata | lazy_property, ...]]]
    _SLOT_DESCRS: ClassVar[tuple[lazy_slot, ...]] = ()

    def __init_subclass__(cls) -> None:
        descrs: dict[str, lazy_basedata | lazy_property] = {}
        slots: dict[str, lazy_slot] = {}
        for parent_cls in cls.__mro__[::-1]:
            for name, method in parent_cls.__dict__.items():
                if (covered_descr := descrs.get(name)) is not None:
                    assert isinstance(method, lazy_basedata | lazy_property)
                    cls._check_annotation_matching(method.return_annotation, covered_descr.return_annotation)
                if isinstance(method, lazy_basedata | lazy_property):
                    descrs[name] = method
                if (covered_slot := slots.get(name)) is not None:
                    assert isinstance(covered_slot, lazy_slot)
                if isinstance(method, lazy_slot):
                    slots[name] = method

        property_descr_to_parameter_descrs: dict[lazy_property, tuple[lazy_basedata | lazy_property, ...]] = {}
        for descr in descrs.values():
            if not isinstance(descr, lazy_property):
                continue
            param_descrs: list[lazy_basedata | lazy_property] = []
            for name, param_annotation in descr.parameters.items():
                param_descr = descrs[name]
                cls._check_annotation_matching(param_descr.return_annotation, param_annotation)
                param_descrs.append(param_descr)
            property_descr_to_parameter_descrs[descr] = tuple(param_descrs)

        def traverse(property_descr: lazy_property, occurred: set[lazy_basedata]) -> Generator[lazy_basedata, None, None]:
            for name in property_descr.parameters:
                param_descr = descrs[name]
                if isinstance(param_descr, lazy_basedata):
                    yield param_descr
                    occurred.add(param_descr)
                else:
                    yield from traverse(param_descr, occurred)

        property_descr_to_basedata_descrs = {
            property_descr: tuple(traverse(property_descr, set()))
            for property_descr in descrs.values()
            if isinstance(property_descr, lazy_property)
        }
        basedata_descr_to_property_descrs = {
            basedata_descr: tuple(
                property_descr
                for property_descr, basedata_descrs in property_descr_to_basedata_descrs.items()
                if basedata_descr in basedata_descrs
            )
            for basedata_descr in descrs.values()
            if isinstance(basedata_descr, lazy_basedata)
        }

        cls.__slots__ = ()  # TODO
        cls._VACANT_INSTANCES = []
        cls._BASEDATA_DESCR_TO_PROPERTY_DESCRS = basedata_descr_to_property_descrs
        cls._PROPERTY_DESCR_TO_BASEDATA_DESCRS = property_descr_to_basedata_descrs
        cls._PROPERTY_DESCR_TO_PARAMETER_DESCRS = property_descr_to_parameter_descrs
        cls._SLOT_DESCRS = tuple(slots.values())
        return super().__init_subclass__()

    def __new__(cls):
        if (instances := cls._VACANT_INSTANCES):
            instance = instances.pop()
            assert isinstance(instance, cls)
        else:
            instance = super().__new__(cls)
            #instance._init_new_instance()
        return instance

    #def __delete__(self) -> None:
    #    self._restock()

    #def _init_new_instance(self) -> None:
    #    pass

    def _copy(self):
        result = self.__new__(self.__class__)
        for basedata_descr in self._BASEDATA_DESCR_TO_PROPERTY_DESCRS:
            basedata = basedata_descr.instance_to_basedata_dict.get(self, None)
            basedata_descr._set_data(result, basedata)
        for slot_descr in self._SLOT_DESCRS:
            slot_descr._copy_value(self, result)
            #if self in slot_descr.instance_to_value_dict:
            #    slot_descr.__set__(result, slot_descr._copy_value(self))
                #basedata_descr.instance_to_basedata_dict[result] = basedata
                #basedata_descr._increment_basedata_refcnt(basedata)
        #for property_descr in self._PROPERTY_DESCR_TO_BASEDATA_DESCRS:
        #    if (basedata_tuple := property_descr.instance_to_basedata_tuple_dict.get(self, None)) is not None:
        #        property_descr.instance_to_basedata_tuple_dict[result] = basedata_tuple
        #        property_descr._increment_basedata_tuple_refcnt(basedata_tuple)
        return result

    #def _reinitialize_data(self) -> None:
    #    for basedata_descr in self._LAZY_BASEDATA_DESCRS:
    #        basedata_descr.instance_to_basedata_dict.pop(self, None)

    def _restock(self) -> None:
        for basedata_descr in self._BASEDATA_DESCR_TO_PROPERTY_DESCRS:
            basedata_descr._set_data(self, None)
        for slot_descr in self._SLOT_DESCRS:
            slot_descr.instance_to_value_dict.pop(self, None)
                #basedata_descr._decrement_basedata_refcnt(basedata)
        #for property_descr in self._PROPERTY_DESCR_TO_BASEDATA_DESCRS:
        #    if (basedata_tuple := property_descr.instance_to_basedata_tuple_dict.pop(self, None)) is not None:
        #        property_descr._decrement_basedata_tuple_refcnt(basedata_tuple)
        self._VACANT_INSTANCES.append(self)

    @classmethod
    def _check_annotation_matching(cls, child_annotation: _Annotation, parent_annotation: _Annotation) -> None:
        error_message = f"Type annotation mismatched: `{child_annotation}` is not compatible with `{parent_annotation}`"
        if isinstance(child_annotation, TypeVar) or isinstance(parent_annotation, TypeVar):
            if isinstance(child_annotation, TypeVar) and isinstance(parent_annotation, TypeVar):
                assert child_annotation == parent_annotation, error_message
            return

        def to_classes(annotation: _Annotation) -> tuple[type, ...]:
            return tuple(
                child.__origin__ if isinstance(child, GenericAlias) else
                Callable if isinstance(child, Callable) else child
                for child in (
                    annotation.__args__ if isinstance(annotation, UnionType) else (annotation,)
                )
            )

        assert all(
            any(
                issubclass(child_cls, parent_cls)
                for parent_cls in to_classes(parent_annotation)
            )
            for child_cls in to_classes(child_annotation)
        ), error_message




#class lazy_property(Generic[_LazyBaseT, _T], Node):
#    def __init__(self, static_method: Callable[..., _T]):
#        #assert isinstance(method, staticmethod)
#        method = static_method.__func__
#        self.method: Callable[..., _T] = method
#        signature = inspect.signature(method)
#        self.name: str = method.__name__
#        self.annotation: _Annotation = signature.return_annotation
#        self.parameters: dict[str, _Annotation] = {
#            f"_{parameter.name}_": parameter.annotation
#            for parameter in list(signature.parameters.values())
#        }
#        self.ancestors: list[lazy_property[_LazyBaseT, _T]] = []
#        self.value_dict: dict[_LazyBaseT, _T] = {}
#        self.requires_update: dict[_LazyBaseT, bool] = {}
#        #self.release_method: Callable[[_T], None] | None = None
#        super().__init__()

#    @overload
#    def __get__(self, instance: None, owner: type[_LazyBaseT] | None = None) -> "lazy_property[_LazyBaseT, _T]": ...

#    @overload
#    def __get__(self, instance: _LazyBaseT, owner: type[_LazyBaseT] | None = None) -> _T: ...

#    def __get__(self, instance: _LazyBaseT | None, owner: type[_LazyBaseT] | None = None) -> "lazy_property[_LazyBaseT, _T] | _T":
#        if instance is None:
#            return self
#        if not self.requires_update[instance]:
#            return self.value_dict[instance]
#        #if self.release_method is not None:
#        #if instance in self.value_dict:
#        #    del self.value_dict[instance]
#                #self.release_method(self.value_dict[instance])
#        value = self.method(*(
#            instance.__getattribute__(parameter)
#            for parameter in self.parameters
#        ))
#        self.value_dict[instance] = value
#        self.requires_update[instance] = False
#        return value

#    def __set__(self, instance: _LazyBaseT, value: _T) -> None:
#        raise ValueError("Attempting to set a readonly lazy property")

#    #@property
#    #def stripped_name(self) -> str:
#    #    return self.name.strip("_")

#    #def releaser(self, release_method: Callable[[_T], None]) -> Callable[[_T], None]:
#    #    self.release_method = release_method
#    #    return release_method

#    def add_instance(self, instance: _LazyBaseT) -> None:
#        self.requires_update[instance] = True

#    def update_ancestors_cache(self) -> None:
#        self.ancestors = list(self.iter_ancestors())

#    def expire_instance(self, instance: _LazyBaseT) -> None:
#        for expired_prop in self.ancestors:
#            expired_prop.requires_update[instance] = True


#class lazy_property_updatable(lazy_property[_LazyBaseT, _T]):
#    @overload
#    def __get__(self, instance: None, owner: type[_LazyBaseT] | None = None) -> "lazy_property_updatable[_LazyBaseT, _T]": ...

#    @overload
#    def __get__(self, instance: _LazyBaseT, owner: type[_LazyBaseT] | None = None) -> _T: ...

#    def __get__(self, instance: _LazyBaseT | None, owner: type[_LazyBaseT] | None = None) -> "lazy_property_updatable[_LazyBaseT, _T] | _T":
#        if instance is None:
#            return self
#        return self.value_dict[instance]

#    def add_instance(self, instance: _LazyBaseT) -> None:
#        self.value_dict[instance] = self.method()

#    def updater(self, update_method: Callable[Concatenate[_LazyBaseT, _P], _R]) -> Callable[Concatenate[_LazyBaseT, _P], _R]:
#        def new_update_method(instance: _LazyBaseT, *args: _P.args, **kwargs: _P.kwargs) -> _R:
#            self.expire_instance(instance)
#            return update_method(instance, *args, **kwargs)
#        return new_update_method


#class lazy_property_writable(lazy_property_updatable[_LazyBaseT, _T]):
#    def __set__(self, instance: _LazyBaseT, value: _T) -> None:
#        self.expire_instance(instance)
#        self.value_dict[instance] = value


#class LazyBase(ABC):
#    _PROPERTIES: ClassVar[list[lazy_property]]

#    def __init_subclass__(cls) -> None:
#        properties: dict[str, lazy_property] = {}
#        for parent_cls in cls.__mro__[::-1]:
#            for name, method in parent_cls.__dict__.items():
#                if name not in properties:
#                    if isinstance(method, lazy_property):
#                        properties[name] = method
#                    continue
#                assert isinstance(method, lazy_property)
#                cls._check_annotation_matching(method.annotation, properties[name].annotation)
#                properties[name] = method

#        for prop in properties.values():
#            if isinstance(prop, lazy_property_updatable):
#                assert not prop.parameters
#                continue
#            for param_name, param_annotation in prop.parameters.items():
#                cls._check_annotation_matching(properties[param_name].annotation, param_annotation)
#                prop.add(properties[param_name])
#        for prop in properties.values():
#            prop.update_ancestors_cache()

#        cls._PROPERTIES = list(properties.values())
#        return super().__init_subclass__()

#    def __new__(cls, *args, **kwargs):
#        instance = super().__new__(cls)
#        for prop in cls._PROPERTIES:
#            prop.add_instance(instance)
#        return instance

#    #def __init__(self) -> None:
#    #    for prop in self._PROPERTIES:
#    #        prop.add_instance(self)
#    #        #print(self.__class__.__name__, prop.name, len(prop.value_dict))
#    #    super().__init__()

#    #def __del__(self) -> None:
#    #    for prop in self._PROPERTIES:
#    #        print(prop.name, len(prop.value_dict))
#    #    super().__del__(self)


"""
class A(LazyBase):
    @lazy_property
    @staticmethod
    def _p_(q: str) -> int:
        return int(q)
    @lazy_basedata
    @staticmethod
    def _q_() -> str:
        return "2"

class B(A):
    pass


a = B()
s = a._p_ + 3
#a._q_ + "8"
print(s, a._p_)
"""
