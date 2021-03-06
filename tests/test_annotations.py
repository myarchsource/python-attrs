"""
Tests for PEP-526 type annotations.

Python 3.6+ only.
"""

import types
import typing

import pytest

import attr

from attr._make import _classvar_prefixes
from attr.exceptions import UnannotatedAttributeError


class TestAnnotations:
    """
    Tests for types derived from variable annotations (PEP-526).
    """

    def test_basic_annotations(self):
        """
        Sets the `Attribute.type` attr from basic type annotations.
        """

        @attr.s
        class C:
            x: int = attr.ib()
            y = attr.ib(type=str)
            z = attr.ib()

        assert int is attr.fields(C).x.type
        assert str is attr.fields(C).y.type
        assert None is attr.fields(C).z.type
        assert C.__init__.__annotations__ == {
            "x": int,
            "y": str,
            "return": None,
        }

    def test_catches_basic_type_conflict(self):
        """
        Raises ValueError if type is specified both ways.
        """
        with pytest.raises(ValueError) as e:

            @attr.s
            class C:
                x: int = attr.ib(type=int)

        assert (
            "Type annotation and type argument cannot both be present",
        ) == e.value.args

    def test_typing_annotations(self):
        """
        Sets the `Attribute.type` attr from typing annotations.
        """

        @attr.s
        class C:
            x: typing.List[int] = attr.ib()
            y = attr.ib(type=typing.Optional[str])

        assert typing.List[int] is attr.fields(C).x.type
        assert typing.Optional[str] is attr.fields(C).y.type
        assert C.__init__.__annotations__ == {
            "x": typing.List[int],
            "y": typing.Optional[str],
            "return": None,
        }

    def test_only_attrs_annotations_collected(self):
        """
        Annotations that aren't set to an attr.ib are ignored.
        """

        @attr.s
        class C:
            x: typing.List[int] = attr.ib()
            y: int

        assert 1 == len(attr.fields(C))
        assert C.__init__.__annotations__ == {
            "x": typing.List[int],
            "return": None,
        }

    @pytest.mark.parametrize("slots", [True, False])
    def test_auto_attribs(self, slots):
        """
        If *auto_attribs* is True, bare annotations are collected too.
        Defaults work and class variables are ignored.
        """

        @attr.s(auto_attribs=True, slots=slots)
        class C:
            cls_var: typing.ClassVar[int] = 23
            a: int
            x: typing.List[int] = attr.Factory(list)
            y: int = 2
            z: int = attr.ib(default=3)
            foo: typing.Any = None

        i = C(42)
        assert "C(a=42, x=[], y=2, z=3, foo=None)" == repr(i)

        attr_names = set(a.name for a in C.__attrs_attrs__)
        assert "a" in attr_names  # just double check that the set works
        assert "cls_var" not in attr_names

        assert int == attr.fields(C).a.type

        assert attr.Factory(list) == attr.fields(C).x.default
        assert typing.List[int] == attr.fields(C).x.type

        assert int == attr.fields(C).y.type
        assert 2 == attr.fields(C).y.default

        assert int == attr.fields(C).z.type

        assert typing.Any == attr.fields(C).foo.type

        # Class body is clean.
        if slots is False:
            with pytest.raises(AttributeError):
                C.y

            assert 2 == i.y
        else:
            assert isinstance(C.y, types.MemberDescriptorType)

            i.y = 23
            assert 23 == i.y

        assert C.__init__.__annotations__ == {
            "a": int,
            "x": typing.List[int],
            "y": int,
            "z": int,
            "foo": typing.Any,
            "return": None,
        }

    @pytest.mark.parametrize("slots", [True, False])
    def test_auto_attribs_unannotated(self, slots):
        """
        Unannotated `attr.ib`s raise an error.
        """
        with pytest.raises(UnannotatedAttributeError) as e:

            @attr.s(slots=slots, auto_attribs=True)
            class C:
                v = attr.ib()
                x: int
                y = attr.ib()
                z: str

        assert (
            "The following `attr.ib`s lack a type annotation: v, y.",
        ) == e.value.args

    @pytest.mark.parametrize("slots", [True, False])
    def test_auto_attribs_subclassing(self, slots):
        """
        Attributes from base classes are inherited, it doesn't matter if the
        subclass has annotations or not.

        Ref #291
        """

        @attr.s(slots=slots, auto_attribs=True)
        class A:
            a: int = 1

        @attr.s(slots=slots, auto_attribs=True)
        class B(A):
            b: int = 2

        @attr.s(slots=slots, auto_attribs=True)
        class C(A):
            pass

        assert "B(a=1, b=2)" == repr(B())
        assert "C(a=1)" == repr(C())

        assert A.__init__.__annotations__ == {"a": int, "return": None}
        assert B.__init__.__annotations__ == {
            "a": int,
            "b": int,
            "return": None,
        }
        assert C.__init__.__annotations__ == {"a": int, "return": None}

    def test_converter_annotations(self):
        """
        Attributes with converters don't have annotations.
        """

        @attr.s(auto_attribs=True)
        class A:
            a: int = attr.ib(converter=int)

        assert A.__init__.__annotations__ == {"return": None}

    @pytest.mark.parametrize("slots", [True, False])
    @pytest.mark.parametrize("classvar", _classvar_prefixes)
    def test_annotations_strings(self, slots, classvar):
        """
        String annotations are passed into __init__ as is.
        """

        @attr.s(auto_attribs=True, slots=slots)
        class C:
            cls_var: classvar + "[int]" = 23
            a: "int"
            x: "typing.List[int]" = attr.Factory(list)
            y: "int" = 2
            z: "int" = attr.ib(default=3)
            foo: "typing.Any" = None

        assert C.__init__.__annotations__ == {
            "a": "int",
            "x": "typing.List[int]",
            "y": "int",
            "z": "int",
            "foo": "typing.Any",
            "return": None,
        }

    def test_keyword_only_auto_attribs(self):
        """
        `kw_only` propagates to attributes defined via `auto_attribs`.
        """

        @attr.s(auto_attribs=True, kw_only=True)
        class C:
            x: int
            y: int

        with pytest.raises(TypeError):
            C(0, 1)

        with pytest.raises(TypeError):
            C(x=0)

        c = C(x=0, y=1)

        assert c.x == 0
        assert c.y == 1

    def test_base_class_variable(self):
        """
        Base class' class variables can be overridden with an attribute
        without resorting to using an explicit `attr.ib()`.
        """

        class Base:
            x: int = 42

        @attr.s(auto_attribs=True)
        class C(Base):
            x: int

        assert 1 == C(1).x

    def test_removes_none_too(self):
        """
        Regression test for #523: make sure defaults that are set to None are
        removed too.
        """

        @attr.s(auto_attribs=True)
        class C:
            x: int = 42
            y: typing.Any = None

        with pytest.raises(AttributeError):
            C.x

        with pytest.raises(AttributeError):
            C.y

    def test_non_comparable_defaults(self):
        """
        Regression test for #585: objects that are not directly comparable
        (for example numpy arrays) would cause a crash when used as
        default values of an attrs auto-attrib class.
        """

        class NonComparable:
            def __eq__(self, other):
                raise ValueError

        @attr.s(auto_attribs=True)
        class C:
            x: typing.Any = NonComparable()
