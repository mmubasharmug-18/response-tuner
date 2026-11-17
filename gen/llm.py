import time

from rag.config import LLM_MODEL, get_api_key


def retryable(error):
    code = getattr(error, "status_code", None)
    if code is not None:
        return code == 429 or code >= 500
    return isinstance(error, (TimeoutError, ConnectionError, RuntimeError)) or type(error).__name__ in (
        "APITimeoutError", "APIConnectionError", "InternalServerError", "RateLimitError",
    )


def wait_time(error, attempt):
    headers = getattr(getattr(error, "response", None), "headers", None)
    try:
        if headers and headers.get("retry-after"):
            return min(float(headers["retry-after"]) + 1, 60)
    except (TypeError, ValueError):
        pass
    return min(4 * 2 ** attempt, 60)


def make_llm(model=None, gap=2.5, retries=4):
    from groq import Groq

    model = model or LLM_MODEL
    client = Groq(api_key=get_api_key(), timeout=40, max_retries=0)
    state = {"last": 0.0}
    options = {"reasoning_effort": "low"} if "gpt-oss" in model else {}

    def call(system, user):
        for attempt in range(retries + 1):
            pause = gap - (time.time() - state["last"])
            if pause > 0:
                time.sleep(pause)
            try:
                reply = client.chat.completions.create(
                    model=model, temperature=0, max_tokens=2000,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}], **options,
                )
                state["last"] = time.time()
                text = (reply.choices[0].message.content or "").strip()
                if not text:
                    raise RuntimeError("the model sent back an empty answer")
                return text
            except Exception as error:
                state["last"] = time.time()
                if attempt == retries or not retryable(error):
                    raise
                time.sleep(wait_time(error, attempt))

    call.model = model
    return call
