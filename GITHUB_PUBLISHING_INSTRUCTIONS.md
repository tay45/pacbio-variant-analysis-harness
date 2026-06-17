# GitHub Publishing Instructions

Before publishing, review `PUBLIC_RELEASE_AUDIT.txt`, `PUBLIC_PACKAGE_AUDIT.txt`, `DOCUMENTATION_LINK_AUDIT.txt`, `git status`, and `git diff --cached`. Confirm the GitHub repository is created empty, without initializing README, LICENSE, or `.gitignore` on GitHub. Verify the authenticated account is `Tay45`, and do not force-push over an existing populated repository.

```bash
git init
git branch -M main
git add .
git status
git commit -m "Initial public alpha release"
git remote add origin https://github.com/Tay45/pacbio-variant-analysis-harness.git
git push -u origin main
git tag -a v0.2.7-alpha.1 -m "Integrated germline and somatic alpha release"
git push origin v0.2.7-alpha.1
```

GitHub CLI alternative, if installed and authenticated:

```bash
gh repo create Tay45/pacbio-variant-analysis-harness --public --source=. --remote=origin --push
git tag -a v0.2.7-alpha.1 -m "Integrated germline and somatic alpha release"
git push origin v0.2.7-alpha.1
```
