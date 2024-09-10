from datetime import timedelta
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
import random
import string

class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=12, null=True)
    password = models.CharField(max_length=100)
    address = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'
  
class Seller(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)
    phone = models.CharField(max_length=12, unique=True)
    address = models.CharField(max_length=255)

    def __str__(self):
        return self.name
    
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    image = models.ImageField(upload_to='category_images/', null=True)

    def __str__(self):
        return self.name
    
    def product_count(self):
        return self.aggregate(product_count=models.Count('product'))['product_count']
     
def generate_sku():
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(6))

class Product(models.Model):
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='product_images/')
    retail_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    description = models.TextField()
    sku = models.CharField(max_length=6, unique=True, default=generate_sku)

    def __str__(self):
        return self.name
    
class Inventory(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, primary_key=True)
    quantity_in_stock = models.IntegerField(default=0)
    reorder_level = models.IntegerField(default=5)
    last_update_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.product.name} - Quantity: {self.quantity_in_stock}'
    
@receiver(post_save, sender=Product)
def create_inventory(sender, instance, created, **kwargs):
    if created:
        Inventory.objects.create(product=instance) 

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('packed', 'Packed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
    ]
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    order_date = models.DateField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_address = models.CharField(max_length=255)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')
    delivery_date = models.DateField(blank=True, null=True)

    def _str_(self):
        return f'Order #{self.pk} - Customer: {self.customer}, Total Amount: {self.total_amount}: {self.status}'
    
    def save(self, *args, **kwargs):
        # Ensure the order_date is set
        if not self.order_date:
            self.order_date = timezone.now().date()
        
        # Set delivery_date if not already set
        if not self.delivery_date:
            self.delivery_date = self.order_date + timedelta(days=7)
        
        super().save(*args, **kwargs)


class OrderDetail(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f'Order #{self.order.pk} - Product: {self.product.name}, Quantity: {self.quantity}, Price: {self.price}'

class Cart(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)

    def sub_total(self):
        return int(self.product.retail_price) * int(self.quantity)

    def __str__(self):
        return f"Cart - Customer: {self.customer.first_name} - Product: {self.product.name} - Qty: {self.quantity}"

class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('successful', 'Successful'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Failed'),
    ]
    transaction_id = models.CharField(max_length=255, primary_key=True)
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    payment_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2) 
    payment_method = models.CharField(max_length=50)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')

    def __str__(self):
        return f"Payment for Order #{self.transaction_id} - Amount: {self.amount} - Method: {self.payment_method}: {self.status}"

class Wishlist(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    def __str__(self):
        return f"Wishlist - Customer: {self.customer.first_name} - Product: {self.product.name}"


class SellerNotification(models.Model):
    sender = models.ForeignKey(User, related_name='sent_seller_notifications', on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name='received_seller_notifications', on_delete=models.CASCADE)
    subject = models.CharField(max_length=100)
    message = models.TextField()
    request_type = models.CharField(max_length=20, choices=[('restock', 'Restock Request')])
    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE, null=True)
    quantity_to_restock = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def _str_(self):
        return self.subject

class Notification(models.Model):
    subject = models.CharField(max_length=20)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def _str_(self):
        return self.subject

class LowStockProducts(models.Model):
    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE)
    quantity_to_restock = models.IntegerField(default=0)

    def _str_(self):
        return f'Name: {self.inventory.product.name[:20]} --- Quantity: {self.inventory.quantity_in_stock} --- Restock Level: {self.inventory.reorder_level}'

# To automatically create entries in the LowStockProducts model when the quantity <= reorder_level and send notification to admin
@receiver(post_save, sender=Inventory)
def check_low_stock(sender, instance, **kwargs):
    if instance.quantity_in_stock <= instance.reorder_level:
        LowStockProducts.objects.create(inventory=instance)
        # Notify admin
        admin_user = User.objects.filter(is_staff=True).first()  # Assuming admin is identified by being a staff user
        if admin_user:
            subject = "Low Stock Alert"
            message = f"{subject}: {instance.product.name} quantity is {instance.quantity_in_stock}."
            Notification.objects.create(subject=subject, message=message)

# To automatically delete entries in the LowStockProducts model when the quantity > restock level
@receiver(post_save, sender=Inventory)
@receiver(post_delete, sender=Inventory)
def check_stock_levels(sender, instance, **kwargs):
    low_stock_entries = LowStockProducts.objects.filter(inventory=instance)
    for entry in low_stock_entries:
        if entry.inventory.quantity_in_stock > entry.inventory.reorder_level:
            entry.delete()








