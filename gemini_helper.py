from config import get_client, MODEL
import time
import re


def call_gemini(
    api_key,
    prompt,
    max_tokens=2000,
    temperature=0.2,
    retries=5
):

    client = get_client(api_key)

    last_error = None

    for attempt in range(retries):

        try:

            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                }
            )

            if response is None:
                raise RuntimeError("No response from Gemini.")

            text = response.text

            if not text:
                raise RuntimeError("Empty Gemini response.")

            return text.strip()

        except Exception as e:

            last_error = e

            msg = str(e)

            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:

                match = re.search(
                    r"retry in\s+([0-9]+)",
                    msg.lower()
                )

                if match:
                    wait = int(match.group(1)) + 2
                else:
                    wait = 40

                print(f"Waiting {wait} seconds...")

                time.sleep(wait)

                continue

            if attempt < retries - 1:

                time.sleep(2 ** attempt)

            else:

                break

    raise RuntimeError(last_error)