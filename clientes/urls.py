from django.urls import path
from .views import SignUp, SignIn, logout_user, PerfilUpdate, Perfil, PerfilChangePassword

urlpatterns = [
    path('signup/', SignUp.as_view(), name='signup'),
    path('signin/', SignIn.as_view(), name='signin'),
    path('logout/', logout_user, name='logout'),
    path('<int:pk>/perfil/', Perfil.as_view(), name='perfil'),
    path('<int:pk>/perfil/update/', PerfilUpdate.as_view(), name='update_perfil'),
    path('<int:pk>/perfil/update-password/', PerfilChangePassword.as_view(), name='update_perfil_password'),
] 
