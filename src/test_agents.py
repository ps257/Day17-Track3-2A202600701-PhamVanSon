from __future__ import annotations

from pathlib import Path

from agent_advanced import AdvancedAgent
from agent_baseline import BaselineAgent
from config import load_config


def make_config(tmp_path: Path):
    """Student TODO: build an isolated config for tests."""
    config = load_config()
    config.state_dir = tmp_path / "state"
    config.compact_threshold_tokens = 10
    config.compact_keep_messages = 2
    return config


def test_user_markdown_read_write_edit(tmp_path: Path) -> None:
    """Student TODO: verify `User.md` can be created, updated, and edited."""
    from memory_store import UserProfileStore
    store = UserProfileStore(tmp_path)
    
    user_id = "test_user"
    assert store.read_text(user_id) == ""
    
    store.write_text(user_id, "- name: John")
    assert store.read_text(user_id) == "- name: John"
    
    edited = store.edit_text(user_id, "John", "Doe")
    assert edited is True
    assert store.read_text(user_id) == "- name: Doe"
    
    assert store.file_size(user_id) > 0


def test_compact_trigger(tmp_path: Path) -> None:
    """Student TODO: verify long threads trigger compaction."""
    config = make_config(tmp_path)
    agent = AdvancedAgent(config, force_offline=True)
    
    for i in range(5):
        agent.reply("user1", "thread1", f"Hello world this is a test message {i} " * 5)
        
    assert agent.compaction_count("thread1") > 0


def test_cross_session_recall(tmp_path: Path) -> None:
    """Student TODO: verify advanced remembers across sessions and baseline does not."""
    config = make_config(tmp_path)
    advanced = AdvancedAgent(config, force_offline=True)
    baseline = BaselineAgent(config, force_offline=True)
    
    advanced.reply("user1", "thread1", "Tôi tên là Sơn")
    baseline.reply("user1", "thread1", "Tôi tên là Sơn")
    
    adv_reply = advanced.reply("user1", "thread2", "Mình tên gì?")
    base_reply = baseline.reply("user1", "thread2", "Mình tên gì?")
    
    assert "Sơn" in adv_reply["content"]
    assert "Sơn" not in base_reply["content"] or "không biết" in base_reply["content"].lower()


def test_compact_reduces_prompt_load_on_long_thread(tmp_path: Path) -> None:
    """Student TODO: compare prompt load of baseline vs advanced on a long thread."""
    config = make_config(tmp_path)
    advanced = AdvancedAgent(config, force_offline=True)
    baseline = BaselineAgent(config, force_offline=True)
    
    for i in range(10):
        msg = "This is a very long message that should trigger compaction for sure. " * 10
        advanced.reply("user1", "thread1", msg)
        baseline.reply("user1", "thread1", msg)
        
    adv_prompt = advanced.prompt_token_usage("thread1")
    base_prompt = baseline.prompt_token_usage("thread1")
    
    assert adv_prompt < base_prompt
