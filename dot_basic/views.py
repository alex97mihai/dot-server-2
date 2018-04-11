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
    if user.profile.corporate is False:
        return render(request, 'users/profile/profile.html')
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
                notification = basic_models.Notification(user = uid, user2 = user, notification_type = 'transfer-complete', date = datetime.date.today(), time = datetime.datetime.now().strftime('%H:%M:%S'), notification = "You have received %s%s from %s" % (currency, str(amount), user.username))
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
        context_dict={'notifications':notifications}
        return render(request, 'users/profile/settings.html', context_dict)
    else:
        return render(request, 'corporate/corporate-settings.html')

@login_required
def historyView(request):
    user = request.user
    if user.profile.corporate is False:
        orders = basic_models.Order.objects.filter(user=user.username, status='pending')
        completed_orders = basic_models.CompleteOrders.objects.filter(user=user.username)
        notifications= basic_models.Notification.objects.filter(user=user)
        operations_list = basic_models.OpHistory.objects.filter(user=user)
        transfer_list = basic_models.TransferHistory.objects.filter(user=user) | basic_models.TransferHistory.objects.filter(user2=user)
        transfer_list = transfer_list.order_by('-date', '-time')
        payment_list = basic_models.PurchasedItem.objects.filter(user=user)
        context_dict = {'payment_list':payment_list, 'orders':orders, 'completed_orders':completed_orders, 'notifications':notifications, 'operations_list': operations_list, 'transfer_list': transfer_list}
        return render(request, 'users/wallet/history.html', context_dict)
    else:
        return redirect ('/')

@login_required
def searchView(request):
    user = request.user
    query = request.GET.get('query', '')
    userlist = User.objects.filter(username__icontains=query)[:5]
    context_dict = {'userlist': userlist}
    return render(request, 'ajax/search.html', context_dict)
