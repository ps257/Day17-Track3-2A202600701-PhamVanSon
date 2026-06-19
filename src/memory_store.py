from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


import re

def estimate_tokens(text: str) -> int:
    """Student TODO: implement a simple token estimator.

    Example idea:
    - Strip whitespace
    - Return 0 for empty text
    - Approximate tokens from character count, e.g. len(text) / 4
    """
    if not text:
        return 0
    return len(text.strip()) // 4


@dataclass
class UserProfileStore:
    """Persistent storage for `User.md`.

    Student TODO:
    - Map each user id to one markdown file
    - Support read / write / edit operations
    - Optionally expose helpers like `facts()` or `upsert_fact()`
    """

    root_dir: Path

    def path_for(self, user_id: str) -> Path:
        import string
        valid_chars = f"-_.() {string.ascii_letters}{string.digits}"
        safe_id = ''.join(c for c in user_id if c in valid_chars).replace(' ', '_')
        return self.root_dir / f"{safe_id}.md"

    def read_text(self, user_id: str) -> str:
        path = self.path_for(user_id)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def write_text(self, user_id: str, content: str) -> Path:
        path = self.path_for(user_id)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def edit_text(self, user_id: str, search_text: str, replacement: str) -> bool:
        content = self.read_text(user_id)
        if search_text in content:
            new_content = content.replace(search_text, replacement)
            self.write_text(user_id, new_content)
            return True
        return False

    def file_size(self, user_id: str) -> int:
        path = self.path_for(user_id)
        if path.exists():
            return path.stat().st_size
        return 0


def extract_profile_updates(message: str) -> dict[str, str]:
    """Student TODO: convert raw user text into stable profile facts.

    Example facts you may want to extract:
    - name
    - location
    - profession
    - preferences / response style
    - favorite food / drink

    Pseudocode:
    1. Build a few regex patterns.
    2. Skip obvious question-only turns.
    3. Return only the facts that are confidently present in the message.
    """
    facts = {}
    lower_msg = message.lower()
    
    if "?" in message:
        return facts
        
    name_match = re.search(r'(tôi là|tên là|mình tên là|gọi mình là|mình là|tên mình là) ([\w\s]+)', lower_msg)
    if name_match:
        name = name_match.group(2).strip()
        # Avoid matching words like "người"
        if len(name) > 1 and name != "người":
             facts['name'] = name
        
    loc_match = re.search(r'(đang sống ở|đang ở|sống tại|ở) ([\w\s]+)', lower_msg)
    if loc_match:
        loc = loc_match.group(2).strip()
        if len(loc) > 1 and not loc.startswith("đây"):
             facts['location'] = loc
        
    job_match = re.search(r'(làm nghề|làm|nghề) ([\w\s]+)', lower_msg)
    if job_match:
        job = job_match.group(2).strip()
        if len(job) > 1:
            facts['profession'] = job
            
    # style match for specific keywords
    if "luôn trả lời" in lower_msg or "style" in lower_msg or "cộc lốc" in lower_msg or "ngắn gọn" in lower_msg:
        facts['style'] = "ngắn gọn, cộc lốc" if "cộc lốc" in lower_msg else "custom style"
        if "đừng" in lower_msg and "dài dòng" in lower_msg:
             facts['style'] = "ngắn gọn"

    if "thích" in lower_msg:
        likes_match = re.search(r'thích ([\w\s]+)', lower_msg)
        if likes_match:
            facts['likes'] = likes_match.group(1).strip()
            
    return facts


def summarize_messages(messages: list[dict[str, str]], max_items: int = 6) -> str:
    """Student TODO: create a compact summary of older messages.

    This can be heuristic text concatenation first.
    Later, you can replace it with an LLM-based summary if desired.
    """
    if not messages:
        return ""
    summary_parts = []
    for m in messages[:max_items]:
        role = m.get("role", "user")
        content = m.get("content", "")
        # A very heuristic summary: just take the first 50 chars of the message
        truncated = content if len(content) < 50 else content[:47] + "..."
        summary_parts.append(f"{role}: {truncated}")
    return "Tóm tắt lịch sử cũ:\n" + "\n".join(summary_parts)


@dataclass
class CompactMemoryManager:
    """Student TODO: implement compact memory for long threads.

    Goal:
    - Keep recent messages in full
    - When the thread grows too large, move older content into a summary
    - Track how many compactions happened for benchmarking
    """

    threshold_tokens: int
    keep_messages: int
    state: dict[str, dict[str, object]] = field(default_factory=dict)

    def append(self, thread_id: str, role: str, content: str) -> None:
        if thread_id not in self.state:
            self.state[thread_id] = {"messages": [], "summary": "", "compactions": 0}
            
        thread_state = self.state[thread_id]
        messages = thread_state["messages"]
        messages.append({"role": role, "content": content})
        
        # Calculate tokens
        total_tokens = sum(estimate_tokens(m["content"]) for m in messages)
        
        if total_tokens > self.threshold_tokens and len(messages) > self.keep_messages:
            # Trigger compaction
            old_messages = messages[:-self.keep_messages]
            new_summary_text = summarize_messages(old_messages)
            
            # Append to existing summary if it exists
            if thread_state["summary"]:
                thread_state["summary"] += "\n" + new_summary_text
            else:
                thread_state["summary"] = new_summary_text
                
            thread_state["messages"] = messages[-self.keep_messages:]
            thread_state["compactions"] += 1

    def context(self, thread_id: str) -> dict[str, object]:
        return self.state.get(thread_id, {"messages": [], "summary": "", "compactions": 0})

    def compaction_count(self, thread_id: str) -> int:
        return self.context(thread_id).get("compactions", 0)
