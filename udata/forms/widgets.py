from wtforms import widgets

TAG_MIN_LENGTH = 2
TAG_MAX_LENGTH = 50


class WidgetHelper:
    classes = []
    attributes = {}

    def __call__(self, field, **kwargs):
        # Handle extra classes
        classes = (kwargs.pop("class", "") or kwargs.pop("class_", "")).split()
        extra_classes = self.classes if isinstance(self.classes, (list, tuple)) else [self.classes]
        classes.extend([cls for cls in extra_classes if cls not in classes])
        kwargs["class"] = " ".join(classes)

        # Handle defaults
        for key, value in self.attributes.items():
            kwargs.setdefault(key, value)

        return super().__call__(field, **kwargs)


class TextInput(WidgetHelper, widgets.TextInput):
    pass


class TextArea(WidgetHelper, widgets.TextArea):
    pass


class MarkdownEditor(WidgetHelper, widgets.TextArea):
    classes = "md"
    attributes = {"rows": 8}


class DateRangePicker(WidgetHelper, widgets.HiddenInput):
    classes = "dtpicker"

    def __call__(self, field, **kwargs):
        if field.data:
            kwargs["data-start-date"] = field.data.start
            kwargs["data-end-date"] = field.data.end
        return super().__call__(field, **kwargs)
