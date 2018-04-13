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
from django.urls import path, re_path

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
    re_path(r'^activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', activate, name='activate_view'),
    # PROFILE
    path('', homeView, name='home'),
    #
    path('profile/', profileView, name='profile'),
    path('profile/<slug:profile>', profileView, name='profile'),
    #
    path('friends/', friendsView, name='friends'),
    path('get_user_info/', get_user_info_AJAX, name='spy'),
    path('messages/', conversationsView, name='conversations'),
    path('messages/<slug:name>', chatView, name='chat'),
    path('send_message/', send_message_AJAX, name='send message'),
    path('get_messages/', get_messages_AJAX, name='get_messages'),
    # WALLET
    path('money/', moneyView, name='operations'),
    path('exchange/', exchangeView, name='exchange'),
    path('transfer/', transferView, name='transfer'),
    path('history/', historyView, name='history'),
    path('search/', searchView, name='search'),
    path('get-notifications/', getNotificationsView, name='get notifications'),
    path('mark-as-seen/', markAsSeenView, name='mark as seen'),
    path('change-default/', changeDefaultView, name='change default currency'),
    # SETTINGS
    path('settings/', settingsView, name='settings'),
    path('settings/profile-picture/', profilePictureView, name='profile pic'),

]  + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
