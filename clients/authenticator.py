from typing import Any
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from django.db.models import Q

UserModel = get_user_model()


class UserEmailAuthBackend(BaseBackend):
    def authenticate(self, _, username: str, password: str) -> AbstractBaseUser | None:
        try:
            user = UserModel.objects.get(Q(username__exact=username) | Q(email__exact=username))
            if user.check_password(password):
                return user
        except UserModel.DoesNotExist:
            return

    def get_user(self, user_id: int) -> AbstractBaseUser | None:
        try:
            return UserModel.objects.get(pk__exact=user_id)
        except UserModel.DoesNotExist:
            return