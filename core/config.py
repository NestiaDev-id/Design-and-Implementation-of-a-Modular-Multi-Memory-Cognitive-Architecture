"""Configuration management for Cognitive Memory System."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import json


@dataclass
class MemoryConfig:
    """Configuration for memory components."""
    
    # STM Settings
    stm_max_turns: int = 10  # Maximum conversation turns to keep
    stm_max_tokens: int = 4096  # Maximum tokens in STM
    
    # LTM Settings
    ltm_storage_path: Path = field(default_factory=lambda: Path("data/ltm"))
    ltm_collection_name: str = "cognitive_memory"
    ltm_top_k: int = 5  # Number of memories to retrieve
    ltm_similarity_threshold: float = 0.7  # Minimum similarity for retrieval
    
    # Consolidation Settings
    consolidate_after_turns: int = 5  # Consolidate STM to LTM every N turns
    

@dataclass
class LLMConfig:
    """Configuration for LLM."""
    
    model_path: str = r"E:\models\qwen\qwen2.5-1.5b-instruct"
    max_new_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    repetition_penalty: float = 1.1
    do_sample: bool = True
    device: str = "cpu"  # cuda or cpu
    torch_dtype: str = "auto"  # auto, float16, bfloat16, float32
    

@dataclass
class AgentConfig:
    """Configuration for agent/decision layer."""
    
    enable_tools: bool = True
    max_tool_iterations: int = 3  # Maximum tool calls per turn
    tool_timeout: float = 30.0  # Timeout for tool execution
    

@dataclass
class Config:
    """Main configuration for the entire system."""
    
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    
    # System Settings
    debug: bool = False
    log_path: Optional[Path] = None
    data_path: Path = field(default_factory=lambda: Path("data"))
    
    def __post_init__(self):
        """Ensure paths exist."""
        self.data_path.mkdir(parents=True, exist_ok=True)
        if self.memory.ltm_storage_path:
            self.memory.ltm_storage_path.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def from_json(cls, path: str | Path) -> "Config":
        """Load configuration from JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        memory_cfg = MemoryConfig(**data.get("memory", {}))
        llm_cfg = LLMConfig(**data.get("llm", {}))
        agent_cfg = AgentConfig(**data.get("agent", {}))
        
        return cls(
            memory=memory_cfg,
            llm=llm_cfg,
            agent=agent_cfg,
            debug=data.get("debug", False),
            log_path=Path(data["log_path"]) if data.get("log_path") else None,
            data_path=Path(data.get("data_path", "data")),
        )
    
    def to_json(self, path: str | Path) -> None:
        """Save configuration to JSON file."""
        data = {
            "memory": {
                "stm_max_turns": self.memory.stm_max_turns,
                "stm_max_tokens": self.memory.stm_max_tokens,
                "ltm_storage_path": str(self.memory.ltm_storage_path),
                "ltm_collection_name": self.memory.ltm_collection_name,
                "ltm_top_k": self.memory.ltm_top_k,
                "ltm_similarity_threshold": self.memory.ltm_similarity_threshold,
                "consolidate_after_turns": self.memory.consolidate_after_turns,
            },
            "llm": {
                "model_path": self.llm.model_path,
                "max_new_tokens": self.llm.max_new_tokens,
                "temperature": self.llm.temperature,
                "top_p": self.llm.top_p,
                "top_k": self.llm.top_k,
                "repetition_penalty": self.llm.repetition_penalty,
                "do_sample": self.llm.do_sample,
                "device": self.llm.device,
                "torch_dtype": self.llm.torch_dtype,
            },
            "agent": {
                "enable_tools": self.agent.enable_tools,
                "max_tool_iterations": self.agent.max_tool_iterations,
                "tool_timeout": self.agent.tool_timeout,
            },
            "debug": self.debug,
            "log_path": str(self.log_path) if self.log_path else None,
            "data_path": str(self.data_path),
        }
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


# Default configuration instance
default_config = Config()
