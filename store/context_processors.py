from store.models import BusinessNameAndLogo

def business_details(request):
    return {
        "business_info": BusinessNameAndLogo.objects.first()
    }
