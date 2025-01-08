from django.shortcuts import render,redirect

def index(request):
    return render(request,'index.html')

def store(request):
    return render(request,'store.html')

# Create your views here.
