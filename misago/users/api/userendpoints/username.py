from rest_framework.response import Response

from django.db import IntegrityError
from django.utils.translation import ugettext as _

from misago.conf import settings
from misago.users.namechanges import UsernameChanges
from misago.users.serializers import ChangeUsernameSerializer


def username_endpoint(request):
    if request.method == 'POST':
        return change_username(request)
    else:
        return options_response(get_username_options(request.user))


def get_username_options(user):
    options = UsernameChanges(user)
    return {
        'changes_left': options.left,
        'next_on': options.next_on,
        'length_min': settings.username_length_min,
        'length_max': settings.username_length_max,
    }


def options_response(options):
    if options['next_on']:
        options['next_on'] = options['next_on'].isoformat()
    return Response(options)


def change_username(request):
    options = get_username_options(request.user)
    if not options['changes_left']:
        return Response(
            {
                'detail': _("You can't change your username now."),
                'options': options,
            },
            status=400,
        )

    serializer = ChangeUsernameSerializer(
        data=request.data,
        context={'user': request.user},
    )

    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    try:
        serializer.change_username(changed_by=request.user)
        return Response({
            'username': request.user.username,
            'slug': request.user.slug,
            'options': get_username_options(request.user)
        })
    except IntegrityError:
        return Response(
            {
                'detail': _("Error changing username. Please try again."),
            },
            status=400,
        )


def moderate_username_endpoint(request, profile):
    if request.method == 'POST':
        serializer = ChangeUsernameSerializer(data=request.data, context={'user': profile})

        if not serializer.is_valid():
            return Response({'detail': serializer.errors}, status=400)

        try:
            serializer.change_username(changed_by=request.user)
            return Response({
                'username': profile.username,
                'slug': profile.slug,
            })
        except IntegrityError:
            return Response(
                {
                    'detail': _("Error changing username. Please try again."),
                },
                status=400,
            )
    else:
        return Response({
            'length_min': settings.username_length_min,
            'length_max': settings.username_length_max,
        })
