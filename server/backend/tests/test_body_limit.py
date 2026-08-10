import unittest

from utils.body_limit import RequestBodyLimitMiddleware


class RequestBodyLimitTests(unittest.IsolatedAsyncioTestCase):
    async def test_rejects_content_length_over_limit_without_calling_app(self):
        app_called = False
        messages = []

        async def app(scope, receive, send):
            nonlocal app_called
            app_called = True

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            messages.append(message)

        middleware = RequestBodyLimitMiddleware(app, max_bytes=4)
        await middleware(
            {
                "type": "http",
                "headers": [(b"content-length", b"5")],
            },
            receive,
            send,
        )

        self.assertFalse(app_called)
        self.assertEqual(messages[0]["status"], 413)

    async def test_counts_streamed_body_when_length_is_missing(self):
        messages = []
        chunks = iter(
            [
                {"type": "http.request", "body": b"123", "more_body": True},
                {"type": "http.request", "body": b"45", "more_body": False},
            ]
        )

        async def app(scope, receive, send):
            await receive()
            await receive()

        async def receive():
            return next(chunks)

        async def send(message):
            messages.append(message)

        middleware = RequestBodyLimitMiddleware(app, max_bytes=4)
        await middleware({"type": "http", "headers": []}, receive, send)

        self.assertEqual(messages[0]["status"], 413)
