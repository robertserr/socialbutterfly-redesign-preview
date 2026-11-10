# Site copy

`site.json` is the source for all of the editable wording on the site. A build script turns it into `index.html`.

Meghan can edit this file through Pages CMS (see the setup notes in the project report) without using GitHub. After she saves, GitHub Actions rebuilds the preview. A separate manual workflow can later upload the built site to SiteGround.

Do not edit `index.html` by hand if you also use this content file — your changes would be overwritten on the next build.
