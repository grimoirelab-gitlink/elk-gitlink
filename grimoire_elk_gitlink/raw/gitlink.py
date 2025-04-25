

from grimoire_elk.raw.elastic import ElasticOcean
from grimoire_elk.elastic_mapping import Mapping as BaseMapping
from ..identities.gitlink import GitlinkIdentities


class Mapping(BaseMapping):

    @staticmethod
    def get_elastic_mappings(es_major):
        """Get Elasticsearch mapping.
        :param es_major: major version of Elasticsearch, as string
        :returns:        dictionary with a key, 'items', with the mapping
        """

        mapping = '''
         {
            "dynamic":true,
                "properties": {
                    "data": {
                        "dynamic":false,
                        "properties": {}
                    }
                }
        }
        '''

        return {"items": mapping}


class GitlinkOcean(ElasticOcean):
    """Gitlink Ocean feeder"""

    mapping = Mapping
    identities = GitlinkIdentities

    @classmethod
    def get_perceval_params_from_url(cls, url):
        """ Get the perceval params given a URL for the data source """

        params = []

        tokens = url.split(' ', 1)  # Just split the URL not the filter
        url = tokens[0]

        owner = url.split('/')[-2]
        repository = url.split('/')[-1]
        params.append(owner)
        params.append(repository)
        return params

    def _fix_item(self, item):
        category = item['category']

        if 'classified_fields_filtered' not in item or not item['classified_fields_filtered']:
            return

        item = item['data']
        comments_attr = None
        if category == "issue":
            identity_types = ['author', 'assignee']
            comments_attr = 'comments_data'
        elif category == "pull_request":
            identity_types = ['merge_by']

        else:
            identity_types = []

        for identity in identity_types:
            if identity not in item:
                continue
            if not item[identity]:
                continue

            identity_attr = identity + "_data"

            item[identity_attr] = {
                'name': item[identity]['login'],
                'login': item[identity]['login'],
                'email': None,
                'company': None,
                'location': None,
            }

        comments = item.get(comments_attr, [])
        for comment in comments:
            comment['user_data'] = {
                'name': comment['user']['login'],
                'login': comment['user']['login'],
                'email': None,
                'company': None,
                'location': None,
            }
