from celery import task
from dot_basic.models import Order as OrderList
from dot_basic.models import CompleteOrders
from datetime import date, time, datetime, timedelta
from django.contrib.auth.models import User


@task
def exchange_celery():
    # wait 1 minutes before automatically completing order
    timeLimit = timedelta(minutes = 1)
    
    orders = OrderList.objects.all()
    for order in orders:
        # get elapsed time for order
        now = datetime.now().strftime('%H:%M:%S')
        now = datetime.strptime(now, '%H:%M:%S').time()
        elapsedTime = datetime.combine(date.min, now) - datetime.combine(date.min, order.time)
        
        if elapsedTime > timeLimit:
            user = User.objects.get(username=str(order.user))

            print(user)
            
            balance = { "EUR":0, "USD":0, "RON":0}

            balance[str(order.home_currency)] = order.home_currency_amount * -1
            balance[str(order.target_currency)] = order.target_currency_amount 

            user.profile.USD = user.profile.USD + balance["USD"]
            user.profile.EUR = user.profile.EUR + balance["EUR"]
            user.profile.RON = user.profile.RON + balance["RON"]
            user.save()

            print(balance)

            # save order to external record and delete from db
            
            CompleteOrder = CompleteOrders(user=order.user, date=order.date, time=order.time, home_currency=order.home_currency, home_currency_amount=order.home_backup, rate=order.rate, target_currency=order.target_currency, target_currency_amount=order.target_backup, status='complete')
            CompleteOrder.save()
            order.delete()
