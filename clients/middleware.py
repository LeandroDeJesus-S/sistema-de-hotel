from django.utils.translation import LANGUAGE_SESSION_KEY, activate


class UserLanguageMiddleware:
    """
    Middleware that sets the active language based on the authenticated user's preference.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and hasattr(request.user, 'language'):
            user_language = request.user.language
            # Only activate if it's different from the session language to avoid redundancy
            # and allow manual session overrides if desired (though usually user pref wins)
            activate(user_language)
            if hasattr(request, 'session'):
                request.session[LANGUAGE_SESSION_KEY] = user_language

        response = self.get_response(request)
        return response
