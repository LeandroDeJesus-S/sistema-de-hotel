import pytest
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware

@pytest.fixture
def request_with_messages(rf):
    request = rf.get('/')
    SessionMiddleware(lambda x: None).process_request(request)
    MessageMiddleware(lambda x: None).process_request(request)
    return request
