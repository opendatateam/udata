from datetime import datetime

from flask import request

from udata.api import API, api, fields
from udata.api_fields import patch
from udata.auth import current_user
from udata.core.organization.models import Organization
from udata.features.notifications.constants import NotificationChannel
from udata.features.notifications.permissions import EditNotificationPermission

from .models import Notification
from .settings import (
    NotificationPreference,
    NotificationSetting,
    resolved_preferences,
    subject_summary,
)

notifs = api.namespace("notifications", "Notifications API")


@notifs.route("/", endpoint="notifications")
class NotificationsAPI(API):
    @api.secure
    @api.doc("list_notifications")
    @api.expect(Notification.__index_parser__)
    @api.marshal_with(Notification.__page_fields__)
    def get(self):
        """List all current user pending notifications"""
        user = current_user._get_current_object()
        # Rows that only carry MAIL belong to somebody who muted the bell and asked for
        # a digest: they exist to be summarized, not to be shown here.
        notifications = Notification.objects(user=user, channels=NotificationChannel.APP)
        return Notification.apply_pagination(Notification.apply_sort_filters(notifications))


subject_summary_fields = api.model(
    "NotificationSubjectSummary",
    {
        "title": fields.String(description="The subject title"),
        "page": fields.String(description="The subject web page"),
        "organization": fields.Nested(
            Organization.__ref_fields__,
            allow_null=True,
            description="The organization to group the subject under",
        ),
    },
)

listed_setting_fields = api.inherit(
    "NotificationSettingListed",
    NotificationSetting.__read_fields__,
    {
        "subject": fields.Nested(
            subject_summary_fields,
            attribute=subject_summary,
            allow_null=True,
            description="The subject as the user may see it today, null once out of reach",
        ),
    },
)


@notifs.route("/settings/", endpoint="notification_settings")
class NotificationSettingsAPI(API):
    @api.secure
    @api.doc("list_notification_settings")
    @api.marshal_list_with(listed_setting_fields)
    def get(self):
        """List the decisions the current user took about their notifications.

        Only decisions are listed: whatever is absent follows the defaults."""
        return list(NotificationSetting.objects(user=current_user.id))

    @api.secure
    @api.doc("set_notification_setting")
    @api.expect(NotificationSetting.__write_fields__)
    @api.marshal_with(NotificationSetting.__read_fields__)
    @api.response(400, "Validation error")
    def put(self):
        """Follow or ignore some notifications on a subject.

        A decision is identified by its subject and event: deciding again replaces the
        previous answer."""
        decision = patch(NotificationSetting(user=current_user._get_current_object()), request)
        setting, created = NotificationSetting.objects.get_or_create(
            user=decision.user,
            scope=decision.scope,
            event=decision.event,
            updates={"enabled": decision.enabled},
        )
        return setting, 201 if created else 200


preference_fields = api.model(
    "NotificationPreferenceResolved",
    {
        "reason": fields.String(description="Why the user is concerned"),
        "channels": fields.List(
            fields.String, description="Where the user hears about it, defaults included"
        ),
    },
)


@notifs.route("/preferences/", endpoint="notification_preferences")
class NotificationPreferencesAPI(API):
    @api.secure
    @api.doc("list_notification_preferences")
    @api.marshal_list_with(preference_fields)
    def get(self):
        """How the current user hears about what concerns them, reason by reason."""
        return resolved_preferences(current_user._get_current_object())

    @api.secure
    @api.doc("set_notification_preference")
    @api.expect(NotificationPreference.__write_fields__)
    @api.marshal_list_with(preference_fields)
    @api.response(400, "Validation error")
    def put(self):
        """Choose the channels of one reason, and get every reason back."""
        user = current_user._get_current_object()
        preference = patch(NotificationPreference(user=user), request)
        NotificationPreference.objects.get_or_create(
            user=user,
            reason=preference.reason,
            updates={"channels": preference.channels},
        )
        return resolved_preferences(user)


@notifs.route("/settings/<notification_setting:setting>/", endpoint="notification_setting")
class NotificationSettingAPI(API):
    @api.secure
    @api.doc("delete_notification_setting")
    @api.response(204, "Decision removed, the default applies again")
    @api.response(404, "Decision not found")
    def delete(self, setting: NotificationSetting):
        """Withdraw a decision, so the default applies again."""
        if setting.user != current_user._get_current_object():
            api.abort(404, "Decision not found")
        setting.delete()
        return "", 204


@notifs.route("/<notification:notification>/read/", endpoint="read_notifications")
class NotificationsReadAPI(API):
    @api.secure
    @api.doc("read_notification", responses={400: "Validation error"})
    @api.marshal_with(Notification.__read_fields__)
    def post(self, notification: Notification):
        """Read a notification."""
        EditNotificationPermission(notification).test()

        notification.handled_at = datetime.now()
        notification.save()

        return notification
