import logging
import re
import time

import requests

from dateutil.relativedelta import relativedelta
from datetime import datetime

from grimoire_elk.elastic import ElasticSearch
from grimoire_elk.errors import ELKError
from grimoirelab_toolkit.datetime import datetime_utcnow, str_to_datetime

from elasticsearch import Elasticsearch as ES, RequestsHttpConnection

from grimoire_elk.enriched.utils import get_time_diff_days

from grimoire_elk.enriched.enrich import Enrich, metadata
from grimoire_elk.elastic_mapping import Mapping as BaseMapping


GITLINK = "www.//gitlink.org.cn/"
GITLINK_ISSUES = "gitlink_issues"
GITLNK_MERGES = "gitlink_pulls"

logger = logging.getLogger(__name__)


class Mapping(BaseMapping):

    @staticmethod
    def get_elastic_mappings(es_major):
        """Get Elasticsearch mapping.
        geopoints type is not created in dynamic mapping
        :param es_major: major version of Elasticsearch, as string
        :returns:        dictionary with a key, 'items', with the mapping
        """

        mapping = """
        {
            "properties": {
               "merge_author_geolocation": {
                   "type": "geo_point"
               },
               "assignee_geolocation": {
                   "type": "geo_point"
               },
               "state": {
                   "type": "keyword"
               },
               "user_geolocation": {
                   "type": "geo_point"
               },
               "title_analyzed": {
                 "type": "text",
                 "index": true
               }
            }
        }
        """

        return {"items": mapping}


class GitlinkEnrich(Enrich):

    mapping = Mapping

    issue_roles = ["author_data", "assignee_data"]
    pr_roles = ["merge_by_data"]
    roles = ["author_data", "assignee_data", "merge_by_data"]

    def __init__(
        self,
        db_sortinghat=None,
        json_projects_map=None,
        db_user="",
        db_password="",
        db_host="",
        db_port=None,
        db_path=None,
        db_ssl=False,
        db_verify_ssl=False,
        db_tenant=None,
        do_refresh_projects=False,
        do_refresh_identities=False,
        author_id=None,
        author_uuid=None,
        filter_raw=None,
        jenkins_rename_file=None,
        unaffiliated_group=None,
        pair_programming=False,
        node_regex=False,
        studies_args=None,
        es_enrich_aliases=None,
        last_enrich_date=None,
        projects_json_repo=None,
        repo_labels=None,
        repo_spaces=None,
    ):
        super().__init__(
            db_sortinghat=db_sortinghat,
            json_projects_map=json_projects_map,
            db_user=db_user,
            db_password=db_password,
            db_host=db_host,
            db_port=db_port,
            db_path=db_path,
            db_ssl=db_ssl,
            db_verify_ssl=db_verify_ssl,
        )

        self.studies = []
        self.studies.append(self.enrich_onion)
        # self.studies.append(self.enrich_pull_requests)
        # self.studies.append(self.enrich_geolocation)
        # self.studies.append(self.enrich_extra_data)
        # self.studies.append(self.enrich_backlog_analysis)

    def set_elastic(self, elastic):
        self.elastic = elastic

    def get_field_author(self):
        return "author_data"

    def get_field_date(self):
        """Field with the date in the JSON enriched items"""
        return "grimoire_creation_date"

    def get_identities(self, item):
        """Return the identities from an item"""

        category = item["category"]
        item = item["data"]

        if category == "issue":
            identity_types = ["author", "assignee"]
        elif category == "pull_request":
            identity_types = ["merge_by"]
        else:
            identity_types = []

        for identity in identity_types:
            identity_attr = identity + "_data"
            if item[identity] and identity_attr in item:
                # In user_data we have the full user data
                user = self.get_sh_identity(item[identity_attr])
                if user:
                    yield user

    def get_sh_identity(self, item, identity_field=None):
        identity = {}

        user = item  # by default a specific user dict is expected
        if "data" in item and type(item) == dict:
            user = item["data"][identity_field]

        if not user:
            return identity

        identity["username"] = user["login"]
        identity["email"] = None
        identity["name"] = None
        if "email" in user:
            identity["email"] = user["email"]
        if "name" in user:
            identity["name"] = user["name"]
        return identity

    def get_project_repository(self, eitem):
        repo = eitem["origin"]
        return repo

    def get_time_to_first_attention(self, item):
        """Get the first date at which a comment was made to the issue by someone
        other than the user who created the issue
        """
        comment_dates = [
            str_to_datetime(comment["created_at"])
            for comment in item["comments_data"]
            if item["author"]["login"] != comment["user"]["login"]
        ]
        if comment_dates:
            return min(comment_dates)
        return None

    # get comments and exclude bot
    def get_num_of_comments_without_bot(self, item):
        """Get the num of comment was made to the issue by someone
        other than the user who created the issue and bot
        """
        comments = [
            comment
            for comment in item["comments_data"]
            if item["author"]["login"] != comment["user"]["login"]
            and not (comment["user"]["name"].endswith("bot"))
        ]
        return len(comments)

    # get first attendtion without bot
    def get_time_to_first_attention_without_bot(self, item):
        """Get the first date at which a comment was made to the issue by someone
        other than the user who created the issue and bot
        """
        comment_dates = [
            str_to_datetime(comment["created_at"])
            for comment in item["comments_data"]
            if item["author"]["login"] != comment["user"]["login"]
            and not (comment["user"]["name"].endswith("bot"))
        ]
        if comment_dates:
            return min(comment_dates)
        return None

    def get_num_of_reviews_without_bot(self, item):
        """Get the num of comment was made to the issue by someone
        other than the user who created the issue and bot
        """
        comments = [
            comment
            for comment in item["comments"]["journals"]
            if item["author"]["login"] != comment["user"]["login"]
            and not (comment["user"]["name"].endswith("bot"))
        ]
        return len(comments)

    def get_time_to_merge_request_response(self, item):
        """Get the first date at which a review was made on the PR by someone
        other than the user who created the PR
        """
        review_dates = []
        for comment in item["comments"]["journals"]:
            # skip comments of ghost users
            if not comment["user"]:
                continue

            # skip comments of the pull request creator
            if item["author"]["login"] == comment["user"]["login"]:
                continue

            review_dates.append(str_to_datetime(comment["created_at"]))

        if review_dates:
            return min(review_dates)

        return None

    # get first attendtion without bot
    def get_time_to_first_review_attention_without_bot(self, item):
        """Get the first date at which a comment was made to the pr by someone
        other than the user who created the pr and bot
        """
        comment_dates = [
            str_to_datetime(comment["created_at"])
            for comment in item["comments"]["journals"]
            if item["author"]["login"] != comment["user"]["login"]
            and not (comment["user"]["name"].endswith("bot"))
        ]
        if comment_dates:
            return min(comment_dates)
        return None

    def get_latest_comment_date(self, item):
        """Get the date of the latest comment on the issue/pr"""

        comment_dates = [
            str_to_datetime(comment["created_at"])
            for comment in item["comments"]["journals"]
        ]
        if comment_dates:
            return max(comment_dates)
        return None

    def get_num_commenters(self, item):
        """Get the number of unique people who commented on the issue/pr"""

        commenters = [
            comment["user"]["login"] for comment in item["comments"]["journals"]
        ]
        return len(set(commenters))

    @metadata
    def get_rich_item(self, item):

        rich_item = {}
        if item["category"] == "issue":
            rich_item = self.__get_rich_issue(item)
        elif item["category"] == "pull_request":
            rich_item = self.__get_rich_pull(item)
        elif item["category"] == "repository":
            rich_item = self.__get_rich_repo(item)
        else:
            logger.error(
                "[gitlink] rich item not defined for gitlink category {}".format(
                    item["category"]
                )
            )

        self.add_repository_labels(rich_item)
        self.add_metadata_filter_raw(rich_item)
        return rich_item

    def __get_rich_pull(self, item):
        rich_pr = {}

        for f in self.RAW_FIELDS_COPY:
            if f in item:
                rich_pr[f] = item[f]
            else:
                rich_pr[f] = None
        # The real data
        pull_request = item["data"]

        merged_by = pull_request.get("merge_by", None)
        if merged_by and merged_by is not None:
            rich_pr["merge_author_login"] = merged_by["login"]
            rich_pr["merge_author_name"] = merged_by["name"]

        else:
            rich_pr["merge_author_name"] = None
            rich_pr["merge_author_login"] = None

        rich_pr["id"] = pull_request["id"]
        rich_pr["id_in_repo"] = pull_request["index"]
        rich_pr["repository"] = self.get_project_repository(rich_pr)
        rich_pr["title"] = pull_request["title"]
        rich_pr["title_analyzed"] = pull_request["title"]
        rich_pr["state"] = pull_request["status"]
        # rich_pr["created_at"] = pull_request["created_at"]
        rich_pr["updated_at"] = item["updated_on"]
        rich_pr["merged"] = pull_request["merged"]
        rich_pr["merged_at"] = pull_request["merged_at"]

        rich_pr["url"] = item["origin"]

        rich_pr["pull_request"] = True
        rich_pr["item_type"] = "pull_request"

        # I'm not sure about this category.
        # rich_pr["gitlink_repo"] = rich_pr["repository"].replace(GITLINK, "")
        # rich_pr["url_id"] = rich_pr["gitlink_repo"] + "/pull/" + rich_pr["id_in_repo"]

        # GMD code development metrics
        rich_pr["forks"] = None

        rich_pr["num_review_comments"] = pull_request["comments"]["total_count"]
        # rich_pr["review_comments_data"] = pull_request["comments"]["journals"]

        # not sure about the use
        if self.prjs_map:
            rich_pr.update(self.get_item_project(rich_pr))

        return rich_pr

    def __get_rich_issue(self, item):
        rich_issue = {}

        for f in self.RAW_FIELDS_COPY:
            if f in item:
                rich_issue[f] = item[f]
            else:
                rich_issue[f] = None
        # The real data
        issue = item["data"]

        rich_issue["time_to_close_days"] = get_time_diff_days(
            issue["created_at"], issue["updated_at"]
        )

        # issue have four status: new(open),processing,resolved,closed,refused,with code for 1 to 5;
        # format { "id":xx,name: in chinese or unicode
        if issue["status"]["id"] == 1 or issue["status"]["id"] == 2:
            rich_issue["time_open_days"] = get_time_diff_days(
                issue["created_at"], datetime_utcnow().replace(tzinfo=None)
            )
        else:
            rich_issue["time_open_days"] = rich_issue["time_to_close_days"]
        rich_issue["user_login"] = issue["author"]["login"]

        user = issue.get("author", None)
        if user is not None and user:
            rich_issue["user_name"] = user["name"]
            rich_issue["author_name"] = user["name"]

        else:
            rich_issue["user_name"] = None
            rich_issue["author_name"] = None

        assignees = issue.get("assignee", None)
        if assignees and assignees is not None:
            assignees_data = []
            for assignee in assignees:
                assignee_data = {}
                assignee_data["assignee_login"] = assignee["login"]
                assignee_data["assignee_name"] = assignee["name"]
                assignees_data.append(assignee_data)
            rich_issue["assignee"] = assignee_data
        else:
            rich_issue["assignee"] = None

        rich_issue["id"] = issue["id"]
        rich_issue["id_in_repo"] = issue["project_issues_index"]
        rich_issue["repository"] = self.get_project_repository(rich_issue)
        # 疑似有问题，先做减法处理
        # rich_issue['title'] = issue['title']
        # rich_issue['title_analyzed'] = issue['title']
        rich_issue["state"] = issue["status"]["name"]
        rich_issue["created_at"] = issue["created_at"]
        rich_issue["updated_at"] = issue["updated_at"]

        if "labels" in issue.keys():
            labels = [label["name"] for label in issue["labels"]]
            rich_issue["labels"] = labels

        rich_issue["pull_request"] = True
        rich_issue["item_type"] = "pull_request"
        if "head" not in issue.keys() and "pull_request" not in issue.keys():
            rich_issue["pull_request"] = False
            rich_issue["item_type"] = "issue"
        if "issue" in rich_issue.keys():
            rich_issue["gitlink_repo"] = rich_issue["issue"].replace(GITLINK, "")
            rich_issue["url_id"] = (
                rich_issue["gitlink_repo"] + "/issues/" + rich_issue["id_in_repo"]
            )

        if self.prjs_map:
            rich_issue.update(self.get_item_project(rich_issue))

        if "project" in item:
            rich_issue["project"] = item["project"]

        rich_issue.update(self.get_grimoire_fields(issue["created_at"], "issue"))

        # item[self.get_field_date()] = rich_issue[self.get_field_date()]
        # rich_issue.update(self.get_item_sh(item, self.issue_roles))

        return rich_issue

    def __get_rich_repo(self, item):
        rich_repo = {}

        for f in self.RAW_FIELDS_COPY:
            if f in item:
                rich_repo[f] = item[f]
            else:
                rich_repo[f] = None

        repo = item["data"]

        rich_repo["forks_count"] = repo["forked_count"]
        rich_repo["subscribers_count"] = repo["watchers_count"]
        rich_repo["praises_count"] = repo["praises_count"]
        rich_repo["fetched_on"] = repo["fetched_on"]
        rich_repo["url"] = item["origin"]
        rich_repo["item_type"] = "repository"

        rich_releases = []
        for release in repo["releases"]:
            rich_releases_dict = {}
            rich_releases_dict["id"] = release["id"]
            rich_releases_dict["tag_name"] = release["tag_name"]
            rich_releases_dict["target_commitish"] = release["target_commitish"]
            # name is gotten in Chinese, so trans in unicode
            rich_releases_dict["name"] = release["name"]
            # so do body
            rich_releases_dict["body"] = release["body"]
            rich_releases_dict["created_at"] = release["created_at"]
            rich_releases_author_dict = {}
            rich_releases_author_dict["login"] = release["user_login"]
            rich_releases_author_dict["name"] = release["user_name"]
            rich_releases_dict["author"] = rich_releases_author_dict
            rich_releases.append(rich_releases_dict)
        rich_repo["releases"] = rich_releases
        rich_repo["releases_count"] = len(rich_releases)

        if self.prjs_map:
            rich_repo.update(self.get_item_project(rich_repo))

        rich_repo.update(
            self.get_grimoire_fields(item["metadata__updated_on"], "repository")
        )

        return rich_repo

    def enrich_onion(
        self,
        ocean_backend,
        enrich_backend,
        in_index,
        out_index,
        data_source=None,
        no_incremental=False,
        contribs_field="uuid",
        timeframe_field="grimoire_creation_date",
        sort_on_field="metadata__timestamp",
        seconds=Enrich.ONION_INTERVAL,
    ):

        if not data_source:
            raise ELKError(cause="Missing data_source attribute")

        if data_source not in [
            GITLINK_ISSUES,
            GITLNK_MERGES,
        ]:
            logger.warning(
                "[gitlink] data source value {} should be: {} or {}".format(
                    data_source, GITLINK_ISSUES, GITLNK_MERGES
                )
            )

        super().enrich_onion(
            enrich_backend=enrich_backend,
            in_index=in_index,
            out_index=out_index,
            data_source=data_source,
            contribs_field=contribs_field,
            timeframe_field=timeframe_field,
            sort_on_field=sort_on_field,
            no_incremental=no_incremental,
            seconds=seconds,
        )
