import unittest
from tests.sample_pb2 import MessageOfTypes, extDouble, extString, NestedExtension
from tests.sample_proto3_pb2 import SomeMessage
from protobuf_to_dict import protobuf_to_dict, dict_to_protobuf
import base64
import nose.tools
import json


class Test(unittest.TestCase):
    def test_basics(self):
        m = self.populate_MessageOfTypes()
        d = protobuf_to_dict(m)
        self.compare(m, d, ['nestedRepeated'])

        m2 = dict_to_protobuf(d, MessageOfTypes)
        assert m == m2

    def test_use_enum_labels(self):
        m = self.populate_MessageOfTypes()
        d = protobuf_to_dict(m, use_enum_labels=True)
        self.compare(m, d, ['enm', 'enmRepeated', 'nestedRepeated'])
        assert d['enm'] == 'C'
        assert d['enmRepeated'] == ['A', 'C']

        m2 = dict_to_protobuf(d, MessageOfTypes)
        assert m == m2

        d['enm'] = 'MEOW'
        with nose.tools.assert_raises(KeyError):
            dict_to_protobuf(d, MessageOfTypes)

        d['enm'] = 'A'
        d['enmRepeated'] = ['B']
        dict_to_protobuf(d, MessageOfTypes)

        d['enmRepeated'] = ['CAT']
        with nose.tools.assert_raises(KeyError):
            dict_to_protobuf(d, MessageOfTypes)

    def test_repeated_enum(self):
        m = self.populate_MessageOfTypes()
        d = protobuf_to_dict(m, use_enum_labels=True)
        self.compare(m, d, ['enm', 'enmRepeated', 'nestedRepeated'])
        assert d['enmRepeated'] == ['A', 'C']

        m2 = dict_to_protobuf(d, MessageOfTypes)
        assert m == m2

        d['enmRepeated'] = ['MEOW']
        with nose.tools.assert_raises(KeyError):
            dict_to_protobuf(d, MessageOfTypes)

    def test_nested_repeated(self):
        m = self.populate_MessageOfTypes()
        m.nestedRepeated.extend([MessageOfTypes.NestedType(req=str(i)) for i in range(10)])

        d = protobuf_to_dict(m)
        self.compare(m, d, exclude=['nestedRepeated'])
        assert d['nestedRepeated'] == [{'req': str(i)} for i in range(10)]

        m2 = dict_to_protobuf(d, MessageOfTypes)
        assert m == m2

    def test_reverse(self):
        m = self.populate_MessageOfTypes()
        m2 = dict_to_protobuf(protobuf_to_dict(m), MessageOfTypes)
        assert m == m2
        m2.dubl = 0
        assert m2 != m

    def test_incomplete(self):
        m = self.populate_MessageOfTypes()
        d = protobuf_to_dict(m)
        d.pop('dubl')
        m2 = dict_to_protobuf(d, MessageOfTypes)
        assert m2.dubl == 0
        assert m != m2

    def test_pass_instance(self):
        m = self.populate_MessageOfTypes()
        d = protobuf_to_dict(m)
        d['dubl'] = 1
        m2 = dict_to_protobuf(d, m)
        assert m is m2
        assert m.dubl == 1

    def test_strict(self):
        m = self.populate_MessageOfTypes()
        d = protobuf_to_dict(m)
        d['meow'] = 1
        with nose.tools.assert_raises(KeyError):
            m2 = dict_to_protobuf(d, MessageOfTypes)
        m2 = dict_to_protobuf(d, MessageOfTypes, strict=False)
        assert m == m2

    def populate_MessageOfTypes(self):
        m = MessageOfTypes()
        m.dubl = 1.7e+308
        m.flot = 3.4e+038
        m.i32 = 2 ** 31 - 1 # 2147483647 #
        m.i64 = 2 ** 63 - 1 #0x7FFFFFFFFFFFFFFF
        m.ui32 = 2 ** 32 - 1
        m.ui64 = 2 ** 64 - 1
        m.si32 = -1 * m.i32
        m.si64 = -1 * m.i64
        m.f32 = m.i32
        m.f64 = m.i64
        m.sf32 = m.si32
        m.sf64 = m.si64
        m.bol = True
        m.strng = "string"
        m.byts = b'\n\x14\x1e'
        assert len(m.byts) == 3, len(m.byts)
        m.nested.req = "req"
        m.enm = MessageOfTypes.C #@UndefinedVariable
        m.enmRepeated.extend([MessageOfTypes.A, MessageOfTypes.C])
        m.range.extend(range(10))
        m.optional_string = 'optional'
        return m

    def compare(self, m, d, exclude=None):
        i = 0
        exclude = ['byts', 'nested'] + (exclude or [])
        for i, field in enumerate(MessageOfTypes.DESCRIPTOR.fields): #@UndefinedVariable
            if field.name not in exclude:
                assert field.name in d, field.name
                assert d[field.name] == getattr(m, field.name), (field.name, d[field.name])
        assert i > 0
        assert m.byts == base64.b64decode(d['byts'])
        assert d['nested'] == {'req': m.nested.req}

    def test_extensions(self):
        m = MessageOfTypes()

        primitives = {extDouble: 123.4, extString: "string", NestedExtension.extInt: 4}

        for key, value in primitives.items():
            m.Extensions[key] = value
        m.Extensions[NestedExtension.extNested].req = "nested"

        # Confirm compatibility with JSON serialization
        res = json.loads(json.dumps(protobuf_to_dict(m)))
        assert '___X' in res
        exts = res['___X']
        assert set(exts.keys()) == set([str(f.number) for f, _ in m.ListFields() if f.is_extension])
        for key, value in primitives.items():
            assert exts[str(key.number)] == value
        assert exts[str(NestedExtension.extNested.number)]['req'] == 'nested'

        deser = dict_to_protobuf(res, MessageOfTypes)
        assert deser
        for key, value in primitives.items():
            assert deser.Extensions[key] == m.Extensions[key]
        assert deser.Extensions[NestedExtension.extNested].req == m.Extensions[NestedExtension.extNested].req

    def test_value_in_dict_is_none(self):
        m = self.populate_MessageOfTypes()
        res = protobuf_to_dict(m)
        res['optional_string'] = None
        res['nested'] = None
        d = dict_to_protobuf(res, MessageOfTypes)
        self.assertEqual(d.optional_string, '')

    def test_message_with_proto3_map_protobuf_to_dict(self):
        m = SomeMessage()
        m.some_map['key1'] = 'value1'
        m.some_map['key2'] = 'value2'
        d = protobuf_to_dict(m)
        some_map = d['some_map']
        self.assertEqual(some_map['key1'], m.some_map['key1'])
        self.assertEqual(some_map['key2'], m.some_map['key2'])

    def test_message_with_proto3_map_dict_to_protobuf(self):
        d = {'some_map': {'key1': 'value1', 'key2': 'value2'}}
        m = dict_to_protobuf(d, SomeMessage)
        self.assertEqual(m.some_map['key1'], d['some_map']['key1'])
        self.assertEqual(m.some_map['key2'], d['some_map']['key2'])

    def test_message_with_proto3_enum_protobuf_to_dict(self):
        m = SomeMessage()
        m.enum_field = 0
        d = protobuf_to_dict(m)
        self.assertEqual(d['enum_field'], 0)

        m = SomeMessage()
        m.enum_field = 1
        d = protobuf_to_dict(m)
        self.assertEqual(d['enum_field'], 1)

    def test_message_with_proto3_enum_dict_to_protobuf(self):
        d = {'enum_field': 0}
        m = dict_to_protobuf(d, SomeMessage)
        self.assertEqual(m.enum_field, 0)

        d = {'enum_field': 1}
        m = dict_to_protobuf(d, SomeMessage)
        self.assertEqual(m.enum_field, 1)

    def test_message_with_proto3_bool_protobuf_to_dict(self):
        m = SomeMessage()
        m.bool_field = False
        d = protobuf_to_dict(m)
        self.assertEqual(d['bool_field'], False)

        m = SomeMessage()
        m.bool_field = True
        d = protobuf_to_dict(m)
        self.assertEqual(d['bool_field'], True)

    def test_message_with_proto3_bool_dict_to_protobuf(self):
        d = {'bool_field': False}
        m = dict_to_protobuf(d, SomeMessage)
        self.assertEqual(m.bool_field, False)

        d = {'bool_field': True}
        m = dict_to_protobuf(d, SomeMessage)
        self.assertEqual(m.bool_field, True)
