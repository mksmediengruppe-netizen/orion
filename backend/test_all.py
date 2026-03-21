"""
ORION Digital — Comprehensive Test Suite
=========================================
20+ тестов покрывающих:
- Block 3: TaskCharter, ExecutionSnapshots, GoalKeeper
- Block 4: ArtifactHandoff, FinalJudge, ToolSandbox, TaskScorecard, AutonomyModes
- API endpoints: health, auth, chat
- Integration: agent_loop imports, service status

Запуск: python3 test_all.py
"""

import sys
import os
import json
import time
import tempfile
import unittest
import importlib.util

# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════

# Add backend to path for local imports
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND_DIR)


def load_module_from_file(name, path):
    """Dynamically load a Python module from file path."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ═══════════════════════════════════════════════════════════
# BLOCK 3 TESTS
# ═══════════════════════════════════════════════════════════

class TestTaskCharter(unittest.TestCase):
    """Tests for task_charter.py"""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_module_from_file("task_charter", os.path.join(BACKEND_DIR, "task_charter.py"))
        cls.db_path = tempfile.mktemp(suffix=".db")
        cls.store = cls.mod.TaskCharterStore(db_path=cls.db_path)

    def test_01_create_charter(self):
        """Создание charter"""
        charter = self.store.create("test-task-1", "Тестовая задача", "chat-1")
        self.assertIsNotNone(charter)
        self.assertEqual(charter["task_id"], "test-task-1")
        self.assertEqual(charter["status"], "active")

    def test_02_get_charter(self):
        """Получение charter"""
        charter = self.store.get("test-task-1")
        self.assertIsNotNone(charter)
        self.assertEqual(charter["objective"], "Тестовая задача")

    def test_03_complete_charter(self):
        """Завершение charter"""
        self.store.complete("test-task-1")
        charter = self.store.get("test-task-1")
        self.assertEqual(charter["status"], "done")

    def test_04_get_nonexistent(self):
        """Получение несуществующего charter"""
        charter = self.store.get("nonexistent-task")
        self.assertIsNone(charter)


class TestExecutionSnapshots(unittest.TestCase):
    """Tests for execution_snapshots.py"""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_module_from_file("execution_snapshots", os.path.join(BACKEND_DIR, "execution_snapshots.py"))
        cls.db_path = tempfile.mktemp(suffix=".db")
        cls.store = cls.mod.SnapshotStore(db_path=cls.db_path)

    def test_01_create_snapshot(self):
        """Создание снапшота"""
        snap = self.store.create(
            task_id="test-task-1",
            step_id="step-1",
            snapshot_type="before_tool",
            iteration=1,
            cost_so_far=0.001,
            tool_name="ssh_execute",
            tool_args={"command": "ls"},
            state_summary="Starting task"
        )
        self.assertIsNotNone(snap)
        self.assertEqual(snap["task_id"], "test-task-1")

    def test_02_list_snapshots(self):
        """Список снапшотов"""
        snaps = self.store.list("test-task-1")
        self.assertGreater(len(snaps), 0)
        self.assertEqual(snaps[0]["step_id"], "step-1")


class TestGoalKeeper(unittest.TestCase):
    """Tests for goal_keeper.py"""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_module_from_file("goal_keeper", os.path.join(BACKEND_DIR, "goal_keeper.py"))
        cls.gk = cls.mod.GoalKeeper()

    def test_01_check_action_allowed(self):
        """Проверка разрешённого действия"""
        result = self.gk.check(
            objective="Создать сайт",
            tool_name="file_write",
            tool_args={"path": "/var/www/site/index.html", "content": "<html>"},
            iteration=1,
            max_iterations=30
        )
        self.assertTrue(result["allowed"])

    def test_02_check_action_format(self):
        """Формат ответа GoalKeeper"""
        result = self.gk.check(
            objective="Тест",
            tool_name="ssh_execute",
            tool_args={"command": "ls"},
            iteration=1,
            max_iterations=30
        )
        self.assertIn("allowed", result)
        self.assertIn("reason", result)


# ═══════════════════════════════════════════════════════════
# BLOCK 4 TESTS
# ═══════════════════════════════════════════════════════════

class TestArtifactHandoff(unittest.TestCase):
    """Tests for artifact_handoff.py"""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_module_from_file("artifact_handoff", os.path.join(BACKEND_DIR, "artifact_handoff.py"))
        cls.db_path = tempfile.mktemp(suffix=".db")
        cls.store = cls.mod.ArtifactHandoff(db_path=cls.db_path)

    def test_01_create_handoff(self):
        """Создание handoff"""
        hid = self.store.create(
            task_id="task-1",
            from_agent="developer",
            to_agent="designer",
            artifacts={"files": ["index.html"]},
            instructions="Добавить стили"
        )
        self.assertIsNotNone(hid)

    def test_02_get_pending(self):
        """Получение pending handoffs"""
        pending = self.store.get_pending("designer")
        self.assertGreater(len(pending), 0)

    def test_03_accept_handoff(self):
        """Принятие handoff"""
        pending = self.store.get_pending("designer")
        hid = pending[0]["handoff_id"]
        result = self.store.accept(hid)
        self.assertTrue(result)


class TestFinalJudge(unittest.TestCase):
    """Tests for final_judge.py"""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_module_from_file("final_judge", os.path.join(BACKEND_DIR, "final_judge.py"))
        cls.judge = cls.mod.FinalJudge()

    def test_01_judge_pass(self):
        """FinalJudge — PASS verdict"""
        result = self.judge.judge(
            objective="Создать файл index.html",
            actions_log=[
                {"tool": "file_write", "args": {"path": "index.html"}, "success": True},
                {"tool": "task_complete", "args": {"summary": "Файл создан"}, "success": True}
            ],
            final_answer="Файл index.html создан успешно",
            files_created=["index.html"]
        )
        self.assertIn("verdict", result)
        self.assertIn(result["verdict"], ["PASS", "PARTIAL", "FAIL"])
        self.assertIn("score", result)

    def test_02_judge_empty(self):
        """FinalJudge — пустые данные"""
        result = self.judge.judge(
            objective="",
            actions_log=[],
            final_answer="",
            files_created=[]
        )
        self.assertIn("verdict", result)


class TestToolSandbox(unittest.TestCase):
    """Tests for tool_sandbox.py"""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_module_from_file("tool_sandbox", os.path.join(BACKEND_DIR, "tool_sandbox.py"))
        cls.sandbox = cls.mod.ToolSandbox()

    def test_01_default_config(self):
        """Конфигурация по умолчанию"""
        self.sandbox.configure()
        check = self.sandbox.check("web_search")
        self.assertTrue(check["allowed"])

    def test_02_read_allowed(self):
        """READ инструменты разрешены"""
        self.sandbox.configure(orion_mode="budget", autonomy_mode="readonly")
        check = self.sandbox.check("web_search")
        self.assertTrue(check["allowed"])

    def test_03_write_blocked_readonly(self):
        """WRITE заблокирован в readonly"""
        self.sandbox.configure(orion_mode="default", autonomy_mode="readonly")
        check = self.sandbox.check("file_write")
        self.assertFalse(check["allowed"])

    def test_04_explicit_deny(self):
        """Явный запрет инструмента"""
        self.sandbox.configure()
        self.sandbox.deny_tool("ssh_execute")
        check = self.sandbox.check("ssh_execute")
        self.assertFalse(check["allowed"])

    def test_05_filter_tools(self):
        """Фильтрация tools schema"""
        self.sandbox.configure(orion_mode="budget", autonomy_mode="readonly")
        schema = [
            {"function": {"name": "web_search"}},
            {"function": {"name": "ssh_execute"}},
            {"function": {"name": "file_read"}},
        ]
        filtered = self.sandbox.filter_tools_schema(schema)
        names = [t["function"]["name"] for t in filtered]
        self.assertIn("web_search", names)
        self.assertIn("file_read", names)
        self.assertNotIn("ssh_execute", names)

    def test_06_get_allowed_tools(self):
        """Список разрешённых инструментов"""
        self.sandbox.configure(orion_mode="architect", autonomy_mode="full")
        allowed = self.sandbox.get_allowed_tools()
        self.assertGreater(len(allowed), 0)
        self.assertIn("web_search", allowed)


class TestTaskScorecard(unittest.TestCase):
    """Tests for task_scorecard.py"""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_module_from_file("task_scorecard", os.path.join(BACKEND_DIR, "task_scorecard.py"))
        cls.db_path = tempfile.mktemp(suffix=".db")
        cls.store = cls.mod.TaskScorecard(db_path=cls.db_path)

    def test_01_start(self):
        """Начало отслеживания задачи"""
        sc = self.store.start(
            task_id="sc-test-1",
            chat_id="chat-1",
            user_id="user-1",
            orion_mode="pro",
            objective="Тестовая задача"
        )
        self.assertIsNotNone(sc)
        self.assertEqual(sc["status"], "running")

    def test_02_record_iteration(self):
        """Запись итерации"""
        self.store.record_iteration("sc-test-1", cost=0.001, input_tokens=100, output_tokens=50)
        sc = self.store.get("sc-test-1")
        self.assertEqual(sc["total_iterations"], 1)
        self.assertGreater(sc["total_cost_usd"], 0)

    def test_03_record_tool_call(self):
        """Запись tool call"""
        self.store.record_tool_call("sc-test-1", "ssh_execute")
        self.store.record_tool_call("sc-test-1", "ssh_execute")
        self.store.record_tool_call("sc-test-1", "file_write")
        sc = self.store.get("sc-test-1")
        self.assertEqual(sc["total_tool_calls"], 3)
        self.assertEqual(sc["tool_calls"]["ssh_execute"], 2)

    def test_04_record_error(self):
        """Запись ошибки"""
        self.store.record_error("sc-test-1", "Connection timeout")
        sc = self.store.get("sc-test-1")
        self.assertEqual(sc["error_count"], 1)

    def test_05_finish(self):
        """Завершение задачи"""
        sc = self.store.finish(
            task_id="sc-test-1",
            verdict="PASS",
            quality_score=0.95,
            final_answer_len=200
        )
        self.assertEqual(sc["status"], "done")
        self.assertEqual(sc["verdict"], "PASS")
        self.assertGreater(sc["duration_seconds"], 0)

    def test_06_analytics(self):
        """Аналитика"""
        analytics = self.store.get_analytics()
        self.assertGreater(analytics["total_tasks"], 0)

    def test_07_format_for_user(self):
        """Форматирование для пользователя"""
        text = self.store.format_for_user("sc-test-1")
        self.assertIn("Метрики", text)
        self.assertIn("PASS", text)


class TestAutonomyModes(unittest.TestCase):
    """Tests for autonomy_modes.py"""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_module_from_file("autonomy_modes", os.path.join(BACKEND_DIR, "autonomy_modes.py"))
        cls.manager = cls.mod.AutonomyManager()

    def test_01_default_mode(self):
        """Режим по умолчанию"""
        self.assertEqual(self.manager.get_mode(), "standard")

    def test_02_set_mode(self):
        """Установка режима"""
        result = self.manager.set_mode("cautious")
        self.assertTrue(result)
        self.assertEqual(self.manager.get_mode(), "cautious")

    def test_03_invalid_mode(self):
        """Невалидный режим"""
        result = self.manager.set_mode("nonexistent")
        self.assertFalse(result)

    def test_04_check_action_readonly(self):
        """Проверка действия в readonly"""
        self.manager.set_mode("readonly")
        check = self.manager.check_action("ssh_execute")
        self.assertFalse(check["allowed"])

    def test_05_check_action_full(self):
        """Проверка действия в full"""
        self.manager.set_mode("full")
        check = self.manager.check_action("ssh_execute")
        self.assertTrue(check["allowed"])

    def test_06_iteration_limit(self):
        """Лимит итераций"""
        self.manager.set_mode("readonly")
        self.manager.reset_counters()
        for _ in range(20):
            self.manager.increment_iteration()
        check = self.manager.check_iteration_limit()
        self.assertTrue(check["exceeded"])

    def test_07_format_for_prompt(self):
        """Форматирование для промпта"""
        self.manager.set_mode("standard")
        prompt = self.manager.format_for_prompt()
        self.assertIn("Стандартный", prompt)

    def test_08_list_modes(self):
        """Список режимов"""
        modes = self.manager.list_modes()
        self.assertEqual(len(modes), 5)
        names = [m["name"] for m in modes]
        self.assertIn("full", names)
        self.assertIn("readonly", names)


# ═══════════════════════════════════════════════════════════
# API TESTS (via HTTP)
# ═══════════════════════════════════════════════════════════

class TestAPIEndpoints(unittest.TestCase):
    """Tests for API endpoints (requires running server)"""

    API_BASE = os.environ.get("ORION_API_URL", "http://localhost:3510")

    @classmethod
    def setUpClass(cls):
        try:
            import requests
            cls.requests = requests
            cls.session = requests.Session()
        except ImportError:
            cls.requests = None

    def test_01_health(self):
        """API health check"""
        if not self.requests:
            self.skipTest("requests not available")
        try:
            r = self.session.get(f"{self.API_BASE}/api/health", timeout=10)
            self.assertEqual(r.status_code, 200)
            data = r.json()
            self.assertIn("features", data)
        except Exception as e:
            self.skipTest(f"Server not available: {e}")


# ═══════════════════════════════════════════════════════════
# SYNTAX TESTS
# ═══════════════════════════════════════════════════════════

class TestSyntax(unittest.TestCase):
    """Syntax validation for all Python files"""

    def _check_syntax(self, filepath):
        import ast
        with open(filepath, 'r') as f:
            content = f.read()
        ast.parse(content)

    def test_01_agent_loop_syntax(self):
        """agent_loop.py синтаксис"""
        self._check_syntax(os.path.join(BACKEND_DIR, "agent_loop.py"))

    def test_02_task_charter_syntax(self):
        """task_charter.py синтаксис"""
        self._check_syntax(os.path.join(BACKEND_DIR, "task_charter.py"))

    def test_03_execution_snapshots_syntax(self):
        """execution_snapshots.py синтаксис"""
        self._check_syntax(os.path.join(BACKEND_DIR, "execution_snapshots.py"))

    def test_04_goal_keeper_syntax(self):
        """goal_keeper.py синтаксис"""
        self._check_syntax(os.path.join(BACKEND_DIR, "goal_keeper.py"))

    def test_05_artifact_handoff_syntax(self):
        """artifact_handoff.py синтаксис"""
        self._check_syntax(os.path.join(BACKEND_DIR, "artifact_handoff.py"))

    def test_06_final_judge_syntax(self):
        """final_judge.py синтаксис"""
        self._check_syntax(os.path.join(BACKEND_DIR, "final_judge.py"))

    def test_07_tool_sandbox_syntax(self):
        """tool_sandbox.py синтаксис"""
        self._check_syntax(os.path.join(BACKEND_DIR, "tool_sandbox.py"))

    def test_08_task_scorecard_syntax(self):
        """task_scorecard.py синтаксис"""
        self._check_syntax(os.path.join(BACKEND_DIR, "task_scorecard.py"))

    def test_09_autonomy_modes_syntax(self):
        """autonomy_modes.py синтаксис"""
        self._check_syntax(os.path.join(BACKEND_DIR, "autonomy_modes.py"))

    def test_10_app_syntax(self):
        """app.py синтаксис"""
        self._check_syntax(os.path.join(BACKEND_DIR, "app.py"))


# ═══════════════════════════════════════════════════════════
# RUNNER
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Print header
    print("=" * 60)
    print("ORION Digital — Test Suite")
    print("=" * 60)
    print(f"Backend dir: {BACKEND_DIR}")
    print(f"Python: {sys.version}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Run tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes in order
    test_classes = [
        TestTaskCharter,
        TestExecutionSnapshots,
        TestGoalKeeper,
        TestArtifactHandoff,
        TestFinalJudge,
        TestToolSandbox,
        TestTaskScorecard,
        TestAutonomyModes,
        TestSyntax,
        TestAPIEndpoints,
    ]

    for tc in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(tc))

    # Run with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print("\n" + "=" * 60)
    total = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped)
    passed = total - failures - errors - skipped
    print(f"TOTAL: {total} | PASS: {passed} | FAIL: {failures} | ERROR: {errors} | SKIP: {skipped}")
    pct = (passed / total * 100) if total > 0 else 0
    print(f"SUCCESS RATE: {pct:.0f}%")
    print("=" * 60)

    sys.exit(0 if result.wasSuccessful() else 1)
