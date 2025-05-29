from fastapi import FastAPI, Request
from llama_cpp import Llama
import uvicorn
import os

app = FastAPI()

# Optional support for llama-cpp based features.
# Load the Llama model lazily if the model path is provided and valid.
LLAMA_MODEL_PATH = os.getenv("LLAMA_MODEL_PATH")
_llm = None

def get_llama_model():
    """Return a loaded `llama_cpp.Llama` instance or `None`."""
    global _llm
    if _llm is not None:
        return _llm
    if not LLAMA_MODEL_PATH:
        print("LLAMA_MODEL_PATH is not set.")
        return None
    try:
        from llama_cpp import Llama  # Optional dependency
    except Exception as exc:
        print(f"llama-cpp-python not available: {exc}")
        return None
    if not os.path.exists(LLAMA_MODEL_PATH):
        print(f"Llama model path not found: {LLAMA_MODEL_PATH}")
        return None
    try:
        _llm = Llama(model_path=LLAMA_MODEL_PATH)
    except Exception as exc:
        print(f"Failed to load Llama model: {exc}")
        _llm = None
    return _llm

# Load llama model directly if not using lazy loader (legacy logic)
llm = Llama(
    model_path="models/wizardcoder/wizardcoder-python-34b-v1.0.Q4_K_M.gguf",
    n_ctx=4096,
    n_threads=8,
    n_gpu_layers=100,
    n_batch=512,
)

@app.post("/generate")
async def generate(request: Request):
    body = await request.json()
    prompt = body.get("prompt", "")
    output = llm(prompt, max_tokens=256)
    return {"response": output["choices"][0]["text"]}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5005)
