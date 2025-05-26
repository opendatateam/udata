from datetime import datetime

from flask import current_app, request
from flask_security import current_user

from udata import tracking
from udata.api import API, api, fields
from udata.core.user.api_fields import user_ref_fields
from udata.models import Follow
from udata.utils import id_or_404

from .signals import on_new_follow

follow_fields = api.model(
    "Follow",
    {
        "id": fields.String(description="The follow object technical ID", readonly=True),
        "follower": fields.Nested(user_ref_fields, description="The follower", readonly=True),
        "since": fields.ISODateTime(
            description="The date from which the user started following", readonly=True
        ),
    },
)

follow_page_fields = api.model("FollowPage", fields.pager(follow_fields))

parser = api.parser()
parser.add_argument("page", type=int, default=1, location="args", help="The page to fetch")
parser.add_argument(
    "page_size", type=int, default=20, location="args", help="The page size to fetch"
)
parser.add_argument(
    "user",
    type=str,
    location="args",
    help="Filter follower by user, it allows to check if a user is following the object",
)

NOTE = "Returns the number of followers left after the operation"


class FollowAPI(API):
    """
    Base Follow Model API.
    """

    model = None

    @api.expect(parser)
    @api.marshal_with(follow_page_fields)
    def get(self, id):
        """List all followers for a given object"""
        args = parser.parse_args()
        model = None
        if hasattr(self.model, "slug"):
            model = self.model.objects(slug=id).first()
        model = model or self.model.objects.only("id").get_or_404(id=id_or_404(id))
        qs = Follow.objects(following=model, until=None)
        if args["user"]:
            qs = qs.filter(follower=id_or_404(args["user"]))

        return qs.paginate(args["page"], args["page_size"])

    @api.secure
    @api.doc(description=NOTE)
    def post(self, id):
        """Follow an object given its ID"""
        model = self.model.objects.get_or_404(id=id_or_404(id))
        follow, created = Follow.objects.get_or_create(
            follower=current_user.id, following=model, until=None
        )
        count = Follow.objects.followers(model).count()
        if not current_app.config["TESTING"]:
            tracking.send_signal(on_new_follow, request, current_user)
        return {"followers": count}, 201 if created else 200

    @api.secure
    @api.doc(description=NOTE)
    def delete(self, id):
        """Unfollow an object given its ID"""
        model = self.model.objects.only("id").get_or_404(id=id_or_404(id))
        follow = Follow.objects.get_or_404(follower=current_user.id, following=model, until=None)
        follow.until = datetime.utcnow()
        follow.save()
        count = Follow.objects.followers(model).count()
        return {"followers": count}, 200
