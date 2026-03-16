"""
L5: User Profile — адаптивный профиль пользователя.
"""
import json, os, logging
from typing import Dict, Optional
from .config import MemoryConfig

logger = logging.getLogger("memory.profile")


class UserProfile:
    def __init__(self, user_id: str):
        self._user_id = user_id
        self._data: Dict = {
            "user_id": user_id,
            "chat_count": 0,
            "facts": [],
            "preferences": {},
            "expertise_level": "unknown"
        }
        self._load()

    def _path(self) -> str:
        os.makedirs(MemoryConfig.PROFILES_DIR, exist_ok=True)
        safe = self._user_id.replace("/", "_").replace("\\", "_")[:50]
        return os.path.join(MemoryConfig.PROFILES_DIR, f"{safe}.json")

    def _load(self):
        try:
            p = self._path()
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
        except:
            pass

    def _save(self):
        try:
            with open(self._path(), "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"UserProfile save: {e}")

    def increment_chats(self):
        self._data["chat_count"] = self._data.get("chat_count", 0) + 1
        self._save()

    def get_prompt_context(self) -> str:
        facts = self._data.get("facts", [])
        prefs = self._data.get("preferences", {})
        if not facts and not prefs:
            return ""
        parts = ["ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ:"]
        if facts:
            parts.append("  Факты: " + "; ".join(facts[:5]))
        if prefs:
            for k, v in list(prefs.items())[:3]:
                parts.append(f"  {k}: {v}")
        return "\n".join(parts)

    def extract_from_chat(self, user_msg: str, assistant_resp: str, call_llm):
        if self._data.get("chat_count", 0) % MemoryConfig.PROFILE_EXTRACT_AFTER_N_CHATS != 0:
            return
        try:
            resp = call_llm([
                {"role": "system", "content": "Извлеки факты о пользователе. JSON: {\"facts\":[\"...\"],\"preferences\":{\"язык\":\"русский\"}}. Только конкретные факты. Без markdown."},
                {"role": "user", "content": f"User: {user_msg[:500]}\nAgent: {assistant_resp[:500]}"}
            ])
            resp = resp.strip()
            if resp.startswith("```"):
                resp = resp.split("\n", 1)[1].rsplit("```", 1)[0]
            data = json.loads(resp)
            existing_facts = set(self._data.get("facts", []))
            for f in data.get("facts", []):
                if f not in existing_facts:
                    existing_facts.add(f)
            self._data["facts"] = list(existing_facts)[:MemoryConfig.PROFILE_MAX_FACTS]
            self._data["preferences"].update(data.get("preferences", {}))
            self._save()
        except:
            pass
