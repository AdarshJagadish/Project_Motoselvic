# context_processors.py

from .models import Category

def categories_processor(request):
    categories = Category.objects.prefetch_related('subcategories').all()
    return {'categories': categories}
