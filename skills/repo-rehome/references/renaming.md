# Renaming a project as it moves

A rehome usually comes with a rename, and the rename is where the avoidable mistakes live.
The trap is assuming one name. There are three layers, they drift apart, and they have very
different costs to change.

## The three layers

**The displayed name** — what a user reads: the page `<title>`, a header, a CLI `--help`
banner, a README H1, an API's own `title`, a slide's kicker, the text of a generated
document. Cheap to change, and the only layer that has to be right on day one.

**The identifier name** — the package directory, the import path, the env-var prefix, a
cookie name, a custom header, a console-script entry point, a broker or client name, a
service account. Expensive, because changing it means every deployed config, every
`.env`, every integration and every test that asserts on it moves at the same time.

**The repository name** — what GitHub calls it. Independent of both, and often the only one
you were told about.

**These do not have to match, and a half-finished rename is worse than an honest split.**
Shipping the displayed name as the new one while the package keeps the old one is a coherent
state you can explain in one line of the README. A rename that is half-applied across the
identifier layer is a state nobody can reason about, and it breaks deployments.

So: rename the displayed layer now, record the identifier layer as a tracked follow-up with
its real blast radius, and say in the README that they differ.

## Find the displayed layer, not the repo's name

The sharpest trap in the whole procedure: **grepping for the repository's name may find
nothing a user ever sees.** In the move this came from, the repo was called one thing, the
package another, and the screen said a third — a product name that appeared nowhere in the
repo name and would never have surfaced by searching for it. A rename pass that greps for
the repo name concludes, wrongly, that there is nothing to do.

Work from the surfaces instead:

```bash
# the page a browser loads, and its metadata
grep -rn '<title>\|og:title\|apple-mobile-web-app-title' --include=*.html .
# the server's own name for itself
grep -rn 'FastAPI(\|Flask(\|app.name\|APP_NAME\|prog=' --include=*.py .
# headers, banners, first lines
head -3 README.md ; grep -rn 'argparse.*description=\|usage:' --include=*.py .
```

Then read the front end for literal strings in headings, nav bars, empty states and sign-in
cards. Expect **no shared constant**: the same displayed name is usually several independent
literals that nothing makes move together. Count them, change all of them, and if a test
asserts on one of them, change it in the same commit — that assertion is the only mechanical
guard against a half-done rename.

Worth checking explicitly, because each one is a surface people forget: an outbound HTTP
`User-Agent` (how the project identifies itself to third parties), a client name registered
with a broker or scheduler (it shows up in *their* logs), and generated documents or slides.

## Do not rename a description of a running system

Deployment notes and runbooks cite real paths, real service names, real directories:
`widget-backend.service`, `/etc/widget/`, `/srv/widget/www`, `/home/svc/widget-old`. Those
are *observations about a machine*, and editing the document does not rename the unit. A
tidy-up pass that "fixes" them produces a runbook that is confidently wrong and will mislead
the next deploy.

Leave them, and add one line saying the name changed and the paths did not. If the paths
should change too, that is a server-side operation first and a documentation edit second.

The same logic covers literal commands in documentation and on slides: if the package is
still `widget_core`, then `python -m widget_core` is the command, and renaming it on the
slide makes the slide lie.

## Historical references are fine; live ones are not

Plan docs, changelogs, backlog entries and commit messages that say "this used to be called
X" are records. Leaving them is correct — rewriting history to pretend the old name never
existed makes the record useless. The line to hold is: anything *printed to a user* says the
new name; anything *describing the past* keeps the old one.

Note that this exemption covers names only. Account identifiers, host addresses and personal
paths in those same documents are a different question, and a move to a more public home is
the moment to settle it — see the `repo-sensitive-scan` skill.

## A checklist that survives the move

- Every displayed surface says the new name, counted and listed.
- The test that asserts on a displayed heading is updated in the same commit.
- The README's first line explains any deliberate mismatch between layers.
- The identifier rename is a tracked item with its occurrence count and its coupling (which
  deployed config, which asserting test).
- Live paths and service names in runbooks are untouched, with one line saying why.
- A generated artifact that embeds the name — a slide deck, a PDF, a built bundle — is
  regenerated from its source, not edited. Check the artifact afterwards: it is the one place
  a stale name survives a successful-looking rename.
