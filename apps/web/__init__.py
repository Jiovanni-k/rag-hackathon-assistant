"""Presentation layer for browsers: Django templates + plain CSS + vanilla JS.

Pages are thin shells; all data goes through the REST API in /api/v1/ (session auth + CSRF),
so the web UI and any other client (mobile app, Postman) use exactly the same backend.
"""
