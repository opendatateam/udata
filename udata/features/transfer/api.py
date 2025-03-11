from flask import abort, request

from udata.api import API, api, base_reference, fields
from udata.core.dataservices.models import Dataservice
from udata.core.dataset.api_fields import dataset_ref_fields
from udata.core.organization.api_fields import org_ref_fields
from udata.core.user.api_fields import user_ref_fields
from udata.features.transfer.permissions import (
    TransferPermission,
    TransferResponsePermission,
)
from udata.models import Dataset, Organization, Reuse, User, db
from udata.utils import id_or_404

from .actions import accept_transfer, refuse_transfer, request_transfer
from .models import TRANSFER_STATUS, Transfer

RESPONSE_TYPES = ["accept", "refuse"]


transfer_request_fields = api.model(
    "TransferRequest",
    {
        "subject": fields.Nested(
            base_reference, required=True, description="The transfered subject"
        ),
        "recipient": fields.Nested(
            base_reference,
            required=True,
            description=("The transfer recipient, either an user or an organization"),
        ),
        "comment": fields.String(
            description="An explanation about the transfer request", required=True
        ),
    },
)


transfer_response_fields = api.model(
    "TransferResponse",
    {
        "response": fields.String(description="The response", required=True, enum=RESPONSE_TYPES),
        "comment": fields.String(description="An optional comment about the transfer response"),
    },
)

person_mapping = {
    User: user_ref_fields,
    Organization: org_ref_fields,
}

subject_mapping = {
    Dataservice: Dataservice.__ref_fields__,
    Dataset: dataset_ref_fields,
    Reuse: Reuse.__ref_fields__,
}

transfer_fields = api.model(
    "Transfer",
    {
        "id": fields.String(readonly=True, description="The transfer unique identifier"),
        "user": fields.Nested(
            user_ref_fields,
            description="The user who requested the transfer",
            readonly=True,
            allow_null=True,
        ),
        "owner": fields.Polymorph(
            person_mapping,
            readonly=True,
            description=("The user or organization currently owning the transfered object"),
        ),
        "recipient": fields.Polymorph(
            person_mapping,
            readonly=True,
            description=("The user or organization receiving the transfered object"),
        ),
        "subject": fields.Polymorph(
            subject_mapping, readonly=True, description="The transfered object"
        ),
        "comment": fields.String(readonly=True, description="A comment about the transfer request"),
        "created": fields.ISODateTime(description="The transfer request date", readonly=True),
        "status": fields.String(
            enum=list(TRANSFER_STATUS), description="The current transfer request status"
        ),
        "responded": fields.ISODateTime(description="The transfer response date", readonly=True),
        "reponse_comment": fields.String(
            readonly=True, description="A comment about the transfer response"
        ),
    },
)


ns = api.namespace("transfer")

requests_parser = api.parser()
requests_parser.add_argument(
    "subject", type=str, help="ID of dataset, dataservice, reuse…", location="args"
)
requests_parser.add_argument(
    "subject_type", choices=["Dataset", "Reuse", "Dataservice"], type=str, help="", location="args"
)
requests_parser.add_argument(
    "recipient", type=str, help="ID of user or organization", location="args"
)
requests_parser.add_argument(
    "status",
    type=str,
    choices=TRANSFER_STATUS.keys(),
    help="ID of user or organization",
    location="args",
)


@ns.route("/", endpoint="transfers")
class TransferRequestsAPI(API):
    @api.doc("list_transfers")
    @api.marshal_list_with(transfer_fields)
    def get(self):
        args = requests_parser.parse_args()

        transfers = Transfer.objects
        if args["subject"]:
            transfers = transfers.generic_in(subject=args["subject"])
        if args["subject_type"]:
            transfers = transfers.filter(__raw__={"subject._cls": args["subject_type"]})
        if args["recipient"]:
            transfers = transfers.generic_in(recipient=args["recipient"])
        if args["status"]:
            transfers = transfers.filter(status=args["status"])

        if not (args["subject"] or args["recipient"]):
            api.abort(400, "Please provide at least a `subject` or a `recipient`")

        return [
            transfer
            for transfer in transfers
            if TransferPermission(transfer.subject).can()
            or TransferResponsePermission(transfer).can()
        ]

    @api.secure
    @api.doc("request_transfer")
    @api.expect(transfer_request_fields)
    @api.marshal_with(transfer_fields)
    def post(self):
        """Initiate transfer request"""
        data = request.json

        subject_model = db.resolve_model(data["subject"])
        subject_id = data["subject"]["id"]
        try:
            subject = subject_model.objects.get(id=subject_id)
        except subject_model.DoesNotExist:
            msg = 'Unkown subject id "{0}"'.format(subject_id)
            ns.abort(400, errors={"subject": msg})

        recipient_model = db.resolve_model(data["recipient"])
        recipient_id = data["recipient"]["id"]
        try:
            recipient = recipient_model.objects.get(id=recipient_id)
        except recipient_model.DoesNotExist:
            msg = 'Unkown recipient id "{0}"'.format(recipient_id)
            ns.abort(400, errors={"recipient": msg})

        comment = data.get("comment")

        transfer = request_transfer(subject, recipient, comment)

        return transfer, 201


@ns.route("/<id>/", endpoint="transfer")
class TransferRequestAPI(API):
    @api.doc("get_transfer")
    @api.marshal_with(transfer_fields)
    def get(self, id):
        """Fetch a transfer request given its identifier"""
        return Transfer.objects.get_or_404(id=id_or_404(id))

    @api.secure
    @api.doc("respond_to_transfer")
    @api.expect(transfer_response_fields)
    @api.marshal_with(transfer_fields)
    def post(self, id):
        """Respond to a transfer request"""
        transfer = Transfer.objects.get_or_404(id=id_or_404(id))

        if transfer.status != "pending":
            abort(400, "Cannot update transfer after accepting/refusing")

        data = request.json
        comment = data.get("comment")

        if data["response"] == "accept":
            return accept_transfer(transfer, comment)
        elif data["response"] == "refuse":
            return refuse_transfer(transfer, comment)
        else:
            raise ValueError()
