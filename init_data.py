import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from blog.models import Category

categories = [
    ('Texnologiya', 'texnologiya'),
    ('Dasturlash', 'dasturlash'),
    ('Dizayn', 'dizayn'),
    ('Hayot', 'hayot'),
    ('Biznes', 'biznes'),
    ('Fan', 'fan'),
    ('Madaniyat', 'madaniyat'),
    ('Sport', 'sport'),
]

for name, slug in categories:
    Category.objects.get_or_create(name=name, defaults={'slug': slug, 'name_uz': name})

print(f'{Category.objects.count()} kategoriya tayyor')
