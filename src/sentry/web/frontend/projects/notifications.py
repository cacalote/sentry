"""
sentry.web.frontend.projects.notifications
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2012 by the Sentry Team, see AUTHORS for more details.
:license: BSD, see LICENSE for more details.
"""
from django.conf import settings
from django.contrib import messages
from django.core.context_processors import csrf
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_protect
from django.utils.translation import ugettext_lazy as _

from sentry.constants import MEMBER_OWNER, DEFAULT_ALERT_PROJECT_THRESHOLD
from sentry.models import TagKey
from sentry.web.decorators import has_access
from sentry.web.forms.projects import (
    AlertSettingsForm, NotificationTagValuesForm, NotificationSettingsForm
)
from sentry.web.helpers import render_to_response


@has_access(MEMBER_OWNER)
@csrf_protect
def notification_settings(request, team, project):
    initial = project.get_option('notifcation:tags', {})

    general_form = NotificationSettingsForm(
        data=request.POST or None,
        prefix='general',
        initial={
            'subject_prefix': project.get_option(
                'mail:subject_prefix', settings.EMAIL_SUBJECT_PREFIX),
        },
    )

    tag_forms = []
    for tag in TagKey.objects.all_keys(project):
        tag_forms.append(NotificationTagValuesForm(
            project=project,
            tag=tag,
            data=request.POST or None,
            prefix='tag-%s' % (tag,),
            initial={
                'values': ', '.join(initial.get(tag, [])),
            },
        ))

    threshold, min_events = project.get_option(
        'alert:threshold', DEFAULT_ALERT_PROJECT_THRESHOLD)

    alert_form = AlertSettingsForm(
        data=request.POST or None,
        prefix='alert',
        initial={
            'pct_threshold': threshold,
            'min_events': min_events,
        }
    )

    all_forms = [
        alert_form,
        general_form,
    ] + tag_forms

    if request.method == 'POST' and all(f.is_valid() for f in all_forms):
        tags = {}
        for t_form in tag_forms:
            values = t_form.cleaned_data['values']
            if values:
                tags[t_form.tag] = values

        project.update_option('notifcation:tags', tags)
        project.update_option('alert:threshold', (
            alert_form.cleaned_data['pct_threshold'], alert_form.cleaned_data['min_events']))
        project.update_option(
            'mail:subject_prefix', general_form.cleaned_data['subject_prefix'])

        messages.add_message(
            request, messages.SUCCESS,
            _('Your settings were saved successfully.'))

        return HttpResponseRedirect(reverse('sentry-project-notifications', args=[project.team.slug, project.slug]))

    context = csrf(request)
    context.update({
        'team': team,
        'project': project,
        'general_form': general_form,
        'alert_form': alert_form,
        'tag_forms': tag_forms,
        'page': 'notifications',
    })
    return render_to_response('sentry/projects/notifications.html', context, request)
