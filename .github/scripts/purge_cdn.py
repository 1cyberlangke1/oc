# -*- coding: utf-8 -*-
"""
GitHub Actions jsDelivr CDN 自动刷新脚本
"""
import os
import subprocess
import urllib.request
import urllib.parse
import json

def get_changed_files():
    # 尝试获取最近一次提交修改的文件
    try:
        diff_output = subprocess.check_output(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
            text=True,
            encoding="utf-8"
        )
        files = [line.strip() for line in diff_output.strip().splitlines() if line.strip()]
        if files:
            return files
    except Exception as e:
        print(f"⚠️ git diff HEAD~1 失败 ({e})，尝试列出所有 character 资产...")

    # 如果无法 git diff（例如首次运行或单一提交），列出 character 目录下的所有文件
    all_files = []
    for root, _, filenames in os.walk("character"):
        for fn in filenames:
            rel_p = os.path.relpath(os.path.join(root, fn), ".").replace("\\", "/")
            all_files.append(rel_p)
    return all_files

def main():
    repo = os.environ.get("GITHUB_REPOSITORY", "1cyberlangke1/oc")
    ref = os.environ.get("GITHUB_REF_NAME", "master")

    print("=" * 65)
    print(f"🚀 开始执行 jsDelivr CDN 自动刷新 | 仓库: {repo} | 分支: {ref}")
    print("=" * 65)

    changed_files = get_changed_files()
    if "" not in changed_files:
        changed_files.insert(0, "")

    print(f"📦 待刷新目标路径总数: {len(changed_files)}")

    success_count = 0
    for f in changed_files:
        encoded_path = urllib.parse.quote(f)
        url = f"https://purge.jsdelivr.net/gh/{repo}@{ref}/{encoded_path}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (GitHub-Actions-Purge)"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                status = data.get("status", "ok")
                disp_name = f if f else "[ROOT / 根目录]"
                print(f"✅ CDN 刷新成功: {disp_name} -> {status}")
                success_count += 1
        except Exception as err:
            print(f"⚠️ CDN 刷新异常: {f} -> {err}")

    print("=" * 65)
    print(f"🎉 CDN 自动刷新流程执行完毕！成功刷新: {success_count}/{len(changed_files)}")
    print("=" * 65)

if __name__ == "__main__":
    main()
