from udata.api.parsers import ModelApiParser


class TopicApiParser(ModelApiParser):
    sorts = {
        'name': 'name',
        'created': 'created_at'
    }

    def __init__(self):
        super().__init__()
        self.parser.add_argument('tag', type=str, location='args')

    @staticmethod
    def parse_filters(topics, args):
        if args.get('q'):
            # Following code splits the 'q' argument by spaces to surround
            # every word in it with quotes before rebuild it.
            # This allows the search_text method to tokenise with an AND
            # between tokens whereas an OR is used without it.
            phrase_query = ' '.join([f'"{elem}"' for elem in args['q'].split(' ')])
            topics = topics.search_text(phrase_query)
        if args.get('tag'):
            topics = topics.filter(tags=args['tag'])
        return topics
