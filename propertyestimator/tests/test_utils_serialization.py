"""
Units tests for propertyestimator.utils.serialization
"""
from enum import Enum, IntEnum

from simtk import unit

from propertyestimator.utils import get_data_filename
from propertyestimator.utils.serialization import serialize_force_field, deserialize_force_field, \
    TypedBaseModel


class Foo:

    def __init__(self):

        self.field1 = 'field1'
        self.field2 = 2

    def __getstate__(self):

        return {
            'field1': self.field1,
            'field2': self.field2
        }

    def __setstate__(self, state):

        self.field1 = state['field1']
        self.field2 = state['field2']


class FooInherited(Foo):

    def __init__(self):

        super().__init__()
        self.field3 = 100

    def __getstate__(self):

        self_state = {'field3': self.field3}
        parent_state = super(FooInherited, self).__getstate__()

        self_state.update(parent_state)

        return self_state

    def __setstate__(self, state):

        self.field3 = state['field3']
        super(FooInherited, self).__setstate__(state)


class Bar(TypedBaseModel):

    def __init__(self):

        self.field1 = 'field1'
        self.field2 = 2

    def __getstate__(self):

        return {
            'field1': self.field1,
            'field2': self.field2,
        }

    def __setstate__(self, state):

        self.field1 = state['field1']
        self.field2 = state['field2']


class BarInherited(Bar):

    field3: str = 1000


class Baz(Enum):

    Option1 = "Option1"
    Option2 = "Option2"


class Qux(IntEnum):

    Option1 = 1
    Option2 = 2


class NestedParent:

    class NestedChild(Enum):

        Option1 = "Option1"
        Option2 = "Option2"


class ComplexObject:

    class NestedClass1:

        def __init__(self):

            self.field1 = 5 * unit.kelvin

        def __getstate__(self):
            return {
                'field1': self.field1,
            }

        def __setstate__(self, state):
            self.field1 = state['field1']

    class NestedClass2:

        def __init__(self):
            self.field1 = Qux.Option1

        def __getstate__(self):
            return {
                'field1': self.field1,
            }

        def __setstate__(self, state):
            self.field1 = state['field1']

    def __init__(self):

        self.field1 = ComplexObject.NestedClass1()
        self.field2 = ComplexObject.NestedClass2()

    def __getstate__(self):

        return {
            'field1': self.field1,
            'field2': self.field2
        }

    def __setstate__(self, state):

        self.field1 = state['field1']
        self.field2 = state['field2']


class TestClass(TypedBaseModel):

    def __init__(self, inputs=None):
        self.inputs = inputs

        self.foo = Foo()
        self.bar = Bar()

        self.foo_inherited = FooInherited()
        self.bar_inherited = BarInherited()

        self.complex = ComplexObject()

    def __getstate__(self):

        return {
            'inputs': self.inputs,

            'foo': self.foo,
            'bar': self.bar,
    
            'foo_inherited': self.foo_inherited,
            'bar_inherited': self.bar_inherited,
    
            'complex': self.complex,
        }

    def __setstate__(self, state):

        self.inputs = state['inputs']

        self.foo = state['foo']
        self.bar = state['bar']

        self.foo_inherited = state['foo_inherited']
        self.bar_inherited = state['bar_inherited']

        self.complex = state['complex']


def test_polymorphic_dictionary():
    """Test the polymorphic dictionary helper class."""

    test_dictionary = {
        "test_str": 'test1',
        "test_int": 1,
        "test_bool": True,
        "test_None": None,
        "test_Foo": Foo(),
        "test_FooInherited": FooInherited(),
        "test_Bar": Bar(),
        "test_BarInherited": BarInherited(),
        "test_Baz": Baz.Option1,
        "test_Qux": Qux.Option1,
        "test_Nested": NestedParent.NestedChild.Option1,
        "test_List": [Foo(), Bar(), 1, 'Hello World'],
        "test_Complex": ComplexObject()
    }

    test_object = TestClass(inputs=test_dictionary)
    test_json = test_object.json()

    test_recreated = TestClass.parse_json(test_json)
    test_recreated_json = test_recreated.json()

    assert test_json == test_recreated_json


def test_force_field_serialization():

    from openforcefield.typing.engines import smirnoff

    force_field = smirnoff.ForceField(get_data_filename('forcefield/smirnoff99Frosst.offxml'))

    serialized_force_field = serialize_force_field(force_field)
    deserialized_force_field = deserialize_force_field(serialized_force_field)

    original_generators = force_field.getGenerators()
    deserialized_generators = deserialized_force_field.getGenerators()

    assert len(original_generators) == len(deserialized_generators)
