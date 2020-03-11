from bson import ObjectId
from werkzeug.datastructures import MultiDict

from udata.forms import ModelForm, fields
from udata.models import db
from udata.tests import TestCase
from udata.utils import faker


class Nested(db.Document):
    name = db.StringField()


class WithReference(db.Document):
    name = db.StringField()
    nested = db.ReferenceField(Nested)


class WithReferenceForm(ModelForm):
    model_class = WithReference
    name = fields.StringField()
    nested = fields.ModelField()


class ModelFieldTestMixin(object):
    model = None
    form = None

    def test_empty_data(self):
        model = self.model()
        form = self.form()

        self.assertIsNone(form.nested.data)

        form.populate_obj(model)

        self.assertIsNone(model.nested)

    def test_initial_data(self):
        nested = Nested.objects.create(name=faker.name())
        model = self.model(nested=nested)
        form = self.form(obj=model)

        self.assertEqual(form.nested.data, nested)

        form.populate_obj(model)

        self.assertEqual(model.nested, nested)

    def test_with_valid_json_data_ref(self):
        nested = Nested.objects.create(name=faker.name())
        model = self.model()
        form = self.form.from_json({'nested': {
            'class': 'Nested',
            'id': str(nested.id)
        }})

        form.validate()
        self.assertEqual(form.errors, {})
        self.assertEqual(form.nested.data, nested)

        form.populate_obj(model)

        self.assertIsInstance(model.nested, Nested)
        self.assertEqual(model.nested, nested)

    def test_with_invalid_ref_class(self):
        nested = Nested.objects.create(name=faker.name())
        form = self.form.from_json({'nested': {
            'class': 'Bad',
            'id': str(nested.id)
        }})

        form.validate()
        self.assertIn('nested', form.errors)
        self.assertEqual(len(form.errors['nested']), 1)

    def test_with_invalid_ref_id(self):
        Nested.objects.create(name=faker.name())
        form = self.form.from_json({'nested': {
            'class': 'Nested',
            'id': 'bad'
        }})

        form.validate()
        self.assertIn('nested', form.errors)
        self.assertEqual(len(form.errors['nested']), 1)

    def test_not_found(self):
        form = self.form.from_json({'nested': {
            'class': 'Nested',
            'id': str(ObjectId())
        }})

        form.validate()
        self.assertIn('nested', form.errors)
        self.assertEqual(len(form.errors['nested']), 1)


class ModelFieldWithReferenceTest(ModelFieldTestMixin, TestCase):
    model = WithReference
    form = WithReferenceForm

    def test_with_valid_form_data_id_only(self):
        nested = Nested.objects.create(name=faker.name())
        model = WithReference()
        form = WithReferenceForm(MultiDict({
            'nested': str(nested.id)
        }))

        form.validate()
        self.assertEqual(form.errors, {})
        self.assertEqual(form.nested.data, nested)

        form.populate_obj(model)

        self.assertIsInstance(model.nested, Nested)
        self.assertEqual(model.nested, nested)

    def test_with_valid_json_data_id_only(self):
        nested = Nested.objects.create(name=faker.name())
        model = WithReference()
        form = WithReferenceForm.from_json({'nested': str(nested.id)})

        form.validate()
        self.assertEqual(form.errors, {})
        self.assertEqual(form.nested.data, nested)

        form.populate_obj(model)

        self.assertIsInstance(model.nested, Nested)
        self.assertEqual(model.nested, nested)

    def test_with_invalid_id(self):
        Nested.objects.create(name=faker.name())
        form = WithReferenceForm.from_json({'nested': 'bad'})

        form.validate()
        self.assertIn('nested', form.errors)
        self.assertEqual(len(form.errors['nested']), 1)


class Nested2(db.Document):
    '''A dummy model just to nesting/ReferenceField'''
    name = db.StringField()


class Nested3(db.Document):
    '''A dummy model just to nesting/ReferenceField'''
    name = db.StringField()


class WithGeneric(db.Document):
    name = db.StringField()
    nested = db.GenericReferenceField()


class WithGenericChoices(db.Document):
    name = db.StringField()
    nested = db.GenericReferenceField(choices=[Nested, Nested2])


class WithGenericForm(ModelForm):
    model_class = WithGeneric
    name = fields.StringField()
    nested = fields.ModelField()


class WithGenericChoicesForm(ModelForm):
    model_class = WithGenericChoices
    name = fields.StringField()
    nested = fields.ModelField()


class ModelFieldWithGenericTest(ModelFieldTestMixin, TestCase):
    model = WithGeneric
    form = WithGenericForm

    def test_with_valid_form_data_id_only(self):
        nested = Nested.objects.create(name=faker.name())
        form = WithGenericForm(MultiDict({
            'nested': str(nested.id)
        }))

        form.validate()
        self.assertIn('nested', form.errors)
        self.assertEqual(len(form.errors['nested']), 1)

    def test_with_valid_json_data_id_only(self):
        nested = Nested.objects.create(name=faker.name())
        form = WithGenericForm.from_json({'nested': str(nested.id)})

        form.validate()
        self.assertIn('nested', form.errors)
        self.assertEqual(len(form.errors['nested']), 1)


class ModelFieldWithGenericChoicesTest(ModelFieldTestMixin, TestCase):
    model = WithGenericChoices
    form = WithGenericChoicesForm

    def test_with_valid_form_data_id_only(self):
        nested = Nested.objects.create(name=faker.name())
        form = WithGenericChoicesForm(MultiDict({
            'nested': str(nested.id)
        }))

        form.validate()
        self.assertIn('nested', form.errors)
        self.assertEqual(len(form.errors['nested']), 1)

    def test_with_valid_json_data_id_only(self):
        nested = Nested.objects.create(name=faker.name())
        form = WithGenericChoicesForm.from_json({'nested': str(nested.id)})

        form.validate()
        self.assertIn('nested', form.errors)
        self.assertEqual(len(form.errors['nested']), 1)

    def test_with_ref_class_not_in_choices(self):
        nested = Nested.objects.create(name=faker.name())
        form = self.form.from_json({'nested': {
            'class': 'Nested3',
            'id': str(nested.id)
        }})

        form.validate()
        self.assertIn('nested', form.errors)
        self.assertEqual(len(form.errors['nested']), 1)
