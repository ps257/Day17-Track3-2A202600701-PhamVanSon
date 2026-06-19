from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from config import LabConfig, load_config
from memory_store import estimate_tokens
from model_provider import build_chat_model


@dataclass
class SessionState:
    messages: list[dict[str, str]] = field(default_factory=list)
    token_usage: int = 0
    prompt_tokens_processed: int = 0


class BaselineAgent:
    """Student TODO: implement Agent A.

    Requirements:
    - Within-session memory only
    - No persistent `User.md`
    - Should forget long-term facts across new threads
    """

    def __init__(self, config: LabConfig | None = None, force_offline: bool = False) -> None:
        self.config = config or load_config()
        self.force_offline = force_offline
        self.sessions: dict[str, SessionState] = {}

        # TODO: optionally initialize a real LangChain/LangGraph agent when dependencies exist.
        self.langchain_agent = None

    def reply(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        """Student TODO: return the agent response and token accounting."""
        if self.langchain_agent and not self.force_offline:
            pass # Not implemented for live mode
        return self._reply_offline(thread_id, message)

    def token_usage(self, thread_id: str) -> int:
        session = self.sessions.get(thread_id)
        return session.token_usage if session else 0

    def prompt_token_usage(self, thread_id: str) -> int:
        session = self.sessions.get(thread_id)
        return session.prompt_tokens_processed if session else 0

    def compaction_count(self, thread_id: str) -> int:
        # Baseline has no compact memory.
        return 0

    def _reply_offline(self, thread_id: str, message: str) -> dict[str, Any]:
        """Student TODO: implement a simple offline behavior."""
        if thread_id not in self.sessions:
            self.sessions[thread_id] = SessionState()
        
        session = self.sessions[thread_id]
        
        context_tokens = sum(estimate_tokens(m["content"]) for m in session.messages)
        user_msg_tokens = estimate_tokens(message)
        session.prompt_tokens_processed += context_tokens + user_msg_tokens
        
        session.messages.append({"role": "user", "content": message})
        
        response = "Xin chào! Tôi có thể giúp gì cho bạn?"
        lower_msg = message.lower()
        
        if "tên gì" in lower_msg or "tên của mình" in lower_msg or "tên tớ" in lower_msg or "mình là ai" in lower_msg:
            found = False
            for m in reversed(session.messages[:-1]): # exclude current message
                if m["role"] == "user":
                    import re
                    match = re.search(r'(tôi là|tên là|mình tên là|tên mình là) ([\w\s]+)', m["content"].lower())
                    if match:
                        name = match.group(2).title().strip()
                        if name.lower() != "người":
                            response = f"Bạn tên là {name}."
                            found = True
                            break
            if not found:
                response = "Tôi không biết tên bạn."
        elif "nghề gì" in lower_msg or "làm nghề" in lower_msg:
            found = False
            for m in reversed(session.messages[:-1]):
                if m["role"] == "user":
                    import re
                    match = re.search(r'(làm nghề|làm|nghề) ([\w\s]+)', m["content"].lower())
                    if match:
                        response = f"Bạn làm nghề {match.group(2).strip()}."
                        found = True
                        break
            if not found:
                response = "Tôi không biết bạn làm nghề gì."
        elif "ở đâu" in lower_msg or "sống ở đâu" in lower_msg:
            found = False
            for m in reversed(session.messages[:-1]):
                if m["role"] == "user":
                    import re
                    match = re.search(r'(đang sống ở|đang ở|sống tại|ở) ([\w\s]+)', m["content"].lower())
                    if match:
                        loc = match.group(2).strip()
                        if not loc.startswith("đây"):
                            response = f"Bạn sống ở {loc}."
                            found = True
                            break
            if not found:
                response = "Tôi không biết bạn sống ở đâu."
        elif "thích gì" in lower_msg or "sở thích" in lower_msg:
            found = False
            for m in reversed(session.messages[:-1]):
                if m["role"] == "user":
                    import re
                    match = re.search(r'thích ([\w\s]+)', m["content"].lower())
                    if match:
                        response = f"Bạn thích {match.group(1).strip()}."
                        found = True
                        break
            if not found:
                response = "Tôi không biết bạn thích gì."
        elif "như thế nào" in lower_msg or "style" in lower_msg:
            response = "Tôi không nhớ."
        else:
            response = "Đã nhận: " + message
            
        session.messages.append({"role": "assistant", "content": response})
        
        reply_tokens = estimate_tokens(response)
        session.token_usage += reply_tokens
        
        return {
            "role": "assistant",
            "content": response
        }

    def _maybe_build_langchain_agent(self):
        """Student TODO: optionally wire `create_agent` + `InMemorySaver` here."""
        pass
