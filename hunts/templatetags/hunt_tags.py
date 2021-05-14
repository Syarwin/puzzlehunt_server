from django import template
from django.conf import settings
from django.template import Template, Context
from hunts.models import Hunt
from datetime import datetime
register = template.Library()


@register.simple_tag(takes_context=True)
def hunt_static(context):
    return settings.MEDIA_URL + "hunt/" + str(context['hunt'].hunt_number) + "/"


@register.simple_tag(takes_context=True)
def site_title(context):
    return settings.SITE_TITLE


@register.simple_tag(takes_context=True)
def contact_email(context):
    return settings.CONTACT_EMAIL


@register.filter()
def render_with_context(value, user):
    return Template(value).render(Context({'curr_hunt': Hunt.objects.get(is_current_hunt=True), 'user': user}))
    
@register.simple_tag(takes_context=True)
def render_with_context_simpletag(context):
    user = context['user']
    value = context['flatpage'].content
    hunt = Hunt.objects.get(is_current_hunt=True)
    team = hunt.team_from_user(user)
    nbsolve = 0
    if team is not None:
      nbsolve = team.puz_solved.count()
    return Template(value).render(Context({'curr_hunt': hunt, 'nb_solve': nbsolve}))

@register.tag
def set_curr_hunt(parser, token):
    return CurrentHuntEventNode()


class CurrentHuntEventNode(template.Node):
    def render(self, context):
        context['tmpl_curr_hunt'] = Hunt.objects.get(is_current_hunt=True)
        return ''


@register.tag
def set_hunts(parser, token):
    return HuntsEventNode()


class HuntsEventNode(template.Node):
    def render(self, context):
        old_hunts = Hunt.objects.filter(end_date__lt=datetime.now()).exclude(is_current_hunt=True)
        context['tmpl_hunts'] = old_hunts.order_by("-hunt_number")[:5]
        return ''


@register.tag
def set_hunt_from_context(parser, token):
    return HuntFromContextEventNode()


class HuntFromContextEventNode(template.Node):
    def render(self, context):
        if("hunt" in context):
            context['tmpl_hunt'] = context['hunt']
            return ''
        elif("puzzle" in context):
            context['tmpl_hunt'] = context['puzzle'].hunt
            return ''
        else:
            context['tmpl_hunt'] = Hunt.objects.get(is_current_hunt=True)
            return ''
