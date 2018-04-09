"""dot URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from django.conf.urls import url
from django.contrib import admin
from django.contrib.auth import views as auth_views
#import all views in my_app
from dot_basic.views import *
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    # DJANGO
    path('login/', auth_views.login, name='login'),
    path('admin/', admin.site.urls),
    path('logout/', logoutView, name='logout'),
    # END OF DJANGO
    #
    # REGISTRATION
    path('signup/', signupView, name='signup'),
    # PROFILE
    path('', homeView, name='home'),
    # WALLET
    path('money/', moneyView, name='operations'),
    path('exchange/', exchangeView, name='exchange'),
    path('transfer/', transferView, name='transfer'),

]  + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)