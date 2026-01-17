from django.urls import path

from .views import (
    Perfil,
    PerfilChangePassword,
    PerfilChangePasswordConfirm,
    PerfilDelete,
    PerfilUpdate,
    RequestPasswordChangeView,
    SignIn,
    SignUp,
    logout_user,
)

urlpatterns = [
    path('signup/', SignUp.as_view(), name='signup'),
    path('signin/', SignIn.as_view(), name='signin'),
    path('logout/', logout_user, name='logout'),
    path('<int:pk>/perfil/', Perfil.as_view(), name='perfil'),
    path('<int:pk>/perfil/update/', PerfilUpdate.as_view(), name='update_perfil'),
    path(
        '<int:pk>/perfil/update-password/',
        PerfilChangePassword.as_view(),
        name='update_perfil_password',
    ),
    path(
        'request-password-change/',
        RequestPasswordChangeView.as_view(),
        name='request_password_change',
    ),
    path(
        '<int:pk>/perfil/update-password/<str:token>/',
        PerfilChangePasswordConfirm.as_view(),
        name='update_perfil_password_confirm',
    ),
    path('<int:pk>/perfil/delete/', PerfilDelete.as_view(), name='delete_perfil'),
]
