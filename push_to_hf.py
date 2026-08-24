#!/usr/bin/env python3
"""
push_to_hf.py -- upload the derived corpus artifacts to a HuggingFace dataset
repo using a token, without the CLI.

These files are large (16GB HotpotQA, 27GB MS-MARCO) and fully derivable from
public BeIR corpora, so publishing them is a convenience for reviewers rather
than a correctness requirement; ARTIFACT_MANIFEST.json already lets anyone
verify a local rebuild. Upload only if storage and bandwidth allow.

Token: create at https://huggingface.co/settings/tokens with WRITE scope, then
either export HF_TOKEN or place it in .env as HF_TOKEN=hf_xxx. The token is
never printed and never passed on the command line.

Usage
    python3 push_to_hf.py --list                # show what would upload
    python3 push_to_hf.py --dry-run             # verify auth and paths only
    python3 push_to_hf.py --only hotpotqa       # one corpus
    python3 push_to_hf.py                       # everything present

Uploads resume if interrupted: huggingface_hub chunks large files and skips
already-transferred parts, so re-running after a dropped connection is safe.
"""
from __future__ import annotations
import argparse, os, sys, time
from pathlib import Path

REPO_ID   = "rpaut03l/trishieldrag-nq-mpnet-embeddings"
REPO_TYPE = "dataset"

# local path -> path inside the dataset repo
ARTIFACTS = {
    "nq": [
        ("embeddings/nq_embeddings.npy",             "nq/embeddings.npy"),
        ("embeddings/nq_embeddings.meta.json",       "nq/meta.json"),
        ("ragshield_2m.index",                       "nq/faiss_ivf.index"),
    ],
    "hotpotqa": [
        ("embeddings/hotpotqa_embeddings.npy",       "hotpotqa/embeddings.npy"),
        ("embeddings/hotpotqa_embeddings.meta.json", "hotpotqa/meta.json"),
        ("hotpotqa.index",                           "hotpotqa/faiss_ivf.index"),
    ],
    "msmarco": [
        ("embeddings/msmarco_embeddings.npy",        "msmarco/embeddings.npy"),
        ("embeddings/msmarco_embeddings.meta.json",  "msmarco/meta.json"),
        ("msmarco.index",                            "msmarco/faiss_ivf.index"),
    ],
    "metadata": [
        ("ARTIFACT_MANIFEST.json",                   "ARTIFACT_MANIFEST.json"),
    ],
}


def human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}"
        n /= 1024


def get_token() -> str:
    tok = os.getenv("HF_TOKEN")
    if not tok:
        try:
            from dotenv import load_dotenv
            load_dotenv()
            tok = os.getenv("HF_TOKEN")
        except ImportError:
            pass
    if not tok:
        sys.exit("HF_TOKEN not set. Create a WRITE token at\n"
                 "  https://huggingface.co/settings/tokens\n"
                 "then:  export HF_TOKEN=hf_xxx   (or add HF_TOKEN=hf_xxx to .env)")
    if not tok.startswith("hf_"):
        sys.exit("HF_TOKEN does not look like a HuggingFace token (expected hf_...)")
    return tok


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=REPO_ID)
    ap.add_argument("--only", choices=sorted(ARTIFACTS), action="append",
                    help="upload only these groups; repeatable")
    ap.add_argument("--list", action="store_true", help="show plan and exit")
    ap.add_argument("--dry-run", action="store_true",
                    help="check auth and file presence, upload nothing")
    ap.add_argument("--skip-existing", action="store_true",
                    help="skip files already present in the repo at the same size")
    args = ap.parse_args()

    groups = args.only or list(ARTIFACTS)
    plan, missing, total = [], [], 0
    for g in groups:
        for local, remote in ARTIFACTS[g]:
            p = Path(local)
            if p.exists():
                plan.append((p, remote, p.stat().st_size))
                total += p.stat().st_size
            else:
                missing.append(local)

    print(f"repo    : {args.repo}  ({REPO_TYPE})")
    print(f"groups  : {', '.join(groups)}")
    print(f"planned : {len(plan)} file(s), {human(total)}\n")
    for p, remote, size in plan:
        print(f"  {str(p):46} -> {remote:34} {human(size):>10}")
    if missing:
        print("\n  not present locally, will be skipped:")
        for m in missing:
            print(f"    {m}")
    if args.list:
        return
    if not plan:
        sys.exit("\nNothing to upload.")

    token = get_token()
    try:
        from huggingface_hub import HfApi
    except ImportError:
        sys.exit("huggingface_hub not installed:  pip install -U huggingface_hub")

    api = HfApi(token=token)
    try:
        who = api.whoami()
        print(f"\nauthenticated as: {who.get('name', '?')}")
    except Exception as e:
        sys.exit(f"\nauthentication failed: {e}")

    try:
        api.create_repo(args.repo, repo_type=REPO_TYPE, exist_ok=True)
        print(f"repo ready: https://huggingface.co/datasets/{args.repo}")
    except Exception as e:
        sys.exit(f"could not access or create repo: {e}")

    if args.skip_existing:
        try:
            info = api.repo_info(args.repo, repo_type=REPO_TYPE, files_metadata=True)
            remote = {sib.rfilename: sib.size for sib in info.siblings}
        except Exception as e:
            print(f"could not list remote files ({e}); uploading everything")
            remote = {}
        kept = []
        for p_, r_, sz in plan:
            if remote.get(r_) == sz:
                print(f"  already present, skipping: {r_} ({human(sz)})")
            else:
                kept.append((p_, r_, sz))
        skipped = len(plan) - len(kept)
        plan, total = kept, sum(x[2] for x in kept)
        if skipped:
            print(f"\nskipping {skipped} file(s); {len(plan)} to upload, {human(total)}")
        if not plan:
            print("\nEverything already uploaded. Nothing to do.")
            return

    if args.dry_run:
        print("\n[dry run] auth and paths verified; nothing uploaded.")
        return

    print(f"\nuploading {human(total)}. Large files are chunked and resumable,")
    print("so re-running after an interruption skips completed parts.\n")

    done = 0
    for p, remote, size in plan:
        print(f"-> {remote}  ({human(size)})", flush=True)
        t0 = time.time()
        try:
            api.upload_file(
                path_or_fileobj=str(p),
                path_in_repo=remote,
                repo_id=args.repo,
                repo_type=REPO_TYPE,
                commit_message=f"Add {remote}",
            )
        except Exception as e:
            print(f"   FAILED: {e}\n   (re-run to resume)", flush=True)
            continue
        dt = time.time() - t0
        done += size
        rate = size / dt / 2**20 if dt else 0
        print(f"   done in {dt/60:.1f} min ({rate:.1f} MB/s), "
              f"{human(done)}/{human(total)} complete\n", flush=True)

    print(f"finished. https://huggingface.co/datasets/{args.repo}")


if __name__ == "__main__":
    main()
