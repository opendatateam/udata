from udata.auth import Permission, UserNeed


class EditNotificationPermission(Permission):
  """Permissions to edit a notification"""

  def __init__(self, subject):
    need = UserNeed(subject.user.fs_uniquifier)
    super(EditNotificationPermission, self).__init__(need)
