from udata.core.organization.constants import NOT_SPECIFIED, PRODUCER_BADGE_TYPES, USER


def get_producer_type(organization, owner) -> list[str]:
    """
    Determine the producer type(s) for a dataset/dataservice/reuse.

    Returns a list of producer types based on organization badges,
    ['not-specified'] if published by an organization without producer badges,
    or ['user'] if published by an individual user.

    Args:
        organization: The organization object (or None)
        owner: The owner user object (or None)

    Returns:
        A list of producer type strings
    """
    if organization is not None:
        if hasattr(organization, "badges") and organization.badges:
            producer_badges = [
                badge.kind for badge in organization.badges if badge.kind in PRODUCER_BADGE_TYPES
            ]
            if producer_badges:
                return producer_badges
        return [NOT_SPECIFIED]
    elif owner is not None:
        return [USER]
    return []
