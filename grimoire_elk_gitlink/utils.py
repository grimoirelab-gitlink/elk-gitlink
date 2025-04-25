# -*- coding: utf-8 -*-
#
# Copyright (C) 2021-2022 Haiming Lin, Yehui Wang, Chenqi Shan
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#   Haiming Lin <lhming23@outlook.com>
#

# Connectors for Perceval
from perceval.backends.gitlink.gitlink import Gitlink,GitlinkCommand
# Connectors for EnrichOcean
from .enriched.gitlink import GitlinkEnrich
from .enriched.gitlink2 import GitlinkEnrich2
# Connectors for Ocean
from .raw.gitlink import GitlinkOcean


def get_connectors():

    return {"gitlink": [Gitlink, GitlinkOcean, GitlinkEnrich, GitlinkCommand],
            "gitlink2": [Gitlink, GitlinkOcean, GitlinkEnrich2, GitlinkCommand]}
