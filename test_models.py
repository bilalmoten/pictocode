import os
from dotenv import load_dotenv
import requests
import time
import threading

# Load environment variables from .env file
load_dotenv(override=True)

# Get API key and endpoints from environment variables
AZURE_KEY = os.environ.get("AZURE_KEY")
GPT4O_ENDPOINT = os.environ.get("GPT4o_ENDPOINT")
GPT4O_MINI_ENDPOINT = os.environ.get("GPT4o_MINI_ENDPOINT")
O1_PREVIEW_ENDPOINT = os.environ.get("O1_PREVIEW_ENDPOINT")
O1_MINI_ENDPOINT = os.environ.get("O1_MINI_ENDPOINT")

# Add debug print statements
print("Environment variables loaded:")
print(f"AZURE_KEY: {'[SET]' if AZURE_KEY else '[NOT SET]'}")
print(f"GPT4O_ENDPOINT: {GPT4O_ENDPOINT}")
print(f"GPT4O_MINI_ENDPOINT: {GPT4O_MINI_ENDPOINT}")
print(f"O1_PREVIEW_ENDPOINT: {O1_PREVIEW_ENDPOINT}")
print(f"O1_MINI_ENDPOINT: {O1_MINI_ENDPOINT}")


def call_model(endpoint, messages, model_name):
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_KEY,
    }

    if "o1" in model_name.lower():
        print("O1 model")
        payload = {
            "messages": messages,
            "max_completion_tokens": 5000,
        }
    else:
        payload = {
            "messages": messages,
            "temperature": 0.7,
            "top_p": 0.95,
            "max_tokens": 100,
        }

    try:
        response = requests.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return f"Error calling {model_name} API: {e}"


def display_timer(stop_event):
    start_time = time.time()
    while not stop_event.is_set():
        elapsed_time = time.time() - start_time
        print(f"\rTime elapsed: {elapsed_time:.2f} seconds", end="", flush=True)
        time.sleep(0.1)


def test_model(model_name):
    endpoints = {
        "gpt4o": GPT4O_ENDPOINT,
        "gpt4o-mini": GPT4O_MINI_ENDPOINT,
        "o1-preview": O1_PREVIEW_ENDPOINT,
        "o1-mini": O1_MINI_ENDPOINT,
    }

    endpoint = endpoints.get(model_name)
    if not endpoint:
        return f"Invalid model name: {model_name}"

    if not endpoint.strip():  # Check if the endpoint is empty or just whitespace
        return f"Endpoint for {model_name} is not set"

    messages = [{"role": "user", "content": "API Testing. Just reply with 'WORKING' "}]

    print(f"Sending request to {model_name}...")
    stop_event = threading.Event()
    timer_thread = threading.Thread(target=display_timer, args=(stop_event,))
    timer_thread.start()

    start_time = time.time()
    result = call_model(endpoint, messages, model_name)
    end_time = time.time()

    stop_event.set()
    timer_thread.join()

    elapsed_time = end_time - start_time
    print(f"\nTotal time taken: {elapsed_time:.2f} seconds")

    # Extract the response message
    response_message = "No response message found"
    if isinstance(result, dict) and "choices" in result:
        choices = result["choices"]
        if choices and isinstance(choices[0], dict) and "message" in choices[0]:
            message = choices[0]["message"]
            if "content" in message:
                response_message = message["content"]

    return f"{model_name} response:\nMessage: {response_message}\n\nFull response:\n{result}"


def main():
    models = [
        "gpt4o",
        "gpt4o-mini",
        "o1-mini",
        "o1-preview",
    ]

    # models = ["gpt4o"]

    for model in models:
        print(f"\nTesting {model}...")
        response = test_model(model)
        print(response)
        print("-" * 50)


if __name__ == "__main__":
    main()
