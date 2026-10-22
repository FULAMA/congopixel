SESSION_KEY = "my_orders"


def remember_order(request, order):
    refs = request.session.get(SESSION_KEY, [])
    if order.reference not in refs:
        refs.append(order.reference)
    request.session[SESSION_KEY] = refs[-20:]


def can_view_order(request, order):
    user = request.user
    if user.is_authenticated and (user.is_staff or order.user_id == user.pk):
        return True
    return order.reference in request.session.get(SESSION_KEY, [])