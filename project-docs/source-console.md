# Source Console

BMTNews exposes a lightweight source console at
[`https://bmt.news/sources/`](https://bmt.news/sources/). It is a static
GitHub Pages view of the production source configuration on `main`.

The console intentionally has no database, custom authentication, or
long-running service:

- reads `data/config.github.json` directly from `main`;
- lists source type, editorial track, category, and effective status;
- filters and searches the current source registry;
- prepares add, edit, pause, resume, and remove requests;
- sends every write request through a GitHub Issue and Pull Request.

The browser never stores a GitHub token and never writes production
configuration directly.

## Supported changes

The console can add, edit, pause, resume, and remove these collection entries:

- public RSS feeds;
- public Telegram channels;
- GitHub repository release feeds;
- Reddit subreddits.

Singleton collectors such as Hacker News, Google News, GDELT, and OSS Insight
can be paused or resumed. Their query-specific settings still require a normal
code change because those structures contain collector-specific fields.

New or updated RSS URLs must use a public HTTP(S) endpoint. Requests containing
environment placeholders, credentials, loopback addresses, private network
addresses, or non-public DNS results are rejected.

## Approval workflow

1. Open the source console and choose an action.
2. Review the prefilled `信息源变更` Issue Form, select the confirmation
   checkbox, and create the issue.
3. A repository maintainer reviews the request and adds the
   `source-approved` label.
4. `.github/workflows/source-change.yml` verifies the approving actor has
   `write`, `maintain`, or `admin` permission.
5. The workflow validates the issue fields, public endpoint, and complete
   Pydantic production configuration.
6. A new `agent/source-issue-<number>` branch is created with only
   `data/config.github.json` changed.
7. The workflow opens a Draft PR when repository Action permissions allow it.
   Otherwise, it comments a ready-to-use compare link on the issue.
8. Normal tests and analysis checks must pass before a maintainer merges the
   PR into `main`.

Adding `source-approved` is the approval action. If a request changes before
approval, review the new contents before adding the label. If its task branch
has already been created, continue changes through that PR or close the request
and open a new one; the workflow will not overwrite an existing task branch.

## Required labels

The repository uses two labels:

| Label | Purpose |
|-------|---------|
| `source-change` | Identifies source-console requests |
| `source-approved` | Authorizes the validation and branch workflow |

The Issue Form applies `source-change` automatically. Only collaborators with
write access should add `source-approved`; the workflow independently checks
that permission before changing anything.

## Operational boundaries

- Do not put API keys, cookies, private feeds, internal URLs, `.env` content,
  or production state in a request.
- Do not manually edit `gh-pages`; the existing GitHub Actions deployment path
  publishes the console.
- The console reflects `main`, so a merged configuration change appears after
  the raw file and Pages deployment caches refresh.
- A source change affects collection only after its PR is merged.
