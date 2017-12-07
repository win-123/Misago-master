from rest_framework.response import Response

from django.utils.translation import ugettext as _

from misago.conf import settings
from misago.core.mail import mail_user
from misago.users.credentialchange import store_new_credential
from misago.users.serializers import ChangeEmailSerializer


def change_email_endpoint(request, pk=None):
    serializer = ChangeEmailSerializer(
        data=request.data,
        context={'user': request.user},
    )

    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    token = store_new_credential(request, 'email', serializer.validated_data['new_email'])

    mail_subject = _("Confirm e-mail change on %(forum_name)s forums")
    mail_subject = mail_subject % {'forum_name': settings.forum_name}

    # swap address with new one so email is sent to new address
    request.user.email = serializer.validated_data['new_email']

    mail_user(
        request, request.user, mail_subject, 'misago/emails/change_email', {'token': token}
    )

    return Response(status=204)
