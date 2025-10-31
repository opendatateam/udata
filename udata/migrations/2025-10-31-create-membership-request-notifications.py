"""
Create MembershipRequestNotification for all pending membership requests
"""

import logging

import click

from udata.core.organization.models import Organization
from udata.core.organization.notifications import MembershipRequestNotification

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing pending membership requests...")

    created_count = 0

    with click.progressbar(
        Organization.objects, length=Organization.objects().count()
    ) as organizations:
        for org in organizations:
            # Get all admin users for this organization
            admin_users = [member.user for member in org.members if member.role == "admin"]

            # Process each pending request
            for request in org.pending_requests:
                # Create a notification for each admin user
                for admin_user in admin_users:
                    try:
                        # Check if notification already exists
                        existing = MembershipRequestNotification.objects(
                            user=admin_user,
                            request_organization=org,
                            request_user=request.user,
                        ).first()

                        if not existing:
                            notification = MembershipRequestNotification(
                                user=admin_user,
                                request_organization=org,
                                request_user=request.user,
                            )
                            # Set the created_at to match the request creation date
                            notification.created_at = request.created
                            notification.save()
                            created_count += 1
                    except Exception as e:
                        log.error(
                            f"Error creating notification for user {admin_user.id} "
                            f"and organization {org.id}: {e}"
                        )
                        continue

    log.info(f"Created {created_count} MembershipRequestNotifications")
