from django.conf import settings


def product(request):
    return {"PRODUCT_NAME": settings.PRODUCT_NAME, "PRODUCT_NAME_EN": settings.PRODUCT_NAME_EN,
            "SHOW_DEMO_ACCOUNTS": settings.SHOW_DEMO_ACCOUNTS,
            "DEMO_STUDENT_PASSWORD": settings.DEMO_STUDENT_PASSWORD if settings.SHOW_DEMO_ACCOUNTS else "",
            "DEMO_ADMIN_PASSWORD": settings.DEMO_ADMIN_PASSWORD if settings.SHOW_DEMO_ACCOUNTS else ""}
