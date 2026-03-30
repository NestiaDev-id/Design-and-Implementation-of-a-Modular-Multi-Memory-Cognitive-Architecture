"""Qwen LLM integration for Cognitive Memory System."""

from typing import Generator, Optional
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
from threading import Thread
import os
import sys

# Tambahkan path project root agar import config aman
sys.path.append(str(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))))

from .config import LLMConfig, default_config


class QwenLLM:
    """Wrapper for Qwen language model."""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """
        Initialize Qwen LLM.
        """
        self.config = config or default_config.llm
        self._model = None
        self._tokenizer = None
        self._loaded = False
    
    def load(self) -> None:
        """Load the model and tokenizer immediately."""
        if self._loaded:
            return
        
        # --- 1. VALIDASI PATH ---
        if not self.config.model_path:
            raise ValueError("Model path is not specified in configuration (NoneType).")
        
        print(f"Loading model from: {self.config.model_path}")

        # --- 2. TENTUKAN DEVICE (Auto Fallback) ---
        # Jika config.device None/Kosong, kita tentukan otomatis
        device_map_arg = self.config.device
        if not device_map_arg:
            device_map_arg = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"Device not specified in config, defaulting to: {device_map_arg}")

        # --- 3. TENTUKAN DTYPE ---
        if self.config.torch_dtype == "auto":
            dtype = "auto"
        elif self.config.torch_dtype == "float16":
            dtype = torch.float16
        elif self.config.torch_dtype == "bfloat16":
            dtype = torch.bfloat16
        else:
            dtype = torch.float32
        
        # --- 4. LOAD TOKENIZER (Terpisah) ---
        try:
            print(" [DEBUG] Loading Tokenizer...", end=" ", flush=True)
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.config.model_path,
                trust_remote_code=True,
            )
            print("DONE.")
        except Exception as e:
            print(f"\n[ERROR] Failed to load Tokenizer: {e}")
            raise e

        # --- 5. LOAD MODEL (Terpisah) ---
        try:
            print(f" [DEBUG] Loading Model (Device: {device_map_arg})...", end=" ", flush=True)
            self._model = AutoModelForCausalLM.from_pretrained(
                self.config.model_path,
                torch_dtype=dtype,
                device_map=device_map_arg,  # Menggunakan variabel yang sudah dipastikan string
                trust_remote_code=True,
            )
            print("DONE.")
            
            self._loaded = True
            print("Model loaded successfully into memory!")
            
        except Exception as e:
            print(f"\n[CRITICAL ERROR] Failed to load Model weights: {e}")
            # Hint untuk user jika error Path/NoneType
            if "NoneType" in str(e):
                print("HINT: This error often happens if 'device_map' is None or if a file path inside the model folder is broken.")
            raise e
    
    def unload(self) -> None:
        """Unload the model to free memory."""
        if self._model is not None:
            del self._model
            self._model = None
        if self._tokenizer is not None:
            del self._tokenizer
            self._tokenizer = None
        self._loaded = False
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    
    @property
    def is_loaded(self) -> bool:
        return self._loaded
    
    def generate(self, prompt: str, max_new_tokens: Optional[int] = None, temperature: Optional[float] = None, **kwargs) -> str:
        if not self._loaded:
            self.load() # Fallback auto-load
        
        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._model.device)
        
        generation_config = {
            "max_new_tokens": max_new_tokens or self.config.max_new_tokens,
            "temperature": temperature or self.config.temperature,
            "top_p": self.config.top_p,
            "top_k": self.config.top_k,
            "repetition_penalty": self.config.repetition_penalty,
            "do_sample": self.config.do_sample,
            "pad_token_id": self._tokenizer.eos_token_id,
        }
        generation_config.update(kwargs)
        
        with torch.no_grad():
            outputs = self._model.generate(**inputs, **generation_config)
        
        generated = outputs[0][inputs["input_ids"].shape[1]:]
        response = self._tokenizer.decode(generated, skip_special_tokens=True)
        return response.strip()
    
    def chat(self, messages: list[dict], max_new_tokens: Optional[int] = None, temperature: Optional[float] = None, **kwargs) -> str:
        if not self._loaded:
            self.load()
        
        prompt = self._tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        return self.generate(prompt, max_new_tokens=max_new_tokens, temperature=temperature, **kwargs)
    
    def stream_chat(self, messages: list[dict], max_new_tokens: Optional[int] = None, temperature: Optional[float] = None, **kwargs) -> Generator[str, None, None]:
        if not self._loaded:
            self.load()
            
        prompt = self._tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._model.device)
        
        streamer = TextIteratorStreamer(self._tokenizer, skip_prompt=True, skip_special_tokens=True)
        
        generation_config = {
            "max_new_tokens": max_new_tokens or self.config.max_new_tokens,
            "temperature": temperature or self.config.temperature,
            "top_p": self.config.top_p,
            "top_k": self.config.top_k,
            "repetition_penalty": self.config.repetition_penalty,
            "do_sample": self.config.do_sample,
            "pad_token_id": self._tokenizer.eos_token_id,
            "streamer": streamer,
        }
        generation_config.update(kwargs)
        
        thread = Thread(target=self._model.generate, kwargs={**inputs, **generation_config})
        thread.start()
        
        for text in streamer:
            yield text
        thread.join()

# Singleton instance
_llm_instance: Optional[QwenLLM] = None

def get_llm(config: Optional[LLMConfig] = None) -> QwenLLM:
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = QwenLLM(config)
    return _llm_instance