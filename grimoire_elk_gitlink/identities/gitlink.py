
from grimoire_elk.identities.identities import Identities


class GitlinkIdentities(Identities):

    @classmethod
    def anonymize_item(cls, item):
        """Remove or hash the fields that contain personal information"""

        category = item['category']

        item = item['data']
        comments_attr = None
        if category == "issue":
            identity_types = ['author', 'assignee']
            comments_attr = 'comments_data'
        elif category == "pull_request":
            identity_types = ['merged_by']
        else:
            identity_types = []

        for identity in identity_types:
            if identity not in item:
                continue
            if not item[identity]:
                continue

            identity_attr = identity + "_data"

            item[identity] = {
                'login': cls._hash(item[identity]['login'])
            }

            item[identity_attr] = {
                'name': cls._hash(item[identity_attr]['login']),
                'login': cls._hash(item[identity_attr]['login']),
                'email': None,
                'company': None,
                'location': None,
            }

        comments = item.get(comments_attr, [])
        for comment in comments:
            if 'user' in comment and comment['user']:
                comment['user'] = {
                    'login': cls._hash(comment['user']['login'])
                }
            comment['user_data'] = {
                'name': cls._hash(comment['user_data']['login']),
                'login': cls._hash(comment['user_data']['login']),
                'email': None,
                'company': None,
                'location': None,
            }
            for reaction in comment['reactions_data']:
                reaction['user'] = {
                    'login': cls._hash(reaction['user']['login'])
                }
