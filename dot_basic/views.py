from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.generic import TemplateView
from django.db.models import Count
from dot_corporate import models as corporate_models
from dot_basic import models as basic_models
from dot_basic import forms as basic_forms
from django.utils import timezone
# EMAIL CONFIRMATION
from django.core.mail import EmailMessage
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from .tokens import account_activation_token
# Non-django imports
import json, os, datetime, decimal, time, csv, codecs
import _strptime
from forex_python.converter import CurrencyRates
import sys
# Create your views here.







# REGISTRATION VIEWS ---------------------------------------------------------------

def logoutView(request):
    logout(request)
    return redirect('/')

def signupView(request):
    if request.method == 'POST':
        form = basic_forms.SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            user.refresh_from_db()  # load the profile instance created by the signal\
            current_site = get_current_site(request)
            mail_subject = 'Activate your Dot account!.'
            message = render_to_string('registration/acc_active_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid':urlsafe_base64_encode(force_bytes(user.pk)).decode(),
                'token':account_activation_token.make_token(user),
            })
            to_email = form.cleaned_data.get('email')
            email = EmailMessage(mail_subject, message, to=[to_email])
            email.send()
            return render(request, 'registration/request_activation.html')
    else:
        form = basic_forms.SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})


def activate(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)
        # return redirect('home')
        return redirect('/')
    else:
        return HttpResponse('Activation link is invalid!')

# ------------------------------------------------------------- # REGISTRATION VIEWS



@login_required
def homeView(request):
    user=request.user
    your_page = True
    if user.profile.corporate is False:
        return render(request, 'users/profile/profile.html', {'your_page': your_page})
    else:
        return render(request, 'corporate/corporate-profile.html')


def moneyView(request):
    user = request.user
    if user.profile.corporate is False:
        if request.method == 'POST':
            # check if user is withdrawing
            if 'withdraw' in request.POST:
                withdrawform = basic_forms.WithdrawForm(request.POST)
                if withdrawform.is_valid():
                    balance = {'EUR': user.profile.EUR, 'RON': user.profile.RON, 'USD': user.profile.USD}
                    currency = withdrawform.cleaned_data.get('currency')
                    amount = withdrawform.cleaned_data.get('amount')
                    if (amount > 0 and amount <= balance[currency]):
                        balance[currency]=balance[currency] - amount
                        HistoryItem = basic_models.OpHistory(user = user,
                                                currency= currency,
                                                amount=amount,
                                                optype='withdraw',
                                                date=datetime.date.today(),
                                                time=datetime.datetime.now().strftime('%H:%M:%S'))
                        HistoryItem.save()
                    user.profile.USD = balance['USD']
                    user.profile.EUR = balance['EUR']
                    user.profile.RON = balance['RON']
                    user.save()
                return redirect('/money/')
                topupform = basic_forms.TopUpForm()
            # user is topping up
            elif 'topup' in request.POST:
                topupform = basic_forms.TopUpForm(request.POST)
                if topupform.is_valid():
                    balance = {'EUR': user.profile.EUR, 'RON': user.profile.RON, 'USD': user.profile.USD}
                    currency = topupform.cleaned_data.get('currency')
                    amount = topupform.cleaned_data.get('amount')
                    if (amount > 0):
                        balance[currency]=balance[currency] + amount
                        HistoryItem = basic_models.OpHistory(user = user,
                                                currency= currency,
                                                amount=amount,
                                                optype='topup',
                                                date=datetime.date.today(),
                                                time=datetime.datetime.now().strftime('%H:%M:%S'))
                        HistoryItem.save()
                    user.profile.USD = balance['USD']
                    user.profile.EUR = balance['EUR']
                    user.profile.RON = balance['RON']
                    user.save()
                    return redirect('/money/')
                withdrawform = basic_forms.WithdrawForm()
        history = basic_models.OpHistory.objects.filter(user=user).order_by('-id')[:5]
        topupform = basic_forms.TopUpForm()
        withdrawform = basic_forms.WithdrawForm()
        return render(request, 'users/wallet/money.html', {'topupform': topupform, 'withdrawform': withdrawform, 'history': history})
    else:
        return redirect('/')



@login_required
def exchangeView(request):
    user = request.user
    if request.method == 'POST':
        error = False
        c = CurrencyRates()
        form = basic_forms.ExchangeForm(request.POST)
        if form.is_valid():

            # get user input
            home_currency = form.cleaned_data.get('home_currency')
            target_currency = form.cleaned_data.get('target_currency')
            home_currency_amount = decimal.Decimal(form.cleaned_data.get('home_currency_amount'))
            username = user.username
            date = datetime.date.today()
            time = datetime.datetime.now().strftime('%H:%M:%S')
            rate = decimal.Decimal(c.get_rate(home_currency, target_currency))
            target_currency_amount = home_currency_amount*rate

            # dictionary linking user profile to string values
            balance = {"EUR":user.profile.EUR, "USD":user.profile.USD, "RON":user.profile.RON}
            # check if user has enough funds to exchange and redirect back with error if not
            if home_currency_amount > balance[home_currency]:
                error = True
                return render(request, 'users/wallet/exchange.html', {'form': form, 'error':error, 'currency': home_currency})

            # create Order object from user input
            order = basic_models.Order(date = date, time = time, user = username, home_currency=home_currency, home_currency_amount=home_currency_amount, rate=rate, target_currency=target_currency, target_currency_amount=target_currency_amount, status='pending', home_backup=home_currency_amount, target_backup=target_currency_amount)
            order.save()

            # check if order can be matched to other users
            orderlist = basic_models.Order.objects.filter(home_currency = order.target_currency, target_currency = order.home_currency).exclude(user=user)

            for order2 in orderlist:
                if order.status is not 'complete':
                    user2 = User.objects.get(username=order2.user)
                    balance2 = {"EUR":user2.profile.EUR, "USD":user2.profile.USD, "RON":user2.profile.RON}
                    if order.home_currency_amount >= order2.target_currency_amount:

                        # user 1 is selling more currency than user 2, so the .home field of his profile will be updated to .home-how much 2 is buying
                        # using order1.home as reference
                        # updating the profile of user1
                        balance[str(order.home_currency)]=balance[str(order.home_currency)]-order2.target_currency_amount
                        # updating the order of user1
                        order.home_currency_amount = order.home_currency_amount - order2.target_currency_amount
                        # updating the profile of user2
                        balance2[str(order2.target_currency)]=balance2[str(order2.target_currency)] + order2.target_currency_amount
                        # updating the order of user 2
                        order2.target_currency_amount = 0
                        # using order2.home as reference
                        # updating the profile of user1
                        balance[str(order.target_currency)]=balance[str(order.target_currency)] + order2.home_currency_amount
                        # updating the order of user1
                        order.target_currency_amount = order.target_currency_amount - order2.home_currency_amount
                        # updating the profile of user2
                        balance2[str(order2.home_currency)] = balance2[str(order2.home_currency)] - order2.home_currency_amount
                        # updating the order of user2
                        order2.home_currency_amount = 0
                    else:
                        # using order1.home as reference
                        # updating the profile of user 1
                        balance[str(order.home_currency)]=balance[str(order.home_currency)] - order.home_currency_amount
                        #updating the profile of user 2
                        balance2[str(order2.target_currency)] = balance2[str(order2.target_currency)] + order.home_currency_amount
                        #updating the order of user2
                        order2.target_currency_amount = order2.target_currency_amount - order.home_currency_amount
                        # updating the order of user 1
                        order.home_currency_amount = 0
                        #using order2.home as reference
                        #updating the profile of user 1
                        balance[str(order.target_currency)] = balance[str(order.target_currency)] + order.target_currency_amount
                        #updating the profile of user 2
                        balance2[str(order2.home_currency)] = balance2[str(order2.home_currency)] - order.target_currency_amount
                        #updating the order of user 2
                        order2.home_currency_amount = order2.home_currency_amount - order.target_currency_amount
                        #updating the order of user 1
                        order.target_currency_amount = 0

                    # saving changes to user profiles
                    user.profile.USD = balance['USD']
                    user.profile.EUR = balance['EUR']
                    user.profile.RON = balance['RON']
                    user.save()

                    user2.profile.USD = balance2['USD']
                    user2.profile.EUR = balance2['EUR']
                    user2.profile.RON = balance2['RON']
                    user2.save()

                    # saving changes to orders
                    if order.home_currency_amount == 0:
                        order.status = 'complete'
                    if order2.home_currency_amount == 0:
                        order2.status = 'complete'
                    order.save()
                    order2.save()

        return redirect('/exchange/')
    else:
        form = basic_forms.ExchangeForm()
    orders = basic_models.Order.objects.filter(user=user.username, status='pending')
    completed_orders = basic_models.CompleteOrders.objects.filter(user=user.username).order_by('-id')[:5]
    context_dict={'form':form, 'orders': orders, 'completed_orders': completed_orders}
    return render(request, 'users/wallet/exchange.html', context_dict)


@login_required
def transferView(request):
    user = request.user
    if user.profile.corporate is False:
        if request.method == 'POST':
            form = basic_forms.TransferForm(request.POST)
            if form.is_valid():
                # get user2, curency and amount from form
                uid = User.objects.get(username=form.cleaned_data.get('username'))
                currency = form.cleaned_data.get('currency')
                amount = form.cleaned_data.get('amount')
                # dictionaries used for mapping the profiles of user1 and user2 to strings
                balance = {'EUR':user.profile.EUR, 'USD':user.profile.USD, 'RON':user.profile.RON}
                balance2 = {'EUR':uid.profile.EUR, 'USD':uid.profile.USD, 'RON':uid.profile.RON}
                # if user has enough money to transfer
                if amount >= 0 and balance[currency] >= amount:
                    balance2[currency] = balance2[currency] + amount
                    balance[currency] = balance[currency] - amount
                    HistoryList = basic_models.TransferHistory(user = user,
                                                  user2 = uid,
                                                  currency = currency,
                                                  amount = amount,
                                                  date = datetime.date.today(),
                                                  time = datetime.datetime.now().strftime('%H:%M:%S') )
                    HistoryList.save()
                # update profiles using values saved in dictionary
                user.profile.EUR = balance['EUR']
                user.profile.RON = balance['RON']
                user.profile.USD = balance['USD']
                uid.profile.EUR = balance2['EUR']
                uid.profile.RON = balance2['RON']
                uid.profile.USD = balance2['USD']
                # save changes to database
                user.save()
                uid.save()
                # pop notification for user 2
                notification = basic_models.Notification(user = uid, user2 = user, notification_type = 'Transfer', date = datetime.date.today(), time = datetime.datetime.now().strftime('%H:%M:%S'), notification = "You have received %s %s from %s" % (str(amount), currency, user.username))
                notification.save()

            return redirect('/transfer/')
        else:
            form = basic_forms.TransferForm()
        transfer_history = basic_models.TransferHistory.objects.filter(user=user) | basic_models.TransferHistory.objects.filter(user2=user)
        transfer_history = transfer_history.order_by('-date', '-time')[:10]
        context_dict={'form': form, 'transfer_history': transfer_history}
        return render(request, 'users/wallet/transfer.html', context_dict)
    else:
        return redirect('/')



@login_required
def settingsView(request):
    user = request.user
    if user.profile.corporate is False:
        notifications=basic_models.Notification.objects.filter(user=user)
        context_dict={}
        return render(request, 'users/profile/settings.html', context_dict)
    else:
        return render(request, 'corporate/corporate-settings.html')

@login_required
def profilePictureView(request):
    user = request.user
    if request.method == 'POST':
        form = basic_forms.ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            user.profile.avatar=form.cleaned_data['image']
            user.save()
            return redirect('/settings/profile-picture/')
    else:
        form = basic_forms.ImageUploadForm()
        context_dict = {'form': form}
        return render(request, 'users/profile/avatar.html', context_dict)

@login_required
def historyView(request):
    user = request.user
    if user.profile.corporate is False:
        orders = basic_models.Order.objects.filter(user=user.username, status='pending')
        completed_orders = basic_models.CompleteOrders.objects.filter(user=user.username)
        operations_list = basic_models.OpHistory.objects.filter(user=user)
        transfer_list = basic_models.TransferHistory.objects.filter(user=user) | basic_models.TransferHistory.objects.filter(user2=user)
        transfer_list = transfer_list.order_by('-date', '-time')
        payment_list = basic_models.PurchasedItem.objects.filter(user=user)
        context_dict = {'payment_list':payment_list, 'orders':orders, 'completed_orders':completed_orders, 'operations_list': operations_list, 'transfer_list': transfer_list}
        return render(request, 'users/wallet/history.html', context_dict)
    else:
        return redirect ('/')

@login_required
def markAsSeenView(request):
    n_id = request.GET.get('id', '')
    notification = basic_models.Notification.objects.get(id=n_id)
    notification.status='seen'
    notification.save()
    return HttpResponse('')

@login_required
def profileView(request, profile=0):
    user = request.user
    your_page = True
    if profile!=0 and profile!=user.username:
        your_page = False
        target = User.objects.get(username=profile)
        is_friend = False
        sent = False
        if basic_models.Friendship.objects.filter(creator=user, friend=target, status='sent').exists():
            sent = True
        if basic_models.Friendship.objects.filter(creator=user, friend=target, status='accepted').exists():
            is_friend = True
        context_dict={'sent': sent, 'is_friend': is_friend, 'target': target, 'your_page': your_page}
        return render(request, 'users/profile/profile.html', context_dict)
    context_dict={'your_page': your_page}
    return render(request, 'users/profile/profile.html', context_dict)

@login_required
def friendsView(request):
    user = request.user
    if request.GET.get('add', ''):
        target = User.objects.get(username=request.GET.get('add', ''))
        if not basic_models.Friendship.objects.filter(creator=user, friend=target).exists():
            if basic_models.Friendship.objects.filter(creator=target, friend=user).exists():
                friendship1 = basic_models.Friendship.objects.get(creator=target, friend=user)
                friendship1.status = 'accepted'
                friendship2 = basic_models.Friendship(creator=user, friend=target, status='accepted')
                friendship1.save()
                notification1 = basic_models.Notification(user = target,
                                                          user2 = user,
                                                          notification_type = "friend-accept",
                                                          date = datetime.date.today(),
                                                          time = datetime.datetime.now().strftime('%H:%M:%S'),
                                                          notification = "You are now friends with %s" % user.username)
                notification2 = basic_models.Notification(user = user,
                                                          user2 = target,
                                                          notification_type = "friend-accept",
                                                          date = datetime.date.today(),
                                                          time = datetime.datetime.now().strftime('%H:%M:%S'),
                                                          notification = "You are now friends with %s" % target.username)
                notification1.save()
                notification2.save()
            else:
                friendship2 = basic_models.Friendship(creator=user, friend=target)
                notification = basic_models.Notification(user = target,
                                                         user2 = user,
                                                         notification_type = "friend-request",
                                                         date = datetime.date.today(),
                                                         time = datetime.datetime.now().strftime('%H:%M:%S'),
                                                         notification="You have a friend request from %s" % user.username)
                notification.save()
            friendship2.save()
        sent = True
        context_dict = {'sent':sent}
        url = '/profile/?user=' + str(target.username)
        return redirect(url)

    elif request.GET.get('rm', ''):
        target = User.objects.get(username=request.GET.get('rm', ''))
        basic_models.Friendship.objects.filter(creator=target, friend=user).delete()
        basic_models.Friendship.objects.filter(creator=user, friend=target).delete()
        url = '/profile/?user=' + str(target.username)
        return redirect(url)

    else:
        accepted_friends = basic_models.Friendship.objects.filter(creator=user, status='accepted')
        pending_friends = basic_models.Friendship.objects.filter(creator=user, status ='sent')
        requests = basic_models.Friendship.objects.filter(friend=user, status='sent')
        context_dict={'accepted_friends': accepted_friends, 'pending_friends': pending_friends, 'requests': requests}
        return render(request, 'users/profile/friends.html', context_dict)



def chatView(request, name=0):
    user = request.user
    if User.objects.filter(username=name).exists():
        chat_buddy = User.objects.get(username=name)
        form = basic_forms.SendMessageForm()
        messages = basic_models.Message.objects.filter(user_from=user, user_to=chat_buddy) | basic_models.Message.objects.filter(user_from=chat_buddy, user_to=user)
        messages = messages.order_by('id')
        mlist = basic_models.Message.objects.filter(user_from=user) | basic_models.Message.objects.filter(user_to=user)
        nlist = {x.user_from and x.user_to for x in mlist}
        nlist = list(nlist)
        nlist.remove(user)
        context_dict = {'form': form, 'chat_buddy': chat_buddy, 'messages': messages, 'nlist': nlist}
        return render(request, 'users/messages/chat.html', context_dict)

def conversationsView(request):
    user = request.user
    return render(request, 'users/messages/chat.html')




# -------- AJAX VIEWS --------#

def get_user_info_AJAX(request):
    if request.is_ajax():
        user = request.user
        target = request.GET.get('friend', '')
        friend = User.objects.get(username=target)
        is_friend = False
        if basic_models.Friendship.objects.filter(creator=user, friend=friend, status='accepted').exists():
            is_friend = True
        context_dict={'friend': friend, 'is_friend': is_friend}
        return render(request, 'ajax/get_user_info.html', context_dict)
    else:
        return redirect('/')

def get_conversations_AJAX(request):
    user = request.user
    mlist = basic_models.Message.objects.filter(user_from=user) | basic_models.Message.objects.filter(user_to=user)
    nlist = {x.user_from and x.user_to for x in mlist}
    nlist = list(nlist)
    nlist.remove(user)
    context_dict = {'nlist': nlist}
    return render(request, 'ajax/get_conversations.html', context_dict)


def send_message_AJAX(request):
    if request.is_ajax():
        if request.method == 'POST':
            message_text = request.POST.get('the_message')
            chat_buddy=request.POST.get('chat_buddy')
            response_data = {}
            message = basic_models.Message(message=message_text,
                                           user_from=request.user,
                                           user_to=User.objects.get(username=chat_buddy))
            message.date = datetime.date.today()
            message.time = datetime.datetime.now().strftime('%H:%M:%S')

            message.save()

            response_data['result'] = 'Create post successful!'
            response_data['postpk'] = message.pk
            response_data['text'] = message.message
            response_data['author'] = message.user_from.username

            return HttpResponse(
                json.dumps(response_data),
                content_type="application/json"
            )
        else:
            return HttpResponse(
                json.dumps({"nothing to see": "this isn't happening"}),
                content_type="application/json"
            )
    else:
        return redirect('/')

def get_messages_AJAX(request):
    if request.is_ajax():
        user = request.user
        chat_buddy = request.GET.get('chat_buddy')
        if User.objects.filter(username=chat_buddy).exists():
            user_to = User.objects.get(username=chat_buddy)
            messages = basic_models.Message.objects.filter(user_from=user, user_to=user_to, status_back="sending") | basic_models.Message.objects.filter(user_from=user_to, user_to=user, status="sending")
            messages = messages.order_by('pk')
            for message in messages:
                if (user == message.user_to):
                    message.status = 'seen'
                    message.save()
                else:
                    message.status_back = 'seen'
                    message.save()
        return render(request, 'ajax/message_list.html', {'messages': messages})
    else:
        return redirect('/')

@login_required
def searchView(request):
    user = request.user
    query = request.GET.get('query', '')
    userlist = User.objects.filter(username__icontains=query)[:5]
    context_dict = {'userlist': userlist}
    return render(request, 'ajax/search.html', context_dict)

@login_required
def getNotificationsView(request):
    user = request.user
    context_dict = {}
    notifications = basic_models.Notification.objects.filter(user=user, status='unseen').order_by('-id')
    if len(notifications) < 5:
        n = 5-len(notifications)
        notifications_seen = basic_models.Notification.objects.filter(user=user, status='seen').order_by('-id')[:n]
        context_dict['notifications_seen'] = notifications_seen
    else:
        notifications = notifications[:5]
    context_dict['notifications'] = notifications
    return render(request, 'ajax/notifications.html', context_dict)


@login_required
def changeDefaultView(request):
    user = request.user
    new = request.GET.get('new', '')
    user.profile.default_payment = new
    user.save()
    return HttpResponse('')
