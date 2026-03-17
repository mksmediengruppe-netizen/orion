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
        logger.info(f"[MEMORY] UserProfile loaded for user_id={user_id!r}, facts={len(self._data.get('facts',[]))}")

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
        except Exception as e:
            logger.warning(f"[MEMORY] UserProfile load error: {e}")

    def _save(self):
        try:
            with open(self._path(), "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            logger.info(f"[MEMORY] UserProfile saved: user={self._user_id!r}, facts={self._data.get('facts',[])} prefs={self._data.get('preferences',{})}")
        except Exception as e:
            logger.error(f"[MEMORY] UserProfile save error: {e}")

    def increment_chats(self):
        self._data["chat_count"] = self._data.get("chat_count", 0) + 1
        self._save()

    def get_prompt_context(self) -> str:
        facts = self._data.get("facts", [])
        prefs = self._data.get("preferences", {})
        logger.info(f"[MEMORY] get_prompt_context: user={self._user_id!r}, facts={facts}, prefs={prefs}")
        if not facts and not prefs:
            return ""
        parts = ["ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ:"]
        if facts:
            parts.append("  Факты: " + "; ".join(facts[:10]))
        if prefs:
            for k, v in list(prefs.items())[:5]:
                parts.append(f"  {k}: {v}")
        result = "\n".join(parts)
        logger.info(f"[MEMORY] get_prompt_context result: {result[:200]}")
        return result

    def extract_from_chat(self, user_msg: str, assistant_resp: str, call_llm):
        """Извлечь факты о пользователе из диалога и сохранить в профиль."""
        logger.info(f"[MEMORY] extract_from_chat START: user={self._user_id!r}, msg={user_msg[:100]!r}")
        if not call_llm:
            logger.warning("[MEMORY] extract_from_chat: call_llm is None, skipping")
            return
        try:
            prompt_sys = (
                "Ты — экстрактор фактов о пользователе. "
                "Из диалога извлеки конкретные факты о пользователе: имя, профессия, стек технологий, город, предпочтения. "
                "ВАЖНО: каждый факт должен быть ПОЛНЫМ предложением, например: "
                "\"Пользователя зовут Александр\", \"Работает с Python и Docker\", \"Живёт в Москве\". "
                "НЕ пиши просто имя или слово — пиши полный факт. "
                "Верни JSON без markdown: {\"facts\":[\"Пользователя зовут ...\",...],\"preferences\":{\"ключ\":\"значение\"}}. "
                "Если фактов нет — верни {\"facts\":[],\"preferences\":{}}."
            )
            prompt_user = f"Сообщение пользователя: {user_msg[:800]}\nОтвет агента: {assistant_resp[:800]}"
            
            resp = call_llm([
                {"role": "system", "content": prompt_sys},
                {"role": "user", "content": prompt_user}
            ])
            logger.info(f"[MEMORY] extract_from_chat LLM response: {resp!r}")
            
            if not resp or not resp.strip():
                logger.warning("[MEMORY] extract_from_chat: empty LLM response")
                return
            
            resp = resp.strip()
            # Убрать markdown блоки
            if "```" in resp:
                lines = resp.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                resp = "\n".join(lines)
            # Найти JSON
            start = resp.find("{")
            end = resp.rfind("}") + 1
            if start >= 0 and end > start:
                resp = resp[start:end]
            
            data = json.loads(resp)
            new_facts = data.get("facts", [])
            new_prefs = data.get("preferences", {})
            
            logger.info(f"[MEMORY] extract_from_chat parsed: facts={new_facts}, prefs={new_prefs}")
            
            existing_facts = list(self._data.get("facts", []))
            existing_set = set(existing_facts)
            added = 0
            for f in new_facts:
                if f and f not in existing_set:
                    existing_facts.append(f)
                    existing_set.add(f)
                    added += 1
            
            self._data["facts"] = existing_facts[:MemoryConfig.PROFILE_MAX_FACTS]
            self._data["preferences"].update(new_prefs)
            self._save()
            logger.info(f"[MEMORY] extract_from_chat DONE: added {added} new facts, total={len(self._data['facts'])}")
            
        except json.JSONDecodeError as je:
            logger.warning(f"[MEMORY] extract_from_chat JSON parse error: {je}, resp={resp!r}")
        except Exception as e:
            logger.warning(f"[MEMORY] extract_from_chat error: {e}", exc_info=True)
