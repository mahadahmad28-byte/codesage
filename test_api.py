"""Quick test of the google-genai SDK to validate API calls."""
import os
import sys

# Test 1: Import
try:
    from google import genai
    from google.genai import types
    print("✅ Import OK")
except ImportError as e:
    print(f"❌ Import FAILED: {e}")
    sys.exit(1)

API_KEY = os.getenv("GEMINI_API_KEY", "")
if not API_KEY:
    # Load from .env manually
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_file):
        for line in open(env_file):
            if line.startswith("GEMINI_API_KEY="):
                API_KEY = line.strip().split("=", 1)[1]
                break

print(f"🔑 API key: {API_KEY[:12]}...{API_KEY[-4:] if len(API_KEY) > 16 else '(too short)'}")

client = genai.Client(api_key=API_KEY)

# Test 2: Embedding
print("\n─── Testing text-embedding-004 ───")
try:
    response = client.models.embed_content(
        model="text-embedding-004",
        contents="Hello, world!",
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
    )
    dims = len(response.embeddings[0].values)
    print(f"✅ Embedding OK — {dims} dimensions")
except Exception as e:
    print(f"❌ Embedding FAILED: {type(e).__name__}: {e}")

    # Try alternate call patterns
    print("\n  Trying without config...")
    try:
        response = client.models.embed_content(
            model="text-embedding-004",
            contents="Hello, world!",
        )
        dims = len(response.embeddings[0].values)
        print(f"  ✅ Works without config — {dims} dimensions")
    except Exception as e2:
        print(f"  ❌ Also failed: {e2}")

    print("\n  Trying with models/ prefix...")
    try:
        response = client.models.embed_content(
            model="models/text-embedding-004",
            contents="Hello, world!",
        )
        dims = len(response.embeddings[0].values)
        print(f"  ✅ Works with models/ prefix — {dims} dimensions")
    except Exception as e3:
        print(f"  ❌ Also failed: {e3}")

# Test 3: Chat generation
print("\n─── Testing gemini-2.0-flash ───")
try:
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents="Say: hello",
        config=types.GenerateContentConfig(
            system_instruction="You are a test bot.",
            temperature=0.1,
        ),
    )
    print(f"✅ Generation OK — '{response.text[:50].strip()}'")
except Exception as e:
    print(f"❌ Generation FAILED: {type(e).__name__}: {e}")

    print("\n  Trying gemini-2.0-flash-exp...")
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents="Say: hello",
        )
        print(f"  ✅ Works with -exp: '{response.text[:50].strip()}'")
    except Exception as e2:
        print(f"  ❌ Also failed: {e2}")

print("\n─── Done ───")
