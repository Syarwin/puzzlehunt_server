# Copyright (C) 2018 The MindbreakersServer Contributors.
#
# This file is part of MindbreakersServer.
#
# MindbreakersServer is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any later version.
#
# MindbreakersServer is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along with Hunter2.  If not, see <http://www.gnu.org/licenses/>.

from django.conf import settings
from django.db.models import F
from django.utils import timezone
from huey import crontab
from huey.contrib.djhuey import db_periodic_task
from django.core.cache import cache

from hunts.models import Hunt


import logging
logger = logging.getLogger(__name__)
wget_arguments = "--max-redirect=20 --show-progress --progress=bar:force:noscroll"


def parse_attributes(META):
    shib_attrs = {}
    error = False
    for header, attr in list(settings.SHIB_ATTRIBUTE_MAP.items()):
        required, name = attr
        values = META.get(header, None)
        if not values:
            values = META.get("HTTP_" + (header.replace("-", "_")).upper(), None)
        value = None
        if values:
            # If multiple attributes releases just care about the 1st one
            try:
                value = values.split(';')[0]
            except IndexError:
                value = values

        shib_attrs[name] = value
        if not value or value == '':
            if required:
                error = True
    return shib_attrs, error