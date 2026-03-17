#!/usr/bin/env python3
"""
PATCH A3 — Добавляет маршрутизацию модели в direct_chat() и send_message()
"""

ROUTING_CODE = '''
        # === МАРШРУТИЗАЦИЯ МОДЕЛИ ===
        model_override = None
        extra_prompt = ""
        try:
            from intent_clarifier import clarify
            intent_result = clarify(user_message)
            primary = intent_result.get("primary_model", "")

            if primary == "gemini":
                model_override = "google/gemini-2.5-pro"
                extra_prompt = """
РЕЖИМ ДИЗАЙНЕРА: Ты создаёшь красивые веб-страницы.
Используй Google Fonts (Inter, Montserrat), градиенты, анимации.
ОБЯЗАТЕЛЬНО сохраняй HTML в файл через file_write или create_artifact.
НЕ ПИШИ код в чат — создавай файл.
"""
            elif primary == "sonnet":
                model_override = "anthropic/claude-sonnet-4.6"
        except Exception:
            pass
'''

with open('/var/www/orion/backend/app.py', 'r', encoding='utf-8') as f:
    content = f.read()
    lines = content.split('\n')

print(f"Total lines: {len(lines)}")

# ─── ПАТЧ 1: direct_chat() — перед loop = AgentLoop( (строка ~2024) ───
# Ищем внутри generate() в direct_chat: "loop = AgentLoop("
# Контекст: "        else:\n                loop = AgentLoop("
# Точнее — ищем блок "if multi_agent:" внутри generate() в direct_chat

TARGET_DIRECT = '            if multi_agent:'
ROUTING_DIRECT = ROUTING_CODE.replace('\n        ', '\n        ')  # 8 пробелов (внутри generate())

# Найдём строку с "if multi_agent:" внутри direct_chat (после строки 2005)
direct_chat_start = None
for i, line in enumerate(lines):
    if 'def direct_chat' in line:
        direct_chat_start = i
        break

print(f"direct_chat starts at line: {direct_chat_start + 1}")

# Найдём "if multi_agent:" после direct_chat_start
target_line_direct = None
for i in range(direct_chat_start, len(lines)):
    if '            if multi_agent:' in lines[i]:
        target_line_direct = i
        break

print(f"'if multi_agent:' in direct_chat at line: {target_line_direct + 1 if target_line_direct else 'NOT FOUND'}")

# Проверим что уже не пропатчено
already_patched_direct = False
if target_line_direct:
    # Смотрим 20 строк перед
    context_before = '\n'.join(lines[max(0, target_line_direct-20):target_line_direct])
    if 'МАРШРУТИЗАЦИЯ МОДЕЛИ' in context_before:
        already_patched_direct = True
        print("direct_chat: ALREADY PATCHED, skipping")

if target_line_direct and not already_patched_direct:
    # Вставляем маршрутизацию перед "if multi_agent:"
    routing_lines = ROUTING_CODE.split('\n')
    # Убираем первую пустую строку
    if routing_lines[0] == '':
        routing_lines = routing_lines[1:]
    lines = lines[:target_line_direct] + routing_lines + lines[target_line_direct:]
    print(f"PATCH 1 applied: inserted {len(routing_lines)} lines before line {target_line_direct + 1}")

# ─── Обновляем AgentLoop в direct_chat — добавляем model_override ───
# После вставки строки сдвинулись, пересчитываем
content_after_patch1 = '\n'.join(lines)

# Найдём AgentLoop в direct_chat (не в send_message)
# В direct_chat: "loop = AgentLoop(\n                    model=model, api_key=api_key,"
# Нужно добавить model_override и system_prompt_override

# Ищем паттерн в direct_chat
direct_agent_old = '''                loop = AgentLoop(
                    model=model, api_key=api_key,
                    orion_mode=orion_mode, session_id=chat_id
                )'''

direct_agent_new = '''                loop = AgentLoop(
                    model=model_override if model_override else model, api_key=api_key,
                    orion_mode=orion_mode, session_id=chat_id,
                    model_override=model_override,
                    system_prompt_override=extra_prompt if extra_prompt else None,
                )'''

if direct_agent_old in content_after_patch1:
    content_after_patch1 = content_after_patch1.replace(direct_agent_old, direct_agent_new, 1)
    print("PATCH 1b applied: AgentLoop in direct_chat updated with model_override")
else:
    print("WARNING: direct_chat AgentLoop pattern not found exactly, trying alternative...")
    # Попробуем найти и показать контекст
    idx = content_after_patch1.find('loop = AgentLoop(')
    if idx >= 0:
        print(f"Found 'loop = AgentLoop(' at char {idx}")
        print(repr(content_after_patch1[idx:idx+200]))

lines = content_after_patch1.split('\n')

# ─── ПАТЧ 2: send_message() — перед agent = AgentLoop( в is_lite_agent ───
# В send_message есть несколько AgentLoop. Нам нужен первый — в is_lite_agent блоке
# Контекст: "            agent = AgentLoop(\n                model=agent_model,\n                api_key=OPENROUTER_API_KEY,\n                api_url=OPENROUTER_BASE_URL,\n                ssh_credentials={},  # No SSH needed"

send_message_start = None
for i, line in enumerate(lines):
    if 'def send_message' in line:
        send_message_start = i
        break

print(f"send_message starts at line: {send_message_start + 1}")

# Найдём "if is_lite_agent:" внутри generate() в send_message
target_line_send = None
for i in range(send_message_start, len(lines)):
    if '        if is_lite_agent:' in lines[i]:
        target_line_send = i
        break

print(f"'if is_lite_agent:' in send_message at line: {target_line_send + 1 if target_line_send else 'NOT FOUND'}")

# Проверим что уже не пропатчено
already_patched_send = False
if target_line_send:
    context_before = '\n'.join(lines[max(0, target_line_send-20):target_line_send])
    if 'МАРШРУТИЗАЦИЯ МОДЕЛИ' in context_before:
        already_patched_send = True
        print("send_message: ALREADY PATCHED, skipping")

if target_line_send and not already_patched_send:
    routing_lines_send = ROUTING_CODE.split('\n')
    if routing_lines_send[0] == '':
        routing_lines_send = routing_lines_send[1:]
    lines = lines[:target_line_send] + routing_lines_send + lines[target_line_send:]
    print(f"PATCH 2 applied: inserted {len(routing_lines_send)} lines before line {target_line_send + 1}")

# ─── Обновляем AgentLoop в send_message (is_lite_agent блок) ───
content_after_patch2 = '\n'.join(lines)

send_agent_old = '''            agent = AgentLoop(
                model=agent_model,
                api_key=OPENROUTER_API_KEY,
                api_url=OPENROUTER_BASE_URL,
                ssh_credentials={},  # No SSH needed for file generation
                user_id=request.user_id  # BUG-5 FIX
            )'''

send_agent_new = '''            agent = AgentLoop(
                model=model_override if model_override else agent_model,
                api_key=OPENROUTER_API_KEY,
                api_url=OPENROUTER_BASE_URL,
                ssh_credentials={},  # No SSH needed for file generation
                user_id=request.user_id,  # BUG-5 FIX
                model_override=model_override,
                system_prompt_override=extra_prompt if extra_prompt else None,
            )'''

if send_agent_old in content_after_patch2:
    content_after_patch2 = content_after_patch2.replace(send_agent_old, send_agent_new, 1)
    print("PATCH 2b applied: AgentLoop in send_message (lite_agent) updated with model_override")
else:
    print("WARNING: send_message lite_agent AgentLoop pattern not found exactly")
    idx = content_after_patch2.find('ssh_credentials={},  # No SSH needed')
    if idx >= 0:
        print(repr(content_after_patch2[idx-200:idx+200]))

# ─── Также обновляем одиночный AgentLoop в send_message (is_agent_task) ───
send_agent2_old = '''                agent = AgentLoop(
                    model=agent_model,
                    api_key=OPENROUTER_API_KEY,
                    api_url=OPENROUTER_BASE_URL,
                    ssh_credentials=ssh_credentials,
                    user_id=request.user_id  # BUG-5 FIX
                )
                agent._chat_id = chat_id  # BUG-5 FIX: передаём chat_id'''

send_agent2_new = '''                agent = AgentLoop(
                    model=model_override if model_override else agent_model,
                    api_key=OPENROUTER_API_KEY,
                    api_url=OPENROUTER_BASE_URL,
                    ssh_credentials=ssh_credentials,
                    user_id=request.user_id,  # BUG-5 FIX
                    model_override=model_override,
                    system_prompt_override=extra_prompt if extra_prompt else None,
                )
                agent._chat_id = chat_id  # BUG-5 FIX: передаём chat_id'''

if send_agent2_old in content_after_patch2:
    content_after_patch2 = content_after_patch2.replace(send_agent2_old, send_agent2_new, 1)
    print("PATCH 2c applied: AgentLoop in send_message (agent_task) updated with model_override")
else:
    print("INFO: send_message agent_task AgentLoop pattern not found (may be ok)")

# ─── Сохраняем ───
with open('/var/www/orion/backend/app.py', 'w', encoding='utf-8') as f:
    f.write(content_after_patch2)

print(f"\nDONE. New file size: {len(content_after_patch2.split(chr(10)))} lines")
print("Patch A3 applied successfully!")
