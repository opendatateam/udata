import pytest

from werkzeug.datastructures import MultiDict

from udata.forms import ModelForm, fields
from udata.i18n import gettext as _
from udata.models import db


pytestmark = [
    pytest.mark.usefixtures('clean_db')
]


class Target(db.Document):
    name = db.StringField()


class Model(db.Document):
    name = db.StringField()
    target = db.GenericReferenceField()


class ModelExplicit(db.Document):
    name = db.StringField()
    target = db.ReferenceField(Target)


class Generic:
    model = Model

    def test_error_with_inline_identifier(self):
        expected_target = Target.objects.create()
        form = self.form.from_json({
            'name': 'test',
            'target': str(expected_target.pk),
        })

        form.validate()

        assert 'target' in form.errors
        assert len(form.errors['target']) == 1
        assert form.errors['target'][0] == _('Expect both class and identifier')

    def test_error_with_identifier_only(self):
        expected_target = Target.objects.create()
        form = self.form.from_json({
            'name': 'test',
            'target': {'id': str(expected_target.pk)},
        })

        form.validate()

        assert 'target' in form.errors
        assert len(form.errors['target']) == 1
        assert form.errors['target'][0] == _('Expect both class and identifier')

    def test_error_with_unknown_model(self):
        form = self.form.from_json({
            'name': 'test',
            'target': {
                'class': 'Unknown',
                'id': 42
            },
        })

        form.validate()

        assert 'target' in form.errors
        assert len(form.errors['target']) == 1
        assert form.errors['target'][0] == 'Model "Unknown" does not exist'


class Explicit:
    model = ModelExplicit

    def test_with_inline_identifier_multidict(self):
        expected_target = Target.objects.create()
        model = self.model()
        form = self.form(MultiDict({
            'name': 'test',
            'target': str(expected_target.pk),
        }))

        form.validate()
        assert form.errors == {}

        form.populate_obj(model)

        assert isinstance(model.target, Target)
        assert model.target == expected_target

    def test_with_identifier_only_multidict(self):
        expected_target = Target.objects.create()
        model = self.model()
        form = self.form(MultiDict({
            'name': 'test',
            'target-id': str(expected_target.pk),
        }))

        form.validate()
        assert form.errors == {}

        form.populate_obj(model)

        assert isinstance(model.target, Target)
        assert model.target == expected_target

    def test_with_inline_identifier_json(self):
        expected_target = Target.objects.create()
        model = self.model()
        form = self.form.from_json({
            'name': 'test',
            'target': str(expected_target.pk),
        })

        form.validate()
        assert form.errors == {}

        form.populate_obj(model)

        assert isinstance(model.target, Target)
        assert model.target == expected_target

    def test_with_identifier_only_json(self):
        expected_target = Target.objects.create()
        model = self.model()
        form = self.form.from_json({
            'name': 'test',
            'target': {'id': str(expected_target.pk)},
        })

        form.validate()
        assert form.errors == {}

        form.populate_obj(model)

        assert isinstance(model.target, Target)
        assert model.target == expected_target

    def test_error_with_class_mismatch(self):
        expected_target = Target.objects.create()
        form = self.form.from_json({
            'name': 'test',
            'target': {
                'class': 'Wrong',
                'id': str(expected_target.pk)
            },
        })

        form.validate()

        assert 'target' in form.errors
        assert len(form.errors['target']) == 1
        assert form.errors['target'][0] == _('Expect a "Target" class but "Wrong" was found')


class Required:
    required = True

    def test_not_provided(self):
        form = self.form.from_json({'name': 'test'})

        form.validate()

        assert 'target' in form.errors
        assert len(form.errors['target']) == 1
        assert 'requis' in form.errors['target'][0]

    def test_none(self):
        form = self.form.from_json({
            'name': 'test',
            'target': None,
        })

        form.validate()

        assert 'target' in form.errors
        assert len(form.errors['target']) == 1
        assert 'requis' in form.errors['target'][0]

    def test_with_initial_object_none(self):
        model = self.model(target=Target.objects.create())

        form = self.form.from_json({
            'name': 'test',
            'target': None,
        }, model)

        form.validate()

        assert 'target' in form.errors
        assert len(form.errors['target']) == 1
        assert 'requis' in form.errors['target'][0]


class Optionnal:
    '''Optional ModelField specific tests'''
    required = False

    def test_with_initial_object_none(self):
        model = self.model(target=Target.objects.create())

        form = self.form.from_json({
            'name': 'test',
            'target': None,
        }, model)

        form.validate()
        assert form.errors == {}

        form.populate_obj(model)

        assert model.target is None


class CommonMixin:
    @property
    def form(self):
        validators = [fields.validators.DataRequired()] if self.required else []

        class Form(ModelForm):
            model_class = self.model
            name = fields.StringField()
            target = fields.ModelField(validators=validators)

        return Form

    def test_empty_data(self):
        model = self.model()
        form = self.form()
        form.populate_obj(model)

        assert model.target is None

    def test_with_valid_multidict(self):
        expected_target = Target.objects.create()
        model = self.model()
        form = self.form(MultiDict({
            'name': 'test',
            'target-class': 'Target',
            'target-id': str(expected_target.pk)
        }))

        form.validate()
        assert form.errors == {}

        form.populate_obj(model)

        assert isinstance(model.target, Target)
        assert model.target == expected_target

    def test_with_valid_json(self):
        expected_target = Target.objects.create()
        model = self.model()
        form = self.form.from_json({
            'name': 'test',
            'target': {
                'class': 'Target',
                'id': str(expected_target.pk)
            }
        })

        form.validate()
        assert form.errors == {}

        form.populate_obj(model)

        assert isinstance(model.target, Target)
        assert model.target == expected_target

    def test_with_initial_object(self):
        initial_target = Target.objects.create()
        expected_target = Target.objects.create()
        model = self.model(target=initial_target)

        form = self.form.from_json({
            'name': 'test',
            'target': {
                'class': 'Target',
                'id': str(expected_target.pk)
            }
        }, model)

        form.validate()
        assert form.errors == {}

        form.populate_obj(model)

        assert isinstance(model.target, Target)
        assert model.target == expected_target

    def test_with_non_submitted_initial_object(self):
        expected_target = Target.objects.create()
        model = self.model(target=expected_target)

        form = self.form.from_json({'name': 'test'}, model)

        form.validate()
        assert form.errors == {}

        form.populate_obj(model)

        assert isinstance(model.target, Target)
        assert model.target == expected_target

    def test_multidict_errors(self):
        form = self.form(MultiDict({
            'name': 'test',
            'target-class': 'Target',
        }))

        form.validate()

        assert 'target' in form.errors
        assert len(form.errors['target']) == 1
        # assert 'Unsupported identifier' in form.errors['target'][0]
        assert form.errors['target'][0] == _('Missing "id" field')

    def test_json_errors(self):
        form = self.form.from_json({
            'name': 'test',
            'target': {
                'class': 'Target',
            }
        })

        form.validate()

        assert 'target' in form.errors
        assert len(form.errors['target']) == 1
        assert form.errors['target'][0] == _('Missing "id" field')

    def test_bad_id(self):
        form = self.form.from_json({
            'name': 'test',
            'target': {
                'class': 'Target',
                'id': 'wrong'
            }
        })

        form.validate()

        assert 'target' in form.errors
        assert len(form.errors['target']) == 1
        assert 'Unsupported identifier' in form.errors['target'][0]


class Optionnal_GenericReference_Test(Generic, Optionnal, CommonMixin):
    pass


class Optionnal_ExplicitReference_Test(Explicit, Optionnal, CommonMixin):
    pass


class Required_GenericReference_Test(Generic, Required, CommonMixin):
    pass


class Required_ExplicitReference_Test(Explicit, Required, CommonMixin):
    pass
