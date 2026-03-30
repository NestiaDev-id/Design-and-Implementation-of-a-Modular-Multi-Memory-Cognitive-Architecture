"""
Cognitive Memory Agent - Main Application

A conversational AI agent with cognitive memory capabilities.
Uses Qwen as the LLM backbone with STM (Short-Term Memory) and LTM (Long-Term Memory).

Usage:
    python main.py
    python main.py --config config.json
    python main.py --debug
"""

import argparse
import sys
import time  # Ditambahkan untuk UX loading
from pathlib import Path
from typing import Optional

# Pastikan folder modul bisa terbaca (opsional, tergantung struktur folder)
sys.path.append(str(Path(__file__).parent))

from core.config import Config, default_config
from core.llm import QwenLLM, get_llm
from memory.memory_manager import MemoryManager
from agent.decision_rules import DecisionLayer, DecisionType
from agent.tool_router import ToolRouter
from context.prompt_generate import ContextBuilder


class CognitiveAgent:
    """
    Main agent class that orchestrates all components.
    
    Flow:
    1. User Input -> Input Handler
    2. STM Update
    3. Decision Layer -> Tool/Memory/Direct
    4. Memory Manager (STM + LTM)
    5. Context Builder
    6. LLM Generation
    7. Output Handler -> User Output
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize Cognitive Agent.
        
        Args:
            config: System configuration
        """
        self.config = config or default_config
        self._debug = self.config.debug
        
        # Initialize LLM
        # Proses ini memakan waktu paling lama (loading weights ke VRAM/RAM)
        self.llm = QwenLLM(self.config.llm)
        
        if self._debug:
            print("[DEBUG] Forcing model load in CognitiveAgent init...")
        self.llm.load()
        
        # Initialize Memory Manager
        self.memory_manager = MemoryManager(
            storage_path=self.config.data_path,
            consolidate_after_turns=self.config.memory.consolidate_after_turns,
        )
        
        # Initialize Tool Router
        self.tool_router = ToolRouter(
            timeout=self.config.agent.tool_timeout,
            memory_manager=self.memory_manager,
        )
        
        # Initialize Decision Layer
        # self.decision_layer = DecisionLayer(tool_router=self.tool_router)
        self.decision_layer = DecisionLayer(
            tool_router=self.tool_router,
            llm=self.llm 
        )
        
        # Initialize Context Builder
        self.context_builder = ContextBuilder(
            max_context_tokens=self.config.memory.stm_max_tokens,
            include_tools=self.config.agent.enable_tools,
        )
        
        # Set system prompt
        self.memory_manager.set_system_prompt(
            self._build_system_prompt()
        )
        
    def warmup(self):
        """
        Melakukan 'pemanasan' model.
        Menjalankan inferensi dummy agar CUDA kernels terinisialisasi
        dan model siap merespons user pertama kali tanpa delay.
        """
        if self._debug:
            print(" [DEBUG] Warming up model parameters...")
            
        # Pesan dummy yang sangat pendek
        dummy_msg = [{"role": "user", "content": "ping"}]
        
        try:
            # Generate 1 token saja cukup untuk memicu loading
            self.llm.chat(messages=dummy_msg, max_new_tokens=1)
        except Exception as e:
            # Error saat warmup tidak boleh mematikan aplikasi, cukup log saja
            if self._debug:
                print(f" [DEBUG] Warmup warning: {e}")

    def _build_system_prompt(self) -> str:
        """Build initial system prompt."""
        tools_desc = ""
        if self.config.agent.enable_tools:
            tools_desc = self.tool_router.get_tools_prompt()
        
        return f"""You are a helpful AI assistant with cognitive memory capabilities.

{tools_desc}

Guidelines:
- Be helpful, accurate, and concise
- If you need to calculate something, use the calculator tool
- If you need current time/date, use the datetime tool
- Remember important information shared by the user
- You can use Bahasa Indonesia or English based on user's language
"""
    
    def process_input(self, user_input: str) -> str:
        """
        Process user input and generate response (Non-streaming).
        """
        # 1. Input Handler - Add to STM
        self.memory_manager.add_user_input(user_input)
        
        if self._debug:
            print(f"[DEBUG] User input: {user_input}")
        
        # 2. Decision Layer - Analyze input
        decision = self.decision_layer.analyze(user_input)
        
        if self._debug:
            print(f"[DEBUG] Decision: {decision.decision_type.value}")
        
        # 3. Handle pre-LLM decisions
        tool_result = None
        
        if decision.decision_type == DecisionType.USE_TOOL and decision.tool_call:
            # Execute tool before LLM
            result = self.tool_router.execute(decision.tool_call)
            tool_result = self.tool_router.format_tool_result(
                decision.tool_call.tool_name, result
            )
            self.memory_manager.add_tool_result(
                tool_result, decision.tool_call.tool_name
            )
            
            if self._debug:
                print(f"[DEBUG] Tool result: {tool_result}")
        
        elif decision.decision_type == DecisionType.STORE_MEMORY and decision.memory_content:
            # Store memory
            self.memory_manager.store_memory(
                content=decision.memory_content,
                memory_type="fact",
                importance=0.8,
            )
            
            if self._debug:
                print(f"[DEBUG] Stored memory: {decision.memory_content}")
        
        # 4. Get context from Memory Manager
        include_ltm = (
            decision.decision_type == DecisionType.RETRIEVE_MEMORY or
            self.decision_layer.should_retrieve_memory(user_input)
        )
        
        memory_context = self.memory_manager.get_context(
            include_ltm=include_ltm,
            ltm_query=decision.memory_query,
        )
        
        if self._debug and memory_context.has_relevant_memories():
            print(f"[DEBUG] LTM memories: {len(memory_context.ltm_memories)}")
        
        # 5. Build context for LLM
        tools_description = self.tool_router.get_tools_prompt() if self.config.agent.enable_tools else None
        
        built_context = self.context_builder.build(
            stm_messages=memory_context.stm_messages,
            ltm_memories=memory_context.ltm_memories,
            tools_description=tools_description,
        )
        
        if self._debug:
            print(f"[DEBUG] Context tokens: ~{built_context.token_estimate}")
        
        # 6. Generate response
        response = self.llm.chat(
            messages=built_context.messages,
            max_new_tokens=self.config.llm.max_new_tokens,
            temperature=self.config.llm.temperature,
        )
        
        # 7. Check for tool calls in response
        llm_decision = self.decision_layer.analyze_llm_output(response)
        
        iteration = 0
        while (
            llm_decision.decision_type == DecisionType.USE_TOOL and 
            llm_decision.tool_call and
            iteration < self.config.agent.max_tool_iterations
        ):
            if self._debug:
                print(f"[DEBUG] LLM tool call: {llm_decision.tool_call.tool_name}")
            
            # Execute tool
            result = self.tool_router.execute(llm_decision.tool_call)
            tool_result = self.tool_router.format_tool_result(
                llm_decision.tool_call.tool_name, result
            )
            
            # Add to STM
            self.memory_manager.add_tool_result(
                tool_result, llm_decision.tool_call.tool_name
            )
            
            # Get updated context
            memory_context = self.memory_manager.get_context(include_ltm=False)
            built_context = self.context_builder.build(
                stm_messages=memory_context.stm_messages,
                tools_description=tools_description,
            )
            
            # Generate new response
            response = self.llm.chat(
                messages=built_context.messages,
                max_new_tokens=self.config.llm.max_new_tokens,
            )
            
            # Check again for tool calls
            llm_decision = self.decision_layer.analyze_llm_output(response)
            iteration += 1
        
        # 8. Clean response (remove tool call syntax if present)
        clean_response = self._clean_response(response)
        
        # 9. Add response to STM
        self.memory_manager.add_assistant_response(clean_response)
        
        # 10. Check if we should store something in LTM
        if self.decision_layer.should_store_memory(user_input, clean_response):
            # Auto-extract and store important info (handled by memory manager logic ideally)
            pass
        
        return clean_response
    
    def _clean_response(self, response: str) -> str:
        """Clean LLM response by removing tool call syntax."""
        import re
        
        # Remove [TOOL: ...] patterns
        cleaned = re.sub(r'\[TOOL:\s*\w+\([^)]*\)\s*\]', '', response)
        
        # Remove empty lines created by removal
        cleaned = "\n".join(line for line in cleaned.split("\n") if line.strip())
        
        return cleaned.strip()
    
    def stream_response(self, user_input: str):
        """
        Stream response for real-time output.
        
        Yields:
            Response chunks
        """
        # Add to STM
        self.memory_manager.add_user_input(user_input)
        
        # Get context
        memory_context = self.memory_manager.get_context(
            include_ltm=self.decision_layer.should_retrieve_memory(user_input)
        )
        
        tools_description = self.tool_router.get_tools_prompt() if self.config.agent.enable_tools else None
        
        built_context = self.context_builder.build(
            stm_messages=memory_context.stm_messages,
            ltm_memories=memory_context.ltm_memories,
            tools_description=tools_description,
        )
        
        # Stream response
        full_response = ""
        # Karena sudah di-warmup di awal, iterasi pertama loop ini akan cepat
        for chunk in self.llm.stream_chat(messages=built_context.messages):
            full_response += chunk
            yield chunk
        
        # Add to STM
        clean_response = self._clean_response(full_response)
        self.memory_manager.add_assistant_response(clean_response)
    
    def get_stats(self) -> dict:
        """Get agent statistics."""
        return {
            "memory": self.memory_manager.get_stats(),
            "tools_registered": len(self.tool_router.registry),
            "llm_loaded": self.llm.is_loaded,
        }
    
    def clear_conversation(self) -> None:
        """Clear STM (conversation history)."""
        self.memory_manager.clear_stm()
        print("Conversation cleared.")
    
    def clear_all_memory(self) -> None:
        """Clear all memory (STM + LTM)."""
        self.memory_manager.clear_all()
        print("All memory cleared.")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Cognitive Memory Agent")
    parser.add_argument("--config", type=str, help="Path to config JSON file")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--no-stream", action="store_true", help="Disable streaming output")
    args = parser.parse_args()
    
    # Load configuration
    if args.config:
        config = Config.from_json(args.config)
    else:
        config = Config()
    
    if args.debug:
        config.debug = True
    
    print("\n" + "=" * 60)
    print("  COGNITIVE MEMORY AGENT")
    print("  Model Architecture: Qwen 2.5")
    print("=" * 60 + "\n")
    
    # --- PROSES LOADING DENGAN VISUAL FEEDBACK ---
    agent = None
    try:
        # Step 1: Init Components
        print(" [1/3] Initializing System Components...", end=" ", flush=True)
        # Load object agent (termasuk load model ke RAM)
        agent = CognitiveAgent(config)
        print("DONE.")
        
        # Step 2: Load Tools (simulasi visual, biasanya cepat)
        print(" [2/3] Registering Tools & Decision Rules...", end=" ", flush=True)
        time.sleep(0.3) 
        print("DONE.")
        
        # Step 3: Warmup Model
        print(" [3/3] Warming up Inference Engine (CUDA)...", end=" ", flush=True)
        # Panggil method warmup yang baru dibuat
        agent.warmup()
        print("DONE.")
        
    except Exception as e:
        print(f"\n\n[FATAL ERROR] Initialization failed: {e}")
        if config.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    print("\n" + "-" * 60)
    print(" System Ready! Type your message.")
    print(" Commands: 'clear' to reset chat, 'quit' to exit, 'stats' for info.")
    print("-" * 60 + "\n")
    
    # Main loop
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            # Handle special commands
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break
            
            if user_input.lower() == "clear":
                agent.clear_conversation()
                continue
            
            if user_input.lower() == "clear all":
                agent.clear_all_memory()
                continue
            
            if user_input.lower() == "stats":
                stats = agent.get_stats()
                print(f"\nStats: {stats}\n")
                continue
            
            # Process input
            print("Assistant: ", end="", flush=True)
            
            if args.no_stream:
                response = agent.process_input(user_input)
                print(response)
            else:
                try:
                    # Model sudah panas, streaming harusnya lancar
                    for chunk in agent.stream_response(user_input):
                        print(chunk, end="", flush=True)
                    print()
                except Exception as e:
                    # Fallback jika streaming error
                    if config.debug:
                        print(f" [Stream Error: {e}] ", end="")
                    response = agent.process_input(user_input)
                    print(response)
            
            print()
            
        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            if config.debug:
                import traceback
                traceback.print_exc()


if __name__ == "__main__":
    main()