from django.conf import settings


def product(request):
    return {"PRODUCT_NAME": settings.PRODUCT_NAME, "PRODUCT_NAME_EN": settings.PRODUCT_NAME_EN,
            "SHOW_DEMO_ACCOUNTS": settings.SHOW_DEMO_ACCOUNTS}
