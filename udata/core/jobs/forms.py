from udata.forms import ModelForm, fields, validators
from udata.i18n import lazy_gettext as _

from .models import PeriodicTask


class CrontabForm(ModelForm):
    model_class = PeriodicTask.Crontab

    minute = fields.StringField(default="*")
    hour = fields.StringField(default="*")
    day_of_week = fields.StringField(default="*")
    day_of_month = fields.StringField(default="*")
    month_of_year = fields.StringField(default="*")


class IntervalForm(ModelForm):
    model_class = PeriodicTask.Interval

    every = fields.IntegerField(validators=[validators.NumberRange(min=0)])
    period = fields.StringField()


class PeriodicTaskForm(ModelForm):
    model_class = PeriodicTask

    name = fields.StringField(_("Name"), [validators.DataRequired()])
    description = fields.StringField(_("Description"))
    task = fields.StringField(_("Tasks"))
    enabled = fields.BooleanField(_("Enabled"))

    def save(self, commit=True, **kwargs):
        """
        PeriodicTask is dynamic and save behavior changed
        See: https://github.com/zakird/celerybeat-mongo/commit/dfbbd20edde91134b57f5406d0ce4eac59d6899b
        """
        if not self.instance:
            self.instance = self.model_class()  # Force populate_obj in super()
        return super(PeriodicTaskForm, self).save(commit, **kwargs)


class CrontabTaskForm(PeriodicTaskForm):
    crontab = fields.FormField(CrontabForm)


class IntervalTaskForm(PeriodicTaskForm):
    interval = fields.FormField(IntervalForm)
