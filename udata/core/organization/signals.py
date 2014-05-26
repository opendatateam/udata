# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from blinker import Namespace

namespace = Namespace()

organization_created = namespace.signal('organization-created')

organization_updated = namespace.signal('organization-updated')

organization_deleted = namespace.signal('organization-deleted')

new_member = namespace.signal('new-member')

new_membership_request = namespace.signal('new-membership-request')

membership_accepted = namespace.signal('membership-accepted')

membership_refused = namespace.signal('membership-refused')
