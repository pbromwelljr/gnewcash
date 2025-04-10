"""Python module to handle searching on objects using a LINQ-like format."""
from collections import deque

from typing import Callable, Any, Optional, List, TypeAlias, Generator, Iterable, Set, Union

Selector: TypeAlias = Callable[[Any, int], Any]
Predicate: TypeAlias = Callable[[Any], bool]

class InvalidOperationException(Exception):
    """Exception thrown when an invalid operation was performed."""

class QueryAction:
    """Base class for other query actions."""

    def perform(self, collection: Iterable[Any]) -> Generator[Any, None, None]:
        """Perform the action on the current element in the collection."""
        # Should be implemented by subclasses.
        raise NotImplementedError


class SelectQueryAction(QueryAction):
    """Class for mapping elements in the collection based on the provided method."""

    def __init__(self, selector: Selector, is_select_many: bool) -> None:
        self.selector: Selector = selector
        self.is_select_many: bool = is_select_many

    def perform(self, collection: Iterable[Any]) -> Generator[Any, None, None]:
        """Run the selector against each element and yield it to the next action."""
        for index, element in enumerate(collection):
            selector_result = self.selector(element, index)
            if self.is_select_many and isinstance(selector_result, Iterable):
                for sub_result in selector_result:
                    yield sub_result
            else:
                yield selector_result


class WhereQueryAction(QueryAction):
    """Class for filtering elements in the collection based on the provided method."""

    def __init__(self, predicate: Predicate) -> None:
        self.predicate: Predicate = predicate

    def perform(self, collection: Iterable[Any]) -> Generator[Any, None, None]:
        """Filter the collection by running each element against the predicate."""
        for element in collection:
            if not self.predicate(element):
                continue
            yield element


class DistinctQueryAction(QueryAction):
    """Class for getting distinct values of elements in the collection."""

    def perform(self, collection: Iterable[Any]) -> Generator[Any, None, None]:
        """Filter results based on distinct values."""
        seen_values: Set[Any] = set()
        for element in collection:
            if element in seen_values:
                continue
            seen_values.add(element)
            yield seen_values


class ExceptQueryAction(QueryAction):
    """Class for filtering out elements that are in a specified collection."""
    def __init__(self, exclude_values: Iterable[Any]) -> None:
        self.exclude_values: Set[Any] = set(exclude_values)

    def perform(self, collection: Iterable[Any]) -> Generator[Any, None, None]:
        """Filter out elements in the collection that are in the specified exclude values."""
        for element in collection:
            if element in self.exclude_values:
                continue
            yield element


class IntersectQueryAction(QueryAction):
    """Class for only including elements that are in a specified collection."""
    def __init__(self, intersect_values: Iterable[Any]) -> None:
        self.intersect_values: Set[Any] = set(intersect_values)

    def perform(self, collection: Iterable[Any]) -> Generator[Any, None, None]:
        """Perform a set intersection on the collection and the specified values."""
        for element in collection:
            if element not in self.intersect_values:
                continue
            yield element


class UnionQueryAction(QueryAction):
    """Class for doing a set union on the collection and specified values."""
    def __init__(self, union_values: Iterable[Any]) -> None:
        self.union_values: Set[Any] = set(union_values)

    def perform(self, collection: Iterable[Any]) -> Generator[Any, None, None]:
        """Perform a set union on the collection and the specified values."""
        for element in collection:
            if element in self.union_values:
                self.union_values.remove(element)
            yield element

        for element in self.union_values:
            yield element


class ReverseQueryAction(QueryAction):
    """Class for reversing the collection."""

    def perform(self, collection: Iterable[Any]) -> Generator[Any, None, None]:
        """Reverses the collection."""
        # Unfortunately. no way to reverse a (potentially) generator without consuming it.
        # So, possible high memory usage here.
        collection_list = list(collection)
        for element in reversed(collection_list):
            yield element


class SkipQueryAction(QueryAction):
    """Class for skipping a certain number of elements."""
    def __init__(self, skip_count: int) -> None:
        self.skip_count: int = skip_count

    def perform(self, collection: Iterable[Any]) -> Generator[Any, None, None]:
        """Skip a certain number of elements."""
        for index, element in enumerate(collection):
            if index < self.skip_count:
                continue
            yield element


class SkipWhileQueryAction(QueryAction):
    """Class for skipping elements while a provided predicate is true."""
    def __init__(self, predicate: Predicate) -> None:
        self.predicate: Predicate = predicate

    def perform(self, collection: Iterable[Any]) -> Generator[Any, None, None]:
        """Skip elements while the provided predicate is true."""
        should_skip_elements = True
        for element in collection:
            if should_skip_elements and self.predicate(element):
                continue
            elif should_skip_elements:
                should_skip_elements = False
            yield element


class TakeQueryAction(QueryAction):
    """Class for taking a certain number of elements."""
    def __init__(self, take_count: int) -> None:
        self.take_count: int = take_count

    def perform(self, collection: Iterable[Any]) -> Generator[Any, None, None]:
        """Take a certain number of elements."""
        for index, element in enumerate(collection):
            if index < self.take_count:
                yield element
            raise StopIteration


class TakeWhileQueryAction(QueryAction):
    """Class for taking elements while a provided predicate is true."""
    def __init__(self, predicate: Predicate) -> None:
        self.predicate: Predicate = predicate

    def perform(self, collection: Iterable[Any]) -> Generator[Any, None, None]:
        """Take elements while the provided predicate is true."""
        for element in collection:
            if self.predicate(element):
                yield element
            raise StopIteration


class Query:
    """Class to handle searching on objects using a LINQ-like format."""

    def __init__(self, collection: Iterable[Any]) -> None:
        self.collection: Iterable[Any] = collection
        self.actions: List[QueryAction] = []

    # PROJECTION AND RESTRICTION METHODS

    def select(self, selector: Selector) -> 'Query':
        """
        Performs a map on the elements in the collection based on the provided method.

        :param selector: Method that takes an element and an index and returns a new element.
        :type selector: Callable[[Any, int], Any]
        :return: Query object
        :rtype: Query
        """
        self.actions.append(SelectQueryAction(selector, is_select_many=False))
        return self

    def select_many(self, selector: Selector) -> 'Query':
        """
        Performs a map on the elements in the collection based on the provided method, flattening iterables if applicable.

        :param selector: Method that takes an element and an index and returns a new element.
        :type selector: Callable[[Any, int], Any]
        :return: Query object
        :rtype: Query
        """
        self.actions.append(SelectQueryAction(selector, is_select_many=True))
        return self

    def where(self, predicate: Predicate) -> 'Query':
        """
        Filters the collection's elements based on the provided method.

        :param predicate: Method that takes an element and returns a boolean (True to include, False to exclude)
        :type predicate: Callable[[Any], bool]
        :return: Query object
        :rtype: Query
        """
        self.actions.append(WhereQueryAction(predicate))
        return self

    # SET METHODS

    def all(self, predicate: Predicate) -> bool:
        """
        Determines whether all the elements of a sequence satisfy a condition.

        :param predicate: Method that takes an element and returns a boolean.
        :type predicate: Callable[[Any], bool]
        :return: True if all elements match the predicate, otherwise false.
        :rtype: bool
        """
        return all(predicate(entry) for entry in self.__evaluate())

    def any(self, predicate: Predicate) -> bool:
        """
        Determines whether any of the elements of a sequence satisfy a condition.

        :param predicate: Method that takes an element and returns a boolean.
        :type predicate: Callable[[Any], bool]
        :return: True if any elements match the predicate, otherwise false.
        :rtype: bool
        """
        return any(predicate(entry) for entry in self.__evaluate())

    def contains(self, value: Any) -> bool:
        """
        Determines whether any of the elements of a sequence match the provided value.

        :param value: Value to compare against each element in the sequence.
        :type value: Any
        :return: True if any of the collection's elements matches the value, otherwise False.
        :rtype: bool
        """
        for entry in self.__evaluate():
            if entry == value:
                return True
        return False

    def distinct(self) -> 'Query':
        """
        Retrieve unique values from the sequence.

        :return: Query object
        :rtype: Query
        """
        self.actions.append(DistinctQueryAction())
        return self

    def except_(self, except_values: Iterable[Any]) -> 'Query':
        """
        Exclude values from the result set.

        :param except_values: Values to exclude from the result set.
        :type except_values: Iterable[Any]
        :return: Query object
        :rtype: Query
        """
        self.actions.append(ExceptQueryAction(except_values))
        return self

    def intersect(self, intersect_values: Iterable[Any]) -> 'Query':
        """
        Only include values from intersect_values in the result set.

        :param intersect_values: Values to exclusively include in the result set.
        :type intersect_values: Iterable[Any]
        :return: Query object
        :rtype: Query
        """
        self.actions.append(IntersectQueryAction(intersect_values))
        return self

    def union(self, union_values: Iterable[Any]) -> 'Query':
        """
        Perform a set union on the collection's elements and the provided values.

        :param union_values: Values to include along with the collection's elements.
        :type union_values: Iterable[Any]
        :return: Query object
        :rtype: Query
        """
        self.actions.append(UnionQueryAction(union_values))
        return self

    def reverse(self) -> 'Query':
        """
        Return the elements in the reverse order.

        :return: Query object
        :rtype: Query
        """
        self.actions.append(ReverseQueryAction())
        return self

    # AGGREGATE METHODS

    def count(self) -> int:
        """
        Retrieves the number of elements in the collection.

        :return: Number of elements in the collection.
        :rtype: int
        """
        return len(list(self.__evaluate()))

    def max(self) -> Any:
        """
        Retrieves the maximum value of the elements in the collection.

        :return: Maximum value of the elements in the collection.
        :rtype: Any
        """
        return max(list(self.__evaluate()))

    def min(self) -> Any:
        """
        Retrieves the minimum value of the elements in the collection.

        :return: Minimum value of the elements in the collection.
        :rtype: Any
        """
        return min(list(self.__evaluate()))

    def sum(self) -> int:
        """
        Retrieves the sum of the elements in the collection.

        :return: Sum of the elements in the collection.
        :rtype: int
        """
        return sum(list(self.__evaluate()))

    # PAGING METHODS

    def element_at(self, index: int, default: Any = None) -> Any:
        """
        Retrieves the element at a specified index from the collection.

        :param index: Index of the element to retrieve.
        :type index: int
        :param default: Default value to use if there's not at element at that index.
        :type default: Any
        :return: Element at the specified index from the collection.
        :rtype: Any
        :exception: IndexError when index is outside of collection and no default value is supplied.
        """
        for iter_index, element in enumerate(self.__evaluate()):
            if iter_index == index:
                return element
        if default is not None:
            return default
        raise IndexError

    def first(self, default: Any = None) -> Any:
        """
        Retrieves the first element in the collection.

        :param default: Default value to use if the collection is empty.
        :type default: Any
        :return: First element in the collection.
        :rtype: Any
        :exception: IndexError when collection is empty and no default value is supplied.
        """
        try:
            return next(self.__evaluate())
        except StopIteration:
            if default is not None:
                return default
            raise IndexError

    def last(self, default: Any = None) -> Any:
        """
        Retrieves the last element in the collection.

        :param default: Default value to use if the collection is empty.
        :type default: Any
        :return: Last element in the collection.
        :rtype: Any
        :exception: IndexError when collection is empty
        """
        dd = deque(self.__evaluate(), maxlen=1)
        try:
            return dd.pop()
        except IndexError:
            if default is not None:
                return default
            raise IndexError

    def single(self, default: Any = None) -> Any:
        """
        Retrieves a single value from the collection. An error will be thrown if there's more than one value.

        :param default: Default value to use if the collection is empty.
        :type default: Any
        :return: Single value from the collection.
        :rtype: Any
        :exception: IndexError on empty collection (if no default provided),
            InvalidOperationException if the collection has more than one element.
        """
        try:
            results = self.__evaluate()
            first_value = next(results)
        except StopIteration:
            if default is not None:
                return default
            raise IndexError

        try:
            next(results)
            raise InvalidOperationException()
        except StopIteration:
            return first_value

    def skip(self, skip_count: int) -> 'Query':
        """
        Skips a certain number of elements in the collection.

        :param skip_count: Number of elements to skip.
        :type skip_count: int
        :return: Query object
        :rtype: Query
        """
        self.actions.append(SkipQueryAction(skip_count))
        return self

    def skip_while(self, predicate: Predicate) -> 'Query':
        """
        Skips elements while the predicate's result for the element is True.

        :param predicate: Function that returns True if the element should be skipped, otherwise False.
        :type predicate: Callable[[Any], bool]
        :return: Query object
        :rtype: Query
        """
        self.actions.append(SkipWhileQueryAction(predicate))
        return self

    def take(self, take_count: int) -> 'Query':
        """
        Takes a certain number of elements in the collection.

        :param take_count: Number of elements to take.
        :type take_count: int
        :return: Query object
        :rtype: Query
        """
        self.actions.append(TakeQueryAction(take_count))
        return self

    def take_while(self, predicate: Predicate) -> 'Query':
        """
        Takes elements while the predicate's result for the element is True.

        :param predicate: Function that returns True if the element should be taken, otherwise False.
        :type predicate: Callable[[Any], bool]
        :return: Query object
        :rtype: Query
        """
        self.actions.append(TakeWhileQueryAction(predicate))
        return self

    def __iter__(self) -> Iterable[Any]:
        return self.__evaluate()

    def __evaluate(self) -> Generator[Any, None, None]:
        # Chain all of our generators together to get a cohesive "query".
        current_iterable: Iterable[Any] = self.collection
        for action in self.actions:
            current_iterable = action.perform(current_iterable)

        for element in current_iterable:
            yield element

    def to_list(self) -> List[Any]:
        """Gets the current query result as a list."""
        return list(self.__evaluate())
