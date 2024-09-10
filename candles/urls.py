# urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
    path('cart/', views.cart, name='cart'),
    path("shop/", views.shop, name="shop"),
    path('checkout/', views.checkout, name='checkout'),
    path('category/<int:pk>/', views.category, name='category'),
    path('contact/', views.contact, name='contact'),
    path('order_complete/', views.order_complete, name='order_complete'),
    path('product_detail/<int:pk>/', views.product, name='product_detail'),
    path('wishlist/', views.wishlist, name='wishlist'),


    path("login/", views.user_login, name="login"),
    path('register/', views.register, name='register'),
    path("logout/", views.signout, name="logout"),

    path("dashboard/", views.dashboard, name="dashboard"),
    path('edit_profile/', views.edit_profile, name='edit_profile'),
    path('change_password/', views.change_password, name='change_password'),
    path('forgot_password/', views.forgot_password, name='forgot_password'),
    path('reset_password/<uidb64>/<token>/', views.reset_password, name='reset_password'),

    path("cart/", views.cart, name="cart"),
    path('add_to_cart/', views.add_to_cart, name='add_to_cart'),
    path('remove_from_cart/', views.remove_from_cart, name='remove_from_cart'),
    path('delete_item_in_cart/<int:id>/', views.delete_item_in_cart, name='delete_item_in_cart'),

    path("checkout/", views.checkout, name="checkout"),
    path("place_order/", views.place_order, name="place_order"),
    path("order_details/<int:pk>/", views.order_details, name="order_details"),

]
