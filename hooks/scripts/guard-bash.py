#!/usr/bin/env python3
"""PreToolUse guard for the Bash tool.

Reads the hook JSON on stdin and denies commands that are destructive or leak secrets:
  - rm -r/-f on a variable, a glob of the root/home, or a path outside the project
  - pkill -f / killall (broad pattern kills hit other agents' processes)
  - docker system|container|volume|image|network|builder prune (host-wide cleanup)
  - git push --force / +refspec to a protected branch
  - reading .env-style secret files into output
A denial is returned as hookSpecificOutput.permissionDecision = "deny" with a reason.
Anything it cannot parse is allowed (normal permission rules still apply).
Protected branches: $GUARD_PROTECTED_BRANCHES (space-separated), default "main master develop".
"""
import json
import os
import re
import shlex
import subprocess
import sys

SECRET_FILE = re.compile(r"(^|/)\.env(\.[A-Za-z0-9_.-]+)?$|(^|/)(id_rsa|id_ed25519|id_ecdsa)$|\.pem$|\.key$")
SECRET_OK = re.compile(r"\.(example|sample|template|dist)$")
READERS = {"cat", "less", "more", "head", "tail", "grep", "egrep", "fgrep", "rg", "sed", "awk", "bat", "xxd",
           "od", "strings", "base64", "source", ".", "cut", "sort", "uniq", "nl", "tac", "jq", "yq", "diff",
           "cp", "scp", "curl", "nc", "openssl", "python", "python3", "node", "perl", "ruby", "vim", "nano", "vi"}
SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
WRAPPERS = {"sudo", "nice", "nohup", "time", "env", "command", "exec", "timeout", "ionice", "xargs", "stdbuf"}


def protected():
    return set((os.environ.get("GUARD_PROTECTED_BRANCHES") or "main master develop").split())


def segments(cmd):
    """Split a command line into simple commands (lists of words)."""
    lex = shlex.shlex(cmd, posix=True, punctuation_chars=";&|()\n")
    lex.whitespace_split = True
    lex.commenters = ""
    words, out = [], []
    for tok in lex:
        if tok and set(tok) <= set(";&|()\n"):
            if words:
                out.append(words)
            words = []
        else:
            words.append(tok)
    if words:
        out.append(words)
    return out


VALUE_OPTS = {"-n", "-u", "-g", "-s", "-k", "-I", "-P", "-L", "-c"}


def strip_wrappers(words):
    """Drop leading VAR=value assignments and wrappers such as `sudo -u x`, `nice -n 15`, `timeout 60`."""
    i = 0
    while i < len(words):
        w = words[i]
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", w):
            i += 1
            continue
        if os.path.basename(w) not in WRAPPERS:
            break
        i += 1
        while i < len(words) and (words[i].startswith("-") or re.fullmatch(r"\d+[smhd]?", words[i])):
            i += 2 if words[i] in VALUE_OPTS else 1
    return words[i:]


def inside(path, roots):
    p = os.path.realpath(os.path.expanduser(path))
    return any(p == r or p.startswith(r.rstrip("/") + "/") for r in roots)


def check_rm(args, cwd, roots):
    flags = "".join(a.lstrip("-") for a in args if a.startswith("-") and not a.startswith("--"))
    long = [a for a in args if a.startswith("--")]
    recursive = "r" in flags or "R" in flags or "--recursive" in long
    force = "f" in flags or "--force" in long
    if not (recursive or force):
        return None
    targets = [a for a in args if not a.startswith("-")]
    for t in targets:
        if "$" in t or "`" in t:
            return f"rm -{flags} on a variable path ({t}): expand it yourself and delete explicit paths"
        if t in ("/", "~", "~/", "*", "/*", "~/*", ".", "..") or t.startswith("~"):
            return f"rm -{flags} on {t}"
        full = t if os.path.isabs(t) else os.path.join(cwd, t)
        if not inside(full, roots):
            return f"rm -{flags} outside the project/workspace ({t})"
    return None


def current_branch(cwd):
    try:
        return subprocess.run(["git", "-C", cwd, "symbolic-ref", "--short", "-q", "HEAD"], capture_output=True,
                              text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def check_push(args, cwd):
    force = any(a.startswith("--force") or (re.match(r"^-[a-zA-Z]+$", a) and "f" in a) for a in args)
    refspecs = [a for a in args if not a.startswith("-")][1:]  # first positional is the remote
    chosen = refspecs if force else [r for r in refspecs if r.startswith("+")]
    if not force and not chosen:
        return None
    targets = [r.lstrip("+").split(":")[-1].replace("refs/heads/", "") for r in chosen] or ["HEAD"]
    branch = None
    hit = []
    for t in targets:
        if t in ("HEAD", ""):
            branch = branch if branch is not None else current_branch(cwd)
            t = branch
        if t in protected():
            hit.append(t)
    return f"force push to a protected branch ({', '.join(hit)})" if hit else None


def check_words(words, cwd, roots, depth=0):
    words = strip_wrappers(words)
    if not words:
        return None
    prog, args = os.path.basename(words[0]), words[1:]
    if prog in SHELLS and "-c" in args and depth < 3:
        i = args.index("-c")
        if i + 1 < len(args):
            return check_command(args[i + 1], cwd, roots, depth + 1)
    if prog == "eval" and depth < 3:
        return check_command(" ".join(args), cwd, roots, depth + 1)
    if prog == "rm":
        return check_rm(args, cwd, roots)
    if prog == "killall":
        return "killall kills by name across every session: kill only PIDs you started"
    if prog == "pkill" and any(a == "-f" or (a.startswith("-") and not a.startswith("--") and "f" in a) or a == "--full" for a in args):
        return "pkill -f matches other agents' processes: kill only PIDs you started"
    if prog in ("docker", "podman"):
        rest = [a for a in args if not a.startswith("-")]
        if "prune" in rest[:2] and (rest[0] in ("system", "container", "volume", "image", "network", "builder", "buildx") or rest[0] == "prune"):
            return f"{prog} {' '.join(rest[:2])} is host-wide cleanup: remove your own resources by name"
    if prog == "git" and args:
        sub_i = next((i for i, a in enumerate(args) if not a.startswith("-") and (i == 0 or args[i - 1] not in ("-C", "-c"))), None)
        if sub_i is not None and args[sub_i] == "push":
            return check_push(args[sub_i + 1:], cwd)
    if prog in READERS:
        for a in args:
            if SECRET_FILE.search(a) and not SECRET_OK.search(a):
                return f"reading a secrets file ({a}) would put credentials into the transcript"
    return None


def check_command(cmd, cwd, roots, depth=0):
    # redirections like `< .env` are not words of the program; catch them here
    for m in re.finditer(r"<\s*([^\s;&|<>]+)", cmd):
        if SECRET_FILE.search(m.group(1)) and not SECRET_OK.search(m.group(1)):
            return f"reading a secrets file ({m.group(1)}) would put credentials into the transcript"
    try:
        segs = segments(cmd)
    except ValueError:
        return None
    for words in segs:
        why = check_words(words, cwd, roots, depth)
        if why:
            return why
    for inner in re.findall(r"\$\(([^()]*)\)", cmd):
        why = check_command(inner, cwd, roots, depth + 1)
        if why:
            return why
    return None


def roots_for(cwd):
    roots = [os.path.realpath(cwd)]
    for k in ("CLAUDE_PROJECT_DIR", "GUARD_EXTRA_ROOTS"):
        for v in (os.environ.get(k) or "").split(":"):
            if v:
                roots.append(os.path.realpath(v))
    tmp = os.environ.get("TMPDIR") or "/tmp"
    roots.append(os.path.realpath(tmp))
    return roots


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    if data.get("tool_name") != "Bash":
        return 0
    cmd = (data.get("tool_input") or {}).get("command") or ""
    cwd = data.get("cwd") or os.getcwd()
    why = check_command(cmd, cwd, roots_for(cwd))
    if why:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                 "permissionDecisionReason": f"guard-bash: {why}"}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
