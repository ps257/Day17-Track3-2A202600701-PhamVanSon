from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config import LabConfig, load_config
from memory_store import CompactMemoryManager, UserProfileStore, estimate_tokens, extract_profile_updates
from model_provider import build_chat_model


@dataclass
class AgentContext:
    user_id: str
    memory_path: str


class AdvancedAgent:
    """Student TODO: implement Agent B / Advanced Agent.

    Required memory layers:
    1. within-session memory
    2. persistent `User.md`
    3. compact memory for long threads
    """

    def __init__(self, config: LabConfig | None = None, force_offline: bool = False) -> None:
        self.config = config or load_config()
        self.force_offline = force_offline
        self.profile_store = UserProfileStore(self.config.state_dir / "profiles")
        self.compact_memory = CompactMemoryManager(
            threshold_tokens=self.config.compact_threshold_tokens,
            keep_messages=self.config.compact_keep_messages,
        )
        self.thread_tokens: dict[str, int] = {}
        self.thread_prompt_tokens: dict[str, int] = {}

        # TODO: optionally initialize a real LangChain/LangGraph agent.
        self.langchain_agent = None

    def reply(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        """Student TODO: route between offline mode and live mode."""
        if self.langchain_agent and not self.force_offline:
            pass
        return self._reply_offline(user_id, thread_id, message)

    def token_usage(self, thread_id: str) -> int:
        return self.thread_tokens.get(thread_id, 0)

    def prompt_token_usage(self, thread_id: str) -> int:
        return self.thread_prompt_tokens.get(thread_id, 0)

    def memory_file_size(self, user_id: str) -> int:
        return self.profile_store.file_size(user_id)

    def compaction_count(self, thread_id: str) -> int:
        return self.compact_memory.compaction_count(thread_id)

    def _reply_offline(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        """Student TODO: implement the deterministic advanced path."""
        # 1. Extract facts and update User.md
        facts = extract_profile_updates(message)
        if facts:
            current_profile = self.profile_store.read_text(user_id)
            for k, v in facts.items():
                fact_line = f"- {k}: {v}"
                if fact_line not in current_profile:
                    import re
                    pattern = rf"- {k}: .*"
                    if re.search(pattern, current_profile):
                        current_profile = re.sub(pattern, fact_line, current_profile)
                    else:
                        current_profile += f"\n{fact_line}" if current_profile else fact_line
            self.profile_store.write_text(user_id, current_profile.strip())
            
        # 2. Append to compact memory (user)
        self.compact_memory.append(thread_id, "user", message)
        
        # 3. Estimate prompt context load
        context_tokens = self._estimate_prompt_context_tokens(user_id, thread_id)
        
        if thread_id not in self.thread_prompt_tokens:
            self.thread_prompt_tokens[thread_id] = 0
            self.thread_tokens[thread_id] = 0
            
        self.thread_prompt_tokens[thread_id] += context_tokens
        
        # 4. Generate response
        response = self._offline_response(user_id, thread_id, message)
        
        # 5. Append assistant reply to compact memory
        self.compact_memory.append(thread_id, "assistant", response)
        
        # 6. Update token counters
        reply_tokens = estimate_tokens(response)
        self.thread_tokens[thread_id] += reply_tokens
        
        return {
            "role": "assistant",
            "content": response
        }

    def _estimate_prompt_context_tokens(self, user_id: str, thread_id: str) -> int:
        """Student TODO: estimate the context carried into one turn."""
        tokens = 0
        profile = self.profile_store.read_text(user_id)
        tokens += estimate_tokens(profile)
        
        context = self.compact_memory.context(thread_id)
        tokens += estimate_tokens(context.get("summary", ""))
        
        for m in context.get("messages", []):
            tokens += estimate_tokens(m["content"])
            
        return tokens

    def _offline_response(self, user_id: str, thread_id: str, message: str) -> str:
        """Student TODO: return a deterministic answer using persisted memory."""
        lower_msg = message.lower()
        profile = self.profile_store.read_text(user_id)
        
        profile_dict = {}
        for line in profile.split("\n"):
            if line.startswith("- "):
                parts = line[2:].split(":", 1)
                if len(parts) == 2:
                    profile_dict[parts[0].strip()] = parts[1].strip()
        
        if "tên gì" in lower_msg or "tên của mình" in lower_msg or "tên tớ" in lower_msg or "mình là ai" in lower_msg:
            name = profile_dict.get("name")
            if name:
                return f"Bạn tên là {name.title()}."
            return "Tôi không biết tên bạn."
        elif "nghề gì" in lower_msg or "làm nghề" in lower_msg:
            job = profile_dict.get("profession")
            if job:
                return f"Bạn làm nghề {job}."
            return "Tôi không biết bạn làm nghề gì."
        elif "ở đâu" in lower_msg or "sống ở đâu" in lower_msg:
            loc = profile_dict.get("location")
            if loc:
                return f"Bạn sống ở {loc}."
            return "Tôi không biết bạn sống ở đâu."
        elif "thích gì" in lower_msg or "sở thích" in lower_msg:
            likes = profile_dict.get("likes")
            if likes:
                return f"Bạn thích {likes}."
            return "Tôi không biết bạn thích gì."
        elif "như thế nào" in lower_msg or "style" in lower_msg:
            style = profile_dict.get("style")
            if style:
                return f"Bạn thích style {style}."
            return "Tôi không nhớ style của bạn."
            
        return "Đã nhận (Advanced): " + message

    def _maybe_build_langchain_agent(self):
        """Student TODO: wire a live agent with tools and compact middleware."""
        pass
