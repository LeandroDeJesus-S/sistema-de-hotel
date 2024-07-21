from django.contrib.messages import get_messages


def get_message(response):
    msgs = get_messages(response.wsgi_request)
    msg_list = list(msgs)
    return msg_list[0].message if msg_list else ''
