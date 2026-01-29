from udata.core.organization.constants import NOT_SPECIFIED, PRODUCER_BADGE_TYPES, USER


def get_producer_type(owned) -> list[str]:
    """
    Determine the producer type(s) for an Owned document (dataset/dataservice/reuse/topic).

    Returns a list of producer types based on organization badges,
    ['not-specified'] if published by an organization without producer badges,
    or ['user'] if published by an individual user.

    Args:
        owned: An Owned document with organization and owner attributes

    Returns:
        A list of producer type strings
    """
    if owned.organization:
        org = owned.organization
        if org.badges:
            producer_badges = [
                badge.kind for badge in org.badges if badge.kind in PRODUCER_BADGE_TYPES
            ]
            if producer_badges:
                return producer_badges
        return [NOT_SPECIFIED]
    elif owned.owner:
        return [USER]
    return []
