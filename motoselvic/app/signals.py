from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from .models import UserProfile, Users
from sentence_transformers import SentenceTransformer
import json

model = SentenceTransformer('all-MiniLM-L6-v2')

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

        vector = model.encode(f"{instance.username} {instance.email}")
        vector_json = json.dumps(vector.tolist())
        Users.objects.get_or_create(user=instance, defaults={'vector_data': vector_json})

    else:
        # Update or create UserProfile
        try:
            instance.userprofile.save()
        except ObjectDoesNotExist:
            UserProfile.objects.get_or_create(user=instance)

        # Update or create Users with vector data
        try:
            instance.ai_profile.save()
        except ObjectDoesNotExist:
            vector = model.encode(f"{instance.username} {instance.email}")
            vector_json = json.dumps(vector.tolist())
            Users.objects.create(user=instance, vector_data=vector_json)