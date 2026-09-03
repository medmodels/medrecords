"""Checks on the quality of the data in a MedRecord."""

from __future__ import annotations

from typing import TYPE_CHECKING, Generic, Mapping, Optional

from graphrecords import EdgeEndpointRole

from medrecords.evaluation.analytic import Analytic, Assessment
from medrecords.evaluation.catalogue.attributes import AttributeAnalytic, IndexType
from medrecords.evaluation.results import read
from medrecords.medrecord import MedRecord

if TYPE_CHECKING:
    from graphrecords import AttributeName, Value, querying

    from medrecords.evaluation.analytic import Detail


class AttributeRange(AttributeAnalytic[IndexType]):
    """Checks that no value of an attribute lies outside a range."""

    _minimum: Value
    _maximum: Value

    def __init__(
        self,
        attribute: AttributeName,
        elements: querying.ElementsExpression[IndexType, querying.Unordered],
        minimum: Value = None,
        maximum: Value = None,
    ) -> None:
        """Initializes a range check.

        Args:
            attribute (AttributeName): The attribute to check.
            elements (querying.ElementsExpression[IndexType, querying.Unordered]):
                The nodes or edges to look at.
            minimum (Value): The smallest acceptable value, or None for no lower
                bound. Defaults to None.
            maximum (Value): The largest acceptable value, or None for no upper
                bound. Defaults to None.

        Raises:
            ValueError: If neither bound is given.
        """
        super().__init__(attribute, elements)

        if minimum is None and maximum is None:
            msg = "a range check needs a minimum or a maximum"
            raise ValueError(msg)

        self._minimum = minimum
        self._maximum = maximum

    def compute(self, medrecord: MedRecord) -> Assessment:
        """Counts the values outside the range.

        Args:
            medrecord (MedRecord): The MedRecord to look at.

        Returns:
            Assessment: The number of values outside the range, which must be
                zero.
        """
        carrying = self._carrying(medrecord)
        values = carrying.attribute(self._attribute)

        if self._minimum is None:
            outside = values > self._maximum
        elif self._maximum is None:
            outside = values < self._minimum
        else:
            outside = (values < self._minimum) | (values > self._maximum)

        count = read(carrying.filter(outside).count().evaluate(), int)
        return Assessment(count, "none allowed", passed=count == 0)

    def title(self) -> Optional[str]:
        """Names the analytic.

        Returns:
            Optional[str]: The heading.
        """
        return f"Values of {self._attribute} outside the range"

    def parameters(self) -> Mapping[str, Detail]:
        """Records the attribute and the bounds.

        Returns:
            Mapping[str, Detail]: The details.
        """
        details = dict(super().parameters())

        if self._minimum is not None:
            details["minimum"] = self._minimum

        if self._maximum is not None:
            details["maximum"] = self._maximum

        return details


class AttributeUniqueness(AttributeAnalytic[IndexType]):
    """Checks that no two elements share a value of an attribute."""

    def compute(self, medrecord: MedRecord) -> Assessment:
        """Counts the elements whose value another element also carries.

        Args:
            medrecord (MedRecord): The MedRecord to look at.

        Returns:
            Assessment: The number of elements with a shared value, which must
                be zero.
        """
        carrying = self._carrying(medrecord)
        shared = carrying.attribute(self._attribute).is_duplicated()

        count = read(carrying.filter(shared).count().evaluate(), int)
        return Assessment(count, "none allowed", passed=count == 0)

    def title(self) -> Optional[str]:
        """Names the analytic.

        Returns:
            Optional[str]: The heading.
        """
        return f"Elements sharing a value of {self._attribute}"


class AttributeOrder(Analytic[MedRecord], Generic[IndexType]):
    """Checks that one date attribute never lies before another."""

    _earlier: AttributeName
    _later: AttributeName
    _elements: querying.ElementsExpression[IndexType, querying.Unordered]

    def __init__(
        self,
        earlier: AttributeName,
        later: AttributeName,
        elements: querying.ElementsExpression[IndexType, querying.Unordered],
    ) -> None:
        """Initializes an order check.

        Args:
            earlier (AttributeName): The attribute that must come first.
            later (AttributeName): The attribute that must not come before it.
            elements (querying.ElementsExpression[IndexType, querying.Unordered]):
                The nodes or edges to look at.
        """
        self._earlier = earlier
        self._later = later
        self._elements = elements

    def compute(self, medrecord: MedRecord) -> Assessment:
        """Counts the elements whose later date lies before the earlier one.

        Elements lacking either attribute are left out.

        Args:
            medrecord (MedRecord): The MedRecord to look at.

        Returns:
            Assessment: The number of elements out of order, which must be zero.
        """
        series = medrecord.query(self._elements)
        dated = series.filter(
            series.has_attribute(self._earlier) & series.has_attribute(self._later)
        )
        disordered = dated.attribute(self._later) < dated.attribute(self._earlier)

        count = read(dated.filter(disordered).count().evaluate(), int)
        return Assessment(count, "none allowed", passed=count == 0)

    def title(self) -> Optional[str]:
        """Names the analytic.

        Returns:
            Optional[str]: The heading.
        """
        return f"Order of {self._earlier} and {self._later}"

    def description(self) -> Optional[str]:
        """Explains the analytic.

        Returns:
            Optional[str]: The text under the heading.
        """
        return "Elements lacking either attribute are left out."

    def parameters(self) -> Mapping[str, Detail]:
        """Records the attributes.

        Returns:
            Mapping[str, Detail]: The details.
        """
        return {"earlier": self._earlier, "later": self._later}


class UnlinkedNodes(Analytic[MedRecord]):
    """Checks that every selected node takes part in one of the selected edges."""

    _nodes: querying.NodesExpression
    _edges: querying.EdgesExpression
    _role: EdgeEndpointRole

    def __init__(
        self,
        nodes: querying.NodesExpression,
        edges: querying.EdgesExpression,
        role: EdgeEndpointRole,
    ) -> None:
        """Initializes a check for unlinked nodes.

        Args:
            nodes (querying.NodesExpression): The nodes that must be linked.
            edges (querying.EdgesExpression): The edges that link them.
            role (EdgeEndpointRole): Whether a node must be the source or the
                target of an edge.
        """
        self._nodes = nodes
        self._edges = edges
        self._role = role

    def compute(self, medrecord: MedRecord) -> Assessment:
        """Counts the nodes without an edge.

        Args:
            medrecord (MedRecord): The MedRecord to look at.

        Returns:
            Assessment: The number of unlinked nodes, which must be zero.
        """
        links = medrecord.query(self._edges)
        linked = (
            links.source_node()
            if self._role is EdgeEndpointRole.Source
            else links.target_node()
        )
        members = medrecord.query(self._nodes)
        unlinked = members.filter(~members.index().is_in(linked.index()))

        count = read(unlinked.count().evaluate(), int)
        return Assessment(count, "none allowed", passed=count == 0)

    def parameters(self) -> Mapping[str, Detail]:
        """Records the role.

        Returns:
            Mapping[str, Detail]: The role.
        """
        return {"role": self._role.name.lower()}
