from udata.api import api


class ModelApiParser:
    """This class allows to describe and customize the api arguments parser behavior."""

    sorts = {}

    def __init__(self, paginate=True):
        self.parser = api.parser()
        # q parameter
        self.parser.add_argument("q", type=str, location="args", help="The search query")
        # Sort arguments
        keys = list(self.sorts)
        choices = keys + ["-" + k for k in keys]
        help_msg = "The field (and direction) on which sorting apply"
        self.parser.add_argument("sort", type=str, location="args", choices=choices, help=help_msg)
        if paginate:
            self.parser.add_argument(
                "page", type=int, location="args", default=1, help="The page to display"
            )
            self.parser.add_argument(
                "page_size", type=int, location="args", default=20, help="The page size"
            )

    def parse(self):
        args = self.parser.parse_args()
        if args["sort"]:
            if args["sort"].startswith("-"):
                # Keyerror because of the '-' character in front of the argument.
                # It is removed to find the value in dict and added back.
                arg_sort = args["sort"][1:]
                args["sort"] = "-" + self.sorts[arg_sort]
            else:
                args["sort"] = self.sorts[args["sort"]]
        return args
