from app.api.routes.copilot import CopilotChatRequest

def test_chat_request_without_thread_id():
    req = CopilotChatRequest(message="Hello")
    assert req.message == "Hello"
    assert req.thread_id is None

def test_chat_request_with_thread_id():
    req = CopilotChatRequest(message="Continue", thread_id="thread-123")
    assert req.thread_id == "thread-123"
