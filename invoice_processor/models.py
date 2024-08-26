from django.db import models
# Create your models here.
class Expense(models.Model):
    invoice_number = models.TextField()
    account_number = models.TextField()
    customer_name = models.TextField()
    invoice_amount = models.DecimalField(max_digits=10, decimal_places=2)
    invoice_date = models.DateField()