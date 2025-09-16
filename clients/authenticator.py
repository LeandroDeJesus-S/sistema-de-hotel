from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.base_user import AbstractBaseUser
from django.db.models import Q

UserModel = get_user_model()


class UserEmailAuthBackend(BaseBackend):
    def authenticate(  # noqa: PLR6301
        self, _, username: str, password: str, **kwargs
    ) -> AbstractBaseUser | None:
        try:
            user = UserModel.objects.get(
                Q(username__exact=username) | Q(email__exact=username)
            )
            if user.check_password(password):
                return user
            return None
        except UserModel.DoesNotExist:
            return None

    def get_user(self, user_id: int) -> AbstractBaseUser | None:  # noqa: PLR6301
        try:
            return UserModel.objects.get(pk__exact=user_id)
        except UserModel.DoesNotExist:
            return None
