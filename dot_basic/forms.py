from django.forms import ModelForm
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from dot_basic.models import *
import datetime

# used for the currency selection widget
currencies = [('EUR','EUR'),('USD','USD'),('RON','RON'),]

class SignUpForm(UserCreationForm):
    email = forms.EmailField(max_length=200, help_text='Required')
    
    def __init__(self, *args, **kwargs):
        super(SignUpForm, self).__init__(*args, **kwargs)
        self.fields['username'].help_text = ''
        self.fields['password2'].help_text = ''
        self.fields['password1'].help_text = 'At least 8 characters'
    class Meta:
        model = User
        fields = ('email', 'username', 'password1', 'password2')


class TopUpForm(forms.Form):
    currency = forms.CharField(label='Currency: ', widget=forms.Select(choices=currencies))
    amount = forms.DecimalField(label='Amount: ')


class WithdrawForm(forms.Form):
    currency = forms.CharField(label='Currency: ', widget=forms.Select(choices=currencies))
    amount = forms.DecimalField(label='Amount: ')

class ExchangeForm(ModelForm):
    home_currency = forms.CharField(label='From: ', widget=forms.Select(choices=currencies))
    target_currency = forms.CharField(label='To: ', widget=forms.Select(choices=currencies))
    home_currency_amount = forms.DecimalField(label='Amount: ')
    class Meta:
        model = Order
        fields = ('home_currency', 'target_currency', 'home_currency_amount')

class TransferForm(forms.Form):
    currency = forms.CharField(label='Currency: ', widget=forms.Select(choices=currencies))
    amount = forms.DecimalField(label='Amount: ')
    username = forms.CharField(label='User:')

class ImageUploadForm(forms.Form):
    image = forms.ImageField()

