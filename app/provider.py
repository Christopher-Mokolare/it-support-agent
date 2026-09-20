from __future__ import annotations
import json
import urllib.request

class ProviderError(Exception): pass

class OpenAICompatibleProvider:
    def __init__(self, api_key, model, base_url):
        if not api_key: raise ProviderError("LLM_API_KEY is required")
        self.api_key,self.model=api_key,model
        self.base_url=(base_url or "https://api.groq.com/openai/v1").rstrip("/")

    def complete(self, messages, tools):
        body={"model":self.model,"messages":messages,"temperature":0.1}
        if tools: body["tools"]=tools; body["tool_choice"]="auto"
        req=urllib.request.Request(self.base_url+"/chat/completions",data=json.dumps(body).encode(),
             headers={"Authorization":"Bearer "+self.api_key,"Content-Type":"application/json"})
        try:
            with urllib.request.urlopen(req,timeout=90) as r: return json.load(r)
        except Exception as e: raise ProviderError(str(e)) from e

def create_provider(settings):
    provider=settings.provider.lower()
    if provider in {"groq","openai","openai-compatible"}:
        base=settings.base_url or ("https://api.groq.com/openai/v1" if provider=="groq" else "https://api.openai.com/v1")
        return OpenAICompatibleProvider(settings.api_key,settings.model,base)
    if provider=="ollama":
        return OpenAICompatibleProvider(settings.api_key or "ollama",settings.model,settings.base_url or "http://localhost:11434/v1")
    raise ProviderError(f"Unsupported LLM_PROVIDER={settings.provider!r}")
