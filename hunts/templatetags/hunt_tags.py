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


@register.filter
def duration(td):

    total_seconds = int(td.total_seconds())

    days = total_seconds // 86400
    remaining_hours = total_seconds % 86400
    remaining_minutes = remaining_hours % 3600
    hours = remaining_hours // 3600
    minutes = remaining_minutes // 60
    seconds = remaining_minutes % 60

    days_str = f'{days}d' if days else ''
    hours_str = f'{hours}h' if hours else ''
    minutes_str = f'{minutes}m' if minutes else ''
    seconds_str = f'{seconds}s' if seconds and not hours_str else ''

    return f'{days_str}{hours_str}{minutes_str}{seconds_str}'

@register.filter()
def render_with_context(value, user):
    return Template(value).render(Context({'curr_hunt': Hunt.objects.get(is_current_hunt=True), 'user': user}))
    
@register.filter()
def render_hunt_with_context(value, team):
    hunt = Hunt.objects.get(is_current_hunt=True)
    nbsolve = 0
    if team is not None:
      nbsolve = team.ep_solved.count()
    return Template(value).render(Context({'curr_hunt': Hunt.objects.get(is_current_hunt=True),  'nb_solve': nbsolve}))
    
@register.simple_tag(takes_context=True)
def render_with_context_simpletag(context):
    user = context['user']
    value = context['flatpage'].content
    hunt = Hunt.objects.get(is_current_hunt=True)
    team = hunt.team_from_user(user)
    nbsolve = 0
    if team is not None:
      nbsolve = team.puz_solved.count()
    return Template(value).render(Context({'curr_hunt': hunt, 'nb_solve': nbsolve, 'user': user}))

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
