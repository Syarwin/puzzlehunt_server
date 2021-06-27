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

from django.contrib.admin.widgets import AdminFileWidget
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.urls import reverse_lazy, reverse
import os

class CustomAdminFileWidget(AdminFileWidget):
    """A FileField Widget that shows secure file link"""
    def __init__(self, attrs={}):
        super(CustomAdminFileWidget, self).__init__(attrs)

    def render(self, name, value, attrs=None, renderer=None):
        output = []
        if value and hasattr(value, "url"):
            url = reverse('puzzle_file',
                          args=(value.instance.puzzle.puzzle_id, value.instance.url_path, ))
            out = u"""<img src="{}" style="width:100px; height:auto"/>"""
            output.append(out.format(url))
        output.append(super(AdminFileWidget, self).render(name, value, attrs, renderer))
        return mark_safe(u''.join(output))
