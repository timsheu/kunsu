"""
test_registry.py — skills/kunsu-dashboard/app/registry.py 的單元測試

覆蓋計畫 U1 的 6 個 test scenarios 與 Verification 描述的五種情境：
  - happy path：合法 registry，全部路徑存在且為有效 git repo
  - edge case：registry 檔案不存在
  - edge case：registry JSON 格式損壞
  - edge case：registry 為合法空物件 {}
  - error path：登記路徑存在但不是 git repo
  - error path：登記路徑完全不存在
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

from app.registry import RegistryResult, load_registry


# ── 輔助函式 ────────────────────────────────────────────────────────────────────

def make_git_repo(path: Path) -> Path:
    """建立最小有效 git repo（git init），回傳其根路徑。"""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "init", str(path)],
        check=True,
        capture_output=True,
    )
    return path


def write_registry(registry_file: Path, data: dict) -> None:
    """將 dict 序列化為 JSON 並寫入 registry 檔案。"""
    registry_file.write_text(json.dumps(data), encoding="utf-8")


# ── Happy path ──────────────────────────────────────────────────────────────────

class TestHappyPath:
    """Scenario 1：合法 registry，全部路徑存在且為有效 git repo。"""

    def test_all_healthy(self, tmp_path):
        """全部登記路徑健康 → 全數進 healthy，stale 為空，registry_error 為 None。"""
        kunsu_path = make_git_repo(tmp_path / "my-kunsu")
        sub_path = make_git_repo(tmp_path / "my-subrepo")

        registry_file = tmp_path / "registry.json"
        write_registry(registry_file, {
            str(sub_path): [
                {"kunsu": str(kunsu_path), "roles": ["writer"]}
            ]
        })

        result = load_registry(registry_file)

        assert isinstance(result, RegistryResult)
        assert result.registry_error is None
        assert str(sub_path) in result.healthy
        assert str(kunsu_path) in result.healthy
        assert result.stale == []

    def test_raw_field_carries_parsed_registry_data(self, tmp_path):
        """raw 欄位帶回已解析的原始 JSON，供呼叫端做身分判斷不需重新開檔

        （code review 修正：main.py 先前會重新讀一次 registry 檔案，
        兩次獨立讀取之間存在競態；raw 欄位讓兩者共用同一次讀取結果）。
        """
        kunsu_path = make_git_repo(tmp_path / "my-kunsu")
        sub_path = make_git_repo(tmp_path / "my-subrepo")
        data = {str(sub_path): [{"kunsu": str(kunsu_path), "roles": ["writer"]}]}

        registry_file = tmp_path / "registry.json"
        write_registry(registry_file, data)

        result = load_registry(registry_file)

        assert result.raw == data

    def test_multiple_subrepos_same_kunsu(self, tmp_path):
        """多個子專案對應同一軍師 → 子專案路徑與軍師路徑皆進 healthy（軍師不重複計算）。"""
        kunsu_path = make_git_repo(tmp_path / "kunsu")
        sub1 = make_git_repo(tmp_path / "sub1")
        sub2 = make_git_repo(tmp_path / "sub2")

        registry_file = tmp_path / "registry.json"
        write_registry(registry_file, {
            str(sub1): [{"kunsu": str(kunsu_path), "roles": ["editor"]}],
            str(sub2): [{"kunsu": str(kunsu_path), "roles": ["reviewer"]}],
        })

        result = load_registry(registry_file)

        assert result.registry_error is None
        assert str(kunsu_path) in result.healthy
        assert str(sub1) in result.healthy
        assert str(sub2) in result.healthy
        assert result.stale == []


# ── Edge cases ──────────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Scenarios 2–4：registry 本身的邊界情境。"""

    def test_registry_file_not_found(self, tmp_path):
        """Scenario 2：registry 檔案不存在 → registry_error 回傳，不拋例外。"""
        missing = tmp_path / "nonexistent-registry.json"

        result = load_registry(missing)

        assert result.registry_error is not None
        # 錯誤訊息應含「not found」提示或路徑
        error_lower = result.registry_error.lower()
        assert "not found" in error_lower or str(missing) in result.registry_error
        assert result.healthy == []
        assert result.stale == []

    def test_corrupt_json(self, tmp_path):
        """Scenario 3：JSON 格式損壞 → registry_error 回傳，訊息與「檔案不存在」不同。"""
        registry_file = tmp_path / "registry.json"
        registry_file.write_text("{this is not valid json!!", encoding="utf-8")

        result = load_registry(registry_file)

        assert result.registry_error is not None
        # 錯誤訊息應含「malformed」或「invalid」提示
        error_lower = result.registry_error.lower()
        assert "malformed" in error_lower or "invalid" in error_lower

        # 確認與「檔案不存在」情境的 registry_error 訊息不同
        missing_result = load_registry(tmp_path / "nonexistent.json")
        assert result.registry_error != missing_result.registry_error

        assert result.healthy == []
        assert result.stale == []

    def test_unreadable_file_returns_error_not_exception(self, tmp_path):
        """Regression（code review C7）：檔案存在但無讀取權限 → registry_error
        回傳，不得讓 PermissionError／OSError 穿透拋出。

        os.path.exists() 對權限不足的檔案仍回傳 True（只需要上層目錄的
        執行權限），所以真正的防護必須在 open() 的例外處理上。
        """
        registry_file = tmp_path / "registry.json"
        write_registry(registry_file, {})
        os.chmod(registry_file, 0o000)
        try:
            result = load_registry(registry_file)
        finally:
            os.chmod(registry_file, 0o644)  # 讓 pytest 的暫存目錄清理不失敗

        assert result.registry_error is not None
        assert result.healthy == []
        assert result.stale == []

    def test_empty_registry_object(self, tmp_path):
        """Scenario 4：registry 為合法空物件 {} → healthy 與 stale 皆空，registry_error 為 None。"""
        registry_file = tmp_path / "registry.json"
        write_registry(registry_file, {})

        result = load_registry(registry_file)

        assert result.registry_error is None
        assert result.healthy == []
        assert result.stale == []


# ── Error paths ─────────────────────────────────────────────────────────────────

class TestErrorPaths:
    """Scenarios 5–6：登記路徑自身的健康檢查失敗。"""

    def test_path_exists_but_not_git_repo(self, tmp_path):
        """Scenario 5：路徑存在但不是 git repo → 標記 stale，不拋例外。"""
        non_git_dir = tmp_path / "not-a-git-repo"
        non_git_dir.mkdir()
        kunsu_path = make_git_repo(tmp_path / "my-kunsu")

        registry_file = tmp_path / "registry.json"
        write_registry(registry_file, {
            str(non_git_dir): [
                {"kunsu": str(kunsu_path), "roles": ["editor"]}
            ]
        })

        result = load_registry(registry_file)

        assert result.registry_error is None
        assert str(non_git_dir) in result.stale
        # 軍師路徑仍正常 → 應在 healthy
        assert str(kunsu_path) in result.healthy
        # non_git_dir 不應出現在 healthy
        assert str(non_git_dir) not in result.healthy

    def test_subdirectory_of_repo_is_stale_not_root(self, tmp_path):
        """Regression（code review C6）：登記路徑是 git repo 的子目錄而非根目錄

        → 標記 stale，不得誤判為 healthy。`git rev-parse --show-toplevel`
        對 repo 內任何子目錄都會 exit 0，若只看 exit code 不比對輸出路徑，
        會與既有 scan-*.sh 腳本的根目錄檢查不一致（腳本會拒絕執行）。
        """
        kunsu_path = make_git_repo(tmp_path / "my-kunsu")
        subdir = kunsu_path / "not-the-root"
        subdir.mkdir()

        registry_file = tmp_path / "registry.json"
        write_registry(registry_file, {
            str(tmp_path / "irrelevant-sub"): [
                {"kunsu": str(subdir), "roles": ["writer"]}
            ]
        })

        result = load_registry(registry_file)

        assert result.registry_error is None
        assert str(subdir) in result.stale
        assert str(subdir) not in result.healthy

    def test_path_does_not_exist(self, tmp_path):
        """Scenario 6：登記路徑完全不存在 → 標記 stale，不拋例外。"""
        kunsu_path = make_git_repo(tmp_path / "my-kunsu")
        ghost_sub = tmp_path / "ghost-subrepo"  # 刻意不建立此目錄

        registry_file = tmp_path / "registry.json"
        write_registry(registry_file, {
            str(ghost_sub): [
                {"kunsu": str(kunsu_path), "roles": ["planner"]}
            ]
        })

        result = load_registry(registry_file)

        assert result.registry_error is None
        assert str(ghost_sub) in result.stale
        assert str(kunsu_path) in result.healthy
        assert str(ghost_sub) not in result.healthy

    def test_all_stale(self, tmp_path):
        """補充：所有路徑皆 stale（無軍師與子專案存在）→ healthy 為空，stale 含全部路徑。"""
        ghost_kunsu = tmp_path / "ghost-kunsu"
        ghost_sub = tmp_path / "ghost-sub"

        registry_file = tmp_path / "registry.json"
        write_registry(registry_file, {
            str(ghost_sub): [
                {"kunsu": str(ghost_kunsu), "roles": ["writer"]}
            ]
        })

        result = load_registry(registry_file)

        assert result.registry_error is None
        assert result.healthy == []
        assert str(ghost_kunsu) in result.stale
        assert str(ghost_sub) in result.stale

    def test_mixed_healthy_and_stale(self, tmp_path):
        """Verification 情境（含 stale 路徑）：部分路徑健康、部分 stale → 分別正確分類。"""
        kunsu_path = make_git_repo(tmp_path / "good-kunsu")
        good_sub = make_git_repo(tmp_path / "good-sub")
        stale_sub = tmp_path / "stale-sub"  # 不建立

        registry_file = tmp_path / "registry.json"
        write_registry(registry_file, {
            str(good_sub): [
                {"kunsu": str(kunsu_path), "roles": ["writer"]}
            ],
            str(stale_sub): [
                {"kunsu": str(kunsu_path), "roles": ["reviewer"]}
            ],
        })

        result = load_registry(registry_file)

        assert result.registry_error is None
        assert str(kunsu_path) in result.healthy
        assert str(good_sub) in result.healthy
        assert str(stale_sub) in result.stale
        # 確認互斥
        assert str(stale_sub) not in result.healthy
        assert str(good_sub) not in result.stale
