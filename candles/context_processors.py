from .models import Category  # Import your Category model

def categories_processor(request):
    categories = Category.objects.all()  # Get all categories
    return {'categories': categories}
