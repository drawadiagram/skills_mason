# Transfer: move the repository itself

Use when the repository should move owner — a personal repo handed to a lab or team
organisation, or a repo moving between organisations — and you want its issues, stars and
URL to travel with it. This is the strongest shape when available, because GitHub does the
work and you write no git at all.

## Can you?

Three gates, all worth checking before planning around a transfer:

- **Admin on the source.** Org-owned means org owner, or admin on that repo. An org policy
  can forbid transferring repos out; an enterprise policy can forbid it entirely.
- **Create rights at the destination.** You need to be able to make a repo in the target
  account or org. Renaming *during* the transfer additionally needs you to be an owner of the
  target org.
- **A free name.** The target cannot already hold a repo of that name, or a fork in the same
  network. A repo that is itself a fork of a *private* upstream cannot be transferred at all.

`survey_repo.py` reports the source's admin bit, whether it is a fork, and whether it is
archived. **An archived repo is read-only — unarchive it before transferring.**

## The call

There is no `gh repo transfer` verb; it is a raw API call.

```bash
gh api -X POST repos/jdoe/widget/transfer -f new_owner=octo-lab
# optional: -f new_name=widget-core   (needs ownership of the target org)
#           -F 'team_ids[]=12345'     (org destinations only)
```

It returns **202 Accepted** and continues asynchronously, so poll rather than assuming:

```bash
gh api repos/octo-lab/widget -q '"\(.full_name)  \(.visibility)  default=\(.default_branch)"'
```

**A transfer to a personal account must be accepted by the new owner.** It will sit pending
until they do, which looks like a failure if you are not expecting it. Transfers into an
organisation you can create in do not need acceptance.

## What travels

Issues, pull requests, the wiki, stars and watchers. Git history, commits and contribution
credit. Webhooks, services, secrets and deploy keys stay associated. Forks stay associated
with the repo, and if the repo is itself a fork it stays attached to its upstream. Git LFS
objects move in the background — a large LFS store takes a while.

**URL redirects**: links to the old location redirect to the new one, and `git clone`,
`git fetch` and `git push` follow the redirect. Still run
`git remote set-url origin <new-url>` in local clones; GitHub recommends it and it stops the
redirect from being load-bearing.

## What does not, and the sharp edges

**Creating anything at the old location permanently destroys the redirects.** If someone makes
a new repo or a fork at `jdoe/widget` after the transfer, every old link breaks for good. If
you want to leave a signpost at the old name, do not — leave the name empty and let the
redirect work.

**The old name may be retired for good.** If the repo contains a Marketplace action, or had
over 100 clones or over 100 Actions runs in the preceding week, the old owner/name pair is
permanently retired and cannot be reused by anyone.

**Issue assignments get rewritten, and the rule depends on direction.** Personal → personal
keeps them. Personal → org keeps assignments to org members and clears the rest. Org →
personal keeps only assignments to the new owner and **removes all issue types**. Org → org
keeps issue types only where the destination org has a matching type. If assignment or type
data matters, export it first.

**Collaborators shift.** Moving between personal accounts makes the original owner a
collaborator and keeps the others. Moving org → personal drops read-only collaborators.

**GitHub Pages does not redirect.** Git links redirect; the Pages site does not. For a private
repo with a custom domain, update DNS *before* transferring — a stale DNS record pointing at
a name you no longer control is a domain-takeover risk.

**Private repo into a Free account loses protected branches and Pages.** Packages may or may
not keep their link to the repo, depending on the registry. Sponsorship tiers granting repo
access can be affected.

**The destination org's defaults now apply** — its default repository permissions and member
privileges, not the source's.

## After

- `git remote set-url origin` in every local clone, and in any CI config, deploy script or
  documentation that hardcodes the old URL. The redirect covers git operations, not a
  hardcoded API path or a raw.githubusercontent link.
- Re-check branch protection and required checks: the destination org's rulesets may add or
  drop constraints you were relying on.
- If the point of the move was also to change the default branch or the repo name, do that
  *after* the transfer, when you hold admin at the new home.
