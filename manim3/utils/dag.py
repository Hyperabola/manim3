__all__ = ["DAGNode"]


#from abc import ABC
from typing import (
    Generator,
    Self,
)

#from ordered_set import OrderedSet


class DAGNode:
    # Node of a doubly linked DAG (directed acyclic graph)
    __slots__ = (
        "_children",
        "_parents"
    )

    def __init__(self: Self) -> None:
        super().__init__()
        #self._nodes: list[LazyObjectNode] = []
        self._children: list[Self] = []
        #self._node_descendants: list[LazyObject] = [self]
        self._parents: list[Self] = []

    def _iter_descendants(self: Self) -> Generator[Self, None, None]:
        occurred: set[Self] = set()

        def iter_descendants(node: Self) -> Generator[Self, None, None]:
            if node in occurred:
                return
            occurred.add(node)
            yield node
            for child in node._children:
                yield from iter_descendants(child)

        yield from iter_descendants(self)

    def _iter_ancestors(self: Self) -> Generator[Self, None, None]:
        occurred: set[Self] = set()

        def iter_ancestors(node: Self) -> Generator[Self, None, None]:
            if node in occurred:
                return
            occurred.add(node)
            yield node
            for child in node._parents:
                yield from iter_ancestors(child)

        yield from iter_ancestors(self)

    def _bind_children(self: Self, *nodes: Self) -> Self:
        if (invalid_nodes := [
            node for node in self._iter_ancestors()
            if node in nodes
        ]):
            raise ValueError(f"Nodes `{invalid_nodes}` have already included `{self}`")
        #for ancestor in self._node_ancestors:
        #    ancestor._node_descendants.update(nodes)
        for node in nodes:
            if node in self._children:
                raise ValueError(f"Node `{node}` is already one of children of `{self}`")
            else:
                self._children.append(node)
            node._parents.append(self)
            #for descendant in self._node_descendants:
            #    descendant._node_ancestors.append(self)
        return self

    def _unbind_children(self: Self, *nodes: Self) -> Self:
        if (invalid_nodes := [
            node for node in nodes
            if node not in self._children
        ]):
            raise ValueError(f"Nodes `{invalid_nodes}` are not children of `{self}`")
        #self._children.difference_update(nodes)
        #for ancestor in self._node_ancestors:
        #    ancestor._node_descendants.difference_update(nodes)
        for node in nodes:
            self._children.remove(node)
            node._parents.remove(self)
            #if not node._parents:
            #    node._restock()
            #for descendant in self._node_descendants:
            #    descendant._node_ancestors.remove(self)
        return self

#class DAGNode(ABC):
#    # Node of a doubly linked DAG (directed acyclic graph)
#    __slots__ = (
#        "_node_children",
#        "_node_descendants",
#        "_node_parents",
#        "_node_ancestors"
#    )

#    def __init__(self: Self) -> None:
#        self._node_children: OrderedSet[Self] = OrderedSet(())
#        self._node_descendants: OrderedSet[Self] = OrderedSet((self,))
#        self._node_parents: OrderedSet[Self] = OrderedSet(())
#        self._node_ancestors: OrderedSet[Self] = OrderedSet((self,))

#    def __len__(self: Self) -> int:
#        return self._node_children.__len__()

#    @overload
#    def __getitem__(self: Self, index: slice) -> OrderedSet[Self]:
#        ...

#    @overload
#    def __getitem__(self: Self, index: Sequence[int]) -> list[Self]:
#        ...

#    @overload
#    def __getitem__(self: Self, index: int) -> Self:
#        ...

#    def __getitem__(
#        self: Self,
#        index: slice | Sequence[int] | int
#    ) -> OrderedSet[Self] | list[Self] | Self:
#        return self._node_children.__getitem__(index)

#    #def iter_node_children(self: Self) -> Iterator[Self]:
#    #    return iter(self._node_children)

#    #def iter_node_descendants(self: Self) -> Iterator[Self]:
#    #    return iter(self._node_descendants)

#    #def iter_node_parents(self: Self) -> Iterator[Self]:
#    #    return iter(self._node_parents)

#    #def iter_node_ancestors(self: Self) -> Iterator[Self]:
#    #    return iter(self._node_ancestors)

#    def bind_children(self: Self, *nodes: Self) -> Self:
#        if (invalid_nodes := self._node_ancestors.intersection(nodes)):
#            raise ValueError(f"Nodes `{invalid_nodes}` have already included `{self}`")
#        self._node_children.update(nodes)
#        for ancestor in self._node_ancestors:
#            ancestor._node_descendants.update(nodes)
#        for node in nodes:
#            node._node_parents.append(self)
#            for descendant in self._node_descendants:
#                descendant._node_ancestors.append(self)
#        return self

#    def unbind_children(self: Self, *nodes: Self) -> Self:
#        if (invalid_nodes := OrderedSet(nodes).difference(self._node_children)):
#            raise ValueError(f"Nodes `{invalid_nodes}` are not children of `{self}`")
#        self._node_children.difference_update(nodes)
#        for ancestor in self._node_ancestors:
#            ancestor._node_descendants.difference_update(nodes)
#        for node in nodes:
#            node._node_parents.discard(self)
#            for descendant in self._node_descendants:
#                descendant._node_ancestors.discard(self)
#        return self

#    #def pop(self, index: int = -1):
#    #    node = self[index]
#    #    self.remove(node)
#    #    return node

#    #def clear(self):
#    #    self.remove(*self._node_children)
#    #    return self
