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
            out = u"""<div class="form-group">
                <label class="col-sm-2 control-label">Link:</label>
                <div class="col-sm-10">
                  <a href="{}">{}</a>
                </div>
            </div>"""
            output.append(out.format(url, value.instance.url_path))
        output.append(super(AdminFileWidget, self).render(name, value, attrs, renderer))
        return mark_safe(u''.join(output))